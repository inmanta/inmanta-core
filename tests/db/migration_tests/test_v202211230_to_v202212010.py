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
from collections.abc import AsyncIterator, Awaitable
from typing import Callable

import pytest
from asyncpg import Connection

from db.common import PGRestore
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
async def migrate_v202211230_to_v202212010(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, server_config
) -> AsyncIterator[Callable[[], Awaitable[None]]]:
    """
    Returns a callable that performs a v202211230 database restore and migrates to v202212010.
    """
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v202211230.sql")) as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    # When the bootloader is started, it also executes the migration to v202212010
    yield ibl.start
    await ibl.stop(timeout=15)


async def test_added_environment_metrics_tables(
    migrate_v202211230_to_v202212010: Callable[[], Awaitable[None]],
    get_tables_in_db: Callable[[], Awaitable[list[str]]],
) -> None:
    """
    Test whether the environment_metrics_counter table was added
    """

    # The table is not present before the migration
    tables = await get_tables_in_db()
    assert "environmentmetricsgauge" not in tables
    assert "environmentmetricstimer" not in tables

    # Migrate DB schema
    await migrate_v202211230_to_v202212010()

    # The table is added to the database
    tables = await get_tables_in_db()
    assert "environmentmetricsgauge" in tables
    assert "environmentmetricstimer" in tables
