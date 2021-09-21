"""
    Copyright 2020 Inmanta

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
from typing import AsyncIterator

import pytest
from asyncpg import Connection
from asyncpg.cursor import Cursor

from db.common import PGRestore
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
@pytest.mark.slowtest
async def migrate_v6_to_v7(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, async_finalizer, server_config
) -> AsyncIterator[None]:
    """
    Performs a v6 database restore and migrates to v7.
    """
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v6.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    await ibl.start()
    # When the bootloader is started, it also executes the migration to v7
    yield
    await ibl.stop()


@pytest.mark.asyncio(timeout=20)
async def test_unique_agent_instances(migrate_v6_to_v7: None, postgresql_client: Connection) -> None:
    # assert that existing documents have been merged and expired state has been set correctly
    async with postgresql_client.transaction():
        records: Cursor = postgresql_client.cursor(
            """
            SELECT COUNT(*)
            FROM public.agentinstance
            GROUP BY tid, process, name
            ;
            """
        )
        assert all([record["count"] == 1 async for record in records])

    # assert unique constraint is present
    constraints = await postgresql_client.fetch(
        """
        SELECT pg_catalog.pg_get_constraintdef(r.oid, true) as condef
        FROM pg_catalog.pg_constraint r
        WHERE conname='agentinstance_unique'
        """
    )
    assert len(constraints) == 1
    assert constraints[0]["condef"] == "UNIQUE (tid, process, name)"
