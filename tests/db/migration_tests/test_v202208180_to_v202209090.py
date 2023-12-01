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
from collections import abc

import pytest


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps", "v202208180.sql"))
async def test_added_notification_related_columns_to_compile_table(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    postgresql_client,
    monkeypatch,
    get_columns_in_db_table: abc.Callable[[str], abc.Awaitable[list[str]]],
) -> None:
    """
    Test the database migration script that adds the `notify_failed_compile` and 'failed_compile_message' column to the
    database.
    """

    async def substitute_func():
        # monkeypatch the cleanup function to keep data in compile table (by default data older than 7 days is removed)
        return

    from inmanta.server.services.compilerservice import CompilerService

    monkeypatch.setattr(CompilerService, "_cleanup", substitute_func)

    # Assert state before running the DB migration script
    assert "notify_failed_compile" not in (await get_columns_in_db_table("compile"))
    assert "failed_compile_message" not in (await get_columns_in_db_table("compile"))

    # Migrate DB schema
    await migrate_db_from()

    # Assert state after running the DB migration script
    assert "notify_failed_compile" in (await get_columns_in_db_table("compile"))
    assert "failed_compile_message" in (await get_columns_in_db_table("compile"))

    compiles = await postgresql_client.fetch("SELECT * FROM public.compile;")
    assert compiles
    for c in compiles:
        assert "notify_failed_compile" in c
        assert c["notify_failed_compile"] is None
        assert "failed_compile_message" in c
        assert c["failed_compile_message"] is None
