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
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
async def migrate_v202111260_to_v202203140(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, server_config
) -> AsyncIterator[Callable[[], Awaitable[None]]]:
    """
    Returns a callable that performs a v202111260 database restore and migrates to v202203140.
    """
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v202111260.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    # When the bootloader is started, it also executes the migration to v202203140
    yield ibl.start
    await ibl.stop(timeout=15)


async def test_added_notification_table(
    migrate_v202111260_to_v202203140: Callable[[], Awaitable[None]],
    get_tables_in_db: Callable[[], Awaitable[List[str]]],
) -> None:
    """
    Test whether the notification table was added
    """

    # The table is not present before the migration
    tables = await get_tables_in_db()
    assert "notification" not in tables

    # Migrate DB schema
    await migrate_v202111260_to_v202203140()

    # The table is added to the database
    tables = await get_tables_in_db()
    assert "notification" in tables
