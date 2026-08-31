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
from inmanta import data, loader, module
from inmanta.agent import executor
from inmanta.agent.executor import EditableModuleInstall, InmantaModuleInstallSpec
from inmanta.data.model import LEGACY_PIP_DEFAULT, InmantaModuleInstallMode, ModuleSource, ModuleSourceMetadata, PipConfig
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
                models.ConfigurationmodelModules.inmanta_module_name,
                models.ConfigurationmodelModules.inmanta_module_version,
                # Null when this module is not registered for this agent, i.e. when the agent installs it without loading
                # it because it is not installed as a package.
                models.AgentModules.agent_name.label("registered_for_agent"),
                models.AgentModules.load_module_on_agent,
                models.InmantaModule.requirements,
                models.InmantaModule.install_mode,
                models.ModuleFiles.python_module_name,
                models.ModuleFiles.file_content_hash,
                models.ModuleFiles.is_byte_code,
                models.File.content.label("source_file_content"),
                setup_cfg_file.content.label("setup_cfg_content"),
                pyproject_toml_file.content.label("pyproject_toml_content"),
                models.Configurationmodel.pip_config,
                models.Configurationmodel.project_constraints,
            )
            .join(
                models.InmantaModule,
                and_(
                    models.ConfigurationmodelModules.inmanta_module_name == models.InmantaModule.name,
                    models.ConfigurationmodelModules.inmanta_module_version == models.InmantaModule.version,
                    models.ConfigurationmodelModules.environment == models.InmantaModule.environment,
                ),
            )
            # The registration of this module for this agent, if it has one. A module that is not installed as a package
            # is installed on every agent of the version, whether it is registered for this one or not.
            .outerjoin(
                models.AgentModules,
                and_(
                    models.ConfigurationmodelModules.inmanta_module_name == models.AgentModules.inmanta_module_name,
                    models.ConfigurationmodelModules.cm_version == models.AgentModules.cm_version,
                    models.ConfigurationmodelModules.environment == models.AgentModules.environment,
                    models.AgentModules.agent_name == agent_name,
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
            .join(
                models.Configurationmodel,
                and_(
                    models.ConfigurationmodelModules.cm_version == models.Configurationmodel.version,
                    models.ConfigurationmodelModules.environment == models.Configurationmodel.environment,
                ),
            )
            .where(
                models.ConfigurationmodelModules.environment == environment,
                models.ConfigurationmodelModules.cm_version == model_version,
                # A package install module only concerns the agents it is registered for. Any other module is installed
                # on every agent of the version.
                or_(
                    models.AgentModules.agent_name.is_not(None),
                    models.InmantaModule.install_mode != InmantaModuleInstallMode.PACKAGE.value,
                ),
            )
            .order_by(models.ConfigurationmodelModules.inmanta_module_name)
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
                    assert row.registered_for_agent == first_row.registered_for_agent
                    assert row.load_module_on_agent == first_row.load_module_on_agent
                    assert row.install_mode == first_row.install_mode
                    assert row.setup_cfg_content == first_row.setup_cfg_content
                    assert row.pyproject_toml_content == first_row.pyproject_toml_content

                pip_config = LEGACY_PIP_DEFAULT if _pip_config is None else PipConfig(**_pip_config)

                install_mode = InmantaModuleInstallMode(first_row.install_mode)

                # Whether this agent has to load the code of this module. It only ever loads a module it is registered for.
                # A null load flag on such a registration means this model version was exported by an iso<10
                # orchestrator: back then every module registered for an agent was loaded on it. That compatibility layer
                # can be dropped in iso11 (#10592).
                load_module: bool = first_row.registered_for_agent is not None and (
                    first_row.load_module_on_agent is None or first_row.load_module_on_agent
                )

                # The python files that make up this module. They are not transported for a package install module: the
                # agent installs it with pip and discovers its files in the venv of the executor.
                module_sources: list[ModuleSource] = (
                    []
                    if install_mode is InmantaModuleInstallMode.PACKAGE
                    else [
                        ModuleSource(
                            metadata=ModuleSourceMetadata(
                                name=row.python_module_name,
                                hash_value=row.file_content_hash,
                                is_byte_code=row.is_byte_code,
                            ),
                            source=row.source_file_content,
                        )
                        for row in rows_list
                    ]
                )

                requirements: list[str] = []
                on_disk_code_install: loader.OnDiskCodeInstall | None = None
                editable_modules: list[EditableModuleInstall] = []
                # Only load the code of this module if this agent was registered for it: another module's handler may
                # import it without this agent ever deploying one of its resources.
                inmanta_modules_to_load: list[str] = [module_name] if load_module else []

                if install_mode is InmantaModuleInstallMode.ON_DISK:
                    # The source of this module is written to disk by the agent, outside of the venv, together with the
                    # python requirements of the module: it is not a python package pip could resolve them from.
                    on_disk_code_install = loader.OnDiskCodeInstall(module_sources=module_sources)
                    # The column is nullable: a module that declares no requirement may have either an empty array or null
                    requirements = list(first_row.requirements or [])
                else:
                    # The code of this module lives in the venv of the executor.
                    if install_mode is InmantaModuleInstallMode.EDITABLE:
                        # Gather everything needed to reconstruct this module as an installable python package on the
                        # agent (python sources + packaging files) so that it can be pip installed in editable mode.
                        # Its python requirements are not transported: pip resolves them from setup.cfg.
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
                        # The agent installs this module with pip, which resolves its requirements.
                        requirements = [
                            f"{module.ModuleV2Source.get_package_name_for(module_name)}=={first_row.inmanta_module_version}"
                        ]

                module_install_specs.append(
                    InmantaModuleInstallSpec(
                        module_name=module_name,
                        module_version=first_row.inmanta_module_version,
                        install_mode=install_mode,
                        blueprint=executor.ExecutorBlueprint(
                            pip_config=pip_config,
                            requirements=requirements,
                            inmanta_modules_to_load=inmanta_modules_to_load,
                            python_version=sys.version_info[:2],
                            environment_id=environment,
                            project_constraints=first_row.project_constraints if first_row.project_constraints else None,
                            editable_modules=editable_modules,
                            on_disk_code_install=on_disk_code_install,
                        ),
                    )
                )

        if not module_install_specs:
            raise CouldNotResolveCode(agent_name, model_version)
        return module_install_specs
