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

from inmanta.agent.code_manager import CodeManager

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_tables_for_agent_code_transport_rework(migrate_db_from: abc.Callable[[], abc.Awaitable[None]]) -> None:

    await migrate_db_from()

    environments = ["bbfe114d-a91b-4cfe-be61-018c112aeafe", "7d3ec9ea-9759-4beb-8629-c7df42ed8d4e"]
    for env in environments:

        codemanager = CodeManager()
        install_spec_1 = await codemanager.get_code(
            environment=env,
            model_version=1,
            agent_name="internal",
        )
        assert len(install_spec_1) == 1
        assert ["inmanta_plugins.std", "inmanta_plugins.std.resources", "inmanta_plugins.std.types"] == [
            module.metadata.name for module in install_spec_1[0].blueprint.sources
        ]
        install_spec_2 = await codemanager.get_code(
            environment=env,
            model_version=1,
            agent_name="localhost",
        )
        assert len(install_spec_2) == 1
        assert ["inmanta_plugins.fs", "inmanta_plugins.fs.json_file", "inmanta_plugins.fs.resources"] == [
            module.metadata.name for module in install_spec_2[0].blueprint.sources
        ]
        assert "inmanta-module-std" in install_spec_2[0].blueprint.requirements
