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
from inmanta.agent.executor import ModuleInstallSpec
from inmanta.data.model import LEGACY_PIP_DEFAULT, ModuleSource, ModuleSourceMetadata, PipConfig
from inmanta.util.async_lru import async_lru_cache
from sqlalchemy import and_, select

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
    async def get_code(self, environment: uuid.UUID, model_version: int, agent_name: str) -> list[ModuleInstallSpec]:
        """
        Get the list of installation specifications (i.e. pip config, python package dependencies,
        Inmanta modules sources) required to deploy resources on a given agent for a given configuration
        model version.

        :return: list of ModuleInstallSpec for this agent and this model version.
        """
        module_install_specs = []

        modules_for_agent = (
            select(
                models.AgentModules.inmanta_module_name,
                models.AgentModules.inmanta_module_version,
                models.InmantaModule.requirements,
                models.ModuleFiles.python_module_name,
                models.ModuleFiles.file_content_hash,
                models.ModuleFiles.is_byte_code,
                models.File.content.label("source_file_content"),
                models.Configurationmodel.pip_config,
                models.Configurationmodel.project_constraints,
            )
            .join(
                models.InmantaModule,
                and_(
                    models.AgentModules.inmanta_module_name == models.InmantaModule.name,
                    models.AgentModules.inmanta_module_version == models.InmantaModule.version,
                    models.AgentModules.environment == models.InmantaModule.environment,
                ),
            )
            .join(
                models.ModuleFiles,
                and_(
                    models.InmantaModule.name == models.ModuleFiles.inmanta_module_name,
                    models.InmantaModule.version == models.ModuleFiles.inmanta_module_version,
                    models.InmantaModule.environment == models.ModuleFiles.environment,
                ),
            )
            .join(
                models.File,
                models.ModuleFiles.file_content_hash == models.File.content_hash,
            )
            .join(
                models.Configurationmodel,
                and_(
                    models.AgentModules.cm_version == models.Configurationmodel.version,
                    models.AgentModules.environment == models.Configurationmodel.environment,
                ),
            )
            .where(
                models.AgentModules.environment == environment,
                models.AgentModules.agent_name == agent_name,
                models.AgentModules.cm_version == model_version,
            )
            .order_by(models.AgentModules.inmanta_module_name)
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
                    assert set(row.requirements) == set(first_row.requirements)
                    assert row.project_constraints == first_row.project_constraints

                pip_config = LEGACY_PIP_DEFAULT if _pip_config is None else PipConfig(**_pip_config)
                module_install_specs.append(
                    ModuleInstallSpec(
                        module_name=module_name,
                        module_version=first_row.inmanta_module_version,
                        blueprint=executor.ExecutorBlueprint(
                            pip_config=pip_config,
                            requirements=first_row.requirements,
                            sources=[
                                ModuleSource(
                                    metadata=ModuleSourceMetadata(
                                        name=row.python_module_name,
                                        hash_value=row.file_content_hash,
                                        is_byte_code=row.is_byte_code,
                                    ),
                                    source=row.source_file_content,
                                )
                                for row in rows_list
                            ],
                            python_version=sys.version_info[:2],
                            environment_id=environment,
                            project_constraints=first_row.project_constraints if first_row.project_constraints else None,
                        ),
                    )
                )

        if not module_install_specs:
            raise CouldNotResolveCode(agent_name, model_version)
        return module_install_specs
