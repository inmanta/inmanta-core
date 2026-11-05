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
import uuid
from collections import abc

import asyncpg
import pytest

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_key_module_files_by_path(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    Every stored file gets the path the agent has always installed it at: each python module as the __init__ file of
    a package, with a .pyc extension for byte code.
    """
    environment: uuid.UUID = await postgresql_client.fetchval("SELECT id FROM public.environment LIMIT 1")
    await postgresql_client.execute(
        "INSERT INTO public.inmanta_module(name, version, environment, requirements) VALUES('mod', 'abc', $1, '{}')",
        environment,
    )
    await postgresql_client.execute(
        "INSERT INTO public.file(content_hash, content) VALUES('h1', 'a'), ('h2', 'b'), ('h3', 'c') ON CONFLICT DO NOTHING"
    )
    await postgresql_client.execute(
        """
        INSERT INTO public.module_files(
            inmanta_module_name, inmanta_module_version, environment, file_content_hash, python_module_name, is_byte_code
        )
        VALUES
            ('mod', 'abc', $1, 'h1', 'inmanta_plugins.mod', false),
            ('mod', 'abc', $1, 'h2', 'inmanta_plugins.mod.sub.leaf', false),
            ('mod', 'abc', $1, 'h3', 'inmanta_plugins.mod.compiled', true)
        """,
        environment,
    )

    await migrate_db_from()

    files = await postgresql_client.fetch(
        "SELECT file_content_hash, path FROM public.module_files WHERE environment=$1 AND inmanta_module_name='mod'",
        environment,
    )
    assert {record["file_content_hash"]: record["path"] for record in files} == {
        "h1": "inmanta_plugins/mod/__init__.py",
        "h2": "inmanta_plugins/mod/sub/leaf/__init__.py",
        "h3": "inmanta_plugins/mod/compiled/__init__.pyc",
    }

    columns = {
        record["column_name"]
        for record in await postgresql_client.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name='module_files'"
        )
    }
    assert "python_module_name" not in columns
    assert "is_byte_code" not in columns

    # The path is part of the primary key: two files of one module can't share it
    with pytest.raises(asyncpg.UniqueViolationError):
        await postgresql_client.execute(
            """
            INSERT INTO public.module_files(inmanta_module_name, inmanta_module_version, environment, file_content_hash, path)
            VALUES ('mod', 'abc', $1, 'h2', 'inmanta_plugins/mod/__init__.py')
            """,
            environment,
        )
