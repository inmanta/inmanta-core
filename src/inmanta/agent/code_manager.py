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

import logging
import sys
import uuid
from typing import Collection

import inmanta.data.sqlalchemy as models
from inmanta.agent import executor
from inmanta.agent.executor import ModuleInstallSpec
from inmanta.data import get_session
from inmanta.data.model import LEGACY_PIP_DEFAULT, InmantaModuleDTO, ModuleSource, ModuleSourceMetadata, PipConfig
from inmanta.protocol import Client
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

    def __init__(self, client: Client) -> None:
        self._client = client

    @async_lru_cache(maxsize=5)
    async def get_pip_config(self, environment: uuid.UUID, version: int) -> PipConfig:
        response = await self._client.get_pip_config(tid=environment, version=version)
        if response.code != 200:
            raise Exception("Could not get pip config from server " + str(response.result))
        assert response.result is not None  # mypy
        pip_config = response.result["data"]
        if pip_config is None:
            return LEGACY_PIP_DEFAULT
        return PipConfig(**pip_config)

    @async_lru_cache(maxsize=1024)
    async def get_code(self, environment: uuid.UUID, model_version: int, agent_name: str) -> Collection[ModuleInstallSpec]:
        """
        Get the collection of installation specifications (i.e. pip config, python package dependencies,
        Inmanta modules sources) required to deploy resources on a given agent for a given configuration
        model version.

        :return: collection of ModuleInstallSpec for this agent and this model version.
        """

        module_install_specs = []
        modules_for_agent = (
            select(
                models.ModulesForAgent.inmanta_module_name,
                models.ModulesForAgent.inmanta_module_version,
                models.InmantaModule.requirements,
                models.FilesInModule.python_module_name,
                models.FilesInModule.file_content_hash,
                models.FilesInModule.is_byte_code,
                models.File.content,
            )
            .join_from(
                models.ModulesForAgent,
                models.InmantaModule,
                and_(
                    models.ModulesForAgent.inmanta_module_name == models.InmantaModule.name,
                    models.ModulesForAgent.inmanta_module_version == models.InmantaModule.version,
                    models.ModulesForAgent.environment == models.InmantaModule.environment,
                ),
            )
            .join_from(
                models.InmantaModule,
                models.FilesInModule,
                and_(
                    models.InmantaModule.name == models.FilesInModule.inmanta_module_name,
                    models.InmantaModule.version == models.FilesInModule.inmanta_module_version,
                    models.InmantaModule.environment == models.FilesInModule.environment,
                ),
            )
            .join_from(
                models.FilesInModule,
                models.File,
                and_(
                    models.FilesInModule.file_content_hash == models.File.content_hash,
                    models.InmantaModule.version == models.FilesInModule.inmanta_module_version,
                    models.InmantaModule.environment == models.FilesInModule.environment,
                ),
            )
            .where(
                models.ModulesForAgent.environment == environment,
                models.ModulesForAgent.agent_name == agent_name,
                models.ModulesForAgent.cm_version == model_version,
            )
            .order_by(models.ModulesForAgent.inmanta_module_name)
        )

        previous_inmanta_module: InmantaModuleDTO = InmantaModuleDTO(
            name="",
            version="",
            files_in_module=[],
            requirements=[],
            for_agents=[],
        )
        previous_module_sources: list[ModuleSource] = []
        async with get_session() as session:
            result = await session.execute(modules_for_agent)
            for res in result.all():
                current_row_module_name = res.inmanta_module_name

                if current_row_module_name != previous_inmanta_module.name:
                    if previous_module_sources:
                        module_install_specs.append(
                            ModuleInstallSpec(
                                module_name=previous_inmanta_module.name,
                                module_version=previous_inmanta_module.version,
                                model_version=model_version,
                                blueprint=executor.ExecutorBlueprint(
                                    pip_config=await self.get_pip_config(environment, model_version),
                                    requirements=previous_inmanta_module.requirements,
                                    sources=previous_module_sources,
                                    python_version=sys.version_info[:2],
                                ),
                            )
                        )
                    previous_inmanta_module = InmantaModuleDTO(
                        name=current_row_module_name,
                        version=res.inmanta_module_version,
                        files_in_module=[],
                        requirements=res.requirements,
                        for_agents=[],
                    )
                    previous_module_sources = [
                        ModuleSource(
                            metadata=ModuleSourceMetadata(
                                name=res.python_module_name,
                                hash_value=res.file_content_hash,
                                is_byte_code=res.is_byte_code,
                            ),
                            source=res.content,
                        )
                    ]
                else:
                    previous_module_sources.append(
                        ModuleSource(
                            metadata=ModuleSourceMetadata(
                                name=res.python_module_name,
                                hash_value=res.file_content_hash,
                                is_byte_code=res.is_byte_code,
                            ),
                            source=res.content,
                        )
                    )
            if previous_module_sources:
                module_install_specs.append(
                    ModuleInstallSpec(
                        module_name=previous_inmanta_module.name,
                        module_version=previous_inmanta_module.version,
                        model_version=model_version,
                        blueprint=executor.ExecutorBlueprint(
                            pip_config=await self.get_pip_config(environment, model_version),
                            requirements=previous_inmanta_module.requirements,
                            sources=previous_module_sources,
                            python_version=sys.version_info[:2],
                        ),
                    )
                )

        if not module_install_specs:
            raise CouldNotResolveCode(agent_name, model_version)
        return module_install_specs
