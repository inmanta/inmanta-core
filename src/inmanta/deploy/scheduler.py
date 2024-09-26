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

from inmanta import data
from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.data import Resource
from inmanta.data.model import ResourceIdStr, ResourceType
from inmanta.deploy import work
from inmanta.deploy.state import DeploymentResult, ModelState, ResourceDetails, ResourceState, ResourceStatus
from inmanta.deploy.tasks import DryRun, RefreshFact, Task
from inmanta.deploy.work import PrioritizedTask
from inmanta.protocol import Client
from inmanta.resources import Id

LOGGER = logging.getLogger(__name__)


class TaskManager(abc.ABC):
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

    def reset(self) -> None:
        """
        Clear out all state and start empty

        only allowed when ResourceScheduler is not running
        """
        assert not self._running
        self._state.reset()
        self._work.reset()

    async def start(self) -> None:
        self.reset()
        self._running = True
        await self.read_version()

    async def stop(self) -> None:
        self._running = False
        self._work.agent_queues.send_shutdown()
        await asyncio.gather(*self._workers.values())

    async def deploy(self) -> None:
        """
        Trigger a deploy
        """
        async with self._scheduler_lock:
            self._work.deploy_with_context(self._state.dirty, deploying=self._deploying_latest)

    async def repair(self) -> None:
        """
        Trigger a repair, i.e. mark all resources as dirty, then trigger a deploy.
        """
        async with self._scheduler_lock:
            self._state.dirty.update(self._state.resources.keys())
            self._work.deploy_with_context(self._state.dirty, deploying=self._deploying_latest)

    async def dryrun(self, dry_run_id: uuid.UUID, version: int) -> None:
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
                    priority=10,
                )
            )

    async def get_facts(self, resource: dict[str, object]) -> None:
        rid = Id.parse_id(resource["id"]).resource_str()
        self._work.agent_queues.queue_put_nowait(
            PrioritizedTask(
                task=RefreshFact(resource=rid),
                priority=10,
            )
        )

    async def _build_resource_mappings_from_db(self, version: int | None = None) -> Mapping[ResourceIdStr, ResourceDetails]:
        """
        Build a view on current resources. Might be filtered for a specific environment, used when a new version is released

        :return: resource_mapping {id -> resource details}
        """
        if version is None:
            # FIXME[8118]: resources have not necessarily been released
            resources_from_db: list[Resource] = await data.Resource.get_resources_in_latest_version(
                environment=self.environment
            )
        else:
            resources_from_db = await data.Resource.get_resources_for_version(self.environment, version)

        resource_mapping = {
            resource.resource_id: ResourceDetails(
                resource_id=resource.resource_id,
                attribute_hash=resource.attribute_hash,
                attributes=resource.attributes,
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

    async def read_version(
        self,
    ) -> None:
        """
        Update model state and scheduled work based on the latest released version in the database, e.g. when the scheduler is
        started or when a new version is released. Triggers a deploy after updating internal state:
        - schedules new or updated resources to be deployed
        - schedules any resources that are not in a known good state.
        - rearranges deploy tasks by requires if required
        """
        environment = await data.Environment.get_by_id(self.environment)
        if environment is None:
            raise ValueError(f"No environment found with this id: `{self.environment}`")
        # FIXME[8119]: version does not necessarily correspond to resources' version
        #       + last_version is reserved, not necessarily released
        #       -> call ConfigurationModel.get_version_nr_latest_version() instead?
        version = environment.last_version
        resources_from_db = await self._build_resource_mappings_from_db()
        requires_from_db = self._construct_requires_mapping(resources_from_db)
        await self._new_version(version, resources_from_db, requires_from_db)

    async def _new_version(
        self,
        version: int,
        resources: Mapping[ResourceIdStr, ResourceDetails],
        requires: Mapping[ResourceIdStr, Set[ResourceIdStr]],
    ) -> None:
        async with self._intent_lock:
            # Inspect new state and compare it with the old one before acquiring scheduler the lock.
            # This is safe because we only read intent-related state here, for which we've already acquired the lock
            deleted_resources: Set[ResourceIdStr] = self._state.resources.keys() - resources.keys()
            for resource in deleted_resources:
                self._work.delete_resource(resource)

            new_desired_state: set[ResourceIdStr] = set()
            added_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            dropped_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            for resource, details in resources.items():
                if (
                    resource not in self._state.resources
                    or details.attribute_hash != self._state.resources[resource].attribute_hash
                ):
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

            # in the current implementation everything below the lock is synchronous, so it's not technically required. It is
            # however kept for two reasons:
            # 1. pass context once more to event loop before starting on the sync path
            #   (could be achieved with a simple sleep(0) if desired)
            # 2. clarity: it clearly signifies that this is the atomic and performance-sensitive part
            async with self._scheduler_lock:
                self._state.version = version
                for resource in new_desired_state:
                    self._state.update_desired_state(resource, resources[resource])
                for resource in added_requires.keys() | dropped_requires.keys():
                    self._state.update_requires(resource, requires[resource])
                # Update set of in-progress non-stale deploys by trimming resources with new state
                self._deploying_latest.difference_update(new_desired_state, deleted_resources)
                # ensure deploy for ALL dirty resources, not just the new ones
                self._work.deploy_with_context(
                    self._state.dirty,
                    deploying=self._deploying_latest,
                    added_requires=added_requires,
                    dropped_requires=dropped_requires,
                )
                for resource in deleted_resources:
                    self._state.drop(resource)
            # Once more, drop all resources that do not exist in this version from the scheduled work, in case they got added
            # again by a deploy trigger (because we dropped them outside the lock).
            for resource in deleted_resources:
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
                # The reported resource state is for a stale resource and therefore no longer relevant.
                return
            state: ResourceState = self._state.resource_state[resource]
            state.status = status
            if deployment_result is not None:
                self._deploying_latest.remove(resource)
                state.deployment_result = deployment_result
                self._work.finished_deploy(resource)
                if deployment_result is DeploymentResult.DEPLOYED:
                    self._state.dirty.discard(resource)
                # propagate events
                if details.attributes.get("send_event", False):
                    provides: Set[ResourceIdStr] = self._state.requires.provides_view().get(resource, set())
                    if provides:
                        # TODO: add test for deploying=set()
                        # do not pass deploying tasks because for event propagation we really want to start a new one,
                        # even if the current intent is already being deployed
                        self._work.deploy_with_context(provides, deploying=set())

    def get_types_for_agent(self, agent: str) -> Collection[ResourceType]:
        return list(self._state.types_per_agent[agent])
