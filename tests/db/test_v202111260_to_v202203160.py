"""
    Copyright 2022 Inmanta

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
from typing import AsyncIterator, Awaitable, Callable, List

import pytest
from asyncpg import Connection

from db.common import PGRestore
from inmanta.const import ResourceState
from inmanta.data import Resource
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
async def migrate_v202111260_to_v202203160(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, server_config
) -> AsyncIterator[Callable[[], Awaitable[None]]]:
    """
    Returns a callable that performs a v202111260 database restore and migrates to v202203160.
    """
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v202111260.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    # When the bootloader is started, it also executes the migration to v202111260
    yield ibl.start
    await ibl.stop()


async def test_added_last_non_deploying_status_column(
    migrate_v202111260_to_v202203160: Callable[[], Awaitable[None]],
    get_columns_in_db_table: Callable[[str], Awaitable[List[str]]],
    get_custom_postgresql_types: Callable[[], Awaitable[List[str]]],
) -> None:
    """
    Test the database migration script that adds the `last_non_deploying_status` column to the database.

    1) Two resources exist in the database dump:

       * std::File[localhost, path=/tmp/test]
       * std::AgentConfig[internal, agentname=localhost]

    2) Overview deploy history:

                      resource_version_id                 | action |  status   |            started
       ---------------------------------------------------+--------+-----------+-------------------------------
       std::AgentConfig[internal,agentname=localhost],v=1 | store  |           | 2022-03-15 16:35:02.557191+01
       std::AgentConfig[internal,agentname=localhost],v=1 | pull   |           | 2022-03-15 16:35:03.466918+01
       std::AgentConfig[internal,agentname=localhost],v=1 | pull   |           | 2022-03-15 16:35:05.591205+01
       std::AgentConfig[internal,agentname=localhost],v=1 | deploy | deployed  | 2022-03-15 16:35:05.592065+01
       std::AgentConfig[internal,agentname=localhost],v=1 | deploy | deployed  | 2022-03-15 16:35:08.387699+01
       std::AgentConfig[internal,agentname=localhost],v=2 | store  |           | 2022-03-15 16:35:14.918778+01
       std::AgentConfig[internal,agentname=localhost],v=2 | deploy | deployed  | 2022-03-15 16:35:14.942906+01
       std::AgentConfig[internal,agentname=localhost],v=2 | pull   |           | 2022-03-15 16:35:15.166585+01
       std::AgentConfig[internal,agentname=localhost],v=2 | deploy | deployed  | 2022-03-15 16:35:18.647132+01
       std::AgentConfig[internal,agentname=localhost],v=2 | deploy | deploying | 2022-03-15 16:35:19.647132+01
       std::File[localhost,path=/tmp/test],v=1            | store  |           | 2022-03-15 16:35:02.557191+01
       std::File[localhost,path=/tmp/test],v=1            | pull   |           | 2022-03-15 16:35:06.625448+01
       std::File[localhost,path=/tmp/test],v=1            | deploy | failed    | 2022-03-15 16:35:09.313108+01
       std::File[localhost,path=/tmp/test],v=2            | store  |           | 2022-03-15 16:35:14.918778+01
       std::File[localhost,path=/tmp/test],v=2            | pull   |           | 2022-03-15 16:35:14.940534+01
       std::File[localhost,path=/tmp/test],v=2            | pull   |           | 2022-03-15 16:35:18.645797+01
       std::File[localhost,path=/tmp/test],v=2            | deploy | failed    | 2022-03-15 16:35:18.647344+01
    """

    # Assert state before running the DB migration script
    assert "last_non_deploying_status" not in (await get_columns_in_db_table("resource"))
    assert "non_deploying_resource_state" not in (await get_custom_postgresql_types())

    # Migrate DB schema
    await migrate_v202111260_to_v202203160()

    # Assert state after running the DB migration script
    assert "last_non_deploying_status" in (await get_columns_in_db_table("resource"))
    assert "non_deploying_resource_state" in (await get_custom_postgresql_types())

    expected_status = {
        "std::AgentConfig[internal,agentname=localhost],v=2": ResourceState.deploying,
        "std::AgentConfig[internal,agentname=localhost],v=1": ResourceState.deployed,
        "std::File[localhost,path=/tmp/test],v=2": ResourceState.failed,
        "std::File[localhost,path=/tmp/test],v=1": ResourceState.failed,
    }
    expected_last_non_deploying_status = {
        "std::AgentConfig[internal,agentname=localhost],v=2": ResourceState.deployed,
        "std::AgentConfig[internal,agentname=localhost],v=1": ResourceState.deployed,
        "std::File[localhost,path=/tmp/test],v=2": ResourceState.failed,
        "std::File[localhost,path=/tmp/test],v=1": ResourceState.failed,
    }

    resources = await Resource.get_list()
    assert len(resources) == 4
    rvid_to_resource = {res.resource_version_id: res for res in resources}
    for rvid, resource in rvid_to_resource.items():
        assert resource.status is expected_status[rvid]
        assert resource.last_non_deploying_status is expected_last_non_deploying_status[rvid]
