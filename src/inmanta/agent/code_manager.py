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

import inmanta.loader
from inmanta import protocol
from inmanta.agent import executor
from inmanta.agent.executor import ResourceInstallSpec
from inmanta.data.model import LEGACY_PIP_DEFAULT, PipConfig
from inmanta.protocol import Client, SyncClient
from inmanta.types import ResourceType
from inmanta.util.async_lru import async_lru_cache

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

    @async_lru_cache(maxsize=1024)
    async def get_code_for_type(self, environment: uuid.UUID, version: int, resource_type: ResourceType) -> ResourceInstallSpec:
        result: protocol.Result = await self._client.get_source_code(environment, version, resource_type)
        if result.code == 200 and result.result is not None:
            sync_client = SyncClient(client=self._client, ioloop=asyncio.get_running_loop())
            requirements: set[str] = set()
            sources: list["inmanta.loader.ModuleSource"] = []
            # Encapsulate source code details in ``ModuleSource`` objects
            module_sources = result.result["data"]["sources"]
            project_constraints = result.result["data"]["project_constraints"]
            for source in module_sources:
                sources.append(
                    inmanta.loader.ModuleSource(
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
                    environment_id=environment,
                    pip_config=await self.get_pip_config(environment, version),
                    requirements=list(requirements),
                    sources=sources,
                    python_version=sys.version_info[:2],
                    project_constraints=project_constraints if project_constraints else None,
                ),
            )
            return resource_install_spec
        else:
            raise CouldNotResolveCode(resource_type, version, str(result.get_result()))

    async def get_code(
        self, environment: uuid.UUID, version: int, resource_types: Collection[ResourceType]
    ) -> tuple[Collection[ResourceInstallSpec], executor.FailedResources]:
        """
        Get the collection of installation specifications (i.e. pip config, python package dependencies,
        Inmanta modules sources) required to deploy a given version for the provided resource types.

        Expects at least one resource type.

        :return: Tuple of:
            - collection of ResourceInstallSpec for resource_types with valid handler code and pip config
            - set of invalid resource_types (no handler code and/or invalid pip config)
        """
        if not resource_types:
            raise ValueError(f"{self.__class__.__name__}.get_code() expects at least one resource type")

        resource_install_specs: list[ResourceInstallSpec] = []
        invalid_resources: executor.FailedResources = {}
        for resource_type in set(resource_types):
            try:
                resource_install_specs.append(await self.get_code_for_type(environment, version, resource_type))
            except CouldNotResolveCode as e:
                LOGGER.error(
                    "%s",
                    e.msg,
                )
                invalid_resources[resource_type] = e
            except Exception as e:
                LOGGER.error(
                    "Failed to get source code for %s version=%d",
                    resource_type,
                    version,
                    exc_info=True,
                )
                invalid_resources[resource_type] = e

        return resource_install_specs, invalid_resources
