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
async def test_extras_column(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    Verify that this migration adds a non-nullable extras column to configurationmodel_modules, and that the model versions
    that are already stored install no extras.
    """
    nr_of_rows: int = await postgresql_client.fetchval("SELECT count(*) FROM public.configurationmodel_modules")
    assert nr_of_rows > 0

    await migrate_db_from()

    column = await postgresql_client.fetchrow("""
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_name = 'configurationmodel_modules' AND column_name = 'extras'
        """)
    assert column is not None
    assert column["is_nullable"] == "NO"

    extras = await postgresql_client.fetch("SELECT extras FROM public.configurationmodel_modules")
    assert len(extras) == nr_of_rows
    assert all(record["extras"] == [] for record in extras)
