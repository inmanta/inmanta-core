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
import logging
import typing
import uuid
from abc import abstractmethod
from collections.abc import Collection, Mapping, Set
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import asyncpg

import inmanta.deploy.timers
from inmanta import const, data
from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.agent.executor import DeployResult, FactResult
from inmanta.data import ConfigurationModel, Environment
from inmanta.data.model import ResourceIdStr, ResourceType, ResourceVersionIdStr
from inmanta.deploy import work
from inmanta.deploy.persistence import StateUpdateManager, ToDbUpdateManager
from inmanta.deploy.state import (
    AgentStatus,
    BlockedStatus,
    ComplianceStatus,
    DeploymentResult,
    ModelState,
    ResourceDetails,
    ResourceState,
)
from inmanta.deploy.tasks import Deploy, DryRun, RefreshFact
from inmanta.deploy.work import PrioritizedTask, TaskPriority
from inmanta.protocol import Client
from inmanta.resources import Id

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResourceIntent:
    model_version: int
    details: ResourceDetails
    dependencies: Optional[Mapping[ResourceIdStr, const.ResourceState]]


class TaskManager(StateUpdateManager, abc.ABC):
    """
    Interface for communication with tasks (deploy.task.Task). Offers methods to inspect intent and to report task results.
    """

    environment: uuid.UUID
    client: Client
    code_manager: CodeManager
    executor_manager: executor.ExecutorManager[executor.Executor]

    @abstractmethod
    def get_types_for_agent(self, agent: str) -> Collection[ResourceType]:
        """
        Returns a collection of all resource types that are known to live on a given agent.
        """

    @abstractmethod
    async def get_resource_intent(
        self,
        resource: ResourceIdStr,
    ) -> Optional[ResourceIntent]:
        """
        Returns the current version and the details for the given resource, or None if it is not (anymore) managed by the
        scheduler.

        Acquires appropriate locks.
        """

    @abstractmethod
    async def deploy_start(
        self,
        resource: ResourceIdStr,
    ) -> Optional[ResourceIntent]:
        """
        Register the start of deployment for the given resource and return its current version details
        along with the last non-deploying state for its dependencies, or None if it is not (anymore)
        managed by the scheduler.

        Acquires appropriate locks.
        """

    @abstractmethod
    async def deploy_done(
        self,
        resource: ResourceIdStr,
        *,
        attribute_hash: str,
        status: ComplianceStatus,
        deployment_result: Optional[DeploymentResult] = None,
    ) -> None:
        """
        Register the end of deployment for the given resource: update the resource state based on the deployment result
        and inform its dependencies that deployment is finished.
        Since knowledge of deployment result implies a finished deploy, it must only be set
        when a deploy has just finished.

        Acquires appropriate locks

        :param resource: The resource to report state for.
        :param attribute_hash: The resource's attribute hash for which this state applies. No scheduler state is updated if the
            hash indicates the state information is stale.
        :param status: The new resource status.
        :param deployment_result: The result of the deploy, iff one just finished, otherwise None.
        """


