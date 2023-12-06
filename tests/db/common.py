"""
    Copyright 2023 Inmanta

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


    Tool to populate the database and dump it for database update testing
"""
import asyncio
import importlib
import os
import re
from typing import List, Optional

import asyncpg

# The content of this file was moved to inmanta.db.util to allow it to be used from other extensions.
# This import statement is present to ensure backwards compatibility.
from inmanta.db.util import MODE_READ_COMMAND, MODE_READ_INPUT, AsyncSingleton, PGRestore  # noqa: F401

from inmanta.data.schema import DBSchema  # isort:skip

PACKAGE_NAME = "versions_to_compact"


async def compact_and_dump(
    compact_dir: str, original_dir: str, outfile: str, schema_name: str, database_name: str, postgres_db
) -> None:
    """
    Compact, apply database migrations using DBSchema, and dump the database schema with modifications.

    :param compact_dir: Directory containing the migration scripts to be compacted.
    :param original_dir: Directory containing the original migration scripts.
    :param outfile: Location of the output file where the dump will be created.
    :param schema_name: Name of the schema to be used in DBSchema.
    :param database_name: Name of the database to connect to.
    :param postgres_db: this should be the postgres_db fixture.
    """

    def extract_version(filename: str) -> Optional[int]:
        """
        Extracts the version number from a filename.
        """
        match = re.match(r"^v(\d+)\.py", filename)
        return int(match[1]) if match else None

    def get_sorted_versions(directory: str) -> List[int]:
        """
        Get a sorted list of version numbers from all migration scripts in a directory.
        """
        versions = []
        for filename in os.listdir(directory):
            version = extract_version(filename)
            if version is not None:  # only select the .py files with a version number and ignore __init__.py
                versions.append(version)
        return sorted(versions)

    def check_versions(compact_dir: str, original_dir: str) -> None:
        """
        Check that the versions in the compact directory contain v1 up to a certain version vX,
        and that all versions in the original directory are strictly higher than vX.
        """
        compact_versions = get_sorted_versions(compact_dir)
        original_versions = get_sorted_versions(original_dir)

        if not compact_versions or not original_versions:
            raise ValueError("One or both directories are empty")

        if compact_versions[0] != 1:
            raise ValueError("The v1 migration script is missing in the scripts to be compacted.")

        highest_compact = compact_versions[-1]
        lowest_original = original_versions[0]

        if highest_compact > lowest_original:
            raise ValueError(
                f"Overlap detected: a version number in the scripts to compact ({highest_compact}) has a higher "
                f"version than one of the remaining migration scripts ({lowest_original})"
            )

    check_versions(compact_dir, original_dir)

    connection = await asyncpg.connect(
        host=postgres_db.host,
        port=postgres_db.port,
        user=postgres_db.user,
        password=postgres_db.password,
        database=database_name,
    )

    try:
        package = importlib.import_module(PACKAGE_NAME)
        schema_manager = DBSchema(schema_name, package, connection)
        await schema_manager.ensure_db_schema()
    finally:
        await connection.close()

    # Dump the database schema using pg_dump
    proc = await asyncio.create_subprocess_exec(
        "pg_dump",
        "-h",
        str(postgres_db.host),
        "-p",
        str(postgres_db.port),
        "-U",
        postgres_db.user,
        "-f",
        outfile,
        "-O",
        "-s",  # This option tells pg_dump to dump only the schema, no data
        database_name,
    )
    await proc.wait()
    # Check the return code of the process
    if proc.returncode != 0:
        raise RuntimeError("pg_dump process failed")
