import functools
import asyncio
import itertools
import typing


@functools.total_ordering
class Task:

    def __init__(self, name:str) -> None:
        self.name = name
        self.cancelled = False
        # Indicates if a cancel is requested
        self.started = False
        self.done = False
    async def run(self) -> None:
        if not self.done or not self.started or not self.cancelled:
            self.started = True
            print(f"Running {self.name}")
            self.done = True

    def cancel(self):
        self.cancelled = True
    def get_priority(self) -> int:
        return 1

class DependentTask:


class TaskQueue:

    def __init__(self, name: str) -> None:
        # Interestingly, the queue is not ordered per-se
        # https://docs.python.org/3/library/heapq.html#priority-queue-implementation-notes
        self.queue: asyncio.PriorityQueue[typing.Tuple[int, int, Task]] = asyncio.PriorityQueue()
        self.counter = itertools.count()  # unique sequence count, makes sort stable in the heap

    async def put(self, task:Task):
        "Add a new task"
        count = next(self.counter)
        entry = (task.get_priority(), count, task)
        await self.queue.put(entry)

    async def get(self) -> Task:
        "Remove and return the lowest priority task. Raise KeyError if empty."
        while True:
            priority, count, task = await self.queue.get()
            if not task.cancelled:
                return task

    def _tidy(self):
        """Make the queue sorted and free of cancelled tasks"""
        # Should be safe https://docs.python.org/3/library/heapq.html#priority-queue-implementation-notes
        self.queue._queue = sorted(item for item in self.queue._queue if not item.cancelled)

    def get_view(self) -> typing.Sequence[typing.Tuple[int, int, Task]]:
        """
        Get access to the queue's internal task list, sorted and with no cancelled tasks
        """
        return sorted(item for item in self.queue._queue if not item.cancelled)


class Agent:
    """ Agent fed by the scheduler"""

    def __init__(self, name: str) -> None:
        self.name = name
        # Interestingly, the queue is not ordered per-se
        # https://docs.python.org/3/library/heapq.html#priority-queue-implementation-notes
        self.queue = TaskQueue()
        self.running = False
        self.runner: typing.Optional[asyncio.Task[None]]

    async def start(self) -> None:
        self.running = True
        self.runner = asyncio.create_task(self.do_run())

    async def stop(self) -> None:
        self.running = False

    async def do_run(self) -> None:
        " Main loop "
        while self.running:
            task = await self.queue.get()
            await task.run()
    async def join(self) -> None:
        if not self.runner:
            return
        await self.runner
        self.runner = None




class EnvironmentScheduler:

    def __init__(self):
        self.agents: dict[str, Agent] = {}

    async def add_agent(self, name: str) -> None:
        if name in self.agents:
            return
        agent = Agent(name)
        self.agents[name] = agent
        await agent.start()

    async def remove_agent(self, name: str) -> None:
        agent = self.agents.get(name)
        if not agent:
            return
        await agent.stop()
        await agent.join()



