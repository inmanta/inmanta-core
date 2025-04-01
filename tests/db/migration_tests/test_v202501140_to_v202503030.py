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

import pytest

import inmanta.data.sqlalchemy as models
from inmanta.data import get_session
from sqlalchemy import select

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_tables_for_agent_code_transport_rework(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    get_tables_in_db: abc.Callable[[], abc.Awaitable[list[str]]],
) -> None:

    assert "inmanta_module" not in await get_tables_in_db()
    assert "files_in_module" not in await get_tables_in_db()
    assert "modules_for_agent" not in await get_tables_in_db()
    assert "code" in await get_tables_in_db()
    await migrate_db_from()
    assert "inmanta_module" in await get_tables_in_db()
    assert "files_in_module" in await get_tables_in_db()
    assert "modules_for_agent" in await get_tables_in_db()
    assert "code" not in await get_tables_in_db()

    async with get_session() as session:
        files_in_module_stmt = select(
            models.FilesInModule.python_module_name,
        ).order_by(models.FilesInModule.python_module_name)
        files = await session.scalars(files_in_module_stmt)
        assert files.all() == [
            "inmanta_plugins.fs",
            "inmanta_plugins.fs.json_file",
            "inmanta_plugins.fs.resources",
            "inmanta_plugins.std",
            "inmanta_plugins.std.resources",
            "inmanta_plugins.std.types",
        ]

        modules_stmt = select(
            models.InmantaModule.name,
        ).order_by(models.InmantaModule.name)
        modules = await session.scalars(modules_stmt)
        assert modules.all() == ["fs", "std"]

        modules_for_agent_stmt = (
            select(
                models.ModulesForAgent.agent_name,
                models.ModulesForAgent.inmanta_module_name,
                models.ModulesForAgent.inmanta_module_version,
            )
            .order_by(models.ModulesForAgent.agent_name)
            .where(models.ModulesForAgent.cm_version == 1)
        )
        modules_for_agent = await session.execute(modules_for_agent_stmt)
        assert modules_for_agent.all() == [
            ("internal", "std", "d95a4a8894881c79b1c791fb94824db2dd961d08"),
            ("localhost", "fs", "a8ecaac2c9448803a18a5d9e16bbd87f133a06fc"),
        ]
