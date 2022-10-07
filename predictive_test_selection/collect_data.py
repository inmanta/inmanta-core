import os
import subprocess
from datetime import datetime
from enum import IntFlag, auto
from typing import List, Mapping

TEST_RESULTS = os.path.join(os.curdir, "out.xml")
BRANCH_NAME = "issue/add-data-collector"

class CommonExtension(IntFlag):
    other = auto()
    mo = auto()
    po = auto()
    pyc = auto()
    json = auto()
    dat = auto()
    pyi = auto()
    py = auto()

def collect_data() -> Mapping[str, str]:
    """
    x date text NOT NULL,
      test_fqn text NOT NULL,
      commit_hash text NOT NULL,
    x n_changes_3 int NOT NULL,
    x n_changes_14 int NOT NULL,
    x n_changes_56 int NOT NULL,
    x file_cardinality int NOT NULL,
      file_extension text NOT NULL,
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
        # "file_cardinality": None,
    }

    data["date"] = datetime.now()

    cmd = ["git", "diff", f"master...{BRANCH_NAME}", "--name-only"]
    changed_files = [line for line in subprocess.check_output(cmd, env=os.environ.copy()).decode().split("\n") if line]
    print(changed_files)

    data["file_cardinality"] = len(changed_files)

    extensions = [
        os.path.splitext(file)[1]
        for file in changed_files
    ]
    print(extensions)
    print([ext for ext in CommonExtension])

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
    # sum([git log --after="{3/14/56} days ago" --format=oneline {file} | wc -l for file in changed_files])
    return data


if __name__ == "__main__":
    print(collect_data())
