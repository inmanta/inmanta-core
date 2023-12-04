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
import asyncpg
import pytest

from inmanta.data.schema import DBSchema, CORE_SCHEMA_NAME

PACKAGE_NAME = "versions_to_compact"

@pytest.mark.asyncio
async def test_compact_and_dump(postgres_db, database_name):
    """
    Compact, apply database migrations using DBSchema, and dump the database schema with modifications.
    """
    outfile = "./compacted_dump.sql"
    connection = await asyncpg.connect(
        host=postgres_db.host,
        port=postgres_db.port,
        user=postgres_db.user,
        password=postgres_db.password,
        database=database_name,
    )

    try:
        # Initialize and use DBSchema
        package = importlib.import_module(PACKAGE_NAME)
        schema_manager = DBSchema(CORE_SCHEMA_NAME, package, connection)
        await schema_manager.ensure_db_schema()
        await schema_manager.set_installed_version(1)
    finally:
        await connection.close()

    # Dump the database schema using pg_dump
    proc = await asyncio.create_subprocess_exec(
        "pg_dump",
        "-h",
        str(postgres_db.host),
        "-p",
        str(postgres_db.port),
        "-f",
        outfile,
        "-O",
        "-U",
        "-s",  # This option tells pg_dump to dump only the schema, no data
        postgres_db.user,
        database_name,
    )
    await proc.wait()

