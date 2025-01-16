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


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202306060.sql"))
async def test_migration(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    get_type_of_column: Callable[[], Awaitable[list[str]]],
) -> None:
    """
    verify that the type of the discovered_at column in the discoveredresource table changed
    """
    assert await get_type_of_column("discoveredresource", "discovered_at") == "timestamp without time zone"

    await migrate_db_from()

    assert await get_type_of_column("discoveredresource", "discovered_at") == "timestamp with time zone"
