"""
Copyright 2025 Inmanta

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

import pytest

from inmanta import data

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_schema_update_settings_column(migrate_db_from: abc.Callable[[], abc.Awaitable[None]], postgresql_client) -> None:
    """
    Test the migration script that updates the schema of the environment.settings column.
    """
    # Fetch settings that exist in environment dev-1 before the migration
    result = await postgresql_client.fetch(f"SELECT settings FROM {data.Environment.table_name()} WHERE name='dev-1'")
    assert len(result) == 1
    settings_before = result[0]["settings"]
    assert len(settings_before) == 7

    # Run migration script
    await migrate_db_from()

    # Ensure correct migration of settings column of environment table
    result = await data.Environment.get_list()
    for r in result:
        assert len(r.settings.settings) > 0
        assert all(setting_name in data.Environment._settings for setting_name in r.settings.settings.keys())
        assert all(s.protected is False for s in r.settings.settings.values())
        assert all(s.protected_by is None for s in r.settings.settings.values())

    # Validate that the values of the settings are correctly migrated
    result = await data.Environment.get_one(name="dev-1")
    # A setting may be added to the settings list by accessing that setting.
    # Only assert >= to keep the test stable.
    assert len(result.settings.settings) >= 7
    for setting_name in settings_before:
        assert result.settings.settings[setting_name].value == settings_before[setting_name]
