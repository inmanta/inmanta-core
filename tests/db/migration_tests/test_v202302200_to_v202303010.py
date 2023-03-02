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
from asyncpg.exceptions import NotNullViolationError

from inmanta import data


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202302200.sql"))
async def test_migration(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]], get_columns_in_db_table, postgresql_client
) -> None:
    """
    Only an index was added: make sure the migration script applies.
    """
    assert "is_suitable_for_partial_compiles" not in await get_columns_in_db_table(data.ConfigurationModel.table_name())
    await migrate_db_from()
    assert "is_suitable_for_partial_compiles" in await get_columns_in_db_table(data.ConfigurationModel.table_name())

    query = f"""
        UPDATE {data.ConfigurationModel.table_name()}
        SET is_suitable_for_partial_compiles=NULL
    """
    with pytest.raises(NotNullViolationError):
        # Ensure that the NOT NULL constraint is enforced
        await postgresql_client.execute(query)
