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

import asyncio
import datetime
import typing
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, Callable, Coroutine, Mapping, Never, Optional, Sequence
from uuid import UUID

import asyncpg
from asyncpg import Connection

from inmanta import const
from inmanta.agent import Agent, executor
from inmanta.agent.executor import DeployReport, DryrunReport, GetFactReport, ResourceDetails, ResourceInstallSpec
from inmanta.const import Change
from inmanta.deploy import state
from inmanta.deploy.persistence import StateUpdateManager
from inmanta.deploy.scheduler import ModelVersion, ResourceScheduler
from inmanta.deploy.timers import TimerManager
from inmanta.protocol import Client
from inmanta.resources import Id
from inmanta.types import ResourceIdStr
from utils import DummyCodeManager

FAIL_DEPLOY: str = "fail_deploy"


class DummyExecutor(executor.Executor):
    """
    A dummy executor:
        * It doesn't actually do any deploys, but instead keeps track of the actions
          (execute, dryrun, get_facts, etc.) that were requested on it.
        * It reports a deploy as failed if the resource has an attribute with the value of the `FAIL_DEPLOY` variable.
        * It doesn't inspect dependencies' state, unlike the default handler
    """

    def __init__(self) -> None:
        self.execute_count = 0
        self.dry_run_count = 0
        self.facts_count = 0
        self.failed_resources = {}
        self.mock_versions = {}

    def reset_counters(self) -> None:
        self.execute_count = 0
        self.dry_run_count = 0
        self.facts_count = 0

    async def execute(
        self,
        action_id: uuid.UUID,
        gid: uuid.UUID,
        resource_details: ResourceDetails,
        reason: str,
        requires: Mapping[ResourceIdStr, const.HandlerResourceState],
    ) -> DeployReport:
        assert reason
        # Actual reason or test reason
        # The actual reasons are of the form `action because of reason`
        assert ("because" in reason) or ("Test" in reason)
        self.execute_count += 1
        result = (
            const.HandlerResourceState.failed
            if resource_details.attributes.get(FAIL_DEPLOY, False) is True
            else const.HandlerResourceState.deployed
        )
        return DeployReport(
            resource_details.rvid,
            action_id,
            resource_state=result,
            messages=[],
            changes={},
            change=Change.nochange,
        )

    async def dry_run(self, resources: Sequence[ResourceDetails], dry_run_id: uuid.UUID) -> None:
        self.dry_run_count += 1

    async def get_facts(self, resource: ResourceDetails) -> None:
        self.facts_count += 1

    async def open_version(self, version: int) -> None:
        pass

    async def close_version(self, version: int) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def join(self) -> None:
        pass


class ManagedExecutor(DummyExecutor):
    """
    Dummy executor that can be driven explicitly by a test case.

    Executor behavior must be controlled through the `deploys` property. It exposes a mapping from resource ids
    to futures. Simply set the desired outcome as the result on the appropriate future.
    """

    def __init__(self) -> None:
        super().__init__()
        self._deploys: dict[ResourceIdStr, asyncio.Future[const.HandlerResourceState]] = {}

    @property
    def deploys(self) -> Mapping[ResourceIdStr, asyncio.Future[const.HandlerResourceState]]:
        return self._deploys

    async def stop(self) -> None:
        # resolve hanging futures to prevent test hanging during teardown
        for deploy in self._deploys.values():
            deploy.set_result(const.HandlerResourceState.failed)

    async def execute(
        self,
        action_id: uuid.UUID,
        gid: uuid.UUID,
        resource_details: ResourceDetails,
        reason: str,
        requires: dict[ResourceIdStr, const.HandlerResourceState],
    ) -> DeployReport:
        assert resource_details.rid not in self._deploys
        self._deploys[resource_details.rid] = asyncio.get_running_loop().create_future()
        # wait until the test case sets desired resource state
        result: const.HandlerResourceState = await self._deploys[resource_details.rid]
        del self._deploys[resource_details.rid]
        self.execute_count += 1

        return DeployReport(
            resource_details.rvid,
            action_id,
            resource_state=const.HandlerResourceState(result),
            messages=[],
            changes={},
            change=Change.nochange,
        )


class DummyManager(executor.ExecutorManager[executor.Executor]):
    """
    An ExecutorManager that allows you to set a custom (mocked) executor for a certain agent.
    """

    def __init__(self):
        self.executors = {}

    def reset_executor_counters(self) -> None:
        for ex in self.executors.values():
            ex.reset_counters()

    def register_managed_executor(self, agent_name: str) -> ManagedExecutor:
        executor = ManagedExecutor()
        self.executors[agent_name] = executor
        return executor

    async def get_executor(
        self, agent_name: str, agent_uri: str, code: typing.Collection[ResourceInstallSpec]
    ) -> DummyExecutor:
        if not code:
            raise ValueError(f"{self.__class__.__name__}.get_executor() expects at least one resource install specification")
        if agent_name not in self.executors:
            self.executors[agent_name] = DummyExecutor()
        return self.executors[agent_name]

    async def stop_for_agent(self, agent_name: str) -> list[DummyExecutor]:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        for ex in self.executors.values():
            await ex.stop()

    async def join(self, thread_pool_finalizer: list[ThreadPoolExecutor], timeout: float) -> None:
        pass


