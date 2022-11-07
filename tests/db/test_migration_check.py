"""
    Copyright 2022 Inmanta

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: code@inmanta.com
"""
from pathlib import Path
from typing import List


def test_migration_check():
    """
    Make sure there is a database dump for the latest version of the db and
    that a migration test exists for this dump.
    """
    versions_folder: Path = Path(".").absolute() / "src" / "inmanta" / "db" / "versions"

    versions: List[Path] = list(versions_folder.glob("v" + "[0-9]" * 9 + ".py"))  # Dumps have format vYYYYMMDDN.py
    latest_version: Path = sorted(versions)[-1]

    migration_tests_folder: Path = Path(".").absolute() / "tests" / "db" / "migration_tests"
    dumps_folder: Path = migration_tests_folder / "dumps"

    dumps: List[Path] = list(dumps_folder.glob("v" + "[0-9]" * 9 + ".sql"))  # Dumps have format vYYYYMMDDN.sql
    latest_dump: Path = sorted(dumps)[-1]

    assert latest_version.stem == latest_dump.stem

    migration_test: Path = sorted(migration_tests_folder.glob("test_v*" + latest_dump.stem + ".py"))[-1]

    assert migration_test.is_file()
