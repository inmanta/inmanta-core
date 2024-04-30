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
from collections.abc import Awaitable
from typing import Callable

import pytest


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202304070.sql"))
async def test_migration(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    get_columns_in_db_table: abc.Callable[[str], abc.Awaitable[abc.Sequence[str]]],
    get_tables_in_db: Callable[[], Awaitable[list[str]]],
    get_primary_key_columns_in_db_table: abc.Callable[[str], abc.Awaitable[abc.Sequence[str]]],
) -> None:
    """
    verify that the discovered_at column is added, that the table is renamed and that the primary key is changed
    """
    tables = await get_tables_in_db()
    assert "unmanagedresource" in tables
    assert "discoveredresource" not in tables
    assert "discovered_at" not in (await get_columns_in_db_table("unmanagedresource"))

    columns_pk = await get_primary_key_columns_in_db_table("unmanagedresource")
    assert len(columns_pk) == 2
    assert "discovered_resource_id" not in columns_pk
    assert "unmanaged_resource_id" in columns_pk

    await migrate_db_from()

    tables = await get_tables_in_db()
    assert "unmanagedresource" not in tables
    assert "discoveredresource" in tables
    assert "discovered_at" in (await get_columns_in_db_table("discoveredresource"))

    columns_pk = await get_primary_key_columns_in_db_table("discoveredresource")
    assert len(columns_pk) == 2
    assert "discovered_resource_id" in columns_pk
    assert "unmanaged_resource_id" not in columns_pk
