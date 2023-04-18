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
from typing import Awaitable, Callable, List

import pytest

from inmanta.data import Environment, UnmanagedResource


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202303071.sql"))
async def test_migration(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    get_tables_in_db: Callable[[], Awaitable[List[str]]],
) -> None:
    """
    verify that the unmanagedresource table is created
    """
    tables = await get_tables_in_db()
    assert "unmanagedresource" not in tables
    await migrate_db_from()
    tables = await get_tables_in_db()
    assert "unmanagedresource" in tables

    env = await Environment.get_one(name="dev-1")
    values = {"value1": "test1", "value2": "test2"}
    await UnmanagedResource(
        unmanaged_resource_id="test::Resource[agent1,key=key]",
        values=values,
        environment=env.id,
    ).insert()
    result = await UnmanagedResource.get_one(environment=env.id, unmanaged_resource_id="test::Resource[agent1,key=key]")
    assert result.values == values
