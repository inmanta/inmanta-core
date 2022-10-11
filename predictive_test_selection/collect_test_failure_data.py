import time
import xml.etree.ElementTree as ET
from datetime import datetime

import requests


def send_influx_db_data(test_file: str, failed: bool, time_stamp: int) -> None:
    if not test_file:
        # Skipped test file have an empty test_file name
        return
    influx_db_string = f"test_result,fqn={test_file} failed={failed} {time_stamp}"
    print(influx_db_string)

    url = "http://mon.ii.inmanta.com:8086/write?db=predictive_test_selection"
    x = requests.post(url, data=influx_db_string)


def parse_xml_test_results(path="junit-py39.xml"):
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


if __name__ == "__main__":
    parse_xml_test_results()
