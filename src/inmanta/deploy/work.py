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
import functools
import itertools
from collections.abc import Iterator, Mapping, Set
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

from inmanta.data.model import ResourceIdStr
from inmanta.resources import Id


@dataclass(frozen=True, kw_only=True)
class Task(abc.ABC):
    """
    Resource action task. Represents the execution of a specific resource action for a given resource.
    """

    resource: ResourceIdStr

    @abc.abstractmethod
    async def execute(self, scheduler: "scheduler.ResourceScheduler", agent: str) -> None:
        """the scheduler is considered to be a friend class: access to internal members is expected"""
        pass

    def delete_with_resource(self) -> bool:
        return True


"""
Type alias for the union of all task types. Allows exhaustive case matches.
"""


T = TypeVar("T", bound=Task, covariant=True)


@dataclass(frozen=True, kw_only=True)
class PrioritizedTask(Generic[T]):
    """
    Resource action task with a priority attached. Lower values represent a higher priority.
    """

    # FIXME[#8008]: merge with TaskQueueItem
    task: T
    priority: int


@functools.total_ordering
@dataclass(kw_only=True)
class TaskQueueItem:
    """
    Task item for the task queue. Adds insert order field to each item and implements full ordering based purely on priority
    and insert order (tiebreaker). Do not rely on == for task equality.

    The insert order field is a simple mechanic to maintain insert order for equal-priority tasks, as suggested in the
    heapq (collection type used by the agent queues) docs. The value should be monotonically rising within a queue. Gaps are
    allowed.
    """

    task: PrioritizedTask[Task]
    insert_order: int

    # Mutable state
    deleted: bool = False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TaskQueueItem):
            return NotImplemented
        return (self.task.priority, self.insert_order) == (other.task.priority, other.insert_order)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, TaskQueueItem):
            return NotImplemented
        return (self.task.priority, self.insert_order) < (other.task.priority, other.insert_order)


class AgentQueues(Mapping[Task, PrioritizedTask[Task]]):
    """
    Per-agent priority queue for ready-to-execute tasks. Clients must not interact with the underlying priority queues directly,
    only through the queue manipulation methods offered by this class.

    Each Task will be queued at most once. If an identical Task is queued later on, it will not be queued separately. It may
    however affect the current task's priority, causing it to be executed earlier than it would have otherwise.
    """

    # FIXME[#8019]: relies on undocumented asyncio.PriorityQueue._queue field and the fact that it's a heapq,
    #               can we do something about that?

    def __init__(self, consumer_factory: Callable[[str], None]) -> None:
        """
        :param consumer_factory: the method that will cause the queue to be consumed, called with agent name as argument
        """
        self._agent_queues: dict[str, asyncio.PriorityQueue[TaskQueueItem]] = {}
        # can not drop tasks from queue without breaking the heap invariant, or potentially breaking asyncio.Queue invariants
        # => take approach suggested in heapq docs: simply mark as deleted.
        # => Keep view on all active tasks for a given resource, which also doubles as lookup for client operations
        # Only tasks in this collection are considered queued, as far as this class' client interface is concerned.
        self._tasks_by_resource: dict[ResourceIdStr, dict[Task, TaskQueueItem]] = {}
        # monotonically rising value for item insert order
        # use simple counter rather than time.monotonic_ns() for performance reasons
        self._entry_count: int = 0
        self._consumer_factory = consumer_factory

    def reset(self) -> None:
        self._agent_queues.clear()
        self._tasks_by_resource.clear()
        self._entry_count = 0

    def _get_queue(self, agent_name: str) -> asyncio.PriorityQueue[TaskQueueItem]:
        # All we do is sync and on the io loop, no need for locks!
        out = self._agent_queues.get(agent_name, None)
        if out is not None:
            return out
        out = asyncio.PriorityQueue()
        self._agent_queues[agent_name] = out
        self._consumer_factory(agent_name)
        return out

    def get_tasks_for_resource(self, resource: ResourceIdStr) -> set[Task]:
        """
        Returns all queued tasks for a given resource id.
        """
        return set(self._tasks_by_resource.get(resource, {}).keys())

    def remove(self, task: Task) -> int:
        """
        Removes the given task from its associated agent queue. Raises KeyError if it is not in the queue.
        Returns the priority at which the deleted task was queued.
        """
        tasks: dict[Task, TaskQueueItem] = self._tasks_by_resource.get(task.resource, {})
        queue_item: TaskQueueItem = tasks[task]
        queue_item.deleted = True
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

    def _queue_item_for_task(self, task: Task) -> Optional[TaskQueueItem]:
        return self._tasks_by_resource.get(task.resource, {}).get(task, None)

    def sorted(self, agent: str) -> list[PrioritizedTask[Task]]:
        # FIXME[#8008]: remove this method: it's only a PoC to hightlight how to achieve a sorted view
        queue: asyncio.PriorityQueue[TaskQueueItem] = self._agent_queues[agent]
        backing_heapq: list[TaskQueueItem] = queue._queue  # type: ignore [attr-defined]
        backing_heapq.sort()
        return [item.task for item in backing_heapq if not item.deleted]

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
            # task is already queued with equal or higher priority
            return
        # reschedule with new priority, no need to explicitly remove, this is achieved by setting self._tasks_by_resource
        if already_queued is not None:
            already_queued.deleted = True
        item: TaskQueueItem = TaskQueueItem(task=prioritized_task, insert_order=self._entry_count)
        self._entry_count += 1
        if task.resource not in self._tasks_by_resource:
            self._tasks_by_resource[task.resource] = {}
        self._tasks_by_resource[task.resource][task] = item
        # FIXME[#8008]: parse agent, may need to be optimized
        agent_name = Id.parse_id(task.resource).agent_name
        self._get_queue(agent_name).put_nowait(item)

    def send_shutdown(self) -> None:
        """Wake up all wrokers after shutdown is signalled"""
        poison_pill = TaskQueueItem(
            task=PrioritizedTask(task=tasks.PoisonPill(resource=ResourceIdStr("system::Terminate[all,stop=True]")), priority=0),
            insert_order=self._entry_count,
        )
        self._entry_count += 1
        for queue in self._agent_queues.values():
            queue.put_nowait(poison_pill)

    async def queue_get(self, agent: str) -> Task:
        """
        Consume a task from an agent's queue. If the queue is empty, blocks until a task becomes available.
        """
        queue: asyncio.PriorityQueue[TaskQueueItem] = self._agent_queues[agent]
        while True:
            item: TaskQueueItem = await queue.get()
            if item.deleted:
                # task was marked as removed, ignore it and consume the next item from the queue
                queue.task_done()
                continue
            # remove from the queue since it's been picked up
            self.discard(item.task.task)
            return item.task.task

    def task_done(self, agent: str) -> None:
        """
        Indicate that a formerly enqueued task for a given agent is complete.

        Used by queue consumers. For each get() used to fetch a task, a subsequent call to task_done() tells the corresponding
        agent queue that the processing on the task is complete.
        """
        self._agent_queues[agent].task_done()

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
    """
    Deploy task that is blocked on one or more of its dependencies (subset of its requires relation).
    """

    task: PrioritizedTask["tasks.Deploy"]
    blocked_on: set[ResourceIdStr]


