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

# The columns that identify an inmanta module or one of its files, per table
MODULE_KEY_COLUMNS: abc.Mapping[str, abc.Sequence[str]] = {
    "inmanta_module": ["name", "version"],
    "module_files": ["inmanta_module_name", "inmanta_module_version", "path"],
    "configurationmodel_modules": ["inmanta_module_name", "inmanta_module_version"],
    "agent_modules": ["inmanta_module_name"],
}


async def get_collations(postgresql_client: asyncpg.Connection) -> dict[tuple[str, str], str | None]:
    """
    The collation of each text column of the module tables, keyed by (table, column). None is the default collation.
    """
    records = await postgresql_client.fetch(
        """
        SELECT table_name, column_name, collation_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = ANY($1::varchar[]) AND data_type = 'character varying'
        """,
        list(MODULE_KEY_COLUMNS),
    )
    return {(record["table_name"], record["column_name"]): record["collation_name"] for record in records}


async def get_rows(postgresql_client: asyncpg.Connection) -> dict[str, list[str]]:
    """
    The rows of each module table, each as the string form of its values, sorted in Python rather than by the database,
    because the database orders these columns by their collation.
    """
    return {
        table: sorted(str(dict(record)) for record in await postgresql_client.fetch(f"SELECT * FROM public.{table}"))
        for table in MODULE_KEY_COLUMNS
    }


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_module_keys_use_c_collation(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    The columns that identify an inmanta module or one of its files use the C collation, the other text columns of these
    tables keep the default one, and no row changes.
    """
    collations_before = await get_collations(postgresql_client)
    assert set(collations_before.values()) == {None}
    rows_before = await get_rows(postgresql_client)
    assert rows_before["configurationmodel_modules"]

    await migrate_db_from()

    module_key_columns = {(table, column) for table, columns in MODULE_KEY_COLUMNS.items() for column in columns}
    assert await get_collations(postgresql_client) == {
        key: "C" if key in module_key_columns else None for key in collations_before
    }
    assert await get_rows(postgresql_client) == rows_before
