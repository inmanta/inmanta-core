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

import concurrent
import typing
import uuid
from collections.abc import Mapping
from copy import deepcopy

from inmanta import const
from inmanta.agent import executor
from inmanta.agent.executor import DeployReport, DryrunReport, GetFactReport, ModuleInstallSpec, ResourceDetails
from inmanta.types import ResourceIdStr


class WriteBarierExecutor(executor.Executor):
    """In process executor that makes sure the resources are not mutated by the underlying executor"""

    def __init__(self, delegate: executor.Executor) -> None:
        self.delegate = delegate

    async def execute(
        self,
        action_id: uuid.UUID,
        gid: uuid.UUID,
        resource_details: ResourceDetails,
        reason: str,
        requires: Mapping[ResourceIdStr, const.ResourceState],
    ) -> DeployReport:
        return await self.delegate.execute(
            action_id,
            gid,
            deepcopy(resource_details),
            reason,
            deepcopy(requires),
        )

    async def dry_run(
        self,
        resource: ResourceDetails,
        dry_run_id: uuid.UUID,
    ) -> DryrunReport:
        return await self.delegate.dry_run(deepcopy(resource), dry_run_id)

    async def get_facts(self, resource: ResourceDetails) -> GetFactReport:
        return await self.delegate.get_facts(deepcopy(resource))

    async def join(self) -> None:
        await self.delegate.join()


class WriteBarierExecutorManager(executor.ExecutorManager[WriteBarierExecutor]):
    """Executor manager wrapping all executors in a write barier"""

    def __init__(self, delegate: executor.ExecutorManager[executor.Executor]) -> None:
        self.delegate = delegate

    async def get_executor(
        self, agent_name: str, agent_uri: str, code: typing.Collection[ModuleInstallSpec]
    ) -> WriteBarierExecutor:
        if not code:
            raise ValueError(f"{self.__class__.__name__}.get_executor() expects at least one resource install specification")
        return WriteBarierExecutor(await self.delegate.get_executor(agent_name, agent_uri, code))

    def get_environment_manager(self) -> executor.VirtualEnvironmentManager | None:
        return self.delegate.get_environment_manager()

    async def stop_all_executors(self) -> list[WriteBarierExecutor]:
        return [WriteBarierExecutor(e) for e in await self.delegate.stop_all_executors()]

    async def stop_for_agent(self, agent_name: str) -> list[WriteBarierExecutor]:
        return [WriteBarierExecutor(e) for e in await self.delegate.stop_for_agent(agent_name)]

    async def start(self) -> None:
        await self.delegate.start()

    async def stop(self) -> None:
        await self.delegate.stop()

    async def join(self, thread_pool_finalizer: list[concurrent.futures.ThreadPoolExecutor], timeout: float) -> None:
        await self.delegate.join(thread_pool_finalizer, timeout)
