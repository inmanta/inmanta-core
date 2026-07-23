"""
Copyright 2026 Inmanta

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

import asyncpg
import pytest

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_token_table(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    # Before the migration the token table does not exist.
    exists_before = await postgresql_client.fetchval(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema='public' AND table_name='token')"
    )
    assert not exists_before

    await migrate_db_from()

    # After the migration the token table exists and is usable through the data layer.
    exists_after = await postgresql_client.fetchval(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema='public' AND table_name='token')"
    )
    assert exists_after
    assert await postgresql_client.fetchval("SELECT count(*) FROM token") == 0
