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


async def has_version_field_in_all_resources(postgresql_client) -> bool:
    """
    Return True iff all resources in the resource table have the version field in the attributes dictionary.
    This method raises an assertion error when there are no resources in the resource table.
    """
    all_attributes = await postgresql_client.fetch(f"SELECT attributes from {data.Resource.table_name()}")
    assert len(all_attributes) > 0
    return all("version" in attrs["attributes"] for attrs in all_attributes)


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202303070.sql"))
async def test_migration(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]], get_columns_in_db_table, postgresql_client
) -> None:
    assert "is_suitable_for_partial_compiles" not in await get_columns_in_db_table(data.ConfigurationModel.table_name())
    assert await has_version_field_in_all_resources(postgresql_client)
    await migrate_db_from()
    assert "is_suitable_for_partial_compiles" in await get_columns_in_db_table(data.ConfigurationModel.table_name())
    assert not await has_version_field_in_all_resources(postgresql_client)

    # Ensure that the value of the is_suitable_for_partial_compiles column is set to False everywhere
    cms = await data.ConfigurationModel.get_list()
    assert len(cms) > 0
    assert all(cm.is_suitable_for_partial_compiles is False for cm in cms)

    # Ensure that the NOT NULL constraint is enforced on the is_suitable_for_partial_compiles column
    query = f"""
        UPDATE {data.ConfigurationModel.table_name()}
        SET is_suitable_for_partial_compiles=NULL
    """
    with pytest.raises(NotNullViolationError):
        await postgresql_client.execute(query)
