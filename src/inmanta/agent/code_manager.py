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
from inmanta.protocol import Client
from inmanta.util.async_lru import async_lru_cache
from sqlalchemy import select

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
                models.ModulesForAgent.inmanta_module_name,
                models.ModulesForAgent.inmanta_module_version,
                models.InmantaModule.requirements,
                models.FilesInModule.python_module_name,
                models.FilesInModule.file_content_hash,
                models.FilesInModule.is_byte_code,
                models.File.content,
            )
            .join(models.InmantaModule)
            .join(models.FilesInModule)
            .join(models.File)
            .where(
                models.ModulesForAgent.environment == environment,
                models.ModulesForAgent.agent_name == agent_name,
                models.ModulesForAgent.cm_version == model_version,
            )
            .order_by(models.ModulesForAgent.inmanta_module_name)
        )

        async with data.get_session() as session:
            result = await session.execute(modules_for_agent)
            for module_name, rows in itertools.groupby(result.all(), key=lambda r: r.name):
                rows_list = list(rows)
                assert rows_list
                assert len({row.version for row in rows_list}) == 1
                ModuleInstallSpec(
                    module_name=module_name.name,
                    module_version=rows_list[0].version,
                    model_version=model_version,
                    blueprint=executor.ExecutorBlueprint(
                        pip_config=await self.get_pip_config(environment, model_version),
                        requirements=rows_list[0].requirements,
                        sources=[
                            ModuleSource(
                                metadata=ModuleSourceMetadata(
                                    name=row.python_module_name,
                                    hash_value=row.file_content_hash,
                                    is_byte_code=row.is_byte_code,
                                ),
                                source=row.content,
                            )
                            for row in rows_list
                        ],
                        python_version=sys.version_info[:2],
                    ),
                )

        if not module_install_specs:
            raise CouldNotResolveCode(agent_name, model_version)
        return module_install_specs
