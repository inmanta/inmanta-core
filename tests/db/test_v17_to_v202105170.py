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
import json
import os
import uuid
from datetime import datetime
from typing import AsyncIterator, Awaitable, Callable, Dict, Iterator, List, Optional

import pydantic
import pytest
from asyncpg import Connection

from db.common import PGRestore
from inmanta.data import Compile
from inmanta.db.versions.v202105170 import TIMESTAMP_COLUMNS
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
@pytest.mark.slowtest
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
async def test_timestamp_timezones(
    migrate_v17_to_v202105170: Callable[[], Awaitable[None]], postgresql_client: Connection
) -> None:
    """
    All timestamps should be timezone-aware.
    """

    async def fetch_timestamps() -> Dict[str, List[Dict[str, Optional[datetime]]]]:
        return {
            table: [
                {**record} for record in await postgresql_client.fetch(f"SELECT %s FROM public.{table};" % ", ".join(columns))
            ]
            for table, columns in TIMESTAMP_COLUMNS.items()
        }

    async def fetch_action_log_timestamps() -> List[datetime]:
        return [
            pydantic.parse_obj_as(datetime, json.loads(msg)["timestamp"])
            for record in await postgresql_client.fetch("SELECT messages FROM public.resourceaction ORDER BY action_id;")
            for msg in record["messages"]
        ]

    def timezone_aware(timestamps: Dict[str, List[Dict[str, Optional[datetime]]]]) -> Iterator[bool]:
        return (
            timestamp.tzinfo is not None
            for table, rows in timestamps.items()
            for row in rows
            for column, timestamp in row.items()
            if timestamp is not None
        )

    # Can't test value conversion on all values because the server might change some values at startup.
    # Add a timestamp and a NULL value to test value conversion.
    project_id: uuid.UUID = uuid.uuid4()
    env_id: uuid.UUID = uuid.uuid4()
    compile_id: uuid.UUID = uuid.uuid4()
    compile_started: datetime = datetime.now()
    await postgresql_client.execute(
        f"""
        INSERT INTO public.project
        VALUES ('{project_id}', 'v202105170-test-project')
        ;
        INSERT INTO public.environment
        VALUES ('{env_id}', 'v202105170-test-env', '{project_id}', '', '', '{{}}')
        ;
        INSERT INTO public.compile
        VALUES ('{compile_id}', '{env_id}', '{compile_started.isoformat()}', NULL)
        ;
        """
    )

    naive_timestamps: Dict[str, List[Dict[str, Optional[datetime]]]] = await fetch_timestamps()
    assert not any(timezone_aware(naive_timestamps))
    naive_action_log_timestamps: List[datetime] = await fetch_action_log_timestamps()
    assert len(naive_action_log_timestamps) > 0
    assert all(timestamp.tzinfo is None for timestamp in naive_action_log_timestamps)

    await migrate_v17_to_v202105170()

    migrated_timestamps: Dict[str, List[Dict[str, Optional[datetime]]]] = await fetch_timestamps()
    assert all(timezone_aware(migrated_timestamps))

    compile: Optional[Compile] = await Compile.get_by_id(compile_id)
    assert compile is not None
    assert compile.started is not None
    assert compile.started.tzinfo is not None
    assert compile.started == compile_started.astimezone()
    assert compile.completed is None

    assert await fetch_action_log_timestamps() == [naive.astimezone() for naive in naive_action_log_timestamps]
