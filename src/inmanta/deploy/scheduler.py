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
import uuid
from abc import abstractmethod
from collections.abc import Collection, Mapping, Set
from typing import Optional
from uuid import UUID

import asyncpg

from inmanta import const, data
from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.agent.executor import DeployResult
from inmanta.data import ConfigurationModel
from inmanta.data.model import ResourceIdStr, ResourceType, ResourceVersionIdStr
from inmanta.deploy import work
from inmanta.deploy.persistence import StateUpdateManager, ToDbUpdateManager
from inmanta.deploy.state import DeploymentResult, ModelState, ResourceDetails, ResourceState, ResourceStatus
from inmanta.deploy.tasks import Deploy, DryRun, RefreshFact, Task
from inmanta.deploy.work import PrioritizedTask, TaskPriority
from inmanta.protocol import Client
from inmanta.resources import Id

LOGGER = logging.getLogger(__name__)


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
        *,
        for_deploy: bool = False,
    ) -> Optional[tuple[int, ResourceDetails]]:
        """
        Returns the current version and the details for the given resource, or None if it is not (anymore) managed by the
        scheduler.

        :param for_deploy: True iff the task will start deploying this intent. If set, must call report_resource_state later
            with deployment result.

        Acquires appropriate locks.
        """

    @abstractmethod
    async def report_resource_state(
        self,
        resource: ResourceIdStr,
        *,
        attribute_hash: str,
        status: ResourceStatus,
        deployment_result: Optional[DeploymentResult] = None,
    ) -> None:
        """
        Report new state for a resource. Since knowledge of deployment result implies a finished deploy, it must only be set
        when a deploy has just finished.

        Acquires appropriate locks

        :param resource: The resource to report state for.
        :param attribute_hash: The resource's attribute hash for which this state applies. No scheduler state is updated if the
            hash indicates the state information is stale.
        :param status: The new resource status.
        :param deployment_result: The result of the deploy, iff one just finished, otherwise None.
        """


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
            new_agent_notify=self._start_for_agent,
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
        self._workers: dict[str, asyncio.Task[None]] = {}
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
        self._state_update_delegate = ToDbUpdateManager(environment)

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

    async def start(self) -> None:
        if self._running:
            return
        self.reset()
        await self._initialize()
        self._running = True

    async def _initialize(self) -> None:
        """
        Initialize the scheduler state and continue the deployment where we were before the server was shutdown.
        """
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
            version, resources=resources_to_deploy, requires=requires, up_to_date_resources=up_to_date_resources
        )

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._work.agent_queues.send_shutdown()
        await asyncio.gather(*self._workers.values())

    async def deploy(self, priority: TaskPriority = TaskPriority.USER_DEPLOY) -> None:
        """
        Trigger a deploy
        """
        if not self._running:
            return
        async with self._scheduler_lock:
            self._work.deploy_with_context(self._state.dirty, priority=priority, deploying=self._deploying_latest)

    async def repair(self, priority: TaskPriority = TaskPriority.USER_REPAIR) -> None:
        """
        Trigger a repair, i.e. mark all resources as dirty, then trigger a deploy.
        """
        if not self._running:
            return
        async with self._scheduler_lock:
            self._state.dirty.update(self._state.resources.keys())
            self._work.deploy_with_context(self._state.dirty, priority=priority, deploying=self._deploying_latest)

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
            await self._new_version(version, resources, requires)

    async def _new_version(
        self,
        version: int,
        resources: Mapping[ResourceIdStr, ResourceDetails],
        requires: Mapping[ResourceIdStr, Set[ResourceIdStr]],
        up_to_date_resources: Optional[Mapping[ResourceIdStr, ResourceDetails]] = None,
    ) -> None:
        up_to_date_resources = {} if up_to_date_resources is None else up_to_date_resources
        async with self._intent_lock:
            # Inspect new state and compare it with the old one before acquiring scheduler the lock.
            # This is safe because we only read intent-related state here, for which we've already acquired the lock
            deleted_resources: Set[ResourceIdStr] = self._state.resources.keys() - resources.keys()
            for resource in deleted_resources:
                self._work.delete_resource(resource)

            new_desired_state: set[ResourceIdStr] = set()
            # Only contains the direct undeployable resources, not the transitive ones.
            blocked_resources: set[ResourceIdStr] = set()
            # Resources that were undeployable in a previous model version, but got unblocked. Not the transitive ones.
            unblocked_resources: set[ResourceIdStr] = set()
            added_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            dropped_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            for resource, details in up_to_date_resources.items():
                self._state.add_up_to_date_resource(resource, details)

            for resource, details in resources.items():
                if details.status is const.ResourceState.undefined:
                    blocked_resources.add(resource)
                    self._work.delete_resource(resource)
                elif resource in self._state.resources:
                    # It's a resource we know.
                    if self._state.resource_state[resource].status is ResourceStatus.UNDEFINED:
                        # The resource has been undeployable in previous versions, but not anymore.
                        unblocked_resources.add(resource)
                    elif details.attribute_hash != self._state.resources[resource].attribute_hash:
                        # The desired state has changed.
                        new_desired_state.add(resource)
                else:
                    # It's a resource we don't know yet.
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
                    self._state.block_resource(resource, details, transient=False)
                for resource in new_desired_state:
                    self._state.update_desired_state(resource, resources[resource])
                for resource in added_requires.keys() | dropped_requires.keys():
                    self._state.update_requires(resource, requires[resource])
                transitively_blocked_resources: set[ResourceIdStr] = self._state.block_provides(resources=blocked_resources)
                for resource in unblocked_resources:
                    self._state.unblock_resource(resource)
                # Update set of in-progress non-stale deploys by trimming resources with new state
                self._deploying_latest.difference_update(
                    new_desired_state, deleted_resources, blocked_resources, transitively_blocked_resources
                )
                # ensure deploy for ALL dirty resources, not just the new ones
                self._work.deploy_with_context(
                    self._state.dirty,
                    priority=TaskPriority.NEW_VERSION_DEPLOY,
                    deploying=self._deploying_latest,
                    added_requires=added_requires,
                    dropped_requires=dropped_requires,
                )
                for resource in deleted_resources:
                    self._state.drop(resource)
                for resource in blocked_resources | transitively_blocked_resources:
                    self._work.delete_resource(resource)

            # Once more, drop all resources that do not exist in this version from the scheduled work, in case they got added
            # again by a deploy trigger (because we dropped them outside the lock).
            for resource in deleted_resources:
                # Delete the deleted resources outside the _scheduler_lock, because we do not want to keep the _scheduler_lock
                # acquired longer than required. The worst that can happen here is that we deploy the deleted resources one
                # time too many, which is not so bad.
                self._work.delete_resource(resource)

    def _start_for_agent(self, agent: str) -> None:
        """Start processing for the given agent"""
        self._workers[agent] = asyncio.create_task(self._run_for_agent(agent))

    async def _run_for_agent(self, agent: str) -> None:
        """Main loop for one agent"""
        while self._running:
            task: Task = await self._work.agent_queues.queue_get(agent)
            try:
                await task.execute(self, agent)
            except Exception:
                LOGGER.exception("Task %s for agent %s has failed and the exception was not properly handled", task, agent)

            self._work.agent_queues.task_done(agent, task)

    # TaskManager interface

    async def get_resource_intent(
        self, resource: ResourceIdStr, *, for_deploy: bool = False
    ) -> Optional[tuple[int, ResourceDetails]]:
        async with self._scheduler_lock:
            # fetch resource details under lock
            try:
                result = self._state.version, self._state.resources[resource]
            except KeyError:
                # Stale resource
                # May occur in rare races between new_version and acquiring the lock we're under here. This race is safe
                # because of this check, and an intrinsic part of the locking design because it's preferred over wider
                # locking for performance reasons.
                return None
            else:
                if for_deploy:
                    # still under lock => can safely add to non-stale in-progress set
                    self._deploying_latest.add(resource)
                return result

    async def report_resource_state(
        self,
        resource: ResourceIdStr,
        *,
        attribute_hash: str,
        status: ResourceStatus,
        deployment_result: Optional[DeploymentResult] = None,
    ) -> None:
        if deployment_result is DeploymentResult.NEW:
            raise ValueError("report_resource_state should not be called to register new resources")

        async with self._scheduler_lock:
            # refresh resource details for latest model state
            details: Optional[ResourceDetails] = self._state.resources.get(resource, None)
            if details is None or details.attribute_hash != attribute_hash:
                # The reported resource state is for a stale resource and therefore no longer relevant for state updates.
                # There is also no need to send out events because a newer version will have been scheduled.
                return
            state: ResourceState = self._state.resource_state[resource]
            state.status = status
            if deployment_result is not None:
                # first update state, then send out events
                self._deploying_latest.remove(resource)
                state.deployment_result = deployment_result
                self._work.finished_deploy(resource)
                if deployment_result is DeploymentResult.DEPLOYED:
                    self._state.dirty.discard(resource)
                # propagate events
                if details.attributes.get(const.RESOURCE_ATTRIBUTE_SEND_EVENTS, False):
                    provides: Set[ResourceIdStr] = self._state.requires.provides_view().get(resource, set())
                    event_listeners: Set[ResourceIdStr] = {
                        dependant
                        for dependant in provides
                        if (dependant_details := self._state.resources.get(dependant, None)) is not None
                        # default to True for backward compatibility, i.e. not all resources have the field
                        if dependant_details.attributes.get(const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS, True)
                    }
                    if event_listeners:
                        # do not pass deploying tasks because for event propagation we really want to start a new one,
                        # even if the current intent is already being deployed
                        task = Deploy(resource=resource)
                        assert task in self._work.agent_queues.in_progress
                        priority = self._work.agent_queues.in_progress[task]
                        self._work.deploy_with_context(event_listeners, priority=priority, deploying=set())

    def get_types_for_agent(self, agent: str) -> Collection[ResourceType]:
        return list(self._state.types_per_agent[agent])

    async def send_in_progress(
        self, action_id: UUID, resource_id: ResourceVersionIdStr
    ) -> dict[ResourceIdStr, const.ResourceState]:
        return await self._state_update_delegate.send_in_progress(action_id, resource_id)

    async def send_deploy_done(self, result: DeployResult) -> None:
        return await self._state_update_delegate.send_deploy_done(result)
