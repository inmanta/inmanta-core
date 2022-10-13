import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Sequence, List, Tuple
import os
import subprocess
from datetime import datetime
from enum import IntFlag, auto
from typing import Any, List, Mapping
import requests







class CommonFileExtension(IntFlag):
    other = auto()
    mo = auto()
    po = auto()
    pyc = auto()
    json = auto()
    dat = auto()
    pyi = auto()
    py = auto()


class DataParser():
    """
        # x date text NOT NULL, => use influxdb timestamp
          test_fqn text NOT NULL, ==> GO for test case not file
        x commit_hash text NOT NULL,
        x n_changes_3 int NOT NULL,
        x n_changes_14 int NOT NULL,
        x n_changes_56 int NOT NULL,
        x file_cardinality int NOT NULL,
        x file_extension text NOT NULL,
          target_cardinality int NOT NULL,  => always 1 since at test case level and not at test file level
          failure_rate_7 real NOT NULL,
          failure_rate_14 real NOT NULL,
          failure_rate_28 real NOT NULL,
          failure_rate_56 real NOT NULL,
          test_failed int NOT NULL
    """
    def __init__(self):
        self.code_change_data: Mapping[str, Any] = {}
        self.test_result_data: Mapping[str, int] = {}

    def parse_code_change(self) -> None:
        """
            Collect all data pertaining to the code change in the currently checked out branch:
            - the commit hash
            - the number of modified files
            - the file extensions of modified files
            - the number of changes to the modified files in the past 3, 14 and 56 days
        """
        data = {
            "commit_hash": None,
            "file_cardinality": None,
            "file_extension": None,
            "n_changes":None,
        }

        # Get latest commit hash:
        data["commit_hash"] = subprocess.check_output(["git", "log", "--pretty=%H", "-1"]).strip()

        # Get current branch
        cmd = ["git", "rev-parse", "--abbrev", "-ref", "HEAD"]
        current_branch = subprocess.check_output(cmd)

        cmd = ["git", "diff", f"master...{current_branch}", "--name-only"]
        changed_files = [line for line in subprocess.check_output(cmd, env=os.environ.copy()).decode().split("\n") if line]

        data["file_cardinality"] = len(changed_files)

        def get_extension_vector() -> List[int]:
            extensions = set([os.path.splitext(file)[1].replace(".", "") for file in changed_files])
            print(extensions)

            out = [0] * 8
            known_exts = [ext for ext in CommonFileExtension]
            for ext in extensions:
                try:
                    idx = known_exts.index(CommonFileExtension[ext])
                except KeyError:
                    idx = known_exts.index(CommonFileExtension["other"])
                out[idx] = 1
            return out

        data["file_extension"] = get_extension_vector()

        def get_changes() -> List[int]:
            n_changes: List[int] = []
            for n_days_ago in [3, 14, 56]:
                acc: int = 0
                for file in changed_files:
                    ps = subprocess.Popen(
                        ["git", "log", f"--after='{n_days_ago} days ago'", "--format=oneline", f"{file}"], stdout=subprocess.PIPE
                    )
                    acc += int(subprocess.check_output(["wc", "-l"], stdin=ps.stdout))
                    ps.wait()

                n_changes.append(acc)
            return n_changes

        data["n_changes"] = get_changes()

        self.code_change_data = data

    def parse_xml_test_results(self, path: str = "junit-py39.xml") -> None:
        """
            Collect all data pertaining to the test cases by parsing the test result xml file (produced by
            '$ py.test --junit-xml=junit-py39.xml')
        """
        tree = ET.parse(path)
        root = tree.getroot()

        self.test_result_data = {}

        for test_suite in root.findall("testsuite"):
            for test_case in test_suite.findall("testcase"):
                if test_case.find("skipped") is not None:  # test got skipped -> we don't record anything
                    continue

                test_file: str = test_case.get("classname")
                test_name: str = test_case.get("name")
                test_fqn: str = ".".join((test_file, test_name))

                test_failed: int = int(test_case.find("failure") is not None)

                self.test_result_data[test_fqn] = test_failed


    def create_data_payload(self) -> str:
        # Use influx_db auto-generated timestamp
        data_points: List[str] = [
            (
                f"test_result,fqn={test_file},commit_hash={self.code_change_data['commit_hash']}"
                f" failed_as_int={failed},n_changes={self.code_change_data['n_changes']},"
                f"file_extension={self.code_change_data['file_extension']},"
                f"file_cardinality={self.code_change_data['file_cardinality']}"
            )
            for test_file, failed in self.test_result_data.items()
        ]
        return "\n".join(data_points)

    def send_influxdb_data(self) -> None:
        url = "http://mon.ii.inmanta.com:8086/write?db=predictive_test_selection&precision=s"
        r = requests.post(url, data=self.create_data_payload())

        r.raise_for_status()




if __name__ == "__main__":
    data_parser = DataParser()
    data_parser.parse_code_change()
    data_parser.parse_xml_test_results()
    data_parser.send_influxdb_data()

    # code_change_data = parse_code_change()
    # data_points = parse_xml_test_results(code_change_data)
    # send_influxdb_data(data_points)
