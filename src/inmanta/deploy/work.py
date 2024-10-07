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
import functools
import itertools
from collections.abc import Iterator, Mapping, Set
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Generic, Optional, TypeVar

from inmanta.data.model import ResourceIdStr
from inmanta.deploy import tasks

"""
Type alias for the union of all task types. Allows exhaustive case matches.
"""


T = TypeVar("T", bound=tasks.Task, covariant=True)


class TaskPriority(IntEnum):
    # These priorities can be freely updated, we only care about the relative order
    TERMINATED = -1
    USER_DEPLOY = 0
    NEW_VERSION_DEPLOY = 1
    USER_REPAIR = 2
    DRYRUN = 3
    INTERVAL_DEPLOY = 4
    FACT_REFRESH = 5
    INTERVAL_REPAIR = 6


@dataclass(frozen=True, kw_only=True)
class PrioritizedTask(Generic[T]):
    """
    Resource action task with a priority attached. Lower values represent a higher priority. Negative priorities are reserved
    for internal use.

    This is a stateless representation of a task with a priority attached, unlike TaskQueueItem, which is a stateful element
    in the task queue.
    """

    task: T
    priority: TaskPriority


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

    task: PrioritizedTask[tasks.Task]
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


class AgentQueues(Mapping[tasks.Task, PrioritizedTask[tasks.Task]]):
    """
    Per-agent priority queue for ready-to-execute tasks. Clients must not interact with the underlying priority queues directly,
    only through the queue manipulation methods offered by this class.

    Each Task will be queued at most once. If an identical Task is queued later on, it will not be queued separately. It may
    however affect the current task's priority, causing it to be executed earlier than it would have otherwise.
    """

    # FIXME[#8019]: relies on undocumented asyncio.PriorityQueue._queue field and the fact that it's a heapq,
    #               can we do something about that?

    def __init__(self, new_agent_notify: Callable[[str], None]) -> None:
        """
        :param new_agent_notify: method to notify consumer about a new agent, called with agent name as argument.
        """
        self._agent_queues: dict[str, asyncio.PriorityQueue[TaskQueueItem]] = {}
        # can not drop tasks from queue without breaking the heap invariant, or potentially breaking asyncio.Queue invariants
        # => take approach suggested in heapq docs: simply mark as deleted.
        # => Keep view on all active tasks for a given resource, which also doubles as lookup for client operations
        # Only tasks in this collection are considered queued, as far as this class' client interface is concerned.
        self._tasks_by_resource: dict[ResourceIdStr, dict[tasks.Task, TaskQueueItem]] = {}
        # monotonically rising value for item insert order
        # use simple counter rather than time.monotonic_ns() for performance reasons
        self._entry_count: int = 0
        self._new_agent_notify: Callable[[str], None] = new_agent_notify
        self._in_progress: set[tasks.Task] = set()

    @property
    def in_progress(self) -> Set[tasks.Task]:
        return self._in_progress

    def reset(self) -> None:
        self._agent_queues.clear()
        self._tasks_by_resource.clear()
        self._entry_count = 0

    def _get_queue(self, agent_name: str) -> asyncio.PriorityQueue[TaskQueueItem]:
        """
        Return the queue for an agent, creating it if it does not exist.

        For internal use only. Queues must not be exposed to end user.
        """
        # All we do is sync and on the io loop, no need for locks!
        out = self._agent_queues.get(agent_name, None)
        if out is not None:
            return out
        out = asyncio.PriorityQueue()
        self._agent_queues[agent_name] = out
        self._new_agent_notify(agent_name)
        return out

    def get_tasks_for_resource(self, resource: ResourceIdStr) -> set[tasks.Task]:
        """
        Returns all queued tasks for a given resource id.
        """
        return set(self._tasks_by_resource.get(resource, {}).keys())

    def remove(self, task: tasks.Task) -> TaskPriority:
        """
        Removes the given task from its associated agent queue. Raises KeyError if it is not in the queue.
        Returns the priority at which the deleted task was queued.
        """
        the_tasks: dict[tasks.Task, TaskQueueItem] = self._tasks_by_resource.get(task.resource, {})
        queue_item: TaskQueueItem = the_tasks[task]
        queue_item.deleted = True
        del the_tasks[task]
        if not the_tasks:
            del self._tasks_by_resource[task.resource]
        return queue_item.task.priority

    def discard(self, task: tasks.Task) -> Optional[TaskPriority]:
        """
        Removes the given task from its associated agent queue if it is present.
        Returns the priority at which the deleted task was queued, if it was at all.
        """
        try:
            return self.remove(task)
        except KeyError:
            return None

    def _queue_item_for_task(self, task: tasks.Task) -> Optional[TaskQueueItem]:
        return self._tasks_by_resource.get(task.resource, {}).get(task, None)

    def sorted(self, agent: str) -> list[PrioritizedTask[tasks.Task]]:
        # FIXME: remove this method: it's only a PoC to hightlight how to achieve a sorted view
        queue: asyncio.PriorityQueue[TaskQueueItem] = self._agent_queues[agent]
        backing_heapq: list[TaskQueueItem] = queue._queue  # type: ignore [attr-defined]
        backing_heapq.sort()
        return [item.task for item in backing_heapq if not item.deleted]

    ########################################
    # asyncio.PriorityQueue-like interface #
    ########################################

    def queue_put_nowait(self, prioritized_task: PrioritizedTask[tasks.Task]) -> None:
        """
        Add a new task to the associated agent's queue.
        """
        task: tasks.Task = prioritized_task.task
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
        self._get_queue(task.id.agent_name).put_nowait(item)

    def send_shutdown(self) -> None:
        """
        Wake up all workers after shutdown is signalled
        """
        poison_pill = TaskQueueItem(
            task=PrioritizedTask(
                task=tasks.PoisonPill(resource=ResourceIdStr("system::Terminate[all,stop=True]")),
                priority=TaskPriority.TERMINATED,
            ),
            insert_order=0,
        )
        for queue in self._agent_queues.values():
            queue.put_nowait(poison_pill)

    async def queue_get(self, agent: str) -> tasks.Task:
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
            self._in_progress.add(item.task.task)
            return item.task.task

    def task_done(self, agent: str, task: tasks.Task) -> None:
        """
        Indicate that a formerly enqueued task for a given agent is complete.

        Used by queue consumers. For each get() used to fetch a task, a subsequent call to task_done() tells the corresponding
        agent queue that the processing on the task is complete.
        """
        self._in_progress.remove(task)
        self._agent_queues[agent].task_done()

    #########################
    # Mapping implementation#
    #########################

    def __getitem__(self, key: tasks.Task) -> PrioritizedTask[tasks.Task]:
        return self._tasks_by_resource.get(key.resource, {})[key].task

    def __iter__(self) -> Iterator[tasks.Task]:
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

    Expects to be informed by the scheduler of deploy requests and/or state changes through add() and
    delete_resource().

    Expects to be informed by scheduler of finished tasks through finished_deploy().

    :param requires: Live, read-only view on requires mapping for the latest model state.
    :param provides: Live, read-only view on provides mapping for the latest model state.
    :param new_agent_notify: Method to notify client of newly created agent queues. When notified about a queue, client is
        expected to start consuming its tasks.
    """

    def __init__(
        self,
        requires: Mapping[ResourceIdStr, Set[ResourceIdStr]],
        provides: Mapping[ResourceIdStr, Set[ResourceIdStr]],
        new_agent_notify: Callable[[str], None],
    ) -> None:
        self.requires: Mapping[ResourceIdStr, Set[ResourceIdStr]] = requires
        self.provides: Mapping[ResourceIdStr, Set[ResourceIdStr]] = provides
        self.agent_queues: AgentQueues = AgentQueues(new_agent_notify)
        self._waiting: dict[ResourceIdStr, BlockedDeploy] = {}

    def reset(self) -> None:
        self.agent_queues.reset()
        self._waiting.clear()

    def deploy_with_context(
        self,
        resources: Set[ResourceIdStr],
        *,
        # TODO: update docstring + consider in_progress_deploys for name?
        priority: TaskPriority,
        deploying: Optional[Set[ResourceIdStr]] = None,
        added_requires: Optional[Mapping[ResourceIdStr, Set[ResourceIdStr]]] = None,
        dropped_requires: Optional[Mapping[ResourceIdStr, Set[ResourceIdStr]]] = None,
    ) -> None:
        """
        Add deploy tasks for the given resources. Additionally update the scheduled work state to reflect the new model state
        and scheduler intent. May defer tasks that were previously considered ready to execute if any of their dependencies are
        added to the scheduled work or if new dependencies are added.

        :param resources: Set of resources that should be deployed. Adds a deploy task to the scheduled work for each
            of these, unless it is already scheduled.
        :param priority: The priority of this deploy.
        :param stale_deploys: Set of resources for which a stale deploy is in progress, i.e. a deploy for an outdated resource
            intent.
        :param added_requires: Requires edges that were added since the previous state update, if any.
        :param dropped_requires: Requires edges that were removed since the previous state update, if any.
        """
        deploying = deploying if deploying is not None else set()
        added_requires = added_requires if added_requires is not None else {}
        dropped_requires = dropped_requires if dropped_requires is not None else {}

        # set of resources for which the blocked_on field was updated without checking whether it has become unblocked
        maybe_runnable: set[ResourceIdStr] = set()

        # lookup caches for visited nodes
        queued: set[ResourceIdStr] = set(deploying)  # queued or running, pre-populate with in-progress deploys
        not_scheduled: set[ResourceIdStr] = set()

        # First drop all dropped requires so that we work on the smallest possible set for this operation.
        for resource, dropped in dropped_requires.items():
            if not dropped:
                # empty set, nothing to do
                continue
            if resource not in self._waiting:
                # this resource is not currently waiting for anything => nothing to do
                continue
            self._waiting[resource].blocked_on.difference_update(dropped)
            maybe_runnable.add(resource)

        def is_scheduled(resource: ResourceIdStr) -> bool:
            """
            Returns whether the resource is currently scheduled, caching the results.
            """
            # start with cheap checks: check waiting and cached sets
            if resource in self._waiting or resource in queued:
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

        def extend_blocked_on(resource: ResourceIdStr, new_blockers: set[ResourceIdStr]) -> None:
            """
            Add to the blocked on set for this resource, deferring the associated deploy task if it is already queued.
            This method takes ownership of the new_blockers set, the caller should not use it again.

            :param resource: The resource for which to add blockers.
            :param new_blockers: The resources to add as blockers. This must be a subset of the resources's scheduled requires,
                i.e. requires that are currently queued or waiting. The method takes ownership of this object.
            """
            if not new_blockers:
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
                task_priority: Optional[TaskPriority] = self.agent_queues.discard(task)
                queued.remove(resource)
                self._waiting[resource] = BlockedDeploy(
                    task=PrioritizedTask(
                        task=task,
                        priority=task_priority if task_priority is not None and task_priority <= priority else priority,
                    ),
                    # task was previously ready to execute => assume no other blockers than this one
                    blocked_on=new_blockers,
                )
            else:
                self._waiting[resource].blocked_on.update(new_blockers)
                maybe_runnable.discard(resource)

        # ensure desired resource deploys are scheduled
        for resource in resources:
            prioritized_task = PrioritizedTask(task=tasks.Deploy(resource=resource), priority=priority)
            if is_scheduled(resource):
                # Deploy is already scheduled / running. Check to see if this task has a higher priority than the one already
                # scheduled. If it has, update the priority. If any of its dependencies are to be
                # scheduled as well, they will follow the provides relation to ensure this deploy waits its turn.
                if prioritized_task.task in self.agent_queues:
                    # simply add it again, the queue will make sure only the highest priority is kept
                    self.agent_queues.queue_put_nowait(prioritized_task)
                if resource in self._waiting:
                    if self._waiting[resource].task.priority > priority:
                        self._waiting[resource].task = prioritized_task
                continue
            # task is not yet scheduled, schedule it now
            blocked_on: set[ResourceIdStr] = {
                dependency for dependency in self.requires.get(resource, ()) if is_scheduled(dependency)
            }
            self._waiting[resource] = BlockedDeploy(
                task=prioritized_task,
                blocked_on=blocked_on,
            )
            not_scheduled.discard(resource)
            if not blocked_on:
                # not currently blocked on anything but new dependencies may still be scheduled => mark for later check
                maybe_runnable.add(resource)

            # inform along provides relation that this task has been scheduled, deferring already scheduled provides
            for dependant in self.provides.get(resource, ()):
                extend_blocked_on(dependant, {resource})

        # update state for added requires
        for resource, new in added_requires.items():
            extend_blocked_on(resource, {r for r in new if is_scheduled(r)})

        # finally check if any tasks have become ready to run
        for resource in maybe_runnable:
            blocked: BlockedDeploy = self._waiting[resource]
            self._queue_if_ready(blocked)
            # no more need to update cache entries

    def _queue_if_ready(self, blocked_deploy: BlockedDeploy) -> None:
        """
        Check if the given deploy has become unblocked and move to the agent queues if it has.
        """
        if blocked_deploy.blocked_on:
            # still waiting for something, nothing to do
            return
        # ready to execute, move to agent queue
        self.agent_queues.queue_put_nowait(blocked_deploy.task)
        del self._waiting[blocked_deploy.task.task.resource]

    def delete_resource(self, resource: ResourceIdStr) -> None:
        """
        Drop tasks for a given resource when it's deleted from the model. Does not affect dry-run tasks because they
        do not act on the latest desired state.
        """
        # delete from waiting collection if deploy task is waiting to be queued
        if resource in self._waiting:
            del self._waiting[resource]
        # additionally delete from agent_queues if a task is already queued
        task: tasks.Task
        for task in self.agent_queues.get_tasks_for_resource(resource):
            if task.delete_with_resource():
                self.agent_queues.discard(task)

    def finished_deploy(self, resource: ResourceIdStr) -> None:
        """
        Report that a resource has finished deploying for its current desired state, regardless of the deploy result (success /
        failure). Stale deploys must never be reported.
        """
        if resource in self._waiting or tasks.Deploy(resource=resource) in self.agent_queues:
            # a new deploy task was scheduled in the meantime, no need to do anything else
            return
        for dependant in self.provides.get(resource, []):
            blocked_deploy: Optional[BlockedDeploy] = self._waiting.get(dependant, None)
            if blocked_deploy is None:
                # dependant is not currently scheduled
                continue
            # remove the finished resource from the blocked on set and check if that unblocks the dependant
            blocked_deploy.blocked_on.discard(resource)
            self._queue_if_ready(blocked_deploy)
