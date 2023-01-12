"""
    Copyright 2023 Inmanta
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
from collections import abc
from datetime import datetime

from asyncpg import Connection

import pytest


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202301110.sql"))
async def test_timestamp_timezones(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    postgresql_client: Connection,
    # get_columns_in_db_table: abc.Callable[[str], abc.Awaitable[abc.Sequence[str]]],
    # get_primary_key_columns_in_db_table: abc.Callable[[str], abc.Awaitable[abc.Sequence[str]]],
) -> None:
    """
    Test that all timestamps are timezone-aware.
    """

    # Fill the tables with dummy data to be able to fetch the types
    project_id: uuid.UUID = uuid.uuid4()
    env_id: uuid.UUID = uuid.uuid4()
    timestamp: datetime = datetime.now()

    await postgresql_client.execute(
        f"""
        INSERT INTO public.project
        VALUES ('{project_id}', 'v202301120-test-project')
        ;
        INSERT INTO public.environment
        VALUES ('{env_id}', 'v202301120-test-env', '{project_id}', '', '', '{{}}')
        ;
        INSERT INTO public.environmentmetricstimer
        VALUES ('{env_id}', 'metrictimer','{timestamp.isoformat()}','1', '2.0')
        ;
        INSERT INTO public.environmentmetricsgauge
        VALUES ('{env_id}', 'metricgauge', '{timestamp.isoformat()}', '1')
        ;
        """
    )

    async def check_column_type(table: str, column: str, type: str) -> None:
        result = await postgresql_client.fetch(
            f"""
                SELECT pg_typeof({column}) as type
                FROM public.{table};
            """
        )
        assert result[0]["type"] == type


    type_pre = 'timestamp without time zone'
    for table in ["environmentmetricsgauge", "environmentmetricstimer"]:
        await check_column_type(table, "timestamp", type_pre)

    # Migrate DB schema
    await migrate_db_from()

    type_post = 'timestamp with time zone'
    for table in ["environmentmetricsgauge", "environmentmetricstimer"]:
        await check_column_type(table, "timestamp", type_post)

