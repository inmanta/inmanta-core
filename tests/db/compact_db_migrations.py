"""
    Copyright 2021 Inmanta

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

import asyncpg
import pytest

MIGRATIONS_DIR = "../../src/inmanta/db/versions"
UP_TO_VERSION = "202206290"  # Specify the version up to which migrations should be applied

# Regular expression to match migration filenames
MIGRATION_FILE_PATTERN = re.compile(r"^v(\d+)\.py$")


# Function to extract version number from the filename
def extract_version(filename):
    match = MIGRATION_FILE_PATTERN.match(filename)
    return int(match.group(1)) if match else None


# Function to apply a migration script
async def apply_migration(connection, migration_file_path):
    spec = importlib.util.spec_from_file_location("migration_module", migration_file_path)
    migration_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration_module)
    if hasattr(migration_module, "update"):
        await migration_module.update(connection)


# Function to apply all migrations up to a specified version
async def apply_migrations_up_to_version(connection, up_to_version):
    migration_files = [f for f in os.listdir(MIGRATIONS_DIR) if MIGRATION_FILE_PATTERN.match(f)]
    sorted_files = sorted(migration_files, key=extract_version)

    for filename in sorted_files:
        if extract_version(filename) < int(up_to_version):
            print(f"Applying migration: {filename}")
            migration_file_path = os.path.join(MIGRATIONS_DIR, filename)
            await apply_migration(connection, migration_file_path)


# Test function that applies migrations and dumps the database schema
@pytest.mark.asyncio
async def test_apply_migrations_and_dump(postgres_db, database_name, tmp_path):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    outfile = os.path.join(script_dir, "compacted_dump.sql")

    print(f"Database dump will be saved to: {outfile}")

    # Connect to the database
    connection = await asyncpg.connect(
        host=postgres_db.host,
        port=postgres_db.port,
        user=postgres_db.user,
        password=postgres_db.password,
        database=database_name,
    )
    try:
        await apply_migrations_up_to_version(connection, UP_TO_VERSION)
    finally:
        await connection.close()

    # Dump the database schema
    proc = await asyncio.create_subprocess_exec(
        "pg_dump",
        "-h",
        postgres_db.host,
        "-p",
        str(postgres_db.port),
        "-U",
        postgres_db.user,
        "-s",  # This option tells pg_dump to dump only the schema, no data
        "-f",
        str(outfile),
        "-O",  # This option skips dumping object ownership to simplify restoration
        database_name,
    )
    await proc.wait()
