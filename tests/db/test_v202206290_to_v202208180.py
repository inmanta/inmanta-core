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
import uuid
from collections import abc
from inmanta.data import ConfigurationModel

import pytest


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202206290.sql"))
async def test_column_add(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    postgresql_client,
    get_columns_in_db_table: abc.Callable[[str], abc.Awaitable[list[str]]],
) -> None:
    """
    Test the database migration script that adds the `partial_base` column to the database.
    """

    # Assert state before running the DB migration script
    assert "partial_base" not in (await get_columns_in_db_table(ConfigurationModel.table_name()))

    # Migrate DB schema
    await migrate_db_from()

    # Assert state after running the DB migration script
    assert "partial_base" in (await get_columns_in_db_table(ConfigurationModel.table_name()))

    assert all(
        model.partial_base is None
        for model in await ConfigurationModel.get_list()
    )

