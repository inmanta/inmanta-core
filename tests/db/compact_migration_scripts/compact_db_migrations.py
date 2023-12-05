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


    Tool to compact db migration scripts
"""
import asyncio
import importlib
import os
import re

import asyncpg

from inmanta.ast.type import List
from inmanta.data.schema import CORE_SCHEMA_NAME, DBSchema

PACKAGE_NAME = "versions_to_compact"


def extract_version(filename):
    match = re.match(r"^v(\d+)", filename)
    return int(match[1]) if match else None


def get_sorted_versions(directory: str) -> List[int]:
    """
    Get a sorted list of version numbers from all migration scripts in a directory.
    """
    versions = []
    for filename in os.listdir(directory):
        if filename.endswith(".py"):
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


async def test_compact_and_dump(postgres_db, database_name):
    """
    Compact, apply database migrations using DBSchema, and dump the database schema with modifications.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    compact_dir = os.path.join(script_dir, "versions_to_compact")
    original_dir = os.path.abspath(os.path.join(script_dir, "../../../src/inmanta/db/versions"))

    check_versions(compact_dir, original_dir)

    outfile = f"{os.path.dirname(__file__)}/compacted_dump.sql"
    connection = await asyncpg.connect(
        host=postgres_db.host,
        port=postgres_db.port,
        user=postgres_db.user,
        password=postgres_db.password,
        database=database_name,
    )

    try:
        package = importlib.import_module(PACKAGE_NAME)
        schema_manager = DBSchema(CORE_SCHEMA_NAME, package, connection)
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
