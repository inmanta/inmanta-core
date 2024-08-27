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
from collections.abc import Mapping, Set
from typing import Optional

from inmanta.data.model import ResourceIdStr
from inmanta.deploy import work
from inmanta.deploy.state import ModelState, ResourceDetails, ResourceStatus


# TODO: polish for first PR
# - finalize scheduler-agent interface -> Task objects + _run_for_agent
# - mypy


# FIXME[#8008] review code structure + functionality + add docstrings


class ResourceScheduler:
    """
    Scheduler for resource actions. Reads resource state from the database and accepts deploy, dry-run, ... requests from the
    server. Schedules these requests as tasks according to priorities and, in case of deploy tasks, requires-provides edges.

    The scheduler expects to be notified by the server whenever a new version is released.
    """
    def __init__(self) -> None:
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

    async def start(self) -> None:
        # FIXME[#8009]: read from DB instead
        pass

    async def deploy(self) -> None:
        async with self._scheduler_lock:
            # FIXME[#8008]: more efficient access to dirty set by caching it on the ModelState
            dirty: Set[ResourceIdStr] = {
                r for r, details in self._state.resource_state.items() if details.status == ResourceStatus.HAS_UPDATE
            }
            # FIXME[#8008]: pass in running deploys
            self._work.update_state(ensure_scheduled=dirty, running_deploys={})

    async def repair(self) -> None:
        # FIXME[#8008]: implement repair
        pass

    # FIXME[#8009]: design step 2: read new state from DB instead of accepting as parameter (method should be notification only, i.e. 0 parameters)
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
            # FIXME[#8008]: what to do when an export changes handler code without changing attributes? Consider in deployed state? What
            #   does current implementation do?
            deleted_resources: Set[ResourceIdStr] = self._state.resources.keys() - resources.keys()
            for resource in deleted_resources:
                self._work.delete_resource(resource)

            new_desired_state: list[ResourceIdStr] = []
            added_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            dropped_requires: dict[ResourceIdStr, Set[ResourceIdStr]] = {}
            for resource, details in resources.items():
                if resource not in self._state.resources or details.attribute_hash != self._state.resources[resource].attribute_hash:
                    self._state.update_pending.add(resource)
                    new_desired_state.append(resource)
                old_requires: Set[ResourceIdStr] = requires.get(resource, set())
                new_requires: Set[ResourceIdStr] = self._state.requires.get(resource, set())
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
                    self._state.update_desired_state(resource, resources[resource])
                for resource in added_requires.keys() | dropped_requires.keys():
                    self._state.update_requires(resource, requires[resource])
                # ensure deploy for ALL dirty resources, not just the new ones
                # FIXME[#8008]: this is copy-pasted, make into a method?
                dirty: Set[ResourceIdStr] = {
                    r for r, details in self._state.resource_state.items() if details.status == ResourceStatus.HAS_UPDATE
                }
                self._work.update_state(
                    ensure_scheduled=dirty,
                    # FIXME[#8008]: pass in running deploys
                    running_deploys={},
                    added_requires=added_requires,
                    dropped_requires=dropped_requires,
                )
                # FIXME[#8008]: design step 7: drop update_pending
            # FIXME[#8008]: design step 10: Once more, drop all resources that do not exist in this version from the scheduled work, in case they got added again by a deploy trigger

    # FIXME[#8008]: set up background workers for each agent, calling _run_for_agent(). Make sure to somehow respond to new
    #           agents or removed ones

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

            # FIXME[#8010]: send task to agent process (not under lock) (separate method?)

            match task:
                case work.Deploy():
                    async with self._scheduler_lock:
                        # refresh resource details for latest model state
                        new_details: Optional[ResourceDetails] = self._state.resources.get(task.resource, None)
                        if new_details is not None and new_details.attribute_hash == resource_details.attribute_hash:
                            # FIXME[#8010]: pass success/failure to notify_provides()
                            # FIXME[#8008]: iff deploy was successful set resource status and deployment result in self.state.resources
                            self._work.notify_provides(task)
                        # The deploy that finished has become stale (state has changed since the deploy started).
                        # Nothing to report on a stale deploy.
                        # A new deploy for the current model state will have been queued already.
                case _:
                    # nothing to do
                    pass
            self._work.agent_queues.task_done(agent)
