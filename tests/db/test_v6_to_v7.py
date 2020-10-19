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

import datetime
import os
import uuid
from dataclasses import dataclass
from typing import AsyncIterator, Awaitable, Callable, List

import pytest
from asyncpg import Connection, Record
from asyncpg.cursor import Cursor

from db.common import PGRestore
from inmanta import data
from inmanta.server.services.databaseservice import DatabaseService


@pytest.fixture
async def migrate_v6_to_v7(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, async_finalizer, server_config
) -> AsyncIterator[Callable[[], Awaitable[None]]]:
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v5.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    db_service: DatabaseService = DatabaseService()

    # When the bootloader is started, it also executes the migration to v7
    yield db_service.start
    await db_service.stop()


@dataclass
class AgentInstanceCount:
    """
    Helper class for describing agent instance table preconditions for a specific tid, process, name combination.
    """

    tid: uuid.UUID
    process: uuid.UUID
    name: str
    count: int
    active_count: int


@pytest.mark.asyncio(timeout=20)
async def test_unique_agent_instances(migrate_v6_to_v7: Callable[[], Awaitable[None]], postgresql_client: Connection) -> None:
    async with postgresql_client.transaction():
        agent_processes: List[Record] = await postgresql_client.fetch("SELECT sid FROM public.agentprocess LIMIT 1;")
        assert len(agent_processes) == 1
        instance_pools: List[AgentInstanceCount] = [
            AgentInstanceCount(
                tid=uuid.uuid4(), process=agent_processes[0]["sid"], name="name", count=count, active_count=active_count
            )
            for count in (1, 2, 3)
            for active_count in (0, 1, 2)
        ]

        for instance_pool in instance_pools:
            for i in range(instance_pool.count):
                await postgresql_client.execute(
                    """
                    INSERT INTO public.agentinstance
                    (id, tid, process, name, expired)
                    VALUES ($1, $2, $3, $4, $5)
                    ;
                    """,
                    *(
                        data.AgentInstance._get_value(value)
                        for value in (
                            uuid.uuid4(),
                            instance_pool.tid,
                            instance_pool.process,
                            instance_pool.name,
                            (None if i < instance_pool.active_count else datetime.datetime.now()),
                        )
                    ),
                )

        records_pre: Cursor = postgresql_client.cursor(
            """
            SELECT tid, process, name, COUNT(expired) AS expired_count, COUNT(*)
            FROM public.agentinstance
            GROUP BY tid, process, name
            ;
            """
        )
        all_instance_pools: List[AgentInstanceCount] = [
            AgentInstanceCount(
                tid=record["tid"],
                process=record["process"],
                name=record["name"],
                count=record["count"],
                active_count=(record["count"] - record["expired_count"]),
            )
            async for record in records_pre
        ]

    await migrate_v6_to_v7()

    # assert that existing documents have been merged and expired state has been set correctly
    async with postgresql_client.transaction():
        for instance_pool in all_instance_pools:
            instances: List[data.AgentInstance] = await data.AgentInstance.get_list(
                tid=instance_pool.tid, process=instance_pool.process, name=instance_pool.name
            )
            assert len(instances) == 1
            assert (instances[0].expired is None) == (instance_pool.active_count > 0)

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
