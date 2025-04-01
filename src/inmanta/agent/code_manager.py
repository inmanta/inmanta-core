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
from inmanta.data.model import LEGACY_PIP_DEFAULT, PipConfig
from inmanta.loader import ModuleSource, convert_module_path_to_namespace
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
                models.ModulesForAgent.cm_version,
                models.InmantaModule.requirements,
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
            .where(
                models.ModulesForAgent.environment == environment,
                models.ModulesForAgent.agent_name == agent_name,
                models.ModulesForAgent.cm_version == model_version,
            )
        )

        async with get_session() as session:
            result = await session.execute(modules_for_agent)
            for res in result.all():
                files_in_module = (
                    select(
                        models.FilesInModule.python_module_name,
                        models.FilesInModule.file_content_hash,
                        models.File.content,
                    )
                    .join_from(
                        models.FilesInModule,
                        models.File,
                    )
                    .where(
                        models.FilesInModule.environment == environment,
                        models.FilesInModule.inmanta_module_name == res.inmanta_module_name,
                        models.FilesInModule.inmanta_module_version == res.inmanta_module_version,
                    )
                )

                files = await session.execute(files_in_module)

                module_install_specs.append(
                    ModuleInstallSpec(
                        module_name=res.module_name,
                        module_version=res.module_version,
                        model_version=res.cm_version,
                        blueprint=executor.ExecutorBlueprint(
                            pip_config=await self.get_pip_config(environment, res.cm_version),
                            requirements=res.requirements,
                            sources=[
                                ModuleSource(
                                    name=convert_module_path_to_namespace(file.file_path),
                                    source=file.content,
                                    hash_value=file.file_content_hash,
                                    is_byte_code=False,
                                )
                                for file in files.all()
                            ],
                            python_version=sys.version_info[:2],
                        ),
                    )
                )

        if not module_install_specs:
            raise CouldNotResolveCode(agent_name, model_version)
        return module_install_specs
