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
from collections.abc import Set
from typing import Any, Mapping, Optional

from inmanta import data, resources
from inmanta.data import Resource
from inmanta.data.model import ResourceIdStr
from inmanta.deploy import work
from inmanta.deploy.state import ModelState, ResourceDetails, ResourceStatus

LOGGER = logging.getLogger(__name__)


# FIXME[#8008] review code structure + functionality + add docstrings
# FIXME[#8008] add import entry point test case


class ResourceScheduler:
    """
    Scheduler for resource actions. Reads resource state from the database and accepts deploy, dry-run, ... requests from the
    server. Schedules these requests as tasks according to priorities and, in case of deploy tasks, requires-provides edges.

    The scheduler expects to be notified by the server whenever a new version is released.
    """

    def __init__(self, environment: uuid.UUID) -> None:
        """
        :param environment: the environment we work for
        """
        self._state: ModelState = ModelState(version=0)
        self._work: work.ScheduledWork = work.ScheduledWork(
            requires=self._state.requires.requires_view(),
            provides=self._state.requires.provides_view(),
        )

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

    async def start(self) -> None:
        await self.update_state()

    async def update_state(self) -> None:
        resource_mapping, require_mapping = await self.build_resource_mappings_from_db()
        self._state.construct(resource_mapping, require_mapping)

    async def stop(self) -> None:
        pass

    async def deploy(self) -> None:
        async with self._scheduler_lock:
            # FIXME[#8008]: more efficient access to dirty set by caching it on the ModelState
            dirty: Set[ResourceIdStr] = {
                r for r, details in self._state.resource_state.items() if details.status == ResourceStatus.HAS_UPDATE
            }
            # FIXME[#8008]: pass in running deploys
            self._work.update_state(ensure_scheduled=dirty, running_deploys=set())

    async def repair(self) -> None:
        # FIXME[#8008]: implement repair
        pass

    async def dryrun(self, dry_run_id: uuid.UUID, version: int) -> None:
        # FIXME
        pass

    async def get_facts(self, resource: dict[str, Any]) -> None:
        # FIXME, also clean up typing of arguments
        pass

    async def build_resource_mappings_from_db(
        self, version: Optional[int] = None
    ) -> tuple[Mapping[ResourceIdStr, ResourceDetails], Mapping[ResourceIdStr, Set[ResourceIdStr]]]:
        """
        Build a view on current resources. Might be filtered for a specific environment, used when a new version is released

        :return: resource_mapping {id -> resource details} and require_mapping {id -> requires}
        """
        resources_from_db: list[Resource]
        if version is None:
            resources_from_db = await data.Resource.get_resources_in_latest_version(environment=self._environment)
        else:
            resources_from_db = await data.Resource.get_resources_for_version(environment=self._environment, version=version)

        resource_mapping = {
            resource.resource_id: ResourceDetails(attribute_hash=resource.attribute_hash, attributes=resource.attributes)
            for resource in resources_from_db
        }
        require_mapping = {
            resource.resource_id: {
                resources.Id.parse_id(req).resource_str() for req in list(resource.attributes.get("requires", []))
            }
            for resource in resources_from_db
        }
        return resource_mapping, require_mapping

    async def new_version(
        self,
    ) -> None:
        await self.update_state()
        environment = await data.Environment.get_by_id(self._environment)
        if environment is None:
            raise ValueError(f"No environment found with this id: `{self._environment}`")
        latest_version = environment.last_version
        resources_from_db, requires_from_db = await self.build_resource_mappings_from_db(version=latest_version - 1)

        async with self._update_lock:
            # Inspect new state and mark resources as "update pending" where appropriate. Since this method is the only writer
            # for "update pending", and a stale read is acceptable, we can do this part before acquiring the exclusive scheduler
            # lock.
            deleted_resources: Set[ResourceIdStr] = self._state.resources.keys() - resources_from_db.keys()
            for resource in deleted_resources:
                self._work.delete_resource(resource)

            new_desired_state: list[ResourceIdStr] = []
            added_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            dropped_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            for resource, details in resources_from_db.items():
                if (
                    resource not in self._state.resources
                    or details.attribute_hash != self._state.resources[resource].attribute_hash
                ):
                    self._state.update_pending.add(resource)
                    new_desired_state.append(resource)
                old_requires: Set[ResourceIdStr] = self._state.requires.get(resource, set())
                new_requires: Set[ResourceIdStr] = requires_from_db.get(resource, set())
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
                self._state.version = latest_version
                for resource in new_desired_state:
                    self._state.update_desired_state(resource, resources_from_db[resource])
                for resource in added_requires.keys() | dropped_requires.keys():
                    self._state.update_requires(resource, requires_from_db[resource])
                # ensure deploy for ALL dirty resources, not just the new ones
                # FIXME[#8008]: this is copy-pasted, make into a method?
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
                # FIXME[#8008]: design step 7: drop update_pending
            # FIXME[#8008]: design step 10: Once more, drop all resources that do not exist in this version from the scheduled
            #               work, in case they got added again by a deploy trigger

    # FIXME[#8008]: set up background workers for each agent, calling _run_for_agent(). Make sure to somehow respond to new
    #           agents or removed ones

    async def _run_task(self, agent: str, task: work.Task, resource_details: ResourceDetails) -> None:
        # FIXME[#8010]: send task to agent process (not under lock)
        pass

    async def _run_for_agent(self, agent: str) -> None:
        # FIXME[#8008]: end condition
        while True:
            task: work.Task = await self._work.agent_queues.queue_get(agent)
            # FIXME[#8008]: skip and reschedule deploy / refresh-fact task if resource marked as update pending?
            resource_details: ResourceDetails
            async with self._scheduler_lock:
                # fetch resource details atomically under lock
                try:
                    resource_details = self._state.resources[task.resource]
                except KeyError:
                    # Stale resource, can simply be dropped.
                    # May occur in rare races between new_version and acquiring the lock we're under here. This race is safe
                    # because of this check, and an intrinsic part of the locking design because it's preferred over wider
                    # locking for performance reasons.
                    continue

            await self._run_task(agent, task, resource_details)

            # post-processing
            match task:
                case work.Deploy():
                    async with self._scheduler_lock:
                        # refresh resource details for latest model state
                        new_details: Optional[ResourceDetails] = self._state.resources.get(task.resource, None)
                        if new_details is not None and new_details.attribute_hash == resource_details.attribute_hash:
                            # FIXME[#8010]: pass success/failure to notify_provides()
                            # FIXME[#8008]: iff deploy was successful set resource status and deployment result
                            #               in self.state.resources
                            self._work.notify_provides(task)
                        # The deploy that finished has become stale (state has changed since the deploy started).
                        # Nothing to report on a stale deploy.
                        # A new deploy for the current model state will have been queued already.
                case _:
                    # nothing to do
                    pass
            self._work.agent_queues.task_done(agent)
