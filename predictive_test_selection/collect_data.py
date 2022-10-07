import os
import subprocess
from datetime import datetime
from typing import Mapping

TEST_RESULTS = os.path.join(os.curdir, "out.xml")
BRANCH_NAME = "issue/add-data-collector"

def collect_data() -> Mapping[str, str]:
    data = {
        "date": None
    }

    data["date"] = datetime.now()

    cmd = f"git diff master...{BRANCH_NAME} --name-only"
    changed_files = subprocess.check_output(cmd, env=os.environ.copy()).decode()
    print(changed_files)
    # sum([git log - -after = "{3/14/56} days ago" - -format = oneline {file} | wc - l for file in changed_files])

    return data


if __name__ == "__main__":
    collect_data()
