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

# TODO: file name and location

import abc
import dataclasses
import enum
from collections.abc import Mapping, Set
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, TypeAlias

from inmanta.data.model import ResourceIdStr
from inmanta.util.collections import BidirectionalManyToManyMapping


class RequiresProvidesMapping(BidirectionalManyToManyMapping[ResourceIdStr, ResourceIdStr]):
    def get_requires(self, resource: ResourceIdStr) -> Optional[Set[ResourceIdStr]]:
        return self.get_primary(resource)

    def get_provides(self, resource: ResourceIdStr) -> Optional[Set[ResourceIdStr]]:
        return self.get_reverse(resource)

    # TODO: methods for updating requires-provides

    def requires(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self

    def provides(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self.reverse_mapping()


@dataclass(frozen=True)
class ResourceDetails:
    attribute_hash: str
    attributes: Mapping[str, object]
    # TODO: consider adding a read-only view on the requires relation?


class ResourceStatus(StrEnum):
    """
    Status of a resource's operational status with respect to its latest desired state, to the best of our knowledge.

    UP_TO_DATE: Resource has had at least one successful deploy for the latest desired state, and no compliance check has
        reported a diff since. Is not affected by later deploy failures, i.e. the last known operational status is assumed to
        hold until observed otherwise.
    HAS_UPDATE: Resource's operational state does not match latest desired state, as far as we know. Either the resource
        has never been deployed, or was deployed for a different desired state or a compliance check revealed a diff.
    """
    UP_TO_DATE = enum.auto()
    HAS_UPDATE = enum.auto()
    # TODO: undefined / orphan? Otherwise a simple boolean `has_update` or `dirty` might suffice


class DeploymentResult(StrEnum):
    """
    The result of a resource's last (finished) deploy. This result may be for an older version than the latest desired state.
    See ResourceStatus for a resource's operational status with respect to its latest desired state.

    NEW: Resource has never been deployed before.
    DEPLOYED: Last resource deployment was successful.
    FAILED: Last resource deployment was unsuccessful.
    """
    NEW = enum.auto()
    DEPLOYED = enum.auto()
    FAILED = enum.auto()
    # TODO: design also has SKIPPED, do we need it now or add it later?


# TODO: where to link here? directly from ModelState or from ResourceDetails? Probably ResourceDetails
@dataclass
class ResourceState:
    # TODO: remove link, replace with documentation
    # based on https://docs.google.com/presentation/d/1F3bFNy2BZtzZgAxQ3Vbvdw7BWI9dq0ty5c3EoLAtUUY/edit#slide=id.g292b508a90d_0_5
    status: ResourceStatus
    deployment_result: DeploymentResult
    # TODO: add other relevant state fields

@dataclass(kw_only=True)
class ModelState:
    # TODO: document (or refactor to make more clear) that resource_state should only be updated under lock, and all other
    #   fields are considered the domain of the scheduler (not the queue executor)
    version: int
    resources: dict[ResourceIdStr, ResourceDetails] = dataclasses.field(default_factory=dict)
    requires: RequiresProvidesMapping = dataclasses.field(default_factory=RequiresProvidesMapping)
    resource_state: dict[ResourceIdStr, ResourceState] = dataclasses.field(default_factory=dict)
    update_pending: set[ResourceIdStr] = dataclasses.field(default_factory=set)
    """
    Resources that have a new desired state (might be simply a change of its dependencies), which are still being processed by
    the resource scheduler. This is a shortlived transient state, used for internal concurrency control. Kept separate from
    ResourceStatus so that it lives outside of the scheduler lock's scope.
    """

    def update_desired_state(
        self,
        resource: ResourceIdStr,
        attributes: ResourceDetails,
    ) -> None:
        # TODO: raise KeyError if already lives in state?
        self.resources[resource] = attributes
        if resource in self.resource_state:
            self.resource_state[resource].status = ResourceStatus.HAS_UPDATE
        else:
            self.resource_state[resource] = ResourceState(status=ResourceStatus.HAS_UPDATE, deployment_result=DeploymentResult.NEW)

    def update_requires(
        self,
        resource: ResourceIdStr,
        requires: Set[ResourceIdStr],
    ) -> None:
        self.requires[resource] = requires


@dataclass(frozen=True, kw_only=True)
class _Task(abc.ABC):
    agent: str
    resource: ResourceIdStr
    priority: int


class Deploy(_Task): pass


@dataclass(frozen=True, kw_only=True)
class DryRun(_Task):
    # TODO: requires more attributes
    pass


class RefreshFact(_Task): pass


Task: TypeAlias = Deploy | DryRun | RefreshFact
"""
Type alias for the union of all task types. Allows exhaustive case matches.
"""

@dataclass
class BlockedDeploy:
    # TODO: docstring: deploy blocked on requires -> blocked_on is subset of requires or None when not yet calculated
    #   + mention that only deploys (never other tasks) are ever blocked
    task: Deploy
    blocked_on: Optional[Set[ResourceIdStr]] = None


@dataclass(frozen=True, order=True, kw_only=True)
class TaskQueueItem:
    priority: int
    task: Task = dataclasses.field(compare=False)
    # TODO: better name. Purpose is to uniquely identify a task item, even if an identical task happens to be added later
    item_id: Task = dataclasses.field(compare=False)


# TODO: style uniformity: dataclass vs normal class
class AgentQueues:
    """
    Per-agent priority queue for ready-to-execute tasks.
    """
    # TODO: relies on undocumented asyncio.PriorityQueue._queue field and the fact that it's a heapq -> refinement ticket

    # TODO: implement queue worker, but where to put it? This class or scheduler? Or separate worker class with self.lock?

    def __init__(self) -> None:
        # TODO: document that queue must not be used directly by class users
        self._agent_queues: dict[str, asyncio.PriorityQueue[TaskQueueItem]] = {}
        self._tasks_by_resource: dict[ResourceIdStr, list[Task]] = {}
        # can not drop tasks from queue without breaking the heap invariant, or potentially breaking asyncio.Queue invariants
        # => take approach suggested in heapq docs: simply mark as deleted
        self._dropped_tasks: set[TaskQueueItem] = set()

    def put_nowait(task: Task, priority: int) -> None:
        # TODO: current implementation is only PoC grade, notable item_id is missing, and dict presence is never checked
        item: TaskQueueItem = TaskQueueItem(priority=priority, task=task, item_id=0)
        self._tasks_by_resource[task.resource].append(task)
        self._agent_queues[agent].put_nowait(item)

    # TODO: current interface and implementation is only PoC grade
    def drop(self, task: Task) -> None:
        self._dropped_tasks.add(task)
        # TODO: also drop from _tasks_by_resource

    def sorted(self, agent: str) -> list[Task]:
        # TODO: remove this method: it's only a PoC to hightlight how to achieve a sorted view
        queue: asyncio.PriorityQueue = self._agent_queues[agent]
        queue._queue.sort()
        return [item.task for item in queue._queue if item not in self._dropped_tasks]

    async def get(self, agent: str) -> Task:
        # TODO: current implementation is only PoC grade
        queue: asyncio.PriorityQueue = self._agent_queues[agent]
        while True:
            item: TaskQueueItem = await queue.get()
            if item in self._dropped_tasks:
                deleted.discard(item)
                continue
            # TODO: drop from _tasks_by_resource
            return item.task


@dataclass
class ScheduledWork:
    # TODO: keep track of in_progress tasks?
    # TODO: make this a data type with bidirectional read+remove access (ResourceIdStr -> list[Task]), so reset_requires can access it
    #       See Wouter's PR for a base?
    agent_queues: dict[str, list[Task]] = dataclasses.field(default_factory=dict)
    waiting: dict[ResourceIdStr, BlockedDeploy] = dataclasses.field(default_factory=dict)

    # TODO: task runner for the agent queues + when done:
    #   - update model state
    #   - follow provides edge to notify waiting tasks and move them to agent_queues

    def delete_resource(self, resource: ResourceIdStr) -> None:
        """
        Drop tasks for a given resource when it's deleted from the model. Does not affect dry-run tasks because they
        do not act on the latest desired state.
        """
        # TODO: delete from agent_queues if in there
        if resource in self.waiting:
            del self.waiting[resource]

    def reset_requires(self, resource: ResourceIdStr) -> None:
        """
        Resets metadata calculated from a resource's requires, i.e. when its requires changes.
        """
        # TODO: need to move out of agent_queues to waiting iff it's in there
        if resource in self.waiting:
            self.waiting[resource].blocked_on = None


# TODO: name
# TODO: expand docstring
class Scheduler:
    """
    Scheduler for resource actions. Reads resource state from the database and accepts deploy, dry-run, ... requests from the
    server. Schedules these requests as tasks according to priorities and, in case of deploy tasks, requires-provides edges.
    """
    def __init__(self) -> None:
        self._state: Optional[ModelState] = None
        self._work: ScheduledWork = ScheduledWork()

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
        self._state = ModelState(version=0)

    @property
    def state(self) -> ModelState:
        if self._state is None:
            # TODO
            raise Exception("Call start first")
        return self._state

    # TODO: name
    # TODO (ticket): design step 2: read new state from DB instead of accepting as parameter (method should be notification only, i.e. 0 parameters)
    async def new_version(
        self,
        version: int,
        resources: Mapping[ResourceIdStr, ResourceDetails],
        requires: Mapping[ResourceIdStr, Set[ResourceIdStr]],
    ) -> None:
        async with self._update_lock.acquire():
            # Inspect new state and mark resources as "update pending" where appropriate. Since this method is the only writer
            # for "update pending", and a stale read is acceptable, we can do this part before acquiring the exclusive scheduler
            # lock.
            # TODO: what to do when an export changes handler code without changing attributes? Consider in deployed state? What
            #   does current implementation do?
            deleted_resources: Set[ResourceIdStr] = self.state.resources.keys() - resources.keys()
            # TODO: drop deleted resources from scheduled work

            # TODO: make sure this part (before scheduler lock is acquired) doesn't block queue until lock is acquired: either
            # run on thread or make sure to regularly pass control to IO loop (preferred)
            new_desired_state: list[ResourceIdStr] = []
            changed_requires: list[ResourceIdStr] = []
            for resource, details in resources.items():
                if resource not in self.state.resources or details.attribute_hash != self.state.resources[resource].attribute_hash:
                    self.state.update_pending.add(resource)
                    new_desired_state.append(resource)
                if requires.get(resource, set()) != self.state.requires.get(resource, set()):
                    self.state.update_pending.add(resource)
                    changed_requires.append(resource)

            #
            async with self._scheduler_lock.acquire():
                self.state.version = version
                for resource in new_desired_state:
                    self.state.update_desired_state(resource, resources[resource])
                for resource in changed_requires:
                    self.state.update_requires(resource, requires[resource])
                    self._work.reset_requires(resource)

                # TODO: design step 6: release scheduler lock
                # TODO: design step 7: drop update_pending
            # TODO: design step 9: call into normal deploy flow's part after the lock (step 4)
            # TODO: design step 10: Once more, drop all resources that do not exist in this version from the scheduled work, in case they got added again by a deploy trigger


# TODO: what needs to be refined before hand-off?
#   - where will this component go to start with?
#
# TODO: opportunities for work hand-off:
# - connection to DB
# - connection to agent
