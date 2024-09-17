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
import uuid
from collections.abc import Mapping, Set
from typing import Optional

from inmanta import data
from inmanta.agent import executor
from inmanta.agent.code_manager import CodeManager
from inmanta.data import Resource
from inmanta.data.model import ResourceIdStr
from inmanta.deploy import work
from inmanta.deploy.state import DeploymentResult, ModelState, ResourceDetails, ResourceState, ResourceStatus
from inmanta.deploy.tasks import DryRun, RefreshFact, Task
from inmanta.deploy.work import PrioritizedTask
from inmanta.protocol import Client
from inmanta.resources import Id

LOGGER = logging.getLogger(__name__)


# FIXME[#8008] review code structure + functionality + add docstrings
# FIXME[#8008] add import entry point test case


class ResourceScheduler:
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
            new_agent_notify=self.start_for_agent,
        )

        self._executor_manager = executor_manager

        # We uphold two locks to prevent concurrency conflicts between external events (e.g. new version or deploy request)
        # and the task executor background tasks.
        #
        # - lock to block scheduler state access (both model state and scheduled work) during scheduler-wide state updates
        #   (e.g. trigger deploy). A single lock suffices since all state accesses (both read and write) by the task runners are
        #   short, synchronous operations (and therefore we wouldn't gain anything by allowing multiple readers).
        self._scheduler_lock: asyncio.Lock = asyncio.Lock()
        # - lock to serialize scheduler state updates (i.e. process new version)
        self._update_lock: asyncio.Lock = asyncio.Lock()
        self._environment = environment

        self._running = False
        # Agent name to worker task
        # here to prevent it from being GC-ed
        self._workers: dict[str, asyncio.Task[None]] = {}

        self._code_manager = CodeManager(client)
        self._environment = environment
        self._client = client

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
            # FIXME[#8008]: more efficient access to dirty set by caching it on the ModelState
            dirty: Set[ResourceIdStr] = {r for r, details in self._state.resource_state.items() if details.needs_deploy()}
            # FIXME[#8008]: pass in running deploys
            self._work.update_state(ensure_scheduled=dirty, running_deploys=set())

    async def repair(self) -> None:
        # FIXME[#8008]: implement repair
        pass

    async def dryrun(self, dry_run_id: uuid.UUID, version: int) -> None:
        resources = await self.build_resource_mappings_from_db(version)
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

    async def get_resource_intent(self, resource: ResourceIdStr) -> Optional[tuple[int, ResourceDetails]]:
        """
        Returns the current version and the details for the given resource, or None if it is not (anymore) managed by the
        scheduler.

        Acquires scheduler lock.
        """
        async with self._scheduler_lock:
            # fetch resource details under lock
            try:
                return self._state.version, self._state.resources[resource]
            except KeyError:
                # Stale resource
                # May occur in rare races between new_version and acquiring the lock we're under here. This race is safe
                # because of this check, and an intrinsic part of the locking design because it's preferred over wider
                # locking for performance reasons.
                return None

    async def report_resource_state(
        self,
        resource: ResourceIdStr,
        attribute_hash: str,
        status: ResourceStatus,
        deployment_result: Optional[DeploymentResult] = None,
    ) -> None:
        """
        Report new state for a resource. Since knowledge of deployment result implies a finished deploy, it must only be set
        when a deploy has just finished.

        Acquires scheduler lock.

        :param resource: The resource to report state for.
        :param attribute_hash: The resource's attribute hash for which this state applies. No scheduler state is updated if the
            hash indicates the state information is stale.
        :param status: The new resource status.
        :param deployment_result: The result of the deploy, iff one just finished, else None.
        """
        async with self._scheduler_lock:
            # refresh resource details for latest model state
            details: Optional[ResourceDetails] = self._state.resources.get(resource, None)
            if details is None or details.attribute_hash != attribute_hash:
                # The reported resource state is for a stale resource and therefore no longer relevant.
                return
            state: ResourceState = self._state.resource_state[resource]
            state.status = status
            if deployment_result is not None:
                state.deployment_result = deployment_result
                self._work.finished_deploy(resource)

    async def build_resource_mappings_from_db(self, version: int | None = None) -> Mapping[ResourceIdStr, ResourceDetails]:
        """
        Build a view on current resources. Might be filtered for a specific environment, used when a new version is released

        :return: resource_mapping {id -> resource details}
        """
        if version is None:
            # TODO: BUG: not necessarily released
            resources_from_db: list[Resource] = await data.Resource.get_resources_in_latest_version(
                environment=self._environment
            )
        else:
            resources_from_db = await data.Resource.get_resources_for_version(self._environment, version)

        resource_mapping = {
            resource.resource_id: ResourceDetails(
                attribute_hash=resource.attribute_hash,
                attributes=resource.attributes,
            )
            for resource in resources_from_db
        }
        return resource_mapping

    def construct_requires_mapping(
        self, resources: Mapping[ResourceIdStr, ResourceDetails]
    ) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        require_mapping = {
            resource: {req.resource_str() for req in details.attributes.get("requires", [])}
            for resource, details in resources.items()
        }
        return require_mapping

    async def read_version(
        self,
    ) -> None:
        """
        Method that is used as a notification from the Server to retrieve the latest data concerning the release of the
        latest version. This method will fetch the latest version and the different resources in their latest version.
        It will then compute the work that needs to be done (resources to create / delete / update) to be up to date with
        this new version.
        """
        environment = await data.Environment.get_by_id(self._environment)
        if environment is None:
            raise ValueError(f"No environment found with this id: `{self._environment}`")
        # TODO BUG: version does not necessarily correspond to resources' version + last_version is reserved, not necessarily released
        #       -> call ConfigurationModel.get_version_nr_latest_version() instead?
        version = environment.last_version
        resources_from_db = await self.build_resource_mappings_from_db()
        requires_from_db = self.construct_requires_mapping(resources_from_db)
        await self.new_version(version, resources_from_db, requires_from_db)

    async def new_version(
        self,
        version: int,
        resources: Mapping[ResourceIdStr, ResourceDetails],
        requires: Mapping[ResourceIdStr, Set[ResourceIdStr]],
    ) -> None:
        async with self._update_lock:
            # Inspect new state and mark resources as "update pending" where appropriate. Since this method is the only writer
            # for "update pending", and a stale read is acceptable, we can do this part before acquiring the exclusive scheduler
            # lock.
            deleted_resources: Set[ResourceIdStr] = self._state.resources.keys() - resources.keys()
            for resource in deleted_resources:
                self._work.delete_resource(resource)

            new_desired_state: list[ResourceIdStr] = []
            added_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            dropped_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            for resource, details in resources.items():
                if (
                    resource not in self._state.resources
                    or details.attribute_hash != self._state.resources[resource].attribute_hash
                ):
                    self._state.update_pending.add(resource)
                    new_desired_state.append(resource)
                old_requires: Set[ResourceIdStr] = self._state.requires.get(resource, set())
                new_requires: Set[ResourceIdStr] = requires.get(resource, set())
                added: Set[ResourceIdStr] = new_requires - old_requires
                dropped: Set[ResourceIdStr] = old_requires - new_requires
                if added:
                    self._state.update_pending.add(resource)
                    added_requires[resource] = added
                if dropped:
                    self._state.update_pending.add(resource)
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
                    self._state.update_desired_state(resources[resource])
                for resource in added_requires.keys() | dropped_requires.keys():
                    self._state.update_requires(resource, requires[resource])
                # ensure deploy for ALL dirty resources, not just the new ones
                # FIXME[#8008]: this is copy-pasted, make into a method?
                # TODO: implement suggestion
                # FIXME: WDB TO SANDER: We should track dirty resources in a collection to not force a scan of the full state
                dirty: Set[ResourceIdStr] = {
                    r for r, details in self._state.resource_state.items() if details.status == ResourceStatus.HAS_UPDATE
                }
                self._work.update_state(
                    ensure_scheduled=dirty,
                    # FIXME[#8008]: pass in running deploys
                    running_deploys=set(),
                    added_requires=added_requires,
                    dropped_requires=dropped_requires,
                )
                for resource in deleted_resources:
                    self._state.drop(resource)
                # FIXME[#8008]: design step 7: drop update_pending
            # FIXME[#8008]: design step 10: Once more, drop all resources that do not exist in this version from the scheduled
            #               work, in case they got added again by a deploy trigger

    # FIXME[#8008]: set up background workers for each agent, calling _run_for_agent(). Make sure to somehow respond to new
    #           agents or removed ones

    def start_for_agent(self, agent: str) -> None:
        """Start processing for the given agent"""
        self._workers[agent] = asyncio.create_task(self._run_for_agent(agent))

    async def _run_for_agent(self, agent: str) -> None:
        """Main loop for one agent"""
        while self._running:
            task: Task = await self._work.agent_queues.queue_get(agent)
            try:
                # FIXME[#8008]: skip and reschedule deploy / refresh-fact task if resource marked as update pending?
                await task.execute(self, agent)
            except Exception:
                LOGGER.exception("Task %s for agent %s has failed and the exception was not properly handled", task, agent)

            self._work.agent_queues.task_done(agent)
