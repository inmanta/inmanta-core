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
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
@pytest.mark.slowtest
async def migrate_v202105170_to_v202106080(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, server_config
) -> AsyncIterator[Callable[[], Awaitable[None]]]:
    """
    Returns a callable that performs a v202105170 database restore and migrates to v202106080.
    """
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v202105170.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    # When the bootloader is started, it also executes the migration to v202105170
    yield ibl.start
    await ibl.stop()


@pytest.mark.asyncio(timeout=20)
async def test_timestamp_timezones(
    migrate_v202105170_to_v202106080: Callable[[], Awaitable[None]],
    postgresql_client: Connection,
    get_columns_in_db_table: Callable[[str], Awaitable[List[str]]],
) -> None:
    """
    Test whether the send_event column was removed from the resourceaction table.
    """
    columns = await get_columns_in_db_table("resourceaction")
    assert "send_event" in columns

    # Migrate DB schema
    await migrate_v202105170_to_v202106080()

    columns.remove("send_event")
    assert "send_event" not in columns
    assert (await get_columns_in_db_table("resourceaction")) == columns
