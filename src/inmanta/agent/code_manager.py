"""
Copyright 2024 Inmanta

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

import itertools
import logging
import sys
import uuid

import inmanta.data.sqlalchemy as models
from inmanta import data
from inmanta.agent import executor
from inmanta.agent.executor import EditableModuleInstall, InmantaModuleInstallSpec, OnDiskCodeInstall
from inmanta.data.model import LEGACY_PIP_DEFAULT, ModuleSource, ModuleSourceMetadata, PipConfig
from inmanta.util import get_python_package_name_for
from inmanta.util.async_lru import async_lru_cache
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import aliased

LOGGER = logging.getLogger(__name__)


class CouldNotResolveCode(Exception):

    def __init__(self, agent_name: str, version: int) -> None:
        self.msg = f"Failed to get source code for agent `{agent_name}` on version {version}."
        super().__init__(self.msg)


class CodeManager:
    """
    Helper responsible for translating resource versions into code

    Caches heavily
    """

    @async_lru_cache(maxsize=1024)
    async def get_code(self, environment: uuid.UUID, model_version: int, agent_name: str) -> list[InmantaModuleInstallSpec]:
        """
        Get the list of installation specifications (i.e. pip config, python package dependencies,
        Inmanta modules sources) required to deploy resources on a given agent for a given configuration
        model version.

        :return: list of InmantaModuleInstallSpec for this agent and this model version.
        """
        module_install_specs = []

        # The setup.cfg and pyproject.toml files of editable modules are stored as regular files, referenced by
        # (nullable) content hashes on the inmanta_module row. Join them in via their own File aliases so we can fetch
        # their content in one query. Outer joins because these hashes are only set for editable modules.
        setup_cfg_file = aliased(models.File)
        pyproject_toml_file = aliased(models.File)

        modules_for_agent = (
            select(
                models.ConfigurationModelModules.inmanta_module_name,
                models.ConfigurationModelModules.inmanta_module_version,
                models.InmantaModule.requirements,
                models.InmantaModule.editable_install,
                models.ModuleFiles.python_module_name,
                models.ModuleFiles.file_content_hash,
                models.ModuleFiles.is_byte_code,
                models.File.content.label("source_file_content"),
                setup_cfg_file.content.label("setup_cfg_content"),
                pyproject_toml_file.content.label("pyproject_toml_content"),
                models.AgentModules.agent_name.label("load_on_agent"),
                models.Configurationmodel.pip_config,
                models.Configurationmodel.project_constraints,
            )
            .join(
                models.InmantaModule,
                and_(
                    models.ConfigurationModelModules.inmanta_module_name == models.InmantaModule.name,
                    models.ConfigurationModelModules.inmanta_module_version == models.InmantaModule.version,
                    models.ConfigurationModelModules.environment == models.InmantaModule.environment,
                ),
            )
            .outerjoin(
                models.ModuleFiles,
                and_(
                    models.InmantaModule.name == models.ModuleFiles.inmanta_module_name,
                    models.InmantaModule.version == models.ModuleFiles.inmanta_module_version,
                    models.InmantaModule.environment == models.ModuleFiles.environment,
                ),
            )
            .outerjoin(
                models.File,
                models.ModuleFiles.file_content_hash == models.File.content_hash,
            )
            .outerjoin(
                setup_cfg_file,
                models.InmantaModule.setup_cfg_hash == setup_cfg_file.content_hash,
            )
            .outerjoin(
                pyproject_toml_file,
                models.InmantaModule.pyproject_toml_hash == pyproject_toml_file.content_hash,
            )
            # A module is registered here only for the agents that load it, so this join tells whether this agent does.
            .outerjoin(
                models.AgentModules,
                and_(
                    models.ConfigurationModelModules.environment == models.AgentModules.environment,
                    models.ConfigurationModelModules.cm_version == models.AgentModules.cm_version,
                    models.ConfigurationModelModules.inmanta_module_name == models.AgentModules.inmanta_module_name,
                    models.AgentModules.agent_name == agent_name,
                ),
            )
            .join(
                models.Configurationmodel,
                and_(
                    models.ConfigurationModelModules.cm_version == models.Configurationmodel.version,
                    models.ConfigurationModelModules.environment == models.Configurationmodel.environment,
                ),
            )
            .where(
                models.ConfigurationModelModules.environment == environment,
                models.ConfigurationModelModules.cm_version == model_version,
                # This agent installs the modules it loads. On top of those, it installs every editable install module of
                # this model version: its transported source is the only way such a module can reach an agent, and the
                # handler of another module may import it.
                or_(
                    models.InmantaModule.editable_install.is_(True),
                    models.AgentModules.agent_name.is_not(None),
                ),
            )
            .order_by(models.ConfigurationModelModules.inmanta_module_name)
        )

        async with data.get_session() as session:
            result = await session.execute(modules_for_agent)
            for module_name, rows in itertools.groupby(result.all(), key=lambda r: r.inmanta_module_name):
                rows_list = list(rows)
                assert rows_list

                first_row = rows_list[0]
                _pip_config = first_row.pip_config
                for row in rows_list:
                    # The following attributes should be consistent across all modules in this version
                    assert row.inmanta_module_version == first_row.inmanta_module_version
                    assert row.pip_config == _pip_config
                    assert row.requirements == first_row.requirements
                    assert row.project_constraints == first_row.project_constraints
                    assert row.editable_install == first_row.editable_install
                    assert row.setup_cfg_content == first_row.setup_cfg_content
                    assert row.pyproject_toml_content == first_row.pyproject_toml_content
                    assert row.load_on_agent == first_row.load_on_agent

                pip_config = LEGACY_PIP_DEFAULT if _pip_config is None else PipConfig(**_pip_config)

                # This module is only loaded on the agents it was registered for. A model version that was exported by an
                # iso<10 orchestrator registered every agent that installs a module, so such a version keeps loading
                # everything it transports.
                load_module: bool = first_row.load_on_agent is not None
                editable_install: bool | None = first_row.editable_install

                # The python files that make up this module, for the install modes that transport them. This list
                # should be empty for package install thanks to the outer join.
                module_sources: list[ModuleSource] = [
                    ModuleSource(
                        metadata=ModuleSourceMetadata(
                            name=row.python_module_name,
                            hash_value=row.file_content_hash,
                            is_byte_code=row.is_byte_code,
                        ),
                        source=row.source_file_content,
                    )
                    for row in rows_list
                    if row.python_module_name is not None
                ]

                requirements: list[str] = []
                legacy_on_disk_code_install: OnDiskCodeInstall | None = None
                editable_modules: list[EditableModuleInstall] = []
                # An agent may have to install a module it doesn't load: another module's handler may import it.
                inmanta_modules_to_load: list[str] = [module_name] if load_module else []

                if editable_install is None:
                    # Exported by an iso<10 orchestrator, which didn't record the install mode: install on disk.
                    # Can be dropped in iso11 (#10592).
                    legacy_on_disk_code_install = OnDiskCodeInstall(module_sources=module_sources)
                    requirements = list(first_row.requirements)
                elif editable_install:
                    # pip resolves the module's requirements from its setup.cfg, which the API makes mandatory for an
                    # editable module.
                    assert first_row.setup_cfg_content is not None
                    editable_modules = [
                        EditableModuleInstall(
                            name=module_name,
                            version=first_row.inmanta_module_version,
                            python_module_sources=module_sources,
                            setup_cfg=first_row.setup_cfg_content,
                            pyproject_toml=first_row.pyproject_toml_content,
                        )
                    ]
                else:
                    requirements = [f"{get_python_package_name_for(module_name)}=={first_row.inmanta_module_version}"]

                module_install_specs.append(
                    InmantaModuleInstallSpec(
                        module_name=module_name,
                        module_version=first_row.inmanta_module_version,
                        blueprint=executor.ExecutorBlueprint(
                            pip_config=pip_config,
                            requirements=requirements,
                            inmanta_modules_to_load=inmanta_modules_to_load,
                            python_version=sys.version_info[:2],
                            environment_id=environment,
                            project_constraints=first_row.project_constraints if first_row.project_constraints else None,
                            editable_modules=editable_modules,
                            legacy_on_disk_code_install=legacy_on_disk_code_install,
                        ),
                    )
                )

        if not module_install_specs:
            raise CouldNotResolveCode(agent_name, model_version)
        return module_install_specs
