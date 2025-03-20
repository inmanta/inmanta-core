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

import asyncpg
import pytest

import inmanta.data.sqlalchemy as models
from inmanta.data import get_session
from sqlalchemy import select

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_tables_for_agent_code_transport_rework(
    postgresql_client: asyncpg.Connection,
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    get_tables_in_db: abc.Callable[[], abc.Awaitable[list[str]]],
) -> None:

    assert "module" not in await get_tables_in_db()
    assert "files_in_module" not in await get_tables_in_db()
    assert "modules_for_agent" not in await get_tables_in_db()
    await migrate_db_from()
    assert "module" in await get_tables_in_db()
    assert "files_in_module" in await get_tables_in_db()
    assert "modules_for_agent" in await get_tables_in_db()

    async with get_session() as session:
        files_in_module_stmt = select(
            models.FilesInModule.file_path,
        ).order_by(models.FilesInModule.file_path)
        files = await session.scalars(files_in_module_stmt)
        assert files.all() == [
            "inmanta_plugins/fs/__init__.py",
            "inmanta_plugins/fs/json_file.py",
            "inmanta_plugins/fs/resources.py",
            "inmanta_plugins/std/__init__.py",
            "inmanta_plugins/std/resources.py",
            "inmanta_plugins/std/types.py",
        ]

        modules_stmt = select(
            models.Module.name,
        ).order_by(models.Module.name)
        modules = await session.scalars(modules_stmt)
        assert modules.all() == ["fs", "std"]

        modules_for_agent_stmt = (
            select(
                models.ModulesForAgent.agent_name,
                models.ModulesForAgent.module_name,
                models.ModulesForAgent.module_version,
            )
            .order_by(models.ModulesForAgent.agent_name)
            .where(models.ModulesForAgent.cm_version == 1)
        )
        modules_for_agent = await session.execute(modules_for_agent_stmt)
        assert modules_for_agent.all() == [
            ("internal", "std", "cbe17aef6300a8f88b8044cd5f1891809b0d0bf4"),
            ("localhost", "fs", "98418787b3a998d6778588156bf05cedaa5c122e"),
        ]
