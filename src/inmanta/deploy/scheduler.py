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

import abc
import asyncio
import contextlib
import datetime
import enum
import itertools
import logging
import typing
import uuid
from abc import abstractmethod
from collections.abc import Collection, Mapping, Sequence, Set
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Optional, Self

import asyncpg

from inmanta import const, data
from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.data import ConfigurationModel, Environment
from inmanta.data.model import Discrepancy, SchedulerStatusReport
from inmanta.deploy import timers, work
from inmanta.deploy.persistence import ToDbUpdateManager
from inmanta.deploy.state import AgentStatus, Blocked, Compliance, DeployResult, ModelState, ResourceIntent, ResourceState
from inmanta.deploy.tasks import Deploy, DryRun, RefreshFact, Task
from inmanta.deploy.work import TaskPriority
from inmanta.protocol import Client
from inmanta.resources import Id
from inmanta.types import ResourceIdStr, ResourceType, ResourceVersionIdStr

LOGGER = logging.getLogger(__name__)
NB_ITERATIONS_PASS_IO_LOOP: int = 100


class StaleResource(Exception):
    """
    An exception that indicates that a resource is not managed by the orchestrator.
    """

    pass


@dataclass(frozen=True)
class ResourceVersionIntent:
    """
    Resource intent for a single resource at a specific version.

    Includes model version and resource intent, as well as the full set of resource types that live on the resource's agent.
    This list will never be empty, and will always include the resource's own type.
    """

    model_version: int
    intent: ResourceIntent
    # All types that live on this agent. Required to ensure that the executor loads the appropriate code for this version,
    # even if new versions come in before the executor is constructed.
    # Should be dropped once this functionality moves to the code manager.
    # At that point, the state's types_per_agent can be dropped as well.
    all_types_for_agent: Collection[ResourceType]


@dataclass(frozen=True)
class DeployIntent(ResourceVersionIntent):
    """
    Deploy intent for a single resource. Includes dependency state to provide to the resource handler.
    """

    dependencies: Mapping[ResourceIdStr, const.ResourceState]
    deploy_start: datetime.datetime


class ResourceIntentChangeType(Enum):
    """
    A state change for a single resource's intent. Represents in which way, if any, a resource changed in a new model version
    versus the currently managed one.

    Internal class meant to unambiguously categorize how resources have changed when processing multiple model versions at once.
    """

    NEW = enum.auto()
    """
    To be considered a new resource, even if one with the same resource id is already managed in the current version.
    e.g. if multiple versions have been released since the currently managed one, and in those a resource is deleted,
    then reappears, we consider it new for all purposes.
    """

    UPDATED = enum.auto()
    """
    The resource has an update to its desired state, this may include a transition from defined to undefined or vice versa.
    """

    DELETED = enum.auto()
    """
    The resource was deleted.
    """


class _ResourceIntentChange(abc.ABC):
    change: ClassVar[ResourceIntentChangeType]


class New(_ResourceIntentChange):
    change = ResourceIntentChangeType.NEW


class Updated(_ResourceIntentChange):
    change = ResourceIntentChangeType.UPDATED


@dataclass(frozen=True, kw_only=True)
class Deleted(_ResourceIntentChange):
    change: ClassVar[ResourceIntentChangeType] = ResourceIntentChangeType.DELETED

    last_seen_version: int


type ResourceIntentChange = New | Updated | Deleted


class ResourceRecord(typing.TypedDict):
    """
    A dict representing a resource database record with all fields relevant for the scheduler.

    Purely for type documentation purposes, as we can't statically verify it, considering asyncpg's limitations.
    """

    resource_id: str
    status: str
    attributes: Mapping[str, object]
    attribute_hash: str


@dataclass(frozen=True)
class ModelVersion:
    """
    A version of the model to be managed by the scheduler.
    """

    version: int
    resources: Mapping[ResourceIdStr, ResourceIntent]
    requires: Mapping[ResourceIdStr, Set[ResourceIdStr]]
    undefined: Set[ResourceIdStr]

    @classmethod
    def from_db_records(cls: type[Self], version: int, resources: Collection[ResourceRecord]) -> Self:
        return cls(
            version=version,
            resources={
                ResourceIdStr(resource["resource_id"]): ResourceIntent(
                    resource_id=ResourceIdStr(resource["resource_id"]),
                    attribute_hash=resource["attribute_hash"],
                    attributes=resource["attributes"],
                )
                for resource in resources
            },
            requires={
                ResourceIdStr(resource["resource_id"]): {
                    Id.parse_id(req).resource_str() for req in resource["attributes"].get("requires", [])
                }
                for resource in resources
            },
            undefined={
                ResourceIdStr(resource["resource_id"])
                for resource in resources
                if const.ResourceState(resource["status"]) is const.ResourceState.undefined
            },
        )


class TaskManager(abc.ABC):
    """
    Interface for communication with tasks (deploy.task.Task). Offers methods to inspect intent and to report task results.
    """

    environment: uuid.UUID
    client: Client
    code_manager: CodeManager
    executor_manager: executor.ExecutorManager[executor.Executor]

    @abstractmethod
    async def get_resource_version_intent(
        self,
        resource: ResourceIdStr,
    ) -> Optional[ResourceVersionIntent]:
        """
        Returns the current version and the intent for the given resource, or None if it is not (anymore) managed by the
        scheduler.

        Acquires appropriate locks.
        """

    @abstractmethod
    async def deploy_start(
        self,
        action_id: uuid.UUID,
        resource: ResourceIdStr,
    ) -> Optional[DeployIntent]:
        """
        Register the start of deployment for the given resource and return its current version intent
        along with the last non-deploying state for its dependencies, or None if it is not (anymore)
        managed by the scheduler.

        If this method returns an intent, the caller must also call deploy_done() at the end of the deploy attempt.

        Acquires appropriate locks.
        """

    @abstractmethod
    async def deploy_done(self, deploy_intent: DeployIntent, report: executor.DeployReport) -> None:
        """
        Register the end of deployment for the given resource: update the resource state based on the deployment result
        and inform its dependencies that deployment is finished. Depending on how fresh the intent is (compared to what is
        currently managed, limited (for outdated) or no (for fully stale) scheduler state may be updated.

        Acquires appropriate locks

        :param deploy_intent: The resource's deploy intent as returned by deploy_start().
        :param report: The DeployReport object describing the result of the deployment.
        """

    @abstractmethod
    async def dryrun_done(self, report: executor.DryrunReport) -> None:
        """
        Report the result of a dry-run.
        """

    @abstractmethod
    async def fact_refresh_done(self, report: executor.GetFactReport) -> None:
        """
        Report the result of a fact refresh.
        """


