import logging
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, List, Mapping, MutableMapping, Sequence, Set, Tuple, Union

import click

import requests

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)
# This parameter is used to configure how far in the past we look back (in days) when computing the number of modifications
# made to files involved in a specific code change. This parameter is used in the learning algorithm as well and as such it
# should not be modified in one place without modifying it in the other.
CHANGE_LOOK_BACK: List[int] = [3, 14, 56]

# Currently supported dev_branches
DEV_BRANCHES = ["master", "iso5", "iso4"]

# Url of the influx db into which we store the collected data
INFLUX_DB_URL = "http://mon.ii.inmanta.com:8086/write?db=predictive_test_selection&precision=s"


class AbortDataCollection(Exception):
    """
    This exception is raised when the current data collection should be aborted.
    """

    pass


@dataclass
class CodeChange:
    """
    Collects all data pertaining to the code change in the currently checked out branch:
    Recorded attributes:
        - commit_hash -> The latest commit hash.
        - modification_count -> Number of modifications made to the files involved in this change in the last 3, 14 and 56 days.
          The points in time at which we look back is configured by the CHANGE_LOOK_BACK parameter.
        - file_cardinality -> Number of files involved in this change.
        - file_extensions -> File extensions of the files involved in this change.
        - dev_branch -> The dev branch this code change is closest to.

    Non-recorded attributes:
        - changed_files -> List of file names involved in this change.

    :raises AbortDataCollection: If this code change was created by the merge tool or if it is aligned with a dev branch
    """

    commit_hash: str = field(init=False)
    modification_count: List[int] = field(init=False)
    file_cardinality: int = field(init=False)
    file_extensions: Set[str] = field(init=False)
    dev_branch: str = field(init=False)

    changed_files: List[str] = field(init=False, repr=False)

    def parse(self):
        # Get latest commit hash:
        self.commit_hash = subprocess.check_output(["git", "log", "--pretty=%H", "-1"]).strip().decode()

        # Get current branch
        cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        current_branch: str = subprocess.check_output(cmd).strip().decode()

        if current_branch.startswith("merge-tool/"):
            raise AbortDataCollection("the code change was created by the merge tool and not by a developer.")

        self._compute_changed_files(current_branch)
        self._compute_file_extensions()
        self._count_modifications()

    def _compute_changed_files(self, current_branch: str) -> None:
        """
        Finds the development branch that is the closest to this code change and sets the relevant attributes accordingly.
        The distance metric used is the total number of files in the diff with the current branch
        """
        max_cardinality: Union[float, int] = float("inf")

        for dev_branch in DEV_BRANCHES:
            cmd = ["git", "diff", f"{dev_branch}...{current_branch}", "--name-only"]
            changed_files = [line.strip() for line in subprocess.check_output(cmd).decode().split("\n") if line.strip()]

            current_cardinality = len(changed_files)

            if current_cardinality < max_cardinality:
                max_cardinality = current_cardinality
                self.dev_branch = dev_branch
                self.changed_files = changed_files
                self.file_cardinality = current_cardinality

            if max_cardinality == 0:
                raise AbortDataCollection(f"the code change is aligned with dev branch {dev_branch}.")

    def _count_modifications(self) -> None:
        """
        Counts the number of modifications that have been made to the files involved in this change for each interval (in days)
        specified in the past CHANGE_LOOK_BACK parameter.
        """
        modification_count: List[int] = []
        for n_days_ago in CHANGE_LOOK_BACK:
            acc: int = 0
            for file in self.changed_files:
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
        self.modification_count = modification_count

    def _compute_file_extensions(self) -> None:
        """
        Computes the set of file extensions present in this code change
        """
        self.file_extensions = set([os.path.splitext(file)[1].replace(".", "") for file in self.changed_files])

    def get_modifications_data_format(self) -> str:
        """
        Converts the modification_count (List[int]) to a condensed csv format.
        e.g [1, 2, 3] becomes "1,2,3"
        """
        return ",".join((str(count) for count in self.modification_count))

    def get_file_extensions_data_format(self) -> str:
        """
        Converts the file_extensions (Set[str]) to a condensed csv format.
        e.g {'txt', 'md', 'py'} becomes 'txt,md,py'
        """
        return ",".join(self.file_extensions)


@dataclass
class TestResult:
    """
    Collects all data pertaining to the test cases by parsing the test result xml file (produced by
    '$ py.test --junit-xml=junit-py39.xml'):
    - test_result_data -> Maps the fully qualified test name <test_file_name>.<test_case> to an integer denoting whether
      this test failed or not.
    """

    test_result_data: MutableMapping[str, int] = field(init=False)

    def parse(self) -> None:
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

    def run(self, dry_run: bool):
        try:
            self.code_change_data.parse()
            self.test_result_data.parse()

            self.send_influxdb_data(dry_run)
        except AbortDataCollection as e:
            LOGGER.debug(f"Data collection was aborted because {str(e)}")

    def _create_data_payload(self) -> str:
        """
        Anatomy of each line of the payload:
        Measurement: test_result
        tag_set: commit_hash, dev_branch, fqn (Tags should be sorted by key for improved performance: https://docs.influxdata.com/influxdb/v1.8/write_protocols/line_protocol_tutorial/
        field_set: failed_as_int, modification_count, file_extensions, file_cardinality
        timestamp: Use influx_db auto-generated timestamp
        """
        data_points: List[str] = [
            (
                f"test_result,commit_hash={self.code_change_data.commit_hash},"
                f"dev_branch={self.code_change_data.dev_branch},fqn={test_fqn}"
                f' failed_as_int={failed},modification_count="{self.code_change_data.get_modifications_data_format()}",'
                f'file_extensions="{self.code_change_data.get_file_extensions_data_format()}",'
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


@click.command()
@click.option("--dry-run/--full-run", default=True, help="If Dry-run only: no data will be sent to the db.")
def main(dry_run: bool):
    data_parser = DataParser()
    data_parser.run(dry_run)


if __name__ == "__main__":
    main()
