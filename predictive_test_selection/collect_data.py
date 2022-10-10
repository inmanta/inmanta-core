import os
import subprocess
import time
from datetime import datetime
from enum import IntFlag, auto
from typing import List, Mapping, Any
import xml.etree.ElementTree as ET

TEST_RESULTS = os.path.join(os.curdir, "out.xml")
BRANCH_NAME = "issue/add-data-collector"

class CommonFileExtension(IntFlag):
    other = auto()
    mo = auto()
    po = auto()
    pyc = auto()
    json = auto()
    dat = auto()
    pyi = auto()
    py = auto()

def collect_data() -> Mapping[str, Any]:
    """
    x date text NOT NULL,
      test_fqn text NOT NULL,
    x commit_hash text NOT NULL,
    x n_changes_3 int NOT NULL,
    x n_changes_14 int NOT NULL,
    x n_changes_56 int NOT NULL,
    x file_cardinality int NOT NULL,
    x file_extension text NOT NULL,
      target_cardinality int NOT NULL,
      failure_rate_7 real NOT NULL,
      failure_rate_14 real NOT NULL,
      failure_rate_28 real NOT NULL,
      failure_rate_56 real NOT NULL,
      minimal_distance int NOT NULL,
      test_failed int NOT NULL
    """
    data = {
        "date": None,
        "file_cardinality": None,
    }

    data["date"] = datetime.now()

    cmd = ["git", "diff", f"master...{BRANCH_NAME}", "--name-only"]
    changed_files = [line for line in subprocess.check_output(cmd, env=os.environ.copy()).decode().split("\n") if line]
    print(changed_files)

    data["file_cardinality"] = len(changed_files)

    def get_extension_vector() -> List[int]:
        extensions = set([
            os.path.splitext(file)[1].replace(".", "")
            for file in changed_files
        ])
        print(extensions)

        out = [0]*8
        known_exts = [ext for ext in CommonFileExtension]
        for ext in extensions:
            try:
                idx = known_exts.index(CommonFileExtension[ext])
            except ValueError:
                idx = known_exts.index(CommonFileExtension["other"])
            out[idx] = 1
        return out

    data["file_extension"] = get_extension_vector()

    def get_changes() -> List[int]:
        n_changes: List[int] = []
        for n_days_ago in [3, 14, 56]:
            acc: int = 0
            for file in changed_files:
                ps = subprocess.Popen(["git", "log", f"--after='{n_days_ago} days ago'", "--format=oneline", f"{file}"], stdout=subprocess.PIPE)
                acc += int(subprocess.check_output(["wc", "-l"], stdin=ps.stdout))
                ps.wait()

            n_changes.append(acc)
        return n_changes

    data["n_changes"] = get_changes()

    # Get latest commit hash:

    data["commit_hash"] = subprocess.check_output(["git", "log", "--pretty=%H", "-1"]).strip()

    # sum([git log --after="{3/14/56} days ago" --format=oneline {file} | wc -l for file in changed_files])


    return data


def send_influx_db_data(test_file: str, failed: bool, time_stamp:int):
    """
        Dummy function for now, TODO: implement sending the data to influx_db
    """
    influx_db_string = f"test_result,fqn={test_file} failed={failed} {time_stamp}"
    print(influx_db_string)



def parse_xml_test_results(path="out.xml"):
    """
        Parse an xml file as produced by '$ py.test --junit-xml=out.xml'
    """
    tree = ET.parse(path)
    root = tree.getroot()

    time_stamp = int(time.mktime(datetime.fromisoformat(root.find("testsuite").get("timestamp")).timetuple()) * 1000)

    previous_test_file = None
    previous_test_file_failure = False

    for test_suite in root.findall("testsuite"):
        for test_case in test_suite.findall("testcase"):
            test_file = test_case.get("classname")

            if previous_test_file != test_file:
                # New test file detected -> send previous data to influx_db
                if previous_test_file is not None:
                    send_influx_db_data(previous_test_file, previous_test_file_failure, time_stamp)

                previous_test_file_failure = False
                previous_test_file = test_file

            if previous_test_file_failure:
                continue

            previous_test_file_failure = test_case.find("failure") is not None

        # Make sure we write the last test file
        send_influx_db_data(previous_test_file, previous_test_file_failure, time_stamp)
