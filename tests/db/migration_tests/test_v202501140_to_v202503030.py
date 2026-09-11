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
from inmanta.agent.executor import InmantaModuleInstallMode

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_tables_for_agent_code_transport_rework(migrate_db_from: abc.Callable[[], abc.Awaitable[None]]) -> None:

    await migrate_db_from()

    environments = ["bbfe114d-a91b-4cfe-be61-018c112aeafe", "7d3ec9ea-9759-4beb-8629-c7df42ed8d4e"]
    # The python files that make up each of the modules of the first model version
    module_sources = {
        "fs": ["inmanta_plugins.fs", "inmanta_plugins.fs.json_file", "inmanta_plugins.fs.resources"],
        "std": ["inmanta_plugins.std", "inmanta_plugins.std.resources", "inmanta_plugins.std.types"],
    }
    # Each of these agents has a resource of a single module in the first model version, so that is the only module it
    # loads. Both modules are still installed on both agents: an on disk install module reaches an agent through its
    # transported source only, and the handler of one module may import the other.
    module_loaded_per_agent = {"internal": "std", "localhost": "fs"}

    for env in environments:
        codemanager = CodeManager()
        for agent_name, loaded_module in module_loaded_per_agent.items():
            install_specs = await codemanager.get_code(environment=env, model_version=1, agent_name=agent_name)
            assert {install_spec.module_name for install_spec in install_specs} == set(module_sources)

            for install_spec in install_specs:
                # The install mode of a module of a model version that was exported by an iso<10 orchestrator is unknown,
                # so its code has to be installed on disk, from the transported source. In particular, it must not be
                # treated as an editable install module, for which no packaging files were persisted back then:
                # reconstructing it as an installable python package would produce a source tree pip can not build.
                assert install_spec.install_mode is InmantaModuleInstallMode.ON_DISK
                assert install_spec.blueprint.editable_modules == []
                assert install_spec.blueprint.on_disk_code_install is not None
                assert module_sources[install_spec.module_name] == [
                    module.metadata.name for module in install_spec.blueprint.on_disk_code_install.module_sources
                ]
                assert install_spec.blueprint.inmanta_modules_to_load == (
                    [install_spec.module_name] if install_spec.module_name == loaded_module else []
                )
                if install_spec.module_name == "fs":
                    # A module installed on disk is not a python package, so pip can not resolve its requirements from
                    # packaging metadata: they are transported alongside its source.
                    assert "inmanta-module-std" in install_spec.blueprint.requirements
