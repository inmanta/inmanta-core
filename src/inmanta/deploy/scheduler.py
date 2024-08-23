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


# TODO: name
# TODO: expand docstring
class Scheduler:
    """
    Scheduler for resource actions. Reads resource state from the database and accepts deploy, dry-run, ... requests from the
    server. Schedules these requests as tasks according to priorities and, in case of deploy tasks, requires-provides edges.
    """
    def __init__(self) -> None:
        self._state: ModelState = ModelState(version=0)
        self._work: work.ScheduledWork = work.ScheduledWork(model_state=self._state)

        # The scheduler continuously processes work in the scheduled work's queues and processes results of executed tasks,
        # which may update both the resource state and the scheduled work (e.g. move unblocked tasks to the queue).
        # TODO: below might not be accurate: will we really use a single worker, or one per agent queue?
        # Since we use a single worker to process the queue, little concurrency control is required there. We only need to lock
        # out state read/write when external events require us update scheduler state from outside this continuous process.
        # To this end we uphold two locks:
        # lock to block scheduler state access during scheduler-wide state updates (e.g. trigger deploy)
        # TODO: does this lock need to allow shared access or can we make the queue worker access it serially without blocking
        #   concurrent tasks (e.g. acqurie only when reading / writing, let go while waiting for agent to do work).
        #   IF SO, document that the lock must only be acquired in very short bursts, except during thses state updates
        self._scheduler_lock: asyncio.Lock = asyncio.Lock()
        # lock to serialize scheduler state updates (i.e. process new version)
        self._update_lock: asyncio.Lock = asyncio.Lock()

    def start(self) -> None:
        # TODO (ticket): read from DB instead
        pass

    async def deploy(self) -> None:
        async with self._scheduler_lock:
            # TODO: more efficient access to dirty set by caching it on the ModelState
            dirty: Set[ResourceIdStr] = {
                r for r, details in self._state.resource_state.items() if details.status == ResourceStatus.HAS_UPDATE
            }
            self._work.update_state(ensure_scheduled=dirty)

    # TODO: name
    # TODO (ticket): design step 2: read new state from DB instead of accepting as parameter (method should be notification only, i.e. 0 parameters)
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
            # TODO: what to do when an export changes handler code without changing attributes? Consider in deployed state? What
            #   does current implementation do?
            deleted_resources: Set[ResourceIdStr] = self._state.resources.keys() - resources.keys()
            for resource in deleted_resources:
                self._work.delete_resource(resource)

            # TODO: make sure this part (before scheduler lock is acquired) doesn't block queue until lock is acquired: either
            # run on thread or make sure to regularly pass control to IO loop (preferred)
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

            async with self._scheduler_lock:
                self._state.version = version
                for resource in new_desired_state:
                    self._state.update_desired_state(resource, resources[resource])
                for resource in added_requires.keys() | dropped_requires.keys():
                    self._state.update_requires(resource, requires[resource])
                # ensure deploy for ALL dirty resources, not just the new ones
                # TODO: this is copy-pasted, make into a method?
                dirty: Set[ResourceIdStr] = {
                    r for r, details in self._state.resource_state.items() if details.status == ResourceStatus.HAS_UPDATE
                }
                self._work.update_state(
                    ensure_scheduled=dirty,
                    new_requires=added_requires,
                    dropped_requires=dropped_requires,
                )
                # TODO: design step 7: drop update_pending
            # TODO: design step 10: Once more, drop all resources that do not exist in this version from the scheduled work, in case they got added again by a deploy trigger

    async def _run_for_agent(self, agent: str) -> None:
        # TODO: end condition
        while True:
            task: work.Task = await self._work.agent_queues.queue_get(agent)
            # TODO: skip and reschedule deploy / refresh-fact task if resource marked as update pending?
            resource_details: ResourceDetails
            async with self._scheduler_lock:
                # fetch resource details atomically under lock
                resource_details = self._state.resources[task.resource]

            # TODO: send task to agent process (not under lock)

            match task:
                case work.Deploy():
                    async with self._scheduler_lock:
                        # refresh resource details for latest model state
                        new_details: Optional[ResourceDetails] = self._state.resources.get(task.resource, None)
                        if new_details is not None and new_details.attribute_hash == resource_details.attribute_hash:
                            # TODO: iff deploy was successful set resource status and deployment result in self.state.resources
                            self._work.notify_provides(task)
                        # The deploy that finished has become stale (state has changed since the deploy started).
                        # Nothing to report on a stale deploy.
                        # A new deploy for the current model state will have been queued already.
                case _:
                    # nothing to do
                    pass
            self._work.agent_queues.task_done(agent)


# TODO: what needs to be refined before hand-off?
#   - where will this component go to start with?
#
# TODO: opportunities for work hand-off:
# - connection to DB
# - connection to agent


# Draft PR:
# - restructure modules
# - open draft PR
# - create refinement tickets
