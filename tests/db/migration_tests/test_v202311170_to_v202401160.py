"""
    Copyright 2024 Inmanta

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
import re
from collections import abc

import asyncpg
import pytest

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_non_expiring_facts(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]], get_columns_in_db_table
) -> None:
    """
    This migration script adds the ``expires`` column to the parameter table.

    Following 0002-database-upgrade-testing.md ADR:
        - Update "pre" dump v202311170.sql: add a fact to the parameter table using "old" codebase (master)
        - Ensure the migration correctly populates the newly added ``expires`` column with default ``True`` value.
    """

    columns_before_migration = await get_columns_in_db_table("parameter")
    assert "expires" not in columns_before_migration

    await migrate_db_from()

    columns_after_migration = await get_columns_in_db_table("parameter")
    assert "expires" in columns_after_migration

    expires = await postgresql_client.fetchval("SELECT expires FROM public.parameter where name='test_default_expires';")

    assert expires is True

    # result = await client.get_param(tid="2dd63a9e-7804-4d20-9cf7-751a50b3c1a9", id="expiring", resource_id="test::SetNonExpiringFact[agent1,key=expiring]")
    # assert result.code == 200
