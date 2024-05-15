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
import bisect
import graphlib
import itertools
import logging
import typing

if typing.TYPE_CHECKING:
    import _typeshed

LOGGER = logging.getLogger(__name__)


class BaseTask(abc.ABC):
    """
    Base class for tasks, has a lifecycle where

    Friend class with TaskQueue (i.e. tightly coupled)

    1. gets added to a queue
    2. the queue calls _enqueue to couple the task to itself
    3. when all requires are resolved, _runnable is called, move self to run queue
    4. when we need to run '_run' is called
    5. _done is called to updated all provides


    """

    def __init__(self) -> None:
        self.cancelled = False
        # Indicates if a cancel is requested
        self.started = False
        self.done = False

        # Link to the parent queue, required to jump into run queue
        self._queue: typing.Optional["TaskQueue"] = None
        # priority / insertion number / self
        self._entry: typing.Optional[typing.Tuple[int, int, "BaseTask"]] = None

        # Inter task dependencies
        self.waitcount = 0
        self.requires: list["BaseTask"] = []
        self.provides: list["BaseTask"] = []

    @abc.abstractmethod
    def name(self) -> str:
        pass

    @abc.abstractmethod
    def priority(self) -> int:
        pass

    @abc.abstractmethod
    async def run(self) -> None:
        pass

    def is_queued(self) -> bool:
        """Are we bound to a queue"""
        return self._queue is not None

    def is_runnable(self) -> bool:
        """Could be be executed"""
        return self.waitcount == 0

    def is_cancelled(self) -> bool:
        """Are we cancelled"""
        return self.cancelled

    def is_running(self) -> bool:
        return self.started and not self.done

    def is_done(self) -> bool:
        return self.done

    def cancel(self) -> None:
        """Will cancel this task IF it is not already done or started"""
        if self.cancelled or self.done or self.started:
            return
        self.cancelled = True
        if self._queue:
            self._queue.full_queue.drop(self._entry)
            if self.waitcount == 0 and not self.started:
                self._queue.run_queue.drop(self._entry)

    def wait_for(self, other: "BaseTask") -> None:
        """
        Declare we wait for some other task

        Adding the same task twice will make this one wait forever!
        """
        if other.done:
            # the other is done, nothing to do
            return
        # double bind the waiter
        self.waitcount += 1
        self.requires.append(other)
        other.provides.append(self)

    def _enqueue(self, into: "TaskQueue", entry: typing.Tuple[int, int, "BaseTask"]) -> None:
        """Internal, bind to queue"""
        assert self._queue is None
        self._queue = into
        self._entry = entry

    def _runnable(self) -> None:
        """Internal, ready to move to run queue"""
        assert self._queue is not None, "Task is not bound to a queue"
        assert self._entry is not None
        self._queue.run_queue.put_nowait(self._entry)
        # no longer needed, prevents memory leaks
        self.requires = []

    async def _run(self) -> None:
        """Internal, run the task, book keeping around run()"""
        # start running if required
        if not (self.done or self.started or self.cancelled):
            self.started = True
            try:
                await self.run()
            finally:
                self._done()

    def _done(self) -> None:
        """Internal, we are done, propagate to waiters, can be called multiple times safely"""
        if self.done:
            return
        self.done = True
        if self._queue:
            self._queue.full_queue.drop(self._entry)
        for awaited in self.provides:
            awaited.waitcount -= 1
            assert not awaited.waitcount < 0
            if awaited.waitcount == 0 and awaited._queue is not None:
                awaited._runnable()


class Task(BaseTask):
    """

    Executable task with name, priority and dependencies

    Concerete Used for testing
    """

    def __init__(self, name: str, priority: int) -> None:
        super().__init__()
        self._name = name
        self._priority = priority

    async def run(self) -> None:
        print(f"Running {self._name}")

    def priority(self) -> int:
        return self._priority

    def name(self) -> str:
        return self._name

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return self._name


T = typing.TypeVar("T", bound="_typeshed.SupportsRichComparison")


class PriorityQueue(asyncio.Queue[T]):
    """
    Completely sorted priority queue

    less efficient than heapq
    """

    _queue: list[T]

    def _init(self, maxsize: int) -> None:
        self._queue = []

    def _put(self, item: T) -> None:
        bisect.insort(self._queue, item)

    def _get(self) -> T:
        return self._queue.pop(0)

    def drop(self, item: T) -> None:
        """Remove this item, raise indexerror if the item is not present"""
        idx = bisect.bisect(self._queue, item) - 1
        assert self._queue[idx] == item
        self._queue.pop(idx)


class TaskQueue:
    """Queue to schedule tasks with inter-dependencies and provide an overview of the queue"""

    def __init__(self) -> None:
        self.full_queue: PriorityQueue[typing.Tuple[int, int, BaseTask]] = PriorityQueue()
        self.run_queue: PriorityQueue[typing.Tuple[int, int, BaseTask]] = PriorityQueue()
        self.counter = itertools.count()  # unique sequence count, makes sort stable in the heap

    def put(self, task: BaseTask) -> None:
        "Add a new task"
        if task.cancelled:
            return
        count = next(self.counter)
        entry = (task.priority(), count, task)
        task._enqueue(self, entry)
        self.full_queue.put_nowait(entry)
        if task.waitcount == 0:
            task._runnable()

    async def get(self) -> BaseTask:
        """Remove and return the lowest priority task. Raise KeyError if empty."""
        priority, count, task = await self.run_queue.get()
        return task

    async def do_next(self) -> BaseTask:
        """run the next task"""
        task = await self.get()
        await task._run()
        return task

    def view(self) -> typing.Sequence[Task]:
        """This leaks a reference to the internal queue: don't touch it"""
        return self.full_queue._queue


class SentinelTask(BaseTask):
    """Task to unblock the queue on shutdown"""

    def name(self) -> str:
        return "Queue Shutdown"

    def priority(self) -> int:
        return 0

    async def run(self) -> None:
        return


class TaskRunner:
    """Logical thread to process work from a task queue

    Can be restarted
    """

    def __init__(self, queue: TaskQueue) -> None:
        self.queue = queue
        self.running = False
        self.should_run = True
        self.finished: typing.Optional[asyncio.Task[None]] = None

    def start(self) -> None:
        self.should_run = True
        self.finished = asyncio.create_task(self.run())

    def stop(self) -> None:
        self.should_run = False
        self.queue.put(SentinelTask())

    async def join(self) -> None:
        assert not self.should_run
        if self.finished:
            await self.finished

    async def run(self) -> None:
        self.running = True
        while self.should_run:
            task = await self.queue.get()
            try:
                await task._run()
            except Exception:
                LOGGER.exception(f"Unexpected exception while executing task {task.name()}")
        self.running = False


class TaskGroup:
    """Utility for managing groups of tasks with the same priority"""

    def __init__(self, tasks: list[BaseTask]):
        self.tasks = tasks

    def finished(self) -> bool:
        return all((task.done or task.cancelled) for task in self.tasks)

    def cancel(self) -> None:
        for task in self.tasks:
            task.cancel()

    def enqueue_all(self, queue: TaskQueue) -> None:
        # pre order tasks to get a reasonably good order
        # purely esthetic
        task_set = set(self.tasks)
        toposorter: graphlib.TopologicalSorter[BaseTask] = graphlib.TopologicalSorter()
        for task in self.tasks:
            toposorter.add(task, *(pre for pre in task.requires if pre in task_set))
        for task in toposorter.static_order():
            queue.put(task)
