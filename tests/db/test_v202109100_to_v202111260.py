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
"""
import os
from typing import AsyncIterator, Awaitable, Callable, List

import pytest
from asyncpg import Connection

from db.common import PGRestore
from inmanta import protocol
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
async def migrate_v202109100_to_v202111260(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, server_config
) -> AsyncIterator[Callable[[], Awaitable[None]]]:
    """
    Returns a callable that performs a v202109100 database restore and migrates to v202111260.
    """
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v202109100.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    # When the bootloader is started, it also executes the migration to v202111260
    yield ibl.start
    await ibl.stop()


@pytest.mark.asyncio(timeout=20)
async def test_added_environment_columns(
    migrate_v202109100_to_v202111260: Callable[[], Awaitable[None]],
    get_columns_in_db_table: Callable[[str], Awaitable[List[str]]],
) -> None:
    """
    Test whether the description and icon columns were added to the environment table.
    """

    # The columns are not present before the migration
    columns = await get_columns_in_db_table("environment")
    assert "icon" not in columns
    assert "description" not in columns

    # Migrate DB schema
    await migrate_v202109100_to_v202111260()

    client = protocol.Client("client")

    # The columns are added to the table
    columns += ["description", "icon"]
    assert (await get_columns_in_db_table("environment")) == columns

    # The environment data is still ok after the migration, and has the correct default values
    result = await client.environment_list()
    assert result.code == 200
    assert len(result.result["data"]) == 2

    env_id = "982a35ab-2785-4221-9926-f4f389416ce3"
    result = await client.environment_get(env_id)
    assert result.code == 200
    assert result.result["data"]["icon"] == ""
    assert result.result["data"]["description"] == ""