class TaskRunner:
    def __init__(self, endpoint: str, scheduler: "ResourceScheduler"):
        self.endpoint = endpoint
        self.status = AgentStatus.STOPPED
        self._scheduler = scheduler
        self._task: typing.Optional[asyncio.Task[None]] = None
        self._notify_tasks: dict[uuid.UUID, asyncio.Task[None]] = {}
        # Lock to prevent race conditions on the running state of this TaskRunner
        self._notify_lock = asyncio.Lock()

    async def start(self) -> None:
        assert (
            self._task is None or self._task.done()
        ), f"Task Runner {self.endpoint} is trying to start twice, this should not happen"
        self.status = AgentStatus.STARTED
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self.status = AgentStatus.STOPPING
        for task in self._notify_tasks.values():
            if not task.done():
                task.cancel()

    async def join(self) -> None:
        assert not self.is_running(), "Joining worker that is not stopped"
        if self._task is None or self._task.done():
            return
        await self._task
        await asyncio.gather(*list(self._notify_tasks.values()), return_exceptions=True)

    async def notify(self, task_id: uuid.UUID | None = None) -> None:
        """
        Method to notify the runner that something has changed in the DB. This method will fetch the new information
        regarding the environment and the information related to the runner (agent). Depending on the desired state of the
        agent, it will either stop / start the agent or do nothing

        :param task_id: Is not None if this task was started using the `notify_sync()` method. It's used to clean up the
                        reference to the associated asyncio.Task object in `self._notify_tasks`. This value is None otherwise.
        """
        try:
            async with self._notify_lock:
                should_be_running = (
                    await self._scheduler.should_be_running()
                    and await self._scheduler.should_runner_be_running(endpoint=self.endpoint)
                )

                match self.status:
                    case AgentStatus.STARTED if not should_be_running:
                        await self.stop()
                    case AgentStatus.STOPPED if should_be_running:
                        await self.start()
                    case AgentStatus.STOPPING if should_be_running:
                        self.status = AgentStatus.STARTED
        finally:
            if task_id:
                del self._notify_tasks[task_id]

    def notify_sync(self) -> None:
        """
        Method to notify the runner that something has changed in the DB in a synchronous manner.
        """
        # We save it to be sure that the task will not be GC
        task_id = uuid.uuid4()
        task = asyncio.create_task(self.notify(task_id))
        self._notify_tasks[task_id] = task

    async def _run(self) -> None:
        """Main loop for one agent. It will first fetch or create its actual state from the DB to make sure that it's
        allowed to run."""
        while self._scheduler._running and self.status == AgentStatus.STARTED:
            work_item: work.MotivatedTask[Task] = await self._scheduler._work.agent_queues.queue_get(self.endpoint)
            try:
                await work_item.task.execute(self._scheduler, self.endpoint, work_item.reason)
            except Exception:
                LOGGER.exception(
                    "Task %s for agent %s has failed and the exception was not properly handled", work_item.task, self.endpoint
                )
            self._scheduler._work.agent_queues.task_done(self.endpoint, work_item.task)

        self.status = AgentStatus.STOPPED

    def is_running(self) -> bool:
        return self.status == AgentStatus.STARTED


