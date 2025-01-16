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


def test_migration_check():
    """
    Make sure there is a database dump for the latest version of the db and
    that a migration test exists for this dump.
    """

    inmanta_dir: Path = Path(__file__).parent.parent.parent.absolute()

    versions_folder: Path = inmanta_dir / "src" / "inmanta" / "db" / "versions"
    versions: list[Path] = list(versions_folder.glob("v" + "[0-9]" * 9 + ".py"))  # Migration files have format vYYYYMMDDN.py
    latest_version: Path = sorted(versions)[-1]

    migration_tests_folder: Path = inmanta_dir / "tests" / "db" / "migration_tests"
    dumps_folder: Path = migration_tests_folder / "dumps"

    dumps: list[Path] = list(dumps_folder.glob("v" + "[0-9]" * 9 + ".sql"))  # Dumps have format vYYYYMMDDN.sql
    latest_dump: Path = sorted(dumps)[-1]

    assert latest_version.stem == latest_dump.stem

    # Make sure the following lines have been removed from the dump:
    forbidden_strings: list[str] = [
        "SELECT pg_catalog.set_config('search_path', '', false);",
        "SET default_table_access_method = heap;",
    ]

    with open(latest_dump) as fh:
        for line_no, line in enumerate(fh.readlines(), start=1):
            if line.startswith("--"):
                continue
            if line.strip() in forbidden_strings:
                raise Exception(
                    f"Line '{line}' was found in dump {latest_dump} L{line_no}. Please remove or comment out this line."
                )

    migration_tests: list[Path] = sorted(migration_tests_folder.glob("test_v*" + latest_dump.stem + ".py"))
    if not migration_tests:
        raise Exception(
            f"No migration test to version {latest_dump.stem} was found in {migration_tests_folder}. Please add such a test."
        )
    migration_test: Path = migration_tests[-1]
    assert migration_test.is_file()