class TaskRunner:
    def __init__(self, endpoint: str, scheduler: "ResourceScheduler"):
        self.endpoint = endpoint
        self.status = AgentStatus.STOPPED
        self._scheduler = scheduler
        self._task: typing.Optional[asyncio.Task[None]] = None
        self._notify_task: typing.Optional[asyncio.Task[None]] = None

    async def _start(self) -> None:
        self.status = AgentStatus.STARTED
        assert (
            self._task is None or self._task.done()
        ), f"Task Runner {self.endpoint} is trying to start twice, this should not happen"
        self._task = asyncio.create_task(self._run())

    async def _stop(self) -> None:
        self.status = AgentStatus.STOPPING

    async def notify(self) -> None:
        """
        Method to notify the runner that something has changed in the DB. This method will fetch the new information
        regarding the environment and the information related to the runner (agent). Depending on the desired state of the
        agent, it will either stop / start the agent or do nothing
        """
        should_be_running = await self._scheduler.should_be_running() and await self._scheduler.should_runner_be_running(
            endpoint=self.endpoint
        )

        match self.status:
            case AgentStatus.STARTED if not should_be_running:
                await self._stop()
            case AgentStatus.STOPPED if should_be_running:
                await self._start()
            case AgentStatus.STOPPING if should_be_running:
                self.status = AgentStatus.STARTED

    def notify_sync(self) -> None:
        """
        Method to notify the runner that something has changed in the DB in a synchronous manner.
        """
        # We save it to be sure that the task will not be GC
        self._notify_task = asyncio.create_task(self.notify())

    async def _run(self) -> None:
        """Main loop for one agent. It will first fetch or create its actual state from the DB to make sure that it's
        allowed to run."""
        while self._scheduler._running and self.status == AgentStatus.STARTED:
            task, reason = await self._scheduler._work.agent_queues.queue_get(self.endpoint)
            try:
                await task.execute(self._scheduler, self.endpoint, reason)
            except Exception:
                LOGGER.exception(
                    "Task %s for agent %s has failed and the exception was not properly handled", task, self.endpoint
                )

            self._scheduler._work.agent_queues.task_done(self.endpoint, task)

        self.status = AgentStatus.STOPPED

    def is_running(self) -> bool:
        return self.status == AgentStatus.STARTED

    async def join(self) -> None:
        if self._task is None or self._task.done():
            return
        await self._task


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
        self._state: ModelState = ModelState(version=0)
        self._work: work.ScheduledWork = work.ScheduledWork(
            requires=self._state.requires.requires_view(),
            provides=self._state.requires.provides_view(),
            new_agent_notify=self._create_agent,
        )

        # We uphold two locks to prevent concurrency conflicts between external events (e.g. new version or deploy request)
        # and the task executor background tasks.
        #
        # - lock to block scheduler state access (both model state and scheduled work) during scheduler-wide state updates
        #   (e.g. trigger deploy). A single lock suffices since all state accesses (both read and write) by the task runners are
        #   short, synchronous operations (and therefore we wouldn't gain anything by allowing multiple readers).
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

        self.environment = environment
        self.client = client
        self.code_manager = CodeManager(client)
        self.executor_manager = executor_manager
        self._state_update_delegate = ToDbUpdateManager(client, environment)

        self._timer_manager = inmanta.deploy.timers.TimerManager(self)

    def reset(self) -> None:
        """
        Clear out all state and start empty

        only allowed when ResourceScheduler is not running
        """
        assert not self._running
        self._state.reset()
        self._work.reset()
        self._workers.clear()
        self._deploying_latest.clear()
        self._timer_manager.reset()

    async def start(self) -> None:
        if self._running:
            return
        self.reset()
        await self.reset_resource_state()

        await self._initialize()
        self._running = True

    async def _initialize(self) -> None:
        """
        Initialize the scheduler state and continue the deployment where we were before the server was shutdown.
        """
        self._timer_manager._initialize()

        async with data.ConfigurationModel.get_connection() as con:
            # Get resources from the database
            try:
                version, resources, requires = await self._get_resources_in_latest_version(connection=con)
            except KeyError:
                # No model version has been released yet.
                return

            # Rely on the incremental calculation to determine which resources should be deployed and which not.
            increment: set[ResourceIdStr]
            increment, _ = await ConfigurationModel.get_increment(self.environment, version, connection=con)

        resources_to_deploy: Mapping[ResourceIdStr, ResourceDetails] = {rid: resources[rid] for rid in increment}
        up_to_date_resources: Mapping[ResourceIdStr, ResourceDetails] = {
            rid: resources[rid] for rid in resources.keys() if rid not in increment
        }

        await self._new_version(
            version,
            resources=resources_to_deploy,
            requires=requires,
            up_to_date_resources=up_to_date_resources,
            reason="Deploy was triggered because the scheduler was started",
        )

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._timer_manager.stop()
        self._work.agent_queues.send_shutdown()

    async def join(self) -> None:
        await asyncio.gather(*[worker.join() for worker in self._workers.values()])
        await self._timer_manager.join()

    async def deploy(self, *, reason: str, priority: TaskPriority = TaskPriority.USER_DEPLOY) -> None:
        """
        Trigger a deploy
        """
        if not self._running:
            return
        async with self._scheduler_lock:
            self._work.deploy_with_context(
                self._state.dirty, reason=reason, priority=priority, deploying=self._deploying_latest
            )

    async def repair(self, *, reason: str, priority: TaskPriority = TaskPriority.USER_REPAIR) -> None:
        """
        Trigger a repair, i.e. mark all unblocked resources as dirty, then trigger a deploy.
        """

        def _should_deploy(resource: ResourceIdStr) -> bool:
            if (resource_state := self._state.resource_state.get(resource)) is not None:
                return not resource_state.blocked.is_blocked()
            # No state was found for this resource. Should probably not happen
            # but err on the side of caution and mark for redeploy.
            return True

        if not self._running:
            return
        async with self._scheduler_lock:
            self._state.dirty.update(resource for resource in self._state.resources.keys() if _should_deploy(resource))
            self._work.deploy_with_context(
                self._state.dirty, reason=reason, priority=priority, deploying=self._deploying_latest
            )

    async def dryrun(self, dry_run_id: uuid.UUID, version: int) -> None:
        if not self._running:
            return
        resources = await self._build_resource_mappings_from_db(version)
        for rid, resource in resources.items():
            self._work.agent_queues.queue_put_nowait(
                PrioritizedTask(
                    task=DryRun(
                        resource=rid,
                        version=version,
                        resource_details=resource,
                        dry_run_id=dry_run_id,
                    ),
                    priority=TaskPriority.DRYRUN,
                )
            )

    async def get_facts(self, resource: dict[str, object]) -> None:
        if not self._running:
            return
        rid = Id.parse_id(resource["id"]).resource_str()
        self._work.agent_queues.queue_put_nowait(
            PrioritizedTask(
                task=RefreshFact(resource=rid),
                priority=TaskPriority.FACT_REFRESH,
            )
        )

    async def trigger_deploy_for_resource(self, resource: ResourceIdStr, reason: str, priority: TaskPriority) -> None:
        """
        Make sure the given resource is marked for deployment with at least the provided priority.
        If the given priority is higher than the previous one (or if it didn't exist before), a new deploy
        task will be scheduled with the provided reason.
        """
        async with self._scheduler_lock:
            if resource not in self._state.resource_state:
                # The resource was removed from the model by the time this method was triggered
                return

            if self._state.resource_state[resource].blocked is BlockedStatus.YES:  # Can't deploy
                return
            to_deploy: set[ResourceIdStr] = {resource}

            self._work.deploy_with_context(
                to_deploy,
                reason=reason,
                priority=priority,
                deploying=self._deploying_latest,
            )

    async def _build_resource_mappings_from_db(
        self, version: int, *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> Mapping[ResourceIdStr, ResourceDetails]:
        """
        Build a view on current resources. Might be filtered for a specific environment, used when a new version is released

        :return: resource_mapping {id -> resource details}
        """
        async with data.Resource.get_connection(connection) as con:
            resources_from_db = await data.Resource.get_resources_for_version(self.environment, version, connection=con)

        resource_mapping = {
            resource.resource_id: ResourceDetails(
                resource_id=resource.resource_id,
                attribute_hash=resource.attribute_hash,
                attributes=resource.attributes,
                status=resource.status,
            )
            for resource in resources_from_db
        }
        return resource_mapping

    def _construct_requires_mapping(
        self, resources: Mapping[ResourceIdStr, ResourceDetails]
    ) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        require_mapping = {
            resource: {Id.parse_id(req).resource_str() for req in details.attributes.get("requires", [])}
            for resource, details in resources.items()
        }
        return require_mapping

    async def _get_resources_in_latest_version(
        self,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> tuple[int, Mapping[ResourceIdStr, ResourceDetails], Mapping[ResourceIdStr, Set[ResourceIdStr]]]:
        """
        Returns a tuple containing:
            1. The version number of the latest released model.
            2. A dict mapping every resource_id in the latest released version to its ResourceDetails.
            3. A dict mapping every resource_id in the latest released version to the set of resources it requires.
        """
        async with ConfigurationModel.get_connection(connection) as con:
            cm_version = await ConfigurationModel.get_latest_version(self.environment, connection=con)
            if cm_version is None:
                raise KeyError()
            model_version = cm_version.version
            resources_from_db = await self._build_resource_mappings_from_db(version=model_version, connection=con)
            requires_from_db = self._construct_requires_mapping(resources_from_db)
            return model_version, resources_from_db, requires_from_db

    async def read_version(
        self,
    ) -> None:
        """
        Update model state and scheduled work based on the latest released version in the database,
        e.g. when a new version is released. Triggers a deploy after updating internal state:
        - schedules new or updated resources to be deployed
        - schedules any resources that are not in a known good state.
        - rearranges deploy tasks by requires if required
        """
        if not self._running:
            return
        try:
            version, resources, requires = await self._get_resources_in_latest_version()
        except KeyError:
            # No model version has been released yet.
            return
        else:
            await self._new_version(
                version,
                resources,
                requires,
                reason="Deploy was triggered because a new version has been released",
            )

    async def reset_resource_state(self) -> None:
        """
        Update resources on the latest version of the model stuck in "deploying" state. This can occur when the Scheduler is
        killed in the middle of a deployment.
        """
        cm_version = await ConfigurationModel.get_latest_version(self.environment)
        if cm_version is None:
            return
        version = cm_version.version

        await data.Resource.reset_resource_state(self.environment, version)

    async def _new_version(
        self,
        version: int,
        resources: Mapping[ResourceIdStr, ResourceDetails],
        requires: Mapping[ResourceIdStr, Set[ResourceIdStr]],
        up_to_date_resources: Optional[Mapping[ResourceIdStr, ResourceDetails]] = None,
        reason: str = "Deploy was triggered because a new version has been released",
    ) -> None:
        up_to_date_resources = {} if up_to_date_resources is None else up_to_date_resources
        async with self._intent_lock:
            # Inspect new state and compare it with the old one before acquiring the scheduler lock.
            # This is safe because we only read intent-related state here, for which we've already acquired the lock
            deleted_resources: Set[ResourceIdStr] = self._state.resources.keys() - resources.keys()
            for resource in deleted_resources:
                self._work.delete_resource(resource)

            # Resources with known deployable changes (new resources or old resources with deployable changes)
            new_desired_state: set[ResourceIdStr] = set()
            # Only contains the direct undeployable resources, not the transitive ones.
            blocked_resources: set[ResourceIdStr] = set()
            # Resources that were undeployable in a previous model version, but got unblocked. Not the transitive ones.
            unblocked_resources: set[ResourceIdStr] = set()

            # Track potential changes in requires per resource
            added_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            dropped_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}

            for resource, details in up_to_date_resources.items():
                self._state.add_up_to_date_resource(resource, details)  # Removes from the dirty set
                # Install timers for these resources. They are up-to-date now,
                # but we want to make sure we periodically repair them.
                self._timer_manager.update_resource(resource, is_dirty=False)

            for resource, details in resources.items():
                if details.status is const.ResourceState.undefined:
                    blocked_resources.add(resource)
                    self._work.delete_resource(resource)
                    # These resources are blocked at the moment. Remove the timers for them
                    # Re-deploy will happen when (if) dependants successfully deploy
                    self._timer_manager.remove_resource(resource)
                elif resource in self._state.resources:
                    # It's a resource we know.
                    if self._state.resource_state[resource].status is ComplianceStatus.UNDEFINED:
                        # The resource has been undeployable in previous versions, but not anymore.
                        unblocked_resources.add(resource)
                    elif details.attribute_hash != self._state.resources[resource].attribute_hash:
                        # The desired state has changed.
                        new_desired_state.add(resource)
                    # Nothing need to be done for these resources' timers yet. They will be
                    # picked up by the scheduler eventually, and only then, after deployment
                    # action should be taken wrt timers.
                else:
                    # It's a resource we don't know yet: it will be marked as dirty
                    # and added to the scheduled work. Per-resource timers for this
                    # resource will be set when (if) the associated deploy task completes
                    # for this resource.
                    new_desired_state.add(resource)

                old_requires: Set[ResourceIdStr] = self._state.requires.get(resource, set())
                new_requires: Set[ResourceIdStr] = requires.get(resource, set())
                added: Set[ResourceIdStr] = new_requires - old_requires
                dropped: Set[ResourceIdStr] = old_requires - new_requires
                if added:
                    added_requires[resource] = added
                if dropped:
                    dropped_requires[resource] = dropped
                # this loop is race-free, potentially slow, and completely synchronous
                # => regularly pass control to the event loop to not block scheduler operation during update prep
                await asyncio.sleep(0)

            # A resource should not be present in more than one of these resource sets
            assert len(new_desired_state | blocked_resources | unblocked_resources) == len(new_desired_state) + len(
                blocked_resources
            ) + len(unblocked_resources)

            # in the current implementation everything below the lock is synchronous, so it's not technically required. It is
            # however kept for two reasons:
            # 1. pass context once more to event loop before starting on the sync path
            #   (could be achieved with a simple sleep(0) if desired)
            # 2. clarity: it clearly signifies that this is the atomic and performance-sensitive part
            async with self._scheduler_lock:
                self._state.version = version
                for resource in blocked_resources:
                    self._state.block_resource(resource, resources[resource], is_transitive=False)  # Removes from the dirty set
                for resource in new_desired_state:
                    self._state.update_desired_state(resource, resources[resource])  # Updates the dirty set
                for resource in added_requires.keys() | dropped_requires.keys():
                    self._state.update_requires(resource, requires[resource])
                transitively_blocked_resources: Set[ResourceIdStr] = self._state.block_provides(resources=blocked_resources)
                for resource in unblocked_resources:
                    self._state.mark_as_defined(resource, resources[resource])  # Updates the dirty set
                # Update set of in-progress non-stale deploys by trimming resources with new state
                self._deploying_latest.difference_update(
                    new_desired_state, deleted_resources, blocked_resources, transitively_blocked_resources
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
                for resource in deleted_resources:
                    self._state.drop(resource)  # Removes from the dirty set
                for resource in blocked_resources | transitively_blocked_resources:
                    self._work.delete_resource(resource)

            # Once more, drop all resources that do not exist in this version from the scheduled work, in case they got added
            # again by a deploy trigger (because we dropped them outside the lock).
            for resource in deleted_resources:
                # Delete the deleted resources outside the _scheduler_lock, because we do not want to keep the _scheduler_lock
                # acquired longer than required. The worst that can happen here is that we deploy the deleted resources one
                # time too many, which is not so bad.
                self._work.delete_resource(resource)
                self._timer_manager.remove_resource(resource)

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
        current_agent = await data.Agent.get(env=self.environment, endpoint=endpoint)
        return not current_agent.paused

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

    def _get_resource_intent(self, resource: ResourceIdStr) -> Optional[ResourceDetails]:
        """
        Get intent of a given resource.
        Always expected to be called under lock
        """
        try:
            return self._state.resources[resource]
        except KeyError:
            # Stale resource
            # May occur in rare races between new_version and acquiring the lock we're under here. This race is safe
            # because of this check, and an intrinsic part of the locking design because it's preferred over wider
            # locking for performance reasons.
            return None

    async def get_resource_intent(self, resource: ResourceIdStr) -> Optional[ResourceIntent]:
        async with self._scheduler_lock:
            # fetch resource details under lock
            resource_details = self._get_resource_intent(resource)
            if resource_details is None:
                return None
            return ResourceIntent(model_version=self._state.version, details=resource_details, dependencies=None)

    async def deploy_start(self, resource: ResourceIdStr) -> Optional[ResourceIntent]:
        self._timer_manager.remove_resource(resource)

        async with self._scheduler_lock:
            # fetch resource details under lock
            resource_details = self._get_resource_intent(resource)
            if resource_details is None:
                return None
            dependencies = await self._get_last_non_deploying_state_for_dependencies(resource=resource)
            self._deploying_latest.add(resource)
            return ResourceIntent(model_version=self._state.version, details=resource_details, dependencies=dependencies)

    async def deploy_done(
        self,
        resource: ResourceIdStr,
        *,
        attribute_hash: str,
        status: ComplianceStatus,
        deployment_result: Optional[DeploymentResult] = None,
    ) -> None:
        if deployment_result is DeploymentResult.NEW:
            raise ValueError("report_resource_state should not be called to register new resources")

        # Keep track of the last known state for this resource before leaving the scheduler lock
        # to re-schedule an individual repair or deploy accordingly:
        #   If the deploy was successful, schedule a repair.
        #   Otherwise, schedule whichever comes sooner between a repair and a deploy.
        is_dirty: bool

        async with self._scheduler_lock:
            # refresh resource details for latest model state
            details: Optional[ResourceDetails] = self._state.resources.get(resource, None)

            if details is None:
                # we are stale and removed
                return

            state: ResourceState = self._state.resource_state[resource]

            if details.attribute_hash != attribute_hash:
                # We are stale but still the last deploy
                # We can update the deployment_result (which is about last deploy)
                # We can't update status (which is about active state only)
                # None of the event propagation or other update happen either for the same reason
                if deployment_result is not None:
                    state.deployment_result = deployment_result
                return

            # We are not stale
            state.status = status
            if deployment_result is not None:
                # first update state, then send out events
                self._deploying_latest.remove(resource)

                previous_deployment_result = state.deployment_result

                state.deployment_result = deployment_result
                self._work.finished_deploy(resource)

                # Set of dependant resources that are interested in deploys of the current resource
                concerned_resources: set[ResourceIdStr] = set()
                provides: Set[ResourceIdStr] = self._state.requires.provides_view().get(resource, set())

                if deployment_result is DeploymentResult.DEPLOYED:
                    self._state.dirty.discard(resource)
                    is_dirty = False

                    if previous_deployment_result != DeploymentResult.DEPLOYED:
                        # This resource went from not deployed to deployed
                        # we have to inform its dependants regardless of event propagation
                        # so that we can try to re-deploy them in case this resource's previous
                        # failure was the reason they were skipped

                        # FIXME: stop informing resource skipped because of
                        #  a custom handler skip via this mechanism

                        for dependant in provides:
                            if not self._state.resources.get(dependant, None):
                                continue
                            if not (dependant_status := self._state.resource_state.get(dependant, None)):
                                continue
                            if dependant_status.blocked is BlockedStatus.NO:
                                concerned_resources.add(dependant)

                else:
                    # In most cases it will already be marked as dirty but in rare cases the deploy that just finished might
                    # have been triggered by an event, on a previously successful deployed resource. Either way, a failure
                    # (or skip) causes it to become dirty now.
                    self._state.dirty.add(resource)
                    is_dirty = True

                    if deployment_result is DeploymentResult.SKIPPED:
                        # Also add back dependents to the dirty set
                        # For now we add all dependents

                        dependant_resources = {
                            dependant for dependant in provides if self._state.resources.get(dependant, None) is not None
                        }
                        self._state.dirty.update(dependant_resources)
                        for dependant in dependant_resources:
                            # No point in re-trying dependants since this resource was skipped
                            # FIXME as part of https://github.com/inmanta/inmanta-core/issues/8423
                            self._timer_manager.remove_resource(dependant)

                # propagate events
                if details.attributes.get(const.RESOURCE_ATTRIBUTE_SEND_EVENTS, False):
                    event_listeners: Set[ResourceIdStr] = {
                        dependant
                        for dependant in provides
                        if (dependant_details := self._state.resources.get(dependant, None)) is not None
                        # default to True for backward compatibility, i.e. not all resources have the field
                        if dependant_details.attributes.get(const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS, True)
                    }
                    concerned_resources.update(event_listeners)

                if concerned_resources:
                    # do not pass deploying tasks because for event propagation we really want to start a new one,
                    # even if the current intent is already being deployed
                    task = Deploy(resource=resource)
                    assert task in self._work.agent_queues.in_progress
                    priority = self._work.agent_queues.in_progress[task]
                    self._timer_manager.remove_resources(concerned_resources)
                    self._work.deploy_with_context(
                        concerned_resources,
                        reason=f"Deploying because an event was received from {resource}",
                        priority=priority,
                        deploying=set(),
                    )

        # No matter the deployment result, schedule a re-deploy for this resource
        self._timer_manager.update_resource(resource, is_dirty=is_dirty)

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
                case ResourceState(status=ComplianceStatus.UNDEFINED):
                    dependencies_state[dep_id] = const.ResourceState.undefined
                case ResourceState(blocked=BlockedStatus.YES):
                    dependencies_state[dep_id] = const.ResourceState.skipped_for_undefined
                case ResourceState(status=ComplianceStatus.HAS_UPDATE):
                    dependencies_state[dep_id] = const.ResourceState.available
                case ResourceState(deployment_result=DeploymentResult.SKIPPED):
                    dependencies_state[dep_id] = const.ResourceState.skipped
                case ResourceState(deployment_result=DeploymentResult.DEPLOYED):
                    dependencies_state[dep_id] = const.ResourceState.deployed
                case ResourceState(deployment_result=DeploymentResult.FAILED):
                    dependencies_state[dep_id] = const.ResourceState.failed
                case _:
                    raise Exception(f"Failed to parse the resource state for {dep_id}: {resource_state_object}")
        return dependencies_state

    def get_types_for_agent(self, agent: str) -> Collection[ResourceType]:
        return list(self._state.types_per_agent[agent])

    async def send_in_progress(self, action_id: UUID, resource_id: ResourceVersionIdStr) -> None:
        await self._state_update_delegate.send_in_progress(action_id, resource_id)

    async def send_deploy_done(self, result: DeployResult) -> None:
        return await self._state_update_delegate.send_deploy_done(result)

    async def dryrun_update(self, env: uuid.UUID, dryrun_result: executor.DryrunResult) -> None:
        await self._state_update_delegate.dryrun_update(env, dryrun_result)

    async def set_parameters(self, fact_result: FactResult) -> None:
        await self._state_update_delegate.set_parameters(fact_result)
