import abc
import asyncio
import bisect
import graphlib
import itertools
import typing


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

    def cancel(self) -> None:
        # todo: this doesn't notify waiters
        self.cancelled = True

    def wait_for(self, other: "Task") -> None:
        """Declare we wait for some other task"""
        if other.done:
            # the other is done, nothing to do
            return
        # double bind the waiter
        self.waitcount += 1
        self.requires.append(other)
        other.provides.append(self)

    def _enqueue(self, into: "TaskQueue", entry: typing.Tuple[int, int, "Task"]) -> None:
        """Internal, bind to queue"""
        assert self._queue is None
        self._queue = into
        self._entry = entry

    def _runnable(self) -> None:
        """Internal, ready to move to run queue"""
        assert self._queue is not None, "Task is not bound to a queue"
        self._queue.run_queue.put_nowait(self._entry)
        # no longer needed, prevents memory leaks
        self.requires = None

    async def _run(self) -> None:
        """Internal, run the task, book keeping around run()"""
        # start running if required
        if not (self.done or self.started or self.cancelled):
            self.started = True
            try:
                await self.run()
            finally:
                self.done = True
                self._done()

    def _done(self) -> None:
        """Internal, we are done, propagate to waiters"""
        for awaited in self.provides:
            awaited.waitcount -= 1
            assert not awaited.waitcount < 0
            if awaited.waitcount == 0:
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

    def __str__(self):
        return self._name

    def __repr__(self):
        return self._name


class PriorityQueue(asyncio.Queue):
    """
    Completely sorted priority queue

    less efficient than heapq
    """

    def _init(self, maxsize):
        self._queue = []

    def _put(self, item):
        bisect.insort(self._queue, item)

    def _get(self):
        return self._queue.pop(0)


class TaskQueue:

    def __init__(self) -> None:
        self.full_queue: asyncio.Queue[typing.Tuple[int, int, BaseTask]] = PriorityQueue()
        self.run_queue: asyncio.Queue[typing.Tuple[int, int, BaseTask]] = PriorityQueue()
        self.counter = itertools.count()  # unique sequence count, makes sort stable in the heap

    def put(self, task: BaseTask):
        "Add a new task"
        count = next(self.counter)
        entry = (task.priority(), count, task)
        task._enqueue(self, entry)
        self.full_queue.put_nowait(entry)
        if task.waitcount == 0:
            task._runnable()

    async def get(self) -> BaseTask:
        """Remove and return the lowest priority task. Raise KeyError if empty."""
        while True:
            priority, count, task = await self.run_queue.get()
            if not task.cancelled:
                return task

    async def do_next(self) -> BaseTask:
        """run the next task"""
        task = await self.get()
        # TODO: handle exceptions to prevent breaking the loop
        await task._run()
        return task


class SentinelTask(BaseTask):
    """Task to unblock the queue on shutdown"""

    def name(self) -> str:
        return "Queue Shutdown"

    def priority(self) -> int:
        return 0

    async def run(self) -> None:
        return


class TaskRunner:

    def __init__(self, queue: TaskQueue) -> None:
        self.queue = queue
        self.running = False
        self.should_run = True
        self.finished: typing.Optional[typing.Awaitable] = None

    def start(self):
        self.finished = asyncio.create_task(self.run())

    def stop(self) -> None:
        self.should_run = False
        self.queue.put(SentinelTask())

    async def join(self):
        await self.finished

    async def run(self):
        self.running = True
        while self.should_run:
            await self.queue.do_next()
        self.running = False


T = typing.TypeVar("T", bound=BaseTask)


class TaskGroup(typing.Generic[T]):
    """Utility for managing groups of tasks with the same priority"""

    def __init__(self, tasks: list[T]):
        self.tasks = tasks

    def finished(self) -> bool:
        return all(task.done for task in self.tasks)

    def cancel(self) -> None:
        for task in self.tasks:
            task.cancel()

    def enqueue_all(self, queue: TaskQueue) -> None:
        # pre order tasks to get a reasonably good order
        # purely esthetic
        task_set = set(self.tasks)
        toposorter = graphlib.TopologicalSorter()
        for task in self.tasks:
            toposorter.add(task, *(pre for pre in task.requires if pre in task_set))
        for task in toposorter.static_order():
            queue.put(task)
