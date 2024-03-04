import asyncio

import inmanta.scheduler.scheduler
from inmanta.scheduler import scheduler


async def test_scheduler():
    myscheduler = scheduler.EnvironmentScheduler()
    a1 = await myscheduler.get_agent("a1")
    a2 = await myscheduler.get_agent("a2")

    taskset = inmanta.scheduler.scheduler.TaskSet(
        [
            scheduler.Task("t1"),
            scheduler.Task("t2"),
            scheduler.Task("t3"),
        ],
        {"t1": ["t3", "t2"], "t3": ["t2"]},
    )

    for task in taskset.linearize():
        await a1.queue.put(task)
    await asyncio.sleep(1)
