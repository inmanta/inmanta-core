"""
    Copyright 2019 Inmanta

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

import os

import pytest
from asyncpg import Connection

from db.common import PGRestore
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
async def migrate_v3_to_v4(hard_clean_db, hard_clean_db_post, postgresql_client: Connection, async_finalizer, server_config):
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v3.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    result = await postgresql_client.fetch(
        """
            SELECT EXISTS
            (SELECT 1
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename = 'form');"""
    )
    assert result[0]["exists"]

    result = await postgresql_client.fetch(
        """
                SELECT EXISTS
                (SELECT 1
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = 'formrecord');"""
    )
    assert result[0]["exists"]
    ibl = InmantaBootloader()

    # When the bootloader is started, it also executes the migration to v4
    await ibl.start()
    async_finalizer(ibl.stop)


@pytest.mark.asyncio
async def test_forms_tables_deleted(migrate_v3_to_v4, async_finalizer, server_config, postgresql_client: Connection):
    result = await postgresql_client.fetch(
        """
                SELECT EXISTS
                (SELECT 1
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = 'form');"""
    )
    assert not result[0]["exists"]

    result = await postgresql_client.fetch(
        """
                    SELECT EXISTS
                    (SELECT 1
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    AND tablename = 'formrecord');"""
    )
    assert not result[0]["exists"]
