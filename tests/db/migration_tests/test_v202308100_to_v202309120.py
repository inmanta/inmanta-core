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


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202308100.sql"))
async def test_add_file_table(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]], get_tables_in_db: abc.Callable[[], abc.Awaitable[list[str]]]
) -> None:
    assert "file" not in await get_tables_in_db()
    await migrate_db_from()
    assert "file" in await get_tables_in_db()
