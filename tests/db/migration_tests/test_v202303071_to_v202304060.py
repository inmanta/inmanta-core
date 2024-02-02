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

from inmanta import data


async def has_purge_on_delete_key_in_settings_dct(postgresql_client) -> bool:
    """
    Return True iff any of the records in the Environment table has the purge_on_delete key in the settings dictionary.
    """
    result = await postgresql_client.fetch(
        f"""
            SELECT 1
            FROM {data.Environment.table_name()}
            WHERE settings ? 'purge_on_delete'
            """
    )
    return len(result) > 0


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202303071.sql"))
async def test_removal_of_purge_on_delete_setting(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]], get_columns_in_db_table, postgresql_client
) -> None:
    """
    Verify that the database migration script removes the purge_on_delete key from the settings dictionary
    of the environment table.
    """
    assert await has_purge_on_delete_key_in_settings_dct(postgresql_client)
    await migrate_db_from()
    assert not await has_purge_on_delete_key_in_settings_dct(postgresql_client)
