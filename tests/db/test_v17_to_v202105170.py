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
from datetime import datetime, timezone
from typing import AsyncIterator, Awaitable, Callable, Dict, List, Optional

import pytest
from asyncpg import Connection

from db.common import PGRestore
from inmanta.db.versions.v202105170 import TIMESTAMP_COLUMNS
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
async def migrate_v17_to_v202105170(
    hard_clean_db, hard_clean_db_post, postgresql_client: Connection, server_config
) -> AsyncIterator[Callable[[], Awaitable[None]]]:
    """
    Returns a callable that performs a v17 database restore and migrates to v202105170.
    """
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v17.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    # When the bootloader is started, it also executes the migration to v202105170
    yield ibl.start
    await ibl.stop()


@pytest.mark.asyncio(timeout=20)
async def test_timestamp_timezones(migrate_v17_to_v202105170: None, postgresql_client: Connection) -> None:
    """
    All timestamps should be timezone-aware.
    """
    async def fetch_timestamps() -> Dict[str, Dict[str, Optional[datetime]]]:
        return {
            table: [
                {**record}
                for record in await postgresql_client.fetch(
                    f"SELECT %s FROM public.{table};" % ", ".join(columns)
                )
            ]
            for table, columns in TIMESTAMP_COLUMNS.items()
        }

    naive_timestamps: Dict[str, List[Dict[str, Optional[datetime]]]] = await fetch_timestamps()
    utc_timestamps: Dict[str, List[Dict[str, Optional[datetime]]]] = {
        table: [
            {
                column: (naive.astimezone(timezone.utc) if naive is not None else None)
                for column, naive in row.items()
            }
            for row in rows
        ]
        for table, rows in naive_timestamps.items()
    }
    # TODO: remove debug prints
    import devtools
    devtools.debug(naive_timestamps)

    await migrate_v17_to_v202105170()

    devtools.debug(await fetch_timestamps())
    assert await fetch_timestamps() == utc_timestamps


# TODO: add a test for new versioning schema tables