class ResourceScheduler(TaskManager):
    """
    Scheduler for resource actions. Reads resource state from the database and accepts deploy, dry-run, ... requests from the
    server. Schedules these requests as tasks according to priorities and, in case of deploy tasks, requires-provides edges.

    The scheduler expects to be notified by the server whenever a new version is released.
    """

    def __init__(
        self, environment: uuid.UUID, executor_manager: executor.ExecutorManager[executor.Executor], client: Client
    ) -> None:
        """
        :param environment: the environment we work for
        :param executor_manager: the executor manager that will provide us with executors
        :param client: connection to the server
        """
        # state and work may be reassigned during initialize
        self._state: ModelState = ModelState(version=0)
        self._work: work.ScheduledWork = work.ScheduledWork(
            requires=self._state.requires.requires_view(),
            provides=self._state.requires.provides_view(),
            new_agent_notify=self._create_agent,
        )

        # We uphold two locks to prevent concurrency conflicts between external events (e.g. new version or deploy request)
        # and the task executor background tasks.
        #
        # - lock to block scheduler state access (this includes model state, scheduled work and resource timers management)
        #   during scheduler-wide state updates (e.g. trigger deploy). A single lock suffices since all state accesses
        #   (both read and write) by the task runners are short, synchronous operations (and therefore we wouldn't gain
        #   anything by allowing multiple readers).
        self._scheduler_lock: asyncio.Lock = asyncio.Lock()
        # - lock to serialize updates to the scheduler's intent (version, attributes, ...), e.g. process a new version.
        self._intent_lock: asyncio.Lock = asyncio.Lock()

        self._running = False
        # Agent name to worker task
        # here to prevent it from being GC-ed
        self._workers: dict[str, TaskRunner] = {}
        # Set of resources for which a concrete non-stale deploy is in progress, i.e. we've committed for a given intent and
        # that intent still reflects the latest resource intent
        # Apart from the obvious, this differs from the agent queues' in-progress deploys in the sense that those are simply
        # tasks that have been picked up while this set contains only those tasks for which we've already committed. For each
        # deploy task, there is a (typically) short window of time where it's considered in progress by the agent queue, but
        # it has not yet started on the actual deploy, i.e. it will still see updates to the resource intent.
        self._deploying_latest: set[ResourceIdStr] = set()
        # Set of orphaned resources for which a deploy is in progress, i.e. a deploy for a resource that went from managed to
        # unmanaged (even if it became managed again afterward, in which case it's considered a new resource that happens to
        # share the resource id)
        self._deploying_unmanaged: set[ResourceIdStr] = set()

        self.environment = environment
        self.client = client
        self.code_manager = CodeManager(client)
        self.executor_manager = executor_manager
        self.state_update_manager = ToDbUpdateManager(client, environment)

        self._timer_manager = timers.TimerManager(self)

        self._deployment_suspended: bool = False

    async def _reset(self) -> None:
        """
        Clear out all state and start empty

        only allowed when ResourceScheduler is not running
        """
        assert not self._running
        self._state.reset()
        self._work.reset()
        # Ensure we are down
        for worker in self._workers.values():
            # We have no timeout here
            # This can potentially hang when an executor hangs
            # However, the stop should forcefully kill the executor
            # This will kill the connection and free the worker
            await worker.join()
        self._workers.clear()
        self._deploying_latest.clear()
        self._deploying_unmanaged.clear()
        await self._timer_manager.reset()

    async def start(self) -> None:
        if self._running:
            return
        LOGGER.debug("Starting resource scheduler for environment %s", str(self.environment))
        await self._reset()
        await self.reset_resource_state()

        await self._initialize()

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        await self._timer_manager.stop()
        # Ensure workers go down
        # First stop them
        for worker in self._workers.values():
            await worker.stop()
        # Then wake them up to receive the stop
        self._work.agent_queues.send_shutdown()

    async def join(self) -> None:
        await asyncio.gather(*[worker.join() for worker in self._workers.values()])
        await self._timer_manager.join()

    async def reset_resource_state(self) -> None:
        """
        Update resources in the latest released version of the model stuck in "deploying" state.
        This can occur when the Scheduler is killed in the middle of a deployment.
        """

        await data.Resource.reset_resource_state(self.environment)

    async def load_timer_settings(self) -> None:
        """Update the timer manager after an update of the timer config"""
        await self._timer_manager.reload_config()

    async def reload_all_timers(self) -> None:
        """
        Internal, request all timers to reload. For all known resources,
        either updates or stops its associated timer, depending on its state.
        """
        # Get lock
        async with self._scheduler_lock:
            for resource, state in self._state.resource_state.items():
                deploy = Deploy(resource=resource)
                if (
                    deploy in self._work.agent_queues
                    or deploy in self._work.agent_queues.in_progress
                    or resource in self._work._waiting
                ):
                    self._timer_manager.stop_timer(resource)
                self._timer_manager.update_timer(resource, state=state)

    async def _initialize(self) -> None:
        """
        Initialize the scheduler state and continue the deployment where we were before the server was shutdown.
        Marks scheduler as running and triggers first deploys.
        """
        await self._timer_manager.initialize()
        # do not start a transaction because:
        # 1. nothing we do here before read_version is inherently transactional: the only write is atomic, and reads do not
        #   benefit from READ COMMITTED (default) isolation level.
        # 2. read_version expects to receive a connection outside of a transaction context
        async with self.state_update_manager.get_connection() as con:
            # Make sure there is an entry for this scheduler in the scheduler database table
            await data.Scheduler._execute_query(
                f"""
                    INSERT INTO {data.Scheduler.table_name()}
                    VALUES($1, NULL)
                    ON CONFLICT DO NOTHING
                """,
                self.environment,
                connection=con,
            )

            environment: Optional[data.Environment] = await data.Environment.get_by_id(self.environment, connection=con)
            assert environment is not None
            should_restore_state: bool = not typing.cast(
                bool, await environment.get(data.RESET_DEPLOY_PROGRESS_ON_START, connection=con)
            )

            # Check if we can restore the scheduler state from a previous run
            restored_state: Optional[ModelState] = (
                await ModelState.create_from_db(self.environment, connection=con) if should_restore_state else None
            )
            if restored_state is not None:
                LOGGER.debug("Scheduler initialization: restoring internal state")
                # Restore scheduler state like it was before the scheduler went down
                self._state = restored_state
                self._work = work.ScheduledWork(
                    requires=self._state.requires.requires_view(),
                    provides=self._state.requires.provides_view(),
                    new_agent_notify=self._create_agent,
                )
                restored_version: int = self._state.version
                # Set running flag because we're ready to start accepting tasks.
                # Set before scheduling first tasks because many methods (e.g. read_version) skip silently when not running
                LOGGER.debug("Scheduler initialization: resuming deploy operations and reading latest model version")
                self._running = True
                # All resources get a timer
                await self.read_version(connection=con)
                async with self._scheduler_lock:
                    LOGGER.debug("Scheduler initialization: setting up initial deploy timers")
                    self._timer_manager.update_timers(self._state.intent.keys() - self._state.dirty)

                if self._state.version == restored_version:
                    # no new version was present. Simply trigger a deploy for everything that's not in a known good state
                    LOGGER.debug("Scheduler initialization: triggering deploy")
                    await self.deploy(
                        reason="the resource scheduler was started",
                        priority=TaskPriority.INTERVAL_DEPLOY,
                    )
            else:
                # This case can occur in three different situations:
                #   1 A model version has been released, but the scheduler didn't process any version yet.
                #     In this case there is no scheduler state to restore.
                #   2 The last processed version has been deleted since the scheduler was last running
                #   3 We migrated the Inmanta server from an old version, that didn't have the resource state
                #     tracking in the database, to a version that does. To cover this case, we rely on the
                #     increment calculation to determine which resources have to be considered dirty and which
                #     not. This migration code path can be removed in a later major version.
                #
                # In cases 1 and 2, all resources are expected to be in the increment (scheduler hasn't processed any versions
                # means we haven't ever deployed anything yet), so those could be covered by simply reading in only the latest
                # version, or by keeping state as is and calling into normal read_version() flow. However, while the migration
                # path is still required for backwards compatibility (3) anyway, we unifi the three cases for simplicity.

                # Set running flag because we're ready to start accepting tasks.
                # Set before scheduling first tasks because many methods (e.g. read_version) skip silently when not running
                LOGGER.debug("Scheduler initialization: resuming deploy operations and reading latest model version")
                self._running = True
                await self._recover_scheduler_state_using_increments_calculation(connection=con)
            LOGGER.debug("Scheduler initialization: finished initialization, scheduler is fully up and running")

    async def _recover_scheduler_state_using_increments_calculation(self, *, connection: asyncpg.connection.Connection) -> None:
        """
        This method exists for backwards compatibility reasons. It initializes the scheduler state
        by relying on the increments calculation logic. This method starts the deployment process.

        :param connection: Connection to use for db operations. Should not be in a transaction context.
        """
        try:
            model: ModelVersion = await self._get_single_model_version_from_db(connection=connection)
        except KeyError:
            # No model version has been released yet.
            return
        LOGGER.debug("Read latest model version %d", model.version)
        # Rely on the incremental calculation to determine which resources should be deployed and which not.
        up_to_date_resources: Set[ResourceIdStr]
        up_to_date_resources, last_deploy_time = await ConfigurationModel.get_last_deployed_and_neg_increment(
            self.environment, model.version, connection=connection
        )
        await self._new_version(
            [model],
            up_to_date_resources=up_to_date_resources,
            last_deploy_time=last_deploy_time,
            reason="the scheduler was started",
            connection=connection,
        )

    async def deploy(
        self,
        *,
        reason: str,
        priority: TaskPriority = TaskPriority.USER_DEPLOY,
        agent: Optional[str] = None,
    ) -> None:
        """
        Trigger a deploy

        :param agent: If given, deploy resources only for this agent. Otherwise deploy for all agents.
        """
        if not self._running:
            LOGGER.debug("Ignoring deploy request for halted resource scheduler")
            return
        async with self._scheduler_lock:
            to_deploy: Set[ResourceIdStr] = (
                self._state.dirty if agent is None else self._state.dirty & self._state.resources_by_agent.get(agent, set())
            )
            if agent is not None:
                LOGGER.debug("Triggering deploy for %d resources on agent %s because %s", len(to_deploy), agent, reason)
            else:
                LOGGER.debug("Triggering deploy for %d resources because %s", len(to_deploy), reason)
            self._timer_manager.stop_timers(to_deploy)
            self._work.deploy_with_context(to_deploy, reason=reason, priority=priority, deploying=self._deploying_latest)

    async def repair(
        self,
        *,
        reason: str,
        priority: TaskPriority = TaskPriority.USER_REPAIR,
        agent: Optional[str] = None,
    ) -> None:
        """
        Trigger a repair, i.e. mark all unblocked resources as dirty, then trigger a deploy.

        :param agent: If given, repair resources only for this agent. Otherwise repair for all agents.
        """

        def should_deploy_resource(resource: ResourceIdStr) -> bool:
            if (resource_state := self._state.resource_state.get(resource)) is not None:
                # For now, we repair even resources marked as TEMPORARILY_BLOCKED, just in case our assumptions are wrong
                # We will relax this once we have more confidence in the correct tracking of the state (#8580)
                return resource_state.blocked is not Blocked.BLOCKED
            # No state was found for this resource. Should probably not happen
            # but err on the side of caution and mark for redeploy.
            return True

        if not self._running:
            LOGGER.debug("Ignoring repair request for halted resource scheduler")
            return
        async with self._scheduler_lock:
            in_scope: Set[ResourceIdStr] = (
                self._state.intent.keys() if agent is None else self._state.resources_by_agent.get(agent, set())
            )

            to_deploy: Set[ResourceIdStr] = {resource for resource in in_scope if should_deploy_resource(resource)}
            if agent is not None:
                LOGGER.debug("Triggering deploy for %d resources on agent %s because %s", len(to_deploy), agent, reason)
            else:
                LOGGER.debug("Triggering deploy for %d resources because %s", len(to_deploy), reason)
            self._state.dirty.update(to_deploy)
            self._timer_manager.stop_timers(to_deploy)
            self._work.deploy_with_context(to_deploy, reason=reason, priority=priority, deploying=self._deploying_latest)

    async def dryrun(self, dry_run_id: uuid.UUID, version: int) -> None:
        if not self._running:
            LOGGER.debug("Ignoring dry-run request for halted resource scheduler")
            return

        paused_agents = await self.all_paused_agents()

        LOGGER.debug("Triggering dry-run %s for version %d", str(dry_run_id), version)
        model: ModelVersion = await self._get_single_model_version_from_db(version=version)
        for resource, resource_intent in model.resources.items():
            if resource in model.undefined:
                continue

            if resource_intent.id.agent_name in paused_agents:
                # Paused agents are handled on the calling side
                continue

            self._work.agent_queues.queue_put_nowait(
                DryRun(
                    resource=resource_intent.resource_id,
                    version=model.version,
                    resource_intent=ResourceIntent(
                        resource_id=resource_intent.resource_id,
                        attribute_hash=resource_intent.attribute_hash,
                        attributes=resource_intent.attributes,
                    ),
                    dry_run_id=dry_run_id,
                ),
                priority=TaskPriority.DRYRUN,
            )

    async def get_facts(self, resource: dict[str, object]) -> None:
        if not self._running:
            return
        rid = Id.parse_id(resource["id"]).resource_str()
        self._work.agent_queues.queue_put_nowait(
            RefreshFact(resource=rid),
            priority=TaskPriority.FACT_REFRESH,
        )

    async def deploy_resource(self, resource: ResourceIdStr, reason: str, priority: TaskPriority) -> None:
        """
        Make sure the given resource is marked for deployment with at least the provided priority.
        If the given priority is higher than the previous one (or if it didn't exist before), a new deploy
        task will be scheduled with the provided reason.
        """
        async with self._scheduler_lock:
            if resource not in self._state.resource_state:
                # The resource was removed from the model by the time this method was triggered
                return

            # When explicitly requested for a single resource, we allow deploying even deploys marked as
            # Blocked.TEMPORARILY_BLOCKED
            if self._state.resource_state[resource].blocked is Blocked.BLOCKED:  # Can't deploy
                return
            self._timer_manager.stop_timer(resource)
            self._work.deploy_with_context(
                {resource},
                reason=reason,
                priority=priority,
                deploying=self._deploying_latest,
            )

    async def _get_single_model_version_from_db(
        self,
        *,
        version: int | None = None,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> ModelVersion:
        """
        Returns a single model version as fetched from the database. Returns the requested version if provided
        (regardless of whether it has been released or not), otherwise returns the latest released version.

        Raises KeyError if no specific version has been provided and no released versions exist.
        """
        async with self.state_update_manager.get_connection(connection) as con:
            if version is None:
                # Fetch the latest released model version
                cm_version = await ConfigurationModel.get_latest_version(self.environment, connection=con)
                if cm_version is None:
                    raise KeyError()
                version = cm_version.version

            resources_from_db = await data.Resource.get_resources_for_version_raw(
                environment=self.environment,
                version=version,
                projection=ResourceRecord.__required_keys__,
                connection=con,
            )

            return ModelVersion.from_db_records(
                version,
                resources_from_db,  # type: ignore
            )

    async def read_version(
        self,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Update model state and scheduled work based on the latest released version in the database,
        e.g. when a new version is released. Triggers a deploy after updating internal state:
        - schedules new or updated resources to be deployed
        - schedules any resources that are not in a known good state.
        - rearranges deploy tasks by requires if required

        :param connection: Connection to use for db operations. Should not be in a transaction context.
        """
        if not self._running:
            LOGGER.debug("Ignoring request to read latest version for halted resource scheduler")
            return
        async with self._intent_lock, self.state_update_manager.get_connection(connection) as con:
            # Note: we're not very sensitive to races on the latest released version here. The server will always notify us
            # *after* a new version is released. So we'll always be in one of two scenearios:
            # - the latest released version was released before we started processing this notification
            # - a new version was released after we started processing this communication or is being released now, in which
            #   case a new notification will be / have been sent and blocked on the intent locked until we're done here.
            # So if we end up with a race, we can be confident that we'll always process the associated notification soon.
            resources_by_version: Sequence[tuple[int, Sequence[Mapping[str, object]]]] = (
                await data.Resource.get_resources_since_version_raw(
                    self.environment,
                    since=self._state.version,
                    projection=ResourceRecord.__required_keys__,
                    connection=con,
                )
            )
            new_versions: Sequence[ModelVersion] = [
                ModelVersion.from_db_records(
                    version,
                    resources,  # type: ignore
                )
                for version, resources in resources_by_version
            ]
            LOGGER.debug(
                "Read %d model versions newer than the currently managed version %d",
                len(resources_by_version),
                self._state.version,
            )

            await self._new_version(
                new_versions,
                reason="a new version was released",
                connection=con,
            )

    async def _get_intent_changes(
        self,
        new_versions: Sequence[ModelVersion],
        *,
        up_to_date_resources: Optional[Set[ResourceIdStr]] = None,
    ) -> tuple[ModelVersion, dict[ResourceIdStr, ResourceIntentChange]]:
        """
        Returns a consolidated overview of changes to resource intent, given a series of model versions to process.

        Returns a tuple of
        - the resulting model version after processing all versions.
        - a mapping of resources to their change of intent, after processing all versions in sequence. Only contains resources
            with a change of intent. May include resources with DELETED change of intent even if they aren't part of the current
            state.

        :param new_versions: The new versions to process, in ascending order.
        :param up_to_date_resources: A set of resources that are considered up to date and in a known good state, regardless
            of the current state information.
        """
        up_to_date_resources = set() if up_to_date_resources is None else up_to_date_resources

        if not new_versions:
            raise ValueError("Expected at least one new model version")

        LOGGER.debug("Consolidating changes from %d new versions", len(new_versions))

        version: int
        intent: dict[ResourceIdStr, ResourceIntent] = {}
        resource_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
        # keep track of all new resource intent and all changes of intent relative to the currently managed version
        intent_changes: dict[ResourceIdStr, ResourceIntentChange] = {}
        # all undefined resources in the new model versions. Newer version information overrides older ones.
        undefined: set[ResourceIdStr] = set()

        previous_version: int = self._state.version
        for model in new_versions:
            version = model.version
            # resources that don't exist anymore in this version
            for resource in (self._state.intent.keys() | intent.keys()) - model.resources.keys():
                with contextlib.suppress(KeyError):
                    del intent[resource]
                    del resource_requires[resource]
                if resource not in intent_changes or intent_changes[resource].change is not ResourceIntentChangeType.DELETED:
                    intent_changes[resource] = Deleted(last_seen_version=previous_version)
                undefined.discard(resource)

            i: int = 0
            for resource, resource_intent in model.resources.items():
                # this loop is race-free, potentially slow, and completely synchronous
                # => regularly pass control to the event loop to not block scheduler operation during update prep
                if i >= NB_ITERATIONS_PASS_IO_LOOP:
                    await asyncio.sleep(0)
                    i = 0
                i += 1

                # register new resource intent and requires, overriding previous information
                intent[resource] = resource_intent
                # we only care about the requires-provides changes relative to the currently managed ones,
                # not relative to any of the older versions => simply override
                resource_requires[resource] = model.requires.get(resource, set())

                # determine change of intent
                # no change of intent, by definition
                if resource in up_to_date_resources:
                    continue
                # new resources
                if (
                    # exists in this version but not in managed version
                    resource not in self._state.intent.keys()
                    # deleted in a previously processed version and reappeared now
                    # => consider as a new resource rather than an update
                    or (
                        resource in intent_changes
                        and intent_changes[resource].change in (ResourceIntentChangeType.DELETED, ResourceIntentChangeType.NEW)
                    )
                ):
                    intent_changes[resource] = New()
                # resources we already manage
                elif resource_intent.attribute_hash != self._state.intent[resource].attribute_hash:
                    intent_changes[resource] = Updated()
                # no change of intent for this resource, unless defined status changed

                # determine new defined status
                is_undefined: bool
                if resource in model.undefined:
                    undefined.add(resource)
                    is_undefined = True
                else:
                    undefined.discard(resource)
                    is_undefined = False
                if resource not in intent_changes and is_undefined != (
                    self._state.resource_state[resource].compliance is Compliance.UNDEFINED
                ):
                    # resource's defined status changed
                    intent_changes[resource] = Updated()

            previous_version = version

        return (
            ModelVersion(
                version=version,
                resources=intent,
                requires=resource_requires,
                undefined=undefined,
            ),
            intent_changes,
        )

    async def _new_version(
        self,
        new_versions: Sequence[ModelVersion],
        *,
        up_to_date_resources: Optional[Set[ResourceIdStr]] = None,
        last_deploy_time: Mapping[ResourceIdStr, datetime.datetime] | None = None,
        reason: str = "a new version was released",
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Register one or more newly released versions with the scheduler. Updates scheduled state and scheduled work accordingly.

        Expects to be called under the intent lock, and with monotonically increasing versions (relative to the previous calls
        as well as within the new_versions sequence).

        :param up_to_date_resources: Set of resources that are to be considered in an assumed good state due to a previously
            successful deploy for the same intent. Should not include any blocked resources. Mostly intended for the very first
            version when the scheduler is started with a fresh state.
        :param last_deploy_time: last known deploy time of all resources. only intended for the very first
            version when the scheduler is started with a fresh state.
            It must contain ALL resources as it is used to start the timers
        :param reason: The reason to associate with any deploys caused by this newly released version.
        :param connection: Connection to use for db operations. Should not be in a transaction context for two reasons:
            1. This method acquires the scheduler lock, and needs to have control about how it is allowed to interleave with
                transaction commit, if at all.
            2. This method may have a long pre-processing phase, it opens a transaction itself when appropriate
        """
        if not new_versions:
            return
        if connection is not None and connection.is_in_transaction():
            raise ValueError("_new_version() expects its connection to not be in a transaction context")

        first_version: bool = self._state.version == 0

        up_to_date_resources = set() if up_to_date_resources is None else up_to_date_resources
        last_deploy_time = {} if last_deploy_time is None else last_deploy_time

        # pre-process new model versions before acquiring the scheduler lock.
        model: ModelVersion
        intent_changes: Mapping[ResourceIdStr, ResourceIntentChange]
        model, intent_changes = await self._get_intent_changes(new_versions, up_to_date_resources=up_to_date_resources)

        LOGGER.debug(
            (
                "Processing intent changes for %d resources between currently managed model version %d"
                " and new model version %d, because %s"
            ),
            len(intent_changes),
            self._state.version,
            model.version,
            reason,
        )

        # Track potential changes in requires per resource
        added_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}  # includes new resources if they have at least one req
        dropped_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
        i: int = 0
        for resource, requires in model.requires.items():
            old_requires: Set[ResourceIdStr] = self._state.requires.get(resource, set())
            added = requires - old_requires
            if added:
                added_requires[resource] = added
            removed = old_requires - requires
            if removed:
                dropped_requires[resource] = removed

            # pass control back to event loop to maintain scheduler operations until we acquire the lock
            if i >= NB_ITERATIONS_PASS_IO_LOOP:
                await asyncio.sleep(0)
                i = 0
            i += 1

        # convert intent changes to sets for bulk processing
        deleted: dict[ResourceIdStr, Deleted] = {}
        new: set[ResourceIdStr] = set()
        updated: set[ResourceIdStr] = set()
        # resources that were previously undefined but not anymore, including those considered new if they match this property
        became_defined: set[ResourceIdStr] = set()
        # resources that are now undefined but weren't before, including new resources if they are undefined
        became_undefined: set[ResourceIdStr] = set()
        i = 0
        for resource, change in intent_changes.items():
            # pass control back to event loop to maintain scheduler operations until we acquire the lock
            if i >= NB_ITERATIONS_PASS_IO_LOOP:
                await asyncio.sleep(0)
                i = 0
            i += 1

            match change:
                case Deleted():
                    deleted[resource] = change
                    continue
                case New():
                    new.add(resource)
                case Updated():
                    updated.add(resource)
                case _ as _never:
                    typing.assert_never(_never)
            resource_state: Optional[ResourceState] = self._state.resource_state.get(resource)
            if resource_state is None:
                if resource in model.undefined:
                    became_undefined.add(resource)
                continue
            attribute_hash_changed: bool = (
                model.resources[resource].attribute_hash != self._state.intent[resource].attribute_hash
            )
            attribute_hash_unchanged_warning_fmt: str = (
                "The resource with id %s has become %s, but the hash has not changed."
                " This may lead to unexpected deploy behavior"
            )
            if resource in model.undefined and resource_state.compliance is not Compliance.UNDEFINED:
                if not attribute_hash_changed:
                    LOGGER.warning(attribute_hash_unchanged_warning_fmt, resource, "undefined")
                became_undefined.add(resource)
            elif resource not in model.undefined and resource_state.compliance is Compliance.UNDEFINED:
                if not attribute_hash_changed:
                    LOGGER.warning(attribute_hash_unchanged_warning_fmt, resource, "defined")
                became_defined.add(resource)

        # resources that are to be considered new, even if they are already being managed
        force_new: Set[ResourceIdStr] = self._state.intent.keys() & new

        # assert invariants of the constructed sets
        assert len(intent_changes) == len(deleted.keys() | new | updated) == len(deleted) + len(new) + len(updated)
        assert len(became_defined | became_undefined) == (len(became_defined) + len(became_undefined))

        # pass control to IO loop once more before we acquire the lock
        await asyncio.sleep(0)

        # in the current implementation everything below the lock is synchronous, it is however still required (1)
        # and desired even if it weren't strictly required (2):
        # 1. other operations under lock may pass control back to the event loop under the lock. Meaning that even if this
        #   method itself were fully synchronous, it will always still be called in some async context, which may interleave
        #   with awaits in other operations under lock.
        #   and has to be even apart from motivations 2-3, it may interleave with
        # 2. clarity: it clearly signifies that this is the atomic and performance-sensitive part
        async with self._scheduler_lock:
            # update model version
            self._state.version = model.version
            # update resource intent
            for resource in up_to_date_resources:
                # Registers resource and removes from the dirty set
                self._state.update_resource(
                    model.resources[resource], known_compliant=True, last_deployed=last_deploy_time.get(resource, None)
                )
            for resource in new | updated:
                # update resource state and dirty set
                self._state.update_resource(
                    model.resources[resource],
                    force_new=intent_changes[resource].change is ResourceIntentChangeType.NEW,
                    undefined=resource in model.undefined,
                    last_deployed=last_deploy_time.get(resource, None),
                )
            # update requires
            for resource in added_requires.keys() | dropped_requires.keys():
                self._state.update_requires(resource, model.requires[resource])

            # update transitive state
            transitive_unblocked, transitive_blocked = self._state.update_transitive_state(
                new_undefined=became_undefined,
                verify_blocked=added_requires.keys(),
                verify_unblocked=became_defined | dropped_requires.keys(),
            )
            # update TEMPORARILY_BLOCKED (skipped-for-dependencies) state
            # for resources with a dependency for which state was reset
            resources_with_reset_requires: Set[ResourceIdStr] = set(
                itertools.chain.from_iterable(
                    self._state.requires.provides_view().get(resource, set()) for resource in force_new
                )
            )
            for resource in resources_with_reset_requires:
                if (
                    # it is currently TEMPORARILY_BLOCKED blocked
                    self._state.resource_state[resource].blocked is Blocked.TEMPORARILY_BLOCKED
                    # it shouldn't be any longer
                    and not self._state.should_skip_for_dependencies(resource)
                ):
                    self._state.resource_state[resource].blocked = Blocked.NOT_BLOCKED

            # Update set of in-progress deploys that became unmanaged
            self._deploying_unmanaged.update(self._deploying_latest & (new | deleted.keys()))
            # Update set of in-progress non-stale deploys by trimming resources with new state
            self._deploying_latest.difference_update(intent_changes.keys(), transitive_blocked)

            # Remove timers for resources that are:
            #    - in the dirty set (because they will be picked up by the scheduler eventually)
            #    - blocked: must not be deployed
            #    - deleted from the model
            self._timer_manager.stop_timers(self._state.dirty | became_undefined | transitive_blocked)
            self._timer_manager.remove_timers(deleted.keys())
            # Install timers for initial up-to-date resources. They are up-to-date now,
            # but we want to make sure we periodically repair them.
            self._timer_manager.update_timers(
                up_to_date_resources | ((transitive_unblocked | resources_with_reset_requires) - self._state.dirty)
            )

            # ensure deploy for ALL dirty resources, not just the new ones
            self._work.deploy_with_context(
                self._state.dirty,
                reason=reason,
                priority=TaskPriority.NEW_VERSION_DEPLOY,
                deploying=self._deploying_latest,
                added_requires=added_requires,
                dropped_requires=dropped_requires,
            )
            for resource in deleted:
                if resource in self._state.resource_state:
                    self._state.drop(resource)  # Removes from the dirty set
            for resource in deleted.keys() | became_undefined | transitive_blocked:
                self._work.delete_resource(resource)

            # Updating the blocked state should be done under the scheduler lock, because this state is written
            # by both the deploy and the new version code path.
            resources_with_updated_blocked_state: Set[ResourceIdStr] = (
                became_undefined | transitive_blocked | transitive_unblocked
            )

        LOGGER.debug(
            "Successfully updated resource scheduler to manage model version %d. Writing intent changes to the database.",
            model.version,
        )
        async with self.state_update_manager.get_connection(connection=connection) as con, con.transaction():
            # Update intent for resources with new desired state
            # Safe to update outside of the lock: scheduler persisted intent is allowed to lag behind its in-memory intent
            # because we always update again after recovering, and we never write to these same columns from any other place.
            # TODO[#8541]: with the changes planned in #8541, the "never write to these same columns from any other places"
            #   statement may not hold anymore. In any case, the transaction must not interleave or wrap the scheduler lock.
            await self.state_update_manager.update_resource_intent(
                self.environment,
                intent={
                    rid: (self._state.resource_state[rid], self._state.intent[rid])
                    for rid in (new | updated | resources_with_updated_blocked_state) - deleted.keys()
                },
                update_blocked_state=True,
                connection=con,
            )
            # Mark orphaned resources
            if first_version:
                # We're starting fresh. Make sure to mark all orphans, because we may be skipping some unprocessed versions.
                await self.state_update_manager.mark_all_orphans(
                    self.environment, current_version=model.version, connection=con
                )
            else:
                # We're processing versions relative to an already processed version => deleted contains all orphans.
                await self.state_update_manager.mark_as_orphan(self.environment, deleted.keys(), connection=con)
            await self.state_update_manager.set_last_processed_model_version(
                self.environment, self._state.version, connection=con
            )
        LOGGER.debug("Finished writing changes for model version %d to the database", model.version)

    def _create_agent(self, agent: str) -> None:
        """Start processing for the given agent"""
        self._workers[agent] = TaskRunner(endpoint=agent, scheduler=self)
        self._workers[agent].notify_sync()

    async def should_be_running(self) -> bool:
        """
        Check in the DB (authoritative entity) if the Scheduler should be running
            i.e. if the environment is not halted.
        """
        current_environment = await Environment.get_by_id(self.environment)
        assert current_environment
        return not current_environment.halted

    async def should_runner_be_running(self, endpoint: str) -> bool:
        """
        Check in the DB (authoritative entity) if the agent (or the Scheduler if endpoint == Scheduler id) should be running
            i.e. if it is not paused.

        :param endpoint: The name of the agent
        """
        await data.Agent.insert_if_not_exist(environment=self.environment, endpoint=endpoint)
        if self._deployment_suspended:
            return False
        current_agent = await data.Agent.get(env=self.environment, endpoint=endpoint)
        return not current_agent.paused

    async def all_paused_agents(self) -> set[str]:
        return {agent.name for agent in await data.Agent.get_list(environment=self.environment, paused=True)}

    async def refresh_agent_state_from_db(self, name: str) -> None:
        """
        Refresh from the DB (authoritative entity) the actual state of the agent.
            - If the agent is not paused: It will make sure that the agent is running.
            - If the agent is paused: Stop a particular agent.

        :param name: The name of the agent
        """
        if name in self._workers:
            await self._workers[name].notify()

    async def refresh_all_agent_states_from_db(self) -> None:
        """
        Refresh from the DB (authoritative entity) the actual state of all agents.
            - If an agent is not paused: It will make sure that the agent is running.
            - If an agent is paused: Stop a particular agent.
        """
        for worker in self._workers.values():
            await worker.notify()

    async def is_agent_running(self, name: str) -> bool:
        """
        Return True if the provided agent is running, at least an agent that the Scheduler is aware of

        :param name: The name of the agent
        """
        return name in self._workers and self._workers[name].is_running()

    # TaskManager interface

    def _get_resource_intent(self, resource: ResourceIdStr) -> Optional[ResourceIntent]:
        """
        Get intent of a given resource.
        Always expected to be called under lock
        """
        try:
            return self._state.intent[resource]
        except KeyError:
            # Stale resource
            # May occur in rare races between new_version and acquiring the lock we're under here. This race is safe
            # because of this check, and an intrinsic part of the locking design because it's preferred over wider
            # locking for performance reasons.
            return None

    async def get_resource_version_intent(self, resource: ResourceIdStr) -> Optional[ResourceVersionIntent]:
        async with self._scheduler_lock:
            # fetch resource intent under lock
            resource_intent = self._get_resource_intent(resource)
            if resource_intent is None:
                return None
            return ResourceVersionIntent(
                model_version=self._state.version,
                intent=resource_intent,
                all_types_for_agent=list(self._state.types_per_agent[self._state.intent[resource].id.agent_name]),
            )

    async def deploy_start(self, action_id: uuid.UUID, resource: ResourceIdStr) -> Optional[DeployIntent]:
        async with self._scheduler_lock:
            # fetch resource intent under lock
            resource_intent = self._get_resource_intent(resource)
            if resource_intent is None or self._state.resource_state[resource].blocked is Blocked.BLOCKED:
                # We are trying to deploy a stale resource.
                return None
            dependencies = await self._get_last_non_deploying_state_for_dependencies(resource=resource)
            self._deploying_latest.add(resource)
            deploy_intent = DeployIntent(
                model_version=self._state.version,
                intent=resource_intent,
                dependencies=dependencies,
                deploy_start=datetime.datetime.now().astimezone(),
                all_types_for_agent=list(self._state.types_per_agent[self._state.intent[resource].id.agent_name]),
            )
            # Update the state in the database.
            await self.state_update_manager.send_in_progress(
                action_id, Id.parse_id(ResourceVersionIdStr(f"{resource},v={self._state.version}"))
            )
            return deploy_intent

    async def deploy_done(self, deploy_intent: DeployIntent, report: executor.DeployReport) -> None:
        finished = datetime.datetime.now().astimezone()
        try:
            state: Optional[ResourceState]
            try:
                state = await self._update_scheduler_state_for_finished_deploy(deploy_intent, report, finished)
            except StaleResource:
                # The resource is no longer managed (or in rare cases it has shortly become unmanaged sometime
                # between this version and the currently managed version, either way, the deploy that finished
                # represents a stale intent). We do still want to report that the deploy finished for this version,
                # even if it is stale, we simply don't report any state. new, ununtouched state for this resource
                # id), because that still represents the most current state for this resource, even if it is
                # independent from this deploy. The scheduler will then report that this resource id with this
                # specific version finished deploy.
                state = None
            # Write deployment result to the database.
            await self.state_update_manager.send_deploy_done(
                attribute_hash=deploy_intent.intent.attribute_hash,
                result=report,
                state=state,
                started=deploy_intent.deploy_start,
                finished=finished,
            )
        finally:
            # Always do this, even if the DB is broken
            async with self._scheduler_lock:
                # report to the scheduled work that we're done
                self._work.finished_deploy(report.resource_id)
                state = self._state.resource_state.get(deploy_intent.intent.resource_id)
                if state is not None:
                    self._timer_manager.update_timer(deploy_intent.intent.resource_id, state=state)

    async def dryrun_done(self, report: executor.DryrunReport) -> None:
        await self.state_update_manager.dryrun_update(env=self.environment, dryrun_result=report)

    async def fact_refresh_done(self, report: executor.GetFactReport) -> None:
        await self.state_update_manager.set_parameters(fact_result=report)

    async def _update_scheduler_state_for_finished_deploy(
        self, deploy_intent: DeployIntent, result: executor.DeployReport, finished: datetime.datetime
    ) -> ResourceState:
        """
        Update the state of the scheduler based on the DeployResult of the given resource.

        May add log messages to the given deploy result object.

        :raise StaleResource: This update is about a resource that is no longer managed by the server.
        :return: The new state of the resource, even if no changes were made. The returned object is a static copy that
            represents the state at the end of the deploy, and can therefore safely be returned out of the scheduler lock.
        """
        resource: ResourceIdStr = result.resource_id
        deploy_result: DeployResult = DeployResult.from_handler_resource_state(result.resource_state)

        async with self._scheduler_lock:
            # refresh resource intent for latest model state
            resource_intent: Optional[ResourceIntent] = self._state.intent.get(resource, None)

            if resource_intent is None or resource in self._deploying_unmanaged:
                # we are stale and removed
                self._deploying_unmanaged.discard(resource)
                raise StaleResource()

            state: ResourceState = self._state.resource_state[resource]

            recovered_from_failure: bool = deploy_result is DeployResult.DEPLOYED and state.last_deploy_result not in (
                DeployResult.DEPLOYED,
                DeployResult.NEW,
            )

            # The second part of the or would not be required because is implied by the first,
            # except that we don't enforce the hash diff.
            # We emit a warning if we observe this, but that still doesn't prevent it.
            # While it should not happen it can
            if (
                resource_intent.attribute_hash != deploy_intent.intent.attribute_hash
                or state.compliance is Compliance.UNDEFINED
            ):
                # We are stale but still the last deploy
                # We can update the last_deploy_result (which is about last deploy)
                # We can't update compliance (which is about active state only)
                # None of the event propagation or other update happen either for the same reason
                # except for the event to notify dependents of failure recovery (to unblock skipped for dependencies)
                # because we might otherwise miss the recovery (in the sense that the next deploy wouldn't be a transition
                # from a bad to a good state, since we're transitioning to that good state now).

                state.last_deploy_result = deploy_result
                state.last_deployed = finished
                if recovered_from_failure:
                    self._send_events(resource_intent, stale_deploy=True, recovered_from_failure=True)
                return state.copy()

            # We are not stale
            state.compliance = Compliance.COMPLIANT if deploy_result is DeployResult.DEPLOYED else Compliance.NON_COMPLIANT

            # first update state, then send out events
            self._deploying_latest.remove(resource)
            state.last_deploy_result = deploy_result
            state.last_deployed = finished

            # Check if we need to mark a resource as temporarily blocked
            # We only do that if it is not already blocked (Blocked.BLOCKED)
            # We might already be unblocked if a dependency succeeded on another agent, e.g. while waiting for the lock
            # so HandlerResourceState.skipped_for_dependency might be outdated, we have an inconsistency between the
            # state of the dependencies and the exception that was raised by the handler.
            # If all dependencies are compliant we don't want to temporarily block this resource.
            if (
                state.blocked is not Blocked.BLOCKED
                and result.resource_state is const.HandlerResourceState.skipped_for_dependency
                and self._state.should_skip_for_dependencies(resource)
            ):
                state.blocked = Blocked.TEMPORARILY_BLOCKED
                # Remove this resource from the dirty set when we block it
                self._state.dirty.discard(resource)
            elif deploy_result is DeployResult.DEPLOYED:
                # Remove this resource from the dirty set if it is successfully deployed
                self._state.dirty.discard(resource)
                if state.blocked is Blocked.TEMPORARILY_BLOCKED:
                    # For now, we make sure to schedule even TEMPORARILY_BLOCKED resources for repair, just in case we have made
                    # incorrect assumptions. If this happens, we mark it as unblocked and we trigger a warning.
                    state.blocked = Blocked.NOT_BLOCKED

                    log_line: data.LogLine = self._get_temporarily_blocked_warning(deploy_intent)
                    # write to resource action (and scheduler) log
                    log_line.write_to_logger_for_resource(
                        agent=deploy_intent.intent.id.agent_name,
                        resource_version_string=deploy_intent.intent.id.copy(
                            version=deploy_intent.model_version
                        ).resource_version_str(),
                    )
                    # write to database (via send_deploy_done())
                    result.messages.append(log_line)
            else:
                # In most cases it will already be marked as dirty but in rare cases the deploy that just finished might
                # have been triggered by an event, on a previously successful deployed resource. Either way, a failure
                # (or skip) causes it to become dirty now.
                self._state.dirty.add(resource)

            # propagate events
            self._send_events(resource_intent, recovered_from_failure=recovered_from_failure)

            return state.copy()

    def _send_events(
        self,
        sending_resource: ResourceIntent,
        *,
        stale_deploy: bool = False,
        recovered_from_failure: bool,
    ) -> None:
        """
        Send events to the appropriate dependents of the given resources. Sends out normal events to declared event listeners
        unless this was triggered by a stale deploy. Additionally, if this was triggered by a failure recovery, it unblocks
        skipped dependents where appropriate and sends them an event to deploy.

        Expects to be called under the scheduler lock.

        :param sending_resource: Details for the given resource that has just finished deploying.
        :param state_deploy: The events are triggered by a stale deploy. Only recovery events will be sent.
        :param recovered_from_failure: This resource went from 'not deployed' to 'deployed',
            inform unblocked dependants that they might be able to progress.
        """
        resource_id: ResourceIdStr = sending_resource.resource_id
        provides: Set[ResourceIdStr] = self._state.requires.provides_view().get(resource_id, set())

        event_listeners: Set[ResourceIdStr]
        recovery_listeners: Set[ResourceIdStr]

        if stale_deploy or not sending_resource.attributes.get(const.RESOURCE_ATTRIBUTE_SEND_EVENTS, False):
            event_listeners = set()
        else:
            event_listeners = {
                dependent
                for dependent in provides
                if (dependent_intent := self._state.intent.get(dependent, None)) is not None
                if self._state.resource_state[dependent].blocked is Blocked.NOT_BLOCKED
                # default to True for backward compatibility, i.e. not all resources have the field
                if dependent_intent.attributes.get(const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS, True)
            }

        if not recovered_from_failure:
            recovery_listeners = set()
        else:
            recovery_listeners = {
                dependent
                for dependent in provides
                if self._state.resource_state[dependent].blocked is Blocked.TEMPORARILY_BLOCKED
            }
            # These resources might be able to progress now -> unblock them in addition to sending the event
            self._state.dirty.update(recovery_listeners)
            for skipped_dependent in recovery_listeners:
                # TODO[#8541]: persist in database
                self._state.resource_state[skipped_dependent].blocked = Blocked.NOT_BLOCKED

        all_listeners: Set[ResourceIdStr] = event_listeners | recovery_listeners
        if all_listeners:
            # do not pass deploying tasks because for event propagation we really want to start a new one,
            # even if the current intent is already being deployed
            task = Deploy(resource=resource_id)
            assert task in self._work.agent_queues.in_progress
            priority = self._work.agent_queues.in_progress[task]
            self._timer_manager.stop_timers(all_listeners)
            self._work.deploy_with_context(
                all_listeners,
                reason=(
                    f"a recovery event was received from {resource_id}"
                    if recovered_from_failure
                    else f"an event was received from {resource_id}"
                ),
                priority=priority,
                deploying=self._deploying_latest,
                # force a new deploy to be scheduled because ongoing deploys can not capture the event.
                # We desire new deploys to be scheduled, even if any are ongoing for the same intent.
                force_deploy=True,
            )

    def _get_temporarily_blocked_warning(self, deploy_intent: DeployIntent) -> data.LogLine:
        """
        Warn the user about a resource that was marked as TEMPORARILY_BLOCKED that deployed successfully. Does not actually log
        anything, only returns a log line object for the resource action log.

        Should only be called when the resource did in fact deploy when it was expected to skip for dependencies again.
        Inspects dependencies' state to determine the most appropriate warning message (handler bug or scheduler bug).

        :param deploy_intent: The intent that was just deployed successfully.
        """
        bad_dependencies: Mapping[ResourceIdStr, const.ResourceState] = {
            dependency: dependency_state
            for dependency, dependency_state in deploy_intent.dependencies.items()
            if dependency_state != const.ResourceState.deployed
        }
        if bad_dependencies:
            return data.LogLine.log(
                logging.WARNING,
                (
                    "Resource %(resource)s was expected to skip for dependencies but it deployed successfully."
                    " The handler for this resource raised a SkipResourceForDependencies exception in a previous"
                    " execution, indicating that it would only be able to progress once all requires reached a"
                    " deployed state. Some requires (%(dependencies)s) are still in a non-deployed state,"
                    " therefore it was assumed that a new deploy attempt would have no effect."
                    " This indicates incorrect usage of the exception, and it will lead to resources getting stuck"
                    " in the skipped state. While this can be worked around by triggering a repair for now, that"
                    " may not work in the future."
                    " Please check your handler implementation, and make sure to raise the generic SkipResource"
                    " rather than SkipResourceForDependencies if you wish to skip a deploy for any other reason"
                    " than to wait until all requires are in a good state."
                    " Please contact support if you believe your handler implementation is correct after all."
                ),
                resource=deploy_intent.intent.resource_id,
                dependencies=", ".join(f"{r}: {state.name}" for r, state in bad_dependencies.items()),
            )
        else:
            return data.LogLine.log(
                logging.WARNING,
                (
                    "Inconsistent internal state for resource %(resource)s. The inmanta resource scheduler"
                    " assumed it was still blocked, pending a successful deploy of at least one of its requires."
                    " However, all dependencies are already in a deployed state. This was expected to be impossible"
                    " and it indicates a (non-critical) bug in the inmanta resource scheduler. Please report this"
                    " bug."
                    " In the meantime, if you encounter any resources stuck in the skipped state, trigger a repair"
                    " as a workaround to force a deploy."
                ),
                resource=deploy_intent.intent.resource_id,
            )

    async def _get_last_non_deploying_state_for_dependencies(
        self, resource: ResourceIdStr
    ) -> Mapping[ResourceIdStr, const.ResourceState]:
        """
        Get resource state for every dependency of a given resource from the scheduler state.
        The state is then converted to const.ResourceState.

        Should only be called under scheduler lock.

        :param resource: The id of the resource to find the dependencies for
        """
        requires_view: Mapping[ResourceIdStr, Set[ResourceIdStr]] = self._state.requires.requires_view()
        dependencies: Set[ResourceIdStr] = requires_view.get(resource, set())
        dependencies_state = {}
        for dep_id in dependencies:
            resource_state_object: ResourceState = self._state.resource_state[dep_id]
            match resource_state_object:
                case ResourceState(compliance=Compliance.UNDEFINED):
                    dependencies_state[dep_id] = const.ResourceState.undefined
                case ResourceState(blocked=Blocked.BLOCKED):
                    dependencies_state[dep_id] = const.ResourceState.skipped_for_undefined
                case ResourceState(compliance=Compliance.HAS_UPDATE):
                    dependencies_state[dep_id] = const.ResourceState.available
                case ResourceState(last_deploy_result=DeployResult.SKIPPED):
                    dependencies_state[dep_id] = const.ResourceState.skipped
                case ResourceState(last_deploy_result=DeployResult.DEPLOYED):
                    dependencies_state[dep_id] = const.ResourceState.deployed
                case ResourceState(last_deploy_result=DeployResult.FAILED):
                    dependencies_state[dep_id] = const.ResourceState.failed
                case _:
                    raise Exception(f"Failed to parse the resource state for {dep_id}: {resource_state_object}")
        return dependencies_state

    async def get_resource_state(self) -> SchedulerStatusReport:
        """
        Check that the state of the resources in the DB corresponds
        to the internal state of the scheduler and return a SchedulerStatusReport
        object containing the internal state and any discrepancies between this
        state and that of the DB.
        """

        async def _build_discrepancy_map(
            resource_states_in_db: Mapping[ResourceIdStr, const.ResourceState],
        ) -> dict[ResourceIdStr, list[Discrepancy]]:
            """
            For each resource in the given map, compare its persisted state in the database to its
            state as it is assumed by the scheduler. Build and return a map of all detected discrepancies.

            :param resource_states_in_db: Map each resource to its ResourceState.
            :return: A dict mapping each resource to the discrepancies related to it (if any)
            """
            state_translation_table: dict[
                const.ResourceState, tuple[DeployResult | None, Blocked | None, Compliance | None]
            ] = {
                # A table to translate the old states into the new states
                # None means don't care, mostly used for values we can't derive from the old state
                const.ResourceState.unavailable: (None, Blocked.NOT_BLOCKED, Compliance.NON_COMPLIANT),
                const.ResourceState.skipped: (DeployResult.SKIPPED, None, None),
                const.ResourceState.dry: (None, None, None),  # don't care
                const.ResourceState.deployed: (DeployResult.DEPLOYED, Blocked.NOT_BLOCKED, None),
                const.ResourceState.failed: (DeployResult.FAILED, Blocked.NOT_BLOCKED, None),
                const.ResourceState.deploying: (None, Blocked.NOT_BLOCKED, None),
                const.ResourceState.available: (None, Blocked.NOT_BLOCKED, Compliance.HAS_UPDATE),
                const.ResourceState.undefined: (None, Blocked.BLOCKED, Compliance.UNDEFINED),
                const.ResourceState.skipped_for_undefined: (None, Blocked.BLOCKED, None),
            }

            discrepancy_map: dict[ResourceIdStr, list[Discrepancy]] = {}

            # Resources only present in the DB but missing from the scheduler
            only_in_db = resource_states_in_db.keys() - self._state.resource_state.keys()
            for rid in only_in_db:
                discrepancy_map[rid] = [
                    Discrepancy(
                        rid=rid,
                        field=None,
                        expected=(
                            f"Resource is present in the DB (model version {latest_version}). "
                            "It is expected in the scheduler's state map."
                        ),
                        actual="Resource is missing from the scheduler's state map.",
                    )
                ]

            # Resources only present in the scheduler but missing from the DB
            only_in_scheduler = self._state.resource_state.keys() - resource_states_in_db.keys()
            for rid in only_in_scheduler:
                discrepancy_map[rid] = [
                    Discrepancy(
                        rid=rid,
                        field=None,
                        expected=(
                            f"Resource is not present in the DB (model version {latest_version}). "
                            "It shouldn't be in the scheduler's state map."
                        ),
                        actual="Resource is present in the scheduler's state map.",
                    )
                ]

            # Keep track of the number of iterations to regularly pass control back to the io loop
            i: int = 0
            # For resources in both the DB and the scheduler, check for discrepancies in state
            for rid in resource_states_in_db.keys() & self._state.resource_state.keys():
                resource_discrepancies: list[Discrepancy] = []

                db_resource_status = resource_states_in_db[rid]
                db_deploy_result, db_blocked_status, db_compliance_status = state_translation_table[db_resource_status]

                scheduler_resource_state: ResourceState = self._state.resource_state[rid]
                if db_deploy_result:
                    if scheduler_resource_state.last_deploy_result != db_deploy_result:
                        resource_discrepancies.append(
                            Discrepancy(
                                rid=rid,
                                field="last_deploy_result",
                                expected=db_deploy_result,
                                actual=scheduler_resource_state.last_deploy_result,
                            )
                        )
                if db_blocked_status:
                    if scheduler_resource_state.blocked != db_blocked_status:
                        resource_discrepancies.append(
                            Discrepancy(
                                rid=rid,
                                field="blocked_status",
                                expected=db_blocked_status,
                                actual=scheduler_resource_state.blocked,
                            )
                        )
                if db_compliance_status:
                    if scheduler_resource_state.compliance != db_compliance_status:
                        resource_discrepancies.append(
                            Discrepancy(
                                rid=rid,
                                field="compliance_status",
                                expected=db_compliance_status,
                                actual=scheduler_resource_state.compliance,
                            )
                        )

                if resource_discrepancies:
                    discrepancy_map[rid] = resource_discrepancies

                # Pass back control to the io loop every 100 iterations to not
                # block scheduler operations in case we have a lot of resources.
                if i >= NB_ITERATIONS_PASS_IO_LOOP:
                    await asyncio.sleep(0)
                    i = 0
                i += 1

            return discrepancy_map

        def report_model_version_mismatch(db_version: int | None) -> SchedulerStatusReport:
            LOGGER.info(
                "Cannot compare scheduler status and database status because of "
                "model version mismatch (%s and %s respectively). "
                "The scheduler might not have processed this new version yet.",
                self._state.version,
                db_version,
            )
            return SchedulerStatusReport(
                scheduler_state={},
                db_state={},
                resource_states={},
                discrepancies=[
                    Discrepancy(
                        rid=None,
                        field="model_version",
                        expected=str(db_version),
                        actual=str(self._state.version),
                    )
                ],
            )

        latest_version: int | None
        async with self._scheduler_lock:
            async with self.state_update_manager.get_connection() as connection:
                try:
                    latest_model: ModelVersion = await self._get_single_model_version_from_db(connection=connection)
                except KeyError:
                    return SchedulerStatusReport(scheduler_state={}, db_state={}, resource_states={}, discrepancies={})
                if latest_model.version != self._state.version:
                    return report_model_version_mismatch(latest_model.version)

                resource_states_in_db: Mapping[ResourceIdStr, const.ResourceState]
                latest_version, resource_states_in_db = await data.Resource.get_resource_states_latest_version(
                    env=self.environment, connection=connection
                )
                if latest_version != self._state.version:
                    return report_model_version_mismatch(latest_version)

            discrepancy_map = await _build_discrepancy_map(resource_states_in_db=resource_states_in_db)
            return SchedulerStatusReport(
                scheduler_state=self._state.resource_state,
                db_state=latest_model.resources,
                resource_states=resource_states_in_db,
                discrepancies=discrepancy_map,
            )

    async def suspend_deployments(self, reason: str) -> None:
        """
        Suspend all agent operations. All other scheduler functionality remains active.
        """
        LOGGER.info("Suspending all deployment operations: %s", reason)
        self._deployment_suspended = True
        await asyncio.gather(*[worker.stop() for worker in self._workers.values()])
        self._work.add_poison_pill_to_agent_queues(reason=reason)
        await asyncio.gather(*[worker.join() for worker in self._workers.values()])

    async def resume_deployments(self) -> None:
        """
        Resume all agent operations.
        """
        LOGGER.info("Resuming all deployment operations.")
        self._deployment_suspended = False
        await self.refresh_all_agent_states_from_db()