state_translation_table: dict[const.ResourceState, tuple[state.DeployResult, state.Blocked, state.Compliance]] = {
    # A table to translate the old states into the new states
    # None means don't care, mostly used for values we can't derive from the old state
    const.ResourceState.unavailable: (None, state.Blocked.NOT_BLOCKED, state.Compliance.NON_COMPLIANT),
    const.ResourceState.skipped: (state.DeployResult.SKIPPED, None, None),
    const.ResourceState.dry: (None, None, None),  # don't care
    const.ResourceState.deployed: (state.DeployResult.DEPLOYED, state.Blocked.NOT_BLOCKED, None),
    const.ResourceState.failed: (state.DeployResult.FAILED, state.Blocked.NOT_BLOCKED, None),
    const.ResourceState.deploying: (None, state.Blocked.NOT_BLOCKED, None),
    const.ResourceState.available: (None, state.Blocked.NOT_BLOCKED, state.Compliance.HAS_UPDATE),
    const.ResourceState.undefined: (None, state.Blocked.BLOCKED, state.Compliance.UNDEFINED),
    const.ResourceState.skipped_for_undefined: (None, state.Blocked.BLOCKED, None),
}


class DummyTimerManager(TimerManager):
    async def install_timer(
        self, resource: ResourceIdStr, is_dirty: bool, action: Callable[..., Coroutine[Any, Any, None]]
    ) -> None:
        pass

    def update_timer(self, resource: ResourceIdStr, *, state: state.ResourceState) -> None:
        pass

    def stop_timer(self, resource: ResourceIdStr) -> None:
        pass

    def _trigger_global_deploy(self, cron_expression: str) -> None:
        pass

    def _trigger_global_repair(self, cron_expression: str) -> None:
        pass


class DummyStateManager(StateUpdateManager):

    def __init__(self):
        self.state: dict[ResourceIdStr, const.ResourceState] = {}
        # latest deploy result for each resource
        self.deploys: dict[ResourceIdStr, DeployReport] = {}

    async def send_in_progress(self, action_id: UUID, resource_id: Id) -> None:
        self.state[resource_id.resource_str()] = const.ResourceState.deploying

    async def send_deploy_done(
        self,
        attribute_hash: str,
        result: DeployReport,
        state: state.ResourceState,
        *,
        started: datetime.datetime,
        finished: datetime.datetime,
    ) -> None:
        self.state[result.resource_id] = result.status
        self.deploys[result.resource_id] = result

    def check_with_scheduler(self, scheduler: ResourceScheduler) -> None:
        """Verify that the state we collected corresponds to the state as known by the scheduler"""
        assert self.state
        for resource, cstate in self.state.items():
            deploy_result, blocked, status = state_translation_table[cstate]
            if deploy_result:
                assert scheduler._state.resource_state[resource].last_deploy_result == deploy_result
            if blocked:
                assert scheduler._state.resource_state[resource].blocked == blocked
            if status:
                assert scheduler._state.resource_state[resource].compliance == status

    def set_parameters(self, fact_result: GetFactReport) -> None:
        pass

    async def dryrun_update(self, env: UUID, dryrun_result: DryrunReport) -> None:
        self.state[Id.parse_id(dryrun_result.rvid).resource_str()] = const.ResourceState.dry

    async def update_resource_intent(
        self,
        environment: UUID,
        intent: dict[ResourceIdStr, tuple[state.ResourceState, state.ResourceIntent]],
        update_blocked_state: bool,
        connection: Optional[Connection] = None,
    ) -> None:
        pass

    async def set_last_processed_model_version(
        self, environment: UUID, version: int, connection: Optional[Connection] = None
    ) -> None:
        pass

    @asynccontextmanager
    async def get_connection(self, connection: Optional[Connection] = None) -> AbstractAsyncContextManager[Connection]:
        yield DummyDatabaseConnection()


class TestScheduler(ResourceScheduler):
    def __init__(self, environment: uuid.UUID, executor_manager: executor.ExecutorManager[executor.Executor], client: Client):
        super().__init__(environment, executor_manager, client)
        # Bypass DB
        self.executor_manager = self.executor_manager
        self.code_manager = DummyCodeManager(client)
        self.mock_versions = {}
        self.state_update_manager = DummyStateManager()
        self._timer_manager = DummyTimerManager(self)

    async def read_version(
        self,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        pass

    async def reset_resource_state(self) -> None:
        pass

    async def load_timer_settings(self) -> None:
        pass

    async def _initialize(
        self,
    ) -> None:
        self._running = True

    async def should_be_running(self) -> bool:
        return True

    async def should_runner_be_running(self, endpoint: str) -> bool:
        return True

    async def all_paused_agents(self) -> set[str]:
        return set()

    async def _get_single_model_version_from_db(
        self,
        *,
        version: int | None = None,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> ModelVersion:
        if version is None:
            raise NotImplementedError(
                "The scheduler mock does not implement _get_single_model_version_from_db() without version argument"
            )
        return ModelVersion(
            version=version,
            resources=self.mock_versions[version],
            requires={},
            undefined=set(),
        )


class TestAgent(Agent):
    """
    An agent (scheduler) that mock everything:

    * It uses a mocked ExecutorManager.
    * A dummy code CodeManager.
    * It mock the methods that interact with the database.

    This allows you to:
       * Test the interactions between the scheduler and the executor, without the overhead of any other components,
         like the Inmanta server.
       * The mocked components allow inspection of the deploy actions done by the executor.
    """

    def __init__(
        self,
        environment: Optional[uuid.UUID] = None,
    ):
        super().__init__(environment)
        self.executor_manager = DummyManager()
        self.scheduler = TestScheduler(self.scheduler.environment, self.executor_manager, self.scheduler.client)

    async def load_environment_settings(self) -> None:
        pass


class DummyDatabaseConnection:

    @asynccontextmanager
    async def transaction(self):
        yield None

    async def execute(self, *args, **kwargs) -> Never:
        raise NotImplementedError(
            "Tried to execute a query on the dummy database connection. This likely indicates a bug in the"
            " test framework. All queries should be mocked out when using the dummy database connection."
        )

    async def executemany(self, *args, **kwargs) -> Never:
        await self.execute()
