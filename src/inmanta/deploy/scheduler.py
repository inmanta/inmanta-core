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
import dataclasses
import functools
import itertools
import typing
import uuid
from collections.abc import Iterator, Mapping, Set
from dataclasses import dataclass
from typing import Generic, Optional, TypeAlias, TypeVar

from inmanta.data.model import ResourceIdStr
from inmanta.deploy.state import ModelState, ResourceDetails, ResourceStatus


@dataclass(frozen=True, kw_only=True)
class _Task(abc.ABC):
    agent: str
    resource: ResourceIdStr


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


T = TypeVar("T", bound=Task, covariant=True)


@dataclass(frozen=True, kw_only=True)
class PrioritizedTask(Generic[T]):
    task: T
    # TODO: document lower value is higher priority
    priority: int


@functools.total_ordering
@dataclass(frozen=True, kw_only=True)
class TaskQueueItem:
    """
    Task item for the task queue. Adds unique id to each item and implements full ordering based purely on priority. Do not rely
    on == for task equality.
    """

    task: PrioritizedTask[Task]
    # TODO: Document. Purpose is to uniquely identify a task item, even if an identical task happens to be added later
    item_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TaskQueueItem):
            return NotImplemented
        return self.task.priority == other.task.priority

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, TaskQueueItem):
            return NotImplemented
        return self.task.priority < other.task.priority


# TODO: style uniformity: dataclass vs normal class
class AgentQueues(Mapping[Task, PrioritizedTask[Task]]):
    """
    Per-agent priority queue for ready-to-execute tasks.
    """
    # TODO: relies on undocumented asyncio.PriorityQueue._queue field and the fact that it's a heapq -> refinement ticket

    # TODO: make sure to signal new agents to worker somehow, unless round-robin worker is used

    # TODO: implement queue worker, but where to put it? This class or scheduler? Or separate worker class with self.lock?

    def __init__(self) -> None:
        # TODO: document that queue must not be used directly by class users
        self._agent_queues: dict[str, asyncio.PriorityQueue[TaskQueueItem]] = {}
        # can not drop tasks from queue without breaking the heap invariant, or potentially breaking asyncio.Queue invariants
        # => take approach suggested in heapq docs: simply mark as deleted.
        # => Keep view on all active tasks for a given resource, which also doubles as lookup for client operations
        self._tasks_by_resource: dict[ResourceIdStr, dict[Task, TaskQueueItem]] = {}

    def _queue_item_for_task(self, task: Task) -> Optional[TaskQueueItem]:
        return self._tasks_by_resource.get(task.resource, {}).get(task, None)
        # TODO: document invariant somehwere: each task exists at most once (unless deleted)

    def _is_active(self, item: TaskQueueItem) -> bool:
        """
        Returns true iff this item is still active, i.e. it has not been removed from the queue.
        """
        return item == self._queue_item_for_task(item.task.task)

    ##################
    # User interface #
    ##################

    def get_tasks_for_resource(self, resource: ResourceIdStr) -> set[Task]:
        return set(self._tasks_by_resource.get(resource, {}).keys())

    def remove(self, task: Task) -> int:
        """
        Removes the given task from its associated agent queue. Raises KeyError if it is not in the queue.
        Returns the priority at which the deleted task was queued.
        """
        tasks: dict[Task, TaskQueueItem] = self._tasks_by_resource.get(task.resource, {})
        queue_item: TaskQueueItem = tasks[task]
        del tasks[task]
        if not tasks:
            del self._tasks_by_resource[task.resource]
        return queue_item.task.priority

    def discard(self, task: Task) -> Optional[int]:
        """
        Removes the given task from its associated agent queue if it is present.
        Returns the priority at which the deleted task was queued, if it was at all.
        """
        try:
            return self.remove(task)
        except KeyError:
            return None

    def sorted(self, agent: str) -> list[PrioritizedTask[Task]]:
        # TODO: remove this method: it's only a PoC to hightlight how to achieve a sorted view
        queue: asyncio.PriorityQueue[TaskQueueItem] = self._agent_queues[agent]
        backing_heapq: list[TaskQueueItem] = queue._queue  # type: ignore [attr-defined]
        backing_heapq.sort()
        return [item.task for item in backing_heapq if self._is_active(item)]

    ########################################
    # asyncio.PriorityQueue-like interface #
    ########################################

    def queue_put_nowait(self, prioritized_task: PrioritizedTask[Task]) -> None:
        """
        Add a new task to the associated agent's queue.
        """
        task: Task = prioritized_task.task
        priority: int = prioritized_task.priority
        already_queued: Optional[TaskQueueItem] = self._queue_item_for_task(task)
        if already_queued is not None and already_queued.task.priority <= priority:
            return
        # reschedule with new priority, no need to explicitly remove, this is achieved by setting self._tasks_by_resource
        item: TaskQueueItem = TaskQueueItem(task=prioritized_task)
        if task.resource not in self._tasks_by_resource:
            self._tasks_by_resource[task.resource] = {}
        self._tasks_by_resource[task.resource][task] = item
        self._agent_queues[task.agent].put_nowait(item)

    async def queue_get(self, agent: str) -> Task:
        """
        Consume a task from an agent's queue. If the queue is empty, blocks until a task becomes available.
        """
        queue: asyncio.PriorityQueue[TaskQueueItem] = self._agent_queues[agent]
        while True:
            item: TaskQueueItem = await queue.get()
            if not self._is_active(item):
                # task was marked as removed, ignore it and consume the next item from the queue
                queue.task_done()
                continue
            # remove from the queue since it's been picked up
            # TODO: may need to keep track of running tasks as well, but seperately because a user might want to requeue it while running
            self.discard(item.task.task)
            return item.task.task

    def task_done(self, agent: str) -> None:
        self._agent_queues[agent].task_done()

    # TODO: implement task_done. Requires careful consideration of task lifetime, e.g. an identical Task may be added and consumed before the first calls task_done(), so Task is not a good identity

    #########################
    # Mapping implementation#
    #########################

    def __getitem__(self, key: Task) -> PrioritizedTask[Task]:
        return self._tasks_by_resource.get(key.resource, {})[key].task

    def __iter__(self) -> Iterator[Task]:
        return itertools.chain.from_iterable(self._tasks_by_resource.values())

    def __len__(self) -> int:
        return sum(len(items) for items in self._tasks_by_resource.values())


