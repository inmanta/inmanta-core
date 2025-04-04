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

import inmanta
import inmanta.data.sqlalchemy as models
from inmanta.agent.code_manager import CodeManager
from inmanta.agent.executor import ModuleInstallSpec, ExecutorBlueprint
from inmanta.data import get_session, PipConfig
from inmanta.loader import ModuleSource
from sqlalchemy import select

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_tables_for_agent_code_transport_rework(migrate_db_from: abc.Callable[[], abc.Awaitable[None]]) -> None:

    await migrate_db_from()

    client = inmanta.protocol.Client("client")

    codemanager = CodeManager(client)
    install_spec = await codemanager.get_code(
        environment="a8317edd-74d8-40fc-8933-9aedb77cfed4",
        model_version=1,
        agent_name="internal",
    )
    expected_install_spec = ModuleInstallSpec(
        model_version=1,
        module_name="std",
        module_version="d95a4a8894881c79b1c791fb94824db2dd961d08",
        blueprint=ExecutorBlueprint(
            pip_config=PipConfig(index_url=None, extra_index_url=[], pre=None, use_system_config=True),
            python_version=(3, 12),
            requirements=["Jinja2>=3.1,<4", "email_validator>=1.3,<3", "inmanta-core>=8.7.0.dev", "pydantic>=1.10,<3"],
            sources=ModuleSource(
                name="inmanta_plugins.std.types",
                hash_value="10d63b01c1ec8269f9b10edcb9740cf3519299dc",
                is_byte_code=False,
                source="Module source code",
            ),
        ),
    )
    assert install_spec == expected_install_spec

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
