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
import os
import re

import asyncpg
import pytest

from inmanta.data.schema import DBSchema

UP_TO_VERSION = "202206290"  # Specify the version up to which migrations should be applied

MIGRATIONS_DIR = f"{os.path.dirname(os.path.dirname(__file__))}/src/inmanta/db/versions"
# Regular expression to match migration filenames
MIGRATION_FILE_PATTERN = re.compile(r"^v(\d+)\.py$")


# # Extract version number from the filename
# def extract_version(filename: str) -> int:
#     match = MIGRATION_FILE_PATTERN.match(filename)
#     if match is None:
#         raise ValueError(f"Filename {filename} does not match the expected migration file pattern")
#     return int(match.group(1))
#
#
# # Apply a migration script
# async def apply_migration(connection, migration_file_path):
#     spec = importlib.util.spec_from_file_location("migration_module", migration_file_path)
#     migration_module = importlib.util.module_from_spec(spec)
#     spec.loader.exec_module(migration_module)
#     if hasattr(migration_module, "update"):
#         await migration_module.update(connection)
#
#
# # Apply all migrations up to a specified version
# async def apply_migrations_up_to_version(connection, up_to_version):
#     migration_files = [f for f in os.listdir(MIGRATIONS_DIR) if MIGRATION_FILE_PATTERN.match(f)]
#     sorted_files = sorted(migration_files, key=extract_version)
#
#     for filename in sorted_files:
#         if extract_version(filename) < int(up_to_version):
#             print(f"Applying migration: {filename}")
#             migration_file_path = os.path.join(MIGRATIONS_DIR, filename)
#             await apply_migration(connection, migration_file_path)
#
#
# # Applies migrations and dumps the database schema
# @pytest.mark.asyncio
# async def test_apply_migrations_and_dump(postgres_db, database_name, tmp_path):
#     script_dir = os.path.dirname(os.path.abspath(__file__))
#     outfile = os.path.join(script_dir, "compacted_dump.sql")
#
#     print(f"Database dump will be saved to: {outfile}")
#
#     # Connect to the database
#     connection = await asyncpg.connect(
#         host=postgres_db.host,
#         port=postgres_db.port,
#         user=postgres_db.user,
#         password=postgres_db.password,
#         database=database_name,
#     )
#     try:
#         await apply_migrations_up_to_version(connection, UP_TO_VERSION)
#     finally:
#         await connection.close()
#
#     # Dump the database schema
#     proc = await asyncio.create_subprocess_exec(
#         "pg_dump",
#         "-h",
#         postgres_db.host,
#         "-p",
#         str(postgres_db.port),
#         "-U",
#         postgres_db.user,
#         "-s",  # This option tells pg_dump to dump only the schema, no data
#         "-f",
#         str(outfile),
#         "-O",
#         database_name,
#     )
#     await proc.wait()


def get_migration_modules(up_to_version: str) -> list[str]:
    """
    Get a list of migration module names up to the specified version.
    """
    migration_files = [f for f in os.listdir(MIGRATIONS_DIR) if MIGRATION_FILE_PATTERN.match(f)]
    sorted_files = sorted(migration_files, key=lambda f: int(MIGRATION_FILE_PATTERN.match(f).group(1)))
    return [f[:-3] for f in sorted_files if int(MIGRATION_FILE_PATTERN.match(f).group(1)) <= int(up_to_version)]


@pytest.mark.asyncio
async def compact_and_apply_migrations_and_dump(postgres_db, database_name):
    """
    Compact, apply database migrations using DBSchema, and dump the database schema with modifications.
    """
    outfile = "./test"
    # Connect to the database
    connection = await asyncpg.connect(
        host=postgres_db.host, port=postgres_db.port, user=postgres_db.user, password=postgres_db.password
    )

    try:
        # Initialize and use DBSchema
        migration_modules = get_migration_modules(UP_TO_VERSION)
        schema_manager = DBSchema("your_schema_name", migration_modules, connection)
        await schema_manager.ensure_db_schema()
    finally:
        await connection.close()

    # Dump the database schema using pg_dump
    proc = await asyncio.create_subprocess_exec(
        "pg_dump",
        "-h",
        "127.0.0.1",  # Localhost, adjust if necessary
        "-p",
        str(postgres_db.port),
        "-f",
        outfile,
        "-O",
        "-U",
        postgres_db.user,
        database_name,
    )
    await proc.wait()

    # Remove or comment out undesired lines in the database dump
    lines_to_remove = [
        "SELECT pg_catalog.set_config('search_path', '', false);\n",
        "SET default_table_access_method = heap;\n",
    ]
    with open(outfile, "r+") as fh:
        all_lines = fh.readlines()
        assert all(to_remove in all_lines for to_remove in lines_to_remove)
        fh.seek(0)
        for line in all_lines:
            fh.write(f"--{line}" if line in lines_to_remove else line)
        fh.truncate()
