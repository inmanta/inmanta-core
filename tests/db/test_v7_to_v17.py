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
import uuid
from typing import AsyncIterator

import pytest
from asyncpg import Connection, exceptions

from db.common import PGRestore
from inmanta import data
from inmanta.server.bootloader import InmantaBootloader
from utils import retry_limited


@pytest.fixture
@pytest.mark.slowtest
async def migrate_v7_to_v17(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, server_config
) -> AsyncIterator[None]:
    """
    Performs a v7 database restore and migrates to v17.
    """
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v7.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    await ibl.start()
    # When the bootloader is started, it also executes the migration to v18
    yield
    await ibl.stop()


@pytest.mark.asyncio(timeout=20)
async def test_foreign_key_agent_to_agentinstance(migrate_v7_to_v17: None, postgresql_client: Connection) -> None:
    """
    Deleting an entry in the agentInstance table should not be allowed when it's references from the agent stable.
    """
    env_id = "a21a4bdc-68f0-4c4e-a4f2-a6b42880661a"

    async def is_internal_agent_up() -> bool:
        result = await data.Agent.get_one(environment=env_id, name="internal")
        return result.id_primary is not None

    async def get_id_primary_internal_agent() -> uuid.UUID:
        # Return the id of the AgentInstance that is the primary for the internal agent
        result = await data.Agent.get_one(environment=env_id, name="internal")
        assert result.id_primary is not None
        return result.id_primary

    await retry_limited(is_internal_agent_up, timeout=10)
    id_primary_internal_agent = await get_id_primary_internal_agent()

    # Delete primary agent instance for internal agent should raise an exception
    with pytest.raises(
        exceptions.ForeignKeyViolationError, match=r'violates foreign key constraint "agent_id_primary_fkey" on table "agent"'
    ):
        await postgresql_client.execute(
            f"""
            DELETE FROM public.agentinstance
            WHERE id='{id_primary_internal_agent}';
            """
        )
