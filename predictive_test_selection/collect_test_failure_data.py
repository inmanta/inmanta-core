import logging
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from enum import auto, Enum
from typing import Any, List, Mapping, Sequence, Tuple, MutableMapping

import requests

LOGGER = logging.getLogger(__name__)

# This parameter is used to configure how far in the past we look back (in days) when computing the number of modifications
# made to files involved in a specific code change. This parameter is used in the learning algorithm as well and as such it
# should not be modified in one place without modifying it in the other.
CHANGE_LOOK_BACK: List[int] = [3, 14, 56]

# Url of the influx db into which we store the collected data
INFLUX_DB_URL = "http://mon.ii.inmanta.com:8086/write?db=predictive_test_selection&precision=s"

class CommonFileExtension(Enum):
    other = auto()
    mo = auto()
    po = auto()
    pyc = auto()
    json = auto()
    dat = auto()
    pyi = auto()
    py = auto()


@dataclass
class CodeChange:
    """
        Collects all data pertaining to the code change in the currently checked out branch:
        - commit_hash -> The latest commit hash
        - modification_count -> Number of modifications made to the files involved in this change in the last 3, 14 and 56 days.
          The points in time at which we look back is configured by the CHANGE_LOOK_BACK parameter.
        - file_cardinality -> Number of files involved in this change
        - file_extension -> File extensions of the files involved in this change
    """
    commit_hash: str
    modification_count: List[int]
    file_cardinality: int
    file_extension: List[int]

    def __init__(self):
        # Get latest commit hash:
        self.commit_hash = subprocess.check_output(["git", "log", "--pretty=%H", "-1"]).strip().decode()

        # Get current branch
        cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        current_branch: str = subprocess.check_output(cmd).strip().decode()
        # TODO refactor block
        cmd = ["git", "diff", f"master...{current_branch}", "--name-only"]
        changed_files: List[str] = [line.strip() for line in subprocess.check_output(cmd).decode().split("\n") if line.strip()]

        self.file_cardinality = len(changed_files)
        self.file_extension = self._get_extension_vector(changed_files)
        self.modification_count = self._count_modifications(changed_files)

    def _count_modifications(self, changed_files: List[str]) -> List[int]:
        modification_count: List[int] = []
        for n_days_ago in CHANGE_LOOK_BACK:
            acc: int = 0
            for file in changed_files:
                ps = subprocess.Popen(
                    ["git", "log", f"--after='{n_days_ago} days ago'", "--format=oneline", f"{file}"],
                    stdout=subprocess.PIPE,
                )
                try:
                    acc += int(subprocess.check_output(["wc", "-l"], stdin=ps.stdout))
                finally:
                    ps.stdout.close()
                    ps.wait()

            modification_count.append(acc)
        return modification_count

    def _get_extension_vector(self, changed_files: List[str]) -> List[int]:
        extensions = set([os.path.splitext(file)[1].replace(".", "") for file in changed_files])

        out = [0] * len(CommonFileExtension)
        known_exts = [ext for ext in CommonFileExtension]
        for ext in extensions:
            try:
                idx = known_exts.index(CommonFileExtension[ext])
            except KeyError:
                idx = known_exts.index(CommonFileExtension["other"])
            out[idx] = 1
        return out


@dataclass
class TestResult:
    """
        Collects all data pertaining to the test cases by parsing the test result xml file (produced by
        '$ py.test --junit-xml=junit-py39.xml'):
        - test_result_data -> Maps the fully qualified test name <test_file_name>.<test_case> to an integer denoting whether
          this test failed or not.
    """
    test_result_data: MutableMapping[str, int]

    def __init__(self):
        self._parse_xml_test_results()

    def _parse_xml_test_results(self) -> None:
        self.test_result_data = {}
        path: str = "junit-py39.xml"
        tree = ET.parse(path)
        root = tree.getroot()

        for test_suite in root.findall("testsuite"):
            for test_case in test_suite.findall("testcase"):
                if test_case.find("skipped") is not None:  # test got skipped -> we don't record anything
                    continue

                test_file: str = test_case.get("classname")
                test_name: str = test_case.get("name")
                test_fqn: str = ".".join((test_file, test_name))

                test_failed: int = int(test_case.find("failure") is not None)

                self.test_result_data[test_fqn] = test_failed

        assert self.test_result_data

    def __iter__(self):
        yield from self.test_result_data.items()


class DataParser:
    """
        This class fetches all information regarding a specific code change and the tests that are run on this specific commit
        and sends it all to the influxdb database.


    """
    def __init__(self):
        self.code_change_data: CodeChange = CodeChange()
        self.test_result_data: TestResult = TestResult()

    def _create_data_payload(self) -> str:
        """
            Anatomy of each line of the payload:
            Measurement: test_result
            tag_set: fqn, commit_hash
            field_set: failed_as_int, modification_count, file_extension, file_cardinality
            timestamp: Use influx_db auto-generated timestamp
        """
        data_points: List[str] = [
            (
                f"test_result,fqn={test_fqn},commit_hash={self.code_change_data.commit_hash}"
                f" failed_as_int={failed},modification_count={self.code_change_data.modification_count},"
                f"file_extension={self.code_change_data.file_extension},"
                f"file_cardinality={self.code_change_data.file_cardinality}"
            )
            for test_fqn, failed in self.test_result_data
        ]
        return "\n".join(data_points)

    def send_influxdb_data(self, dry_run: bool = True) -> None:
        payload = self._create_data_payload()

        if not dry_run:
            r = requests.post(INFLUX_DB_URL, data=payload, timeout=10)
            r.raise_for_status()
        else:
            LOGGER.info(payload)


if __name__ == "__main__":
    data_parser = DataParser()
    data_parser.send_influxdb_data()