class ScheduledWork:
    """
    Collection of deploy tasks that should be executed. Manages a priority queue of ready-to-execute tasks per agent
    (AgentQueues), as well as an unordered collection of waiting deploy tasks (across agents). Maintains the following
    invariants in between method calls:
    - Each task exists at most once in the scheduled work. It is however possible for an identical task to be executing.
    - A resource's requires relation is enforced within the set of scheduled work, i.e. for any two deploy tasks in the
        scheduled work, they will be processed in requires order. Only direct requires are considered. It is the responsibility
        of the scheduler to include in-between resources as scheduled work if/when transitive requires ordering is desired.

    Expects to be informed by the scheduler of deploy requests and/or state changes through update_state() and
    delete_resource().

    Expects to be informed by task runners of finished tasks through notify_provides().

    :param requires: Live, read-only view on requires-provides mapping for the latest model state.
    :param consumer_factory: Method to call to start draining the queue when created
    """

    def __init__(
        self,
        requires: Mapping[ResourceIdStr, Set[ResourceIdStr]],
        provides: Mapping[ResourceIdStr, Set[ResourceIdStr]],
        consumer_factory: Callable[[str], None],
    ) -> None:
        self.requires: Mapping[ResourceIdStr, Set[ResourceIdStr]] = requires
        self.provides: Mapping[ResourceIdStr, Set[ResourceIdStr]] = provides
        self.agent_queues: AgentQueues = AgentQueues(consumer_factory)
        self.waiting: dict[ResourceIdStr, BlockedDeploy] = {}

    def reset(self) -> None:
        self.agent_queues.reset()
        self.waiting.clear()

    # FIXME[#8008]: name
    def update_state(
        self,
        *,
        ensure_scheduled: Set[ResourceIdStr],
        running_deploys: Set[ResourceIdStr],
        added_requires: Optional[Mapping[ResourceIdStr, Set[ResourceIdStr]]] = None,
        dropped_requires: Optional[Mapping[ResourceIdStr, Set[ResourceIdStr]]] = None,
    ) -> None:
        """
        Update the scheduled work state to reflect the new model state and scheduler intent. May defer tasks that were
        previously considered ready to execute if any of their dependencies are added to the scheduled work.

        :param ensure_scheduled: Set of resources that should be deployed. Adds a deploy task to the scheduled work for each
            of these, unless it is already scheduled.
        :param running_deploys: Set of resources for which a deploy is currently running, for the latest desired state, i.e.
            stale deploys should be excluded.
        """
        added_requires = added_requires if added_requires is not None else {}
        dropped_requires = dropped_requires if dropped_requires is not None else {}

        # set of resources for which the blocked_on field was updated without checking whether it has become unblocked
        maybe_runnable: set[ResourceIdStr] = set()

        # lookup caches for visited nodes
        queued: set[ResourceIdStr] = set(running_deploys)  # queued or running
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
            task: tasks.Deploy = tasks.Deploy(resource=resource)
            if task in self.agent_queues:
                # populate cache
                queued.add(resource)
                return True
            # populate cache
            not_scheduled.add(resource)
            return False

        def extend_requires(resource: ResourceIdStr, added_requires: set[ResourceIdStr]) -> None:
            # FIXME[#8008]: docstring: added_requires should only contain scheduled subset of requires relation
            #   + takes ownership of set
            if not added_requires:
                # empty set, nothing to do
                return
            if not is_scheduled(resource):
                # resource is not scheduled => nothing to do
                return
            if resource in queued:
                # we're adding a dependency so it's definitely not ready to execute anymore
                # move from agent queue to waiting
                #
                # discard rather than remove because task may already be running, in which case we leave it run its course
                # and simply add a new one
                task: tasks.Deploy = tasks.Deploy(resource=resource)
                priority: Optional[int] = self.agent_queues.discard(task)
                queued.remove(resource)
                self.waiting[resource] = BlockedDeploy(
                    # FIXME[#8015]: default priority
                    task=PrioritizedTask(task=task, priority=priority if priority is not None else 0),
                    # task was previously ready to execute => assume no other blockers than this one
                    blocked_on=added_requires,
                )
            else:
                self.waiting[resource].blocked_on.update(added_requires)
                maybe_runnable.discard(resource)

        # ensure desired resource deploys are scheduled
        for resource in ensure_scheduled:
            if is_scheduled(resource):
                # Deploy is already scheduled / running. No need to do anything here. If any of its dependencies are to be
                # scheduled as well, they will follow the provides relation to ensure this deploy waits its turn.
                continue
            # task is not yet scheduled, schedule it now
            blocked_on: set[ResourceIdStr] = {
                dependency for dependency in self.requires.get(resource, ()) if is_scheduled(dependency)
            }
            self.waiting[resource] = BlockedDeploy(
                # FIXME[#8015]: priority
                task=PrioritizedTask(task=tasks.Deploy(resource=resource), priority=0),
                blocked_on=blocked_on,
            )
            not_scheduled.discard(resource)
            if not blocked_on:
                # not currently blocked on anything but new dependencies may still be scheduled => mark for later check
                maybe_runnable.add(resource)

            # inform along provides relation that this task has been scheduled, deferring already scheduled provides
            for dependant in self.provides.get(resource, ()):
                extend_requires(dependant, {resource})

        # update state for added requires
        for resource, new in added_requires.items():
            extend_requires(resource, {r for r in new if is_scheduled(r)})

        # finally check if any tasks have become ready to run
        for resource in maybe_runnable:
            blocked: BlockedDeploy = self.waiting[resource]
            self._queue_if_ready(blocked)
            # no more need to update cache entries

    def _queue_if_ready(self, blocked_deploy: BlockedDeploy) -> None:
        # FIXME[#8008]: docstring
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
            if task.delete_with_resource():
                self.agent_queues.discard(task)

    def notify_provides(self, finished_deploy: "tasks.Deploy") -> None:
        # FIXME[#8010]: consider failure scenarios -> check how current agent does it, e.g. skip-for-undefined
        # FIXME[#8008]: docstring + mention under lock + mention only iff not stale
        resource: ResourceIdStr = finished_deploy.resource
        for dependant in self.provides.get(resource, []):
            blocked_deploy: Optional[BlockedDeploy] = self.waiting.get(dependant, None)
            if blocked_deploy is None:
                # dependant is not currently scheduled
                continue
            # remove the finished resource from the blocked on set and check if that unblocks the dependant
            blocked_deploy.blocked_on.discard(resource)
            self._queue_if_ready(blocked_deploy)


# Ugly but prevents import loop
# Pure runtime dependency, so can be here
from inmanta.deploy import scheduler, tasks
