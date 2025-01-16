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


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202301190.sql"))
async def test_migration(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    get_tables_in_db: Callable[[], Awaitable[list[str]]],
    get_custom_postgresql_types: Callable[[], Awaitable[list[str]]],
) -> None:
    """
    verify that the auth_method enum and the user table are added.
    edit: the user table was renamed and is tested in test_v202302270_to_v202303070
    """
    # tables = await get_tables_in_db()
    assert "auth_method" not in (await get_custom_postgresql_types())
    # assert "user" not in tables
    await migrate_db_from()
    # tables = await get_tables_in_db()
    assert "auth_method" in (await get_custom_postgresql_types())
    # assert "user" in tables
