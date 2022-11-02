import io
import subprocess
from typing import List

CHANGE_LOOK_BACK: List[int] = [3, 14, 56]
changed_files = [
    "Makefile",
    # "changelogs/unreleased/issue-add-predictive-test-selection-data-collector.yml",
    # "predictive_test_selection/README.md",
    # "predictive_test_selection/data_collector.py",
    # "tox.ini",
]

modification_count: List[int] = []
for n_days_ago in CHANGE_LOOK_BACK:
    acc1: int = 0
    acc2: int = 0
    for file in changed_files:
        ps = subprocess.Popen(
            ["git", "log", f"--after='{n_days_ago} days ago'", "--format=oneline", f"{file}"], stdout=subprocess.PIPE
        )
        try:
            acc1 = sum(1 for line in io.TextIOWrapper(ps.stdout, encoding="utf-8"))
            print(acc1)
            #
            # acc2 += int(subprocess.check_output(["wc", "-l"], stdin=ps.stdout))
            # print(acc2)
        finally:
            ps.stdout.close()
            ps.wait()
