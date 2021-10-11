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
async def migrate_v5_to_v6(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, async_finalizer, server_config
) -> AsyncIterator[None]:
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v5.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    await ibl.start()
    # When the bootloader is started, it also executes the migration to v6
    yield
    await ibl.stop()


@pytest.mark.asyncio
async def test_add_on_delete_cascade_constraint(migrate_v5_to_v6, postgresql_client: Connection) -> None:
    """
    Verify that the ON DELETE CASCADE constraint is set correctly on the substitute_compile_id column
    of the compile table.
    """
    # Assert values in substitute_compile_id column are correct
    compiles = await postgresql_client.fetch("SELECT substitute_compile_id FROM public.compile")
    assert all([c["substitute_compile_id"] is None for c in compiles])

    # Assert that ON DELETE CASCADE is set the foreign key constraint compile_substitute_compile_id_fkey
    constraints = await postgresql_client.fetch(
        """
            SELECT pg_catalog.pg_get_constraintdef(r.oid, true) as condef
            FROM pg_catalog.pg_constraint r
            WHERE conname='compile_substitute_compile_id_fkey'
        """
    )
    assert len(constraints) == 1
    assert "ON DELETE CASCADE" in constraints[0]["condef"]
