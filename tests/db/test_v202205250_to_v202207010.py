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
from typing import Awaitable, Callable, List

import pytest


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202205250.sql"))
async def test_added_resource_set_column(
    migrate_db_from: Callable[[], Awaitable[None]],
    postgresql_client,
    get_columns_in_db_table: Callable[[str], Awaitable[List[str]]],
    get_custom_postgresql_types: Callable[[], Awaitable[List[str]]],
) -> None:
    """
    Test the database migration script that adds the `resource_set` column to the database.

    """

    # Assert state before running the DB migration script
    assert "partial" not in (await get_columns_in_db_table("compile"))
    assert "removed_resource_sets" not in (await get_columns_in_db_table("compile"))

    # Migrate DB schema
    await migrate_db_from()

    # Assert state after running the DB migration script
    assert "partial" in (await get_columns_in_db_table("compile"))
    assert "removed_resource_sets" in (await get_columns_in_db_table("compile"))

    compiles = await postgresql_client.fetch("SELECT * FROM public.compile;")
    for c in compiles:
        assert "partial" in c
        assert c["partial"] is False
        assert "removed_resource_sets" in c
        assert len(c["removed_resource_sets"]) == 0
