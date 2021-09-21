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

from db.common import PGRestore
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
@pytest.mark.slowtest
async def migrate_v4_to_v5(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, async_finalizer, server_config
) -> AsyncIterator[None]:
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v4.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    await ibl.start()
    # When the bootloader is started, it also executes the migration to v5
    yield
    await ibl.stop()


@pytest.mark.asyncio
async def test_db_migration_compile_data(migrate_v4_to_v5, postgresql_client: Connection) -> None:
    compiles = await postgresql_client.fetch("SELECT * FROM public.compile;")
    for c in compiles:
        assert "substitute_compile_id" in c
        assert c["substitute_compile_id"] is None
        assert "compile_data" in c
        assert c["compile_data"] is None


@pytest.mark.asyncio
async def test_db_migration_environment_halt(migrate_v4_to_v5, postgresql_client: Connection) -> None:
    environments = await postgresql_client.fetch("SELECT * FROM public.environment;")
    for env in environments:
        assert "halted" in env
        assert env["halted"] is False
    agents = await postgresql_client.fetch("SELECT * FROM public.agent;")
    for a in agents:
        assert "unpause_on_resume" in a
        assert a["unpause_on_resume"] is None
