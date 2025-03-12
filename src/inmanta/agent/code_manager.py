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

import asyncio
import logging
import sys
import uuid
from typing import Collection

import inmanta.data.sqlalchemy as models
from inmanta import protocol
from inmanta.agent import executor
from inmanta.agent.executor import ModuleInstallSpec, ResourceInstallSpec
from inmanta.data import get_session
from inmanta.data.model import LEGACY_PIP_DEFAULT, PipConfig
from inmanta.loader import ModuleSource
from inmanta.protocol import Client, SyncClient
from inmanta.types import ResourceType
from inmanta.util.async_lru import async_lru_cache
from sqlalchemy import and_, select

LOGGER = logging.getLogger(__name__)


class CouldNotResolveCode(Exception):

    def __init__(self, resource_type: str, version: int, error_message: str) -> None:
        self.msg = f"Failed to get source code for {resource_type} version={version}, result={error_message}"
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

    # async def get_code_for_agent(self, environment: uuid.UUID, model_version: int, agent_name: str) -> ResourceInstallSpec:
    #     async with get_connection_ctx_mgr() as conn:
    #         await data.Scheduler._execute_query(
    #             f"""
    #                 INSERT INTO {data.Scheduler.table_name()}
    #                 VALUES($1, NULL)
    #                 ON CONFLICT DO NOTHING
    #             """,
    #             self.environment,
    #             connection=con,
    #         )

    @async_lru_cache(maxsize=1024)
    async def get_code_for_type(self, environment: uuid.UUID, version: int, resource_type: ResourceType) -> ResourceInstallSpec:
        result: protocol.Result = await self._client.get_source_code(environment, version, resource_type)
        if result.code == 200 and result.result is not None:
            sync_client = SyncClient(client=self._client, ioloop=asyncio.get_running_loop())
            requirements: set[str] = set()
            sources: list["ModuleSource"] = []
            # Encapsulate source code details in ``ModuleSource`` objects
            for source in result.result["data"]:
                sources.append(
                    ModuleSource(
                        name=source["module_name"],
                        is_byte_code=source["is_byte_code"],
                        hash_value=source["hash"],
                        _client=sync_client,
                    )
                )
                requirements.update(source["requirements"])
            resource_install_spec = ResourceInstallSpec(
                resource_type,
                version,
                executor.ExecutorBlueprint(
                    pip_config=await self.get_pip_config(environment, version),
                    requirements=list(requirements),
                    sources=sources,
                    python_version=sys.version_info[:2],
                ),
            )
            return resource_install_spec
        else:
            raise CouldNotResolveCode(resource_type, version, str(result.get_result()))

    @async_lru_cache(maxsize=1024)
    async def get_code(self, environment: uuid.UUID, model_version: int, agent_name: str) -> Collection[ModuleInstallSpec]:
        """
        Get the collection of installation specifications (i.e. pip config, python package dependencies,
        Inmanta modules sources) required to deploy resources on a given agent for a given configuration
        model version.

        :return: Tuple of:
            - collection of ResourceInstallSpec for resource_types with valid handler code and pip config
            - set of invalid resource_types (no handler code and/or invalid pip config)
        """
        # async with get_session() as session:

        module_install_specs = []
        stmt = (
            select(
                models.ModulesForAgent.module_name,
                models.ModulesForAgent.module_version,
                models.ModulesForAgent.cm_version,
                models.Module.requirements,
                models.FilesInModule.file_content_hash,
            )
            .join_from(
                models.ModulesForAgent,
                models.Module,
                and_(
                    models.ModulesForAgent.module_name == models.Module.name,
                    models.ModulesForAgent.module_version == models.Module.version,
                    models.ModulesForAgent.environment == models.Module.environment,
                ),
            )
            .join_from(
                models.Module,
                models.FilesInModule,
                and_(
                    models.Module.name == models.FilesInModule.module_name,
                    models.Module.version == models.FilesInModule.module_version,
                    models.Module.environment == models.FilesInModule.environment,
                ),
            )
            .where(
                models.ModulesForAgent.environment == environment,
                models.ModulesForAgent.agent_name == agent_name,
                models.ModulesForAgent.cm_version == model_version,
            )
        )
        async with get_session() as session:
            result_execute = await session.execute(stmt)
            for res in result_execute.all():
                module_install_specs.append(
                    ModuleInstallSpec(
                        module_name=res.module_name,
                        module_version=res.module_version,
                        model_version=res.cm_version,
                        blueprint=executor.ExecutorBlueprint(
                            pip_config=await self.get_pip_config(environment, model_version),
                            requirements=res.requirements,
                            sources=[],  # TODO
                            python_version=sys.version_info[:2],
                        ),
                    )
                )
        return module_install_specs
        #
        # result: protocol.Result = await self._client.get_source_code(environment, version, resource_type)
        # if result.code == 200 and result.result is not None:
        #     sync_client = SyncClient(client=self._client, ioloop=asyncio.get_running_loop())
        #     requirements: set[str] = set()
        #     sources: list["ModuleSource"] = []
        #     # Encapsulate source code details in ``ModuleSource`` objects
        #     for source in result.result["data"]:
        #         sources.append(
        #             ModuleSource(
        #                 name=source["module_name"],
        #                 is_byte_code=source["is_byte_code"],
        #                 hash_value=source["hash"],
        #                 _client=sync_client,
        #             )
        #         )
        #         requirements.update(source["requirements"])
        #     resource_install_spec = ResourceInstallSpec(
        #         resource_type,
        #         version,
        #         executor.ExecutorBlueprint(
        #             pip_config=await self.get_pip_config(environment, model_version),
        #             requirements=list(requirements),
        #             sources=sources,
        #             python_version=sys.version_info[:2],
        #         ),
        #     )
        #     return resource_install_spec
        # else:
        #     raise CouldNotResolveCode(resource_type, version, str(result.get_result()))
