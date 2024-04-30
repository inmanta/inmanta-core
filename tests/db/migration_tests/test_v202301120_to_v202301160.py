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
from collections import abc

import pytest


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202301120.sql"))
async def test_migration(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    get_columns_in_db_table: abc.Callable[[str], abc.Awaitable[abc.Sequence[str]]],
    get_primary_key_columns_in_db_table: abc.Callable[[str], abc.Awaitable[abc.Sequence[str]]],
) -> None:
    for table_name in ["environmentmetricsgauge", "environmentmetricstimer"]:
        assert "grouped_by" in (await get_columns_in_db_table(table_name))
        assert "category" not in (await get_columns_in_db_table(table_name))

        columns_pk = await get_primary_key_columns_in_db_table(table_name)
        assert len(columns_pk) == 4
        assert "grouped_by" in columns_pk
        assert "category" not in columns_pk

    await migrate_db_from()

    for table_name in ["environmentmetricsgauge", "environmentmetricstimer"]:
        assert "grouped_by" not in (await get_columns_in_db_table(table_name))
        assert "category" in (await get_columns_in_db_table(table_name))

        columns_pk = await get_primary_key_columns_in_db_table(table_name)
        assert len(columns_pk) == 4
        assert "grouped_by" not in columns_pk
        assert "category" in columns_pk