@dataclass
class BlockedDeploy:
    # TODO: docstring: deploy blocked on requires -> blocked_on is subset of requires or None when not yet calculated
    #   + mention that only deploys (never other tasks) are ever blocked
    task: PrioritizedTask[Deploy]
    blocked_on: set[ResourceIdStr]


class ScheduledWork:
    def __init__(self, model_state: ModelState) -> None:
        # TODO TODO TODO TODO TODO
        # TODO: keep track of in_progress tasks?
        # TODO: mention that this class will never modify state. Or alternatively, pass Scheduler instead and add methods on it to
        #       inspect required state (requires-provides + update_pending?)
        self.model_state: ModelState = model_state
        self.agent_queues: AgentQueues = AgentQueues()
        self.waiting: dict[ResourceIdStr, BlockedDeploy] = {}

    # TODO: docstring + name
    def update_state(
        self,
        *,
        ensure_scheduled: Set[ResourceIdStr],
        new_requires: Optional[Mapping[ResourceIdStr, Set[ResourceIdStr]]] = None,
        dropped_requires: Optional[Mapping[ResourceIdStr, Set[ResourceIdStr]]] = None,
    ) -> None:
        new_requires = new_requires if new_requires is not None else {}
        dropped_requires = dropped_requires if dropped_requires is not None else {}

        # set of resources for which the blocked_on field was updated without checking whether it has become unblocked
        maybe_runnable: set[ResourceIdStr] = set()

        # lookup caches for visited nodes
        queued: dict[ResourceIdStr, Deploy] = {}
        not_scheduled: set[ResourceIdStr] = set()

        # First drop all dropped requires so that we work on the smallest possible set for this operation.
        for resource, dropped in dropped_requires.items():
            if not dropped:
                # empty set, nothing to do
                continue
            if resource not in self.waiting:
                # this resource is not currently waiting for anything => nothing to do
                continue
            self.waiting[resource].blocked_on.difference_update(dropped)
            maybe_runnable.add(resource)

        def is_scheduled(resource: ResourceIdStr) -> bool:
            """
            Returns whether the resource is currently scheduled, caching the results.
            """
            # start with cheap checks: check waiting and cached sets
            if resource in self.waiting or resource in queued:
                # definitely scheduled
                return True
            if resource in not_scheduled:
                # definitely not scheduled
                return False
            # finally, check more expensive agent queue
            # TODO: parse agent
            task: Deploy = Deploy(agent="test", resource=resource)
            # TODO TODO TODO TODO
            # TODO: check if
            #   - DEPLOY currently running and attr hash equals self.model_state.resources[resource].attribute_hash
            if task in self.agent_queues or False:
                # populate cache
                queued[resource] = task
                return True
            # populate cache
            not_scheduled.add(resource)
            return False

        # TODO: rename new_requires -> added_requires for ambiguity reasons
        def extend_requires(resource: ResourceIdStr, new_requires: set[ResourceIdStr]) -> None:
            # TODO: docstring: new_requires should only contain scheduled subset of requires relation
            #   + takes ownership of set
            if not new_requires:
                # empty set, nothing to do
                return
            if not is_scheduled(resource):
                # resource is not scheduled => nothing to do
                return
            if resource in queued:
                # we're adding a dependency so it's definitely not ready to execute anymore
                # move from agent queue to waiting
                task: Deploy = queued[resource]
                # discard rather than remove because task may already be running, in which case we leave it run its course
                # and simply add a new one
                priority: Optional[int] = self.agent_queues.discard(task)
                del queued[resource]
                self.waiting[resource] = BlockedDeploy(
                    # TODO(ticket): default priority
                    task=PrioritizedTask(task=task, priority=priority if priority is not None else 0),
                    # task was previously ready to execute => assume no other blockers than this one
                    blocked_on=new_requires,
                )
            else:
                self.waiting[resource].blocked_on.update(new_requires)
                maybe_runnable.discard(resource)

        # ensure desired resource deploys are scheduled
        for resource in ensure_scheduled:
            if is_scheduled(resource):
                continue
            # task is not yet scheduled, schedule it now
            blocked_on: set[ResourceIdStr] = {
                dependency
                for dependency in self.model_state.requires.get(resource, ())
                if is_scheduled(dependency)
            }
            self.waiting[resource] = BlockedDeploy(
                # TODO(ticket): priority
                # TODO: parse agent
                task=PrioritizedTask(task=Deploy(agent="test", resource=resource), priority=0),
                blocked_on=blocked_on,
            )
            not_scheduled.discard(resource)
            if not blocked_on:
                # not currently blocked on anything but new dependencies may still be scheduled => mark for later check
                maybe_runnable.add(resource)

            # inform along provides relation that this task has been scheduled, deferring already scheduled provides
            for dependant in self.model_state.requires.provides().get(resource, ()):
                extend_requires(dependant, {resource})

        # update state for added requires
        for resource, new in new_requires.items():
            extend_requires(resource, {r for r in new if is_scheduled(r)})

        # finally check if any tasks have become ready to run
        for resource in maybe_runnable:
            blocked: BlockedDeploy = self.waiting[resource]
            self._run_if_ready(blocked)
            # no more need to update cache entries

    def _run_if_ready(self, blocked_deploy: BlockedDeploy) -> None:
        # TODO: docstring
        if blocked_deploy.blocked_on:
            # still waiting for something, nothing to do
            return
        # ready to execute, move to agent queue
        self.agent_queues.queue_put_nowait(blocked_deploy.task)
        del self.waiting[blocked_deploy.task.task.resource]

    def delete_resource(self, resource: ResourceIdStr) -> None:
        """
        Drop tasks for a given resource when it's deleted from the model. Does not affect dry-run tasks because they
        do not act on the latest desired state.
        """
        # delete from waiting collection if deploy task is waiting to be queued
        if resource in self.waiting:
            del self.waiting[resource]
        # additionally delete from agent_queues if a task is already queued
        task: Task
        for task in self.agent_queues.get_tasks_for_resource(resource):
            delete: bool
            match task:
                case Deploy():
                    delete = True
                case DryRun():
                    delete = False
                case RefreshFact():
                    delete = True
                case _ as _never:
                    typing.assert_never(_never)
            if delete:
                self.agent_queues.discard(task)

    def notify_provides(self, finished_deploy: Deploy) -> None:
        # TODO: docstring + mention under lock + mention only iff not stale
        resource: ResourceIdStr = finished_deploy.resource
        for dependant in self.model_state.requires.provides()[resource]:
            blocked_deploy: Optional[BlockedDeploy] = self.waiting.get(dependant, None)
            if blocked_deploy is None:
                # dependant is not currently scheduled
                continue
            # remove the finished resource from the blocked on set and check if that unblocks the dependant
            blocked_deploy.blocked_on.discard(resource)
            self._run_if_ready(blocked_deploy)


# TODO: name
# TODO: expand docstring
class Scheduler:
    """
    Scheduler for resource actions. Reads resource state from the database and accepts deploy, dry-run, ... requests from the
    server. Schedules these requests as tasks according to priorities and, in case of deploy tasks, requires-provides edges.
    """
    def __init__(self) -> None:
        self._state: ModelState = ModelState(version=0)
        self._work: ScheduledWork = ScheduledWork(model_state=self._state)

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
            task: Task = await self._work.agent_queues.queue_get(agent)
            # TODO: skip and reschedule deploy / refresh-fact task if resource marked as update pending?
            resource_details: ResourceDetails
            async with self._scheduler_lock:
                # fetch resource details atomically under lock
                resource_details = self._state.resources[task.resource]

            # TODO: send task to agent process (not under lock)

            match task:
                case Deploy():
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
