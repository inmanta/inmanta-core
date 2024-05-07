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

import utils
from inmanta.scheduler import scheduler


async def test_very_basics():

    queue = scheduler.TaskQueue()

    t1 = scheduler.Task("t1", 100)
    t2 = scheduler.Task("t2", 100)
    t3 = scheduler.Task("t3", 100)
    t4 = scheduler.Task("t4", 1)
    t5 = scheduler.Task("t5", 100)
    t2.wait_for(t5)
    t6 = scheduler.Task("t6", 50)
    t7 = scheduler.Task("t7", 50)
    t7.wait_for(t6)

    queue.put(t1)
    queue.put(t2)
    queue.put(t3)
    queue.put(t4)
    queue.put(t5)

    assert t4 == await queue.do_next()
    assert t1 == await queue.do_next()
    assert t3 == await queue.do_next()
    assert t5 == await queue.do_next()
    assert t2 == await queue.do_next()

    t6 = scheduler.Task("t6", 50)
    t7 = scheduler.Task("t7", 50)
    t7.wait_for(t6)
    queue.put(t6)
    assert t6 == await queue.do_next()
    queue.put(t7)
    assert t7 == await queue.do_next()

    t6 = scheduler.Task("t6", 50)
    t7 = scheduler.Task("t7", 50)
    t7.wait_for(t6)
    queue.put(t7)
    # queue empty
    when_done = asyncio.ensure_future(queue.do_next())
    await asyncio.sleep(0)
    assert not when_done.done()
    queue.put(t6)
    assert t6 == await when_done
    assert t7 == await queue.do_next()


class HangTask(scheduler.Task):

    def __init__(self, name: str, prio: int) -> None:
        super().__init__(name, prio)
        self.event = asyncio.Event()
        self.event.clear()

    def go(self) -> None:
        self.event.set()

    async def run(self) -> None:
        await self.event.wait()


class FailTask(scheduler.Task):

    async def run(self) -> None:
        raise Exception("BAD!")


async def test_task_runner():
    queue = scheduler.TaskQueue()
    t1 = scheduler.Task("t1", 1)
    t2 = scheduler.Task("t2", 2)
    t3 = FailTask("t2", 2)
    # t6 makes it hang
    t6 = HangTask("t6", 50)
    t7 = scheduler.Task("t7", 50)
    t7.wait_for(t6)

    queue.put(t1)
    queue.put(t2)
    queue.put(t3)
    queue.put(t6)
    queue.put(t7)

    runner = scheduler.TaskRunner(queue)
    runner.start()
    await asyncio.sleep(0)

    await utils.retry_limited(lambda: t1.done, 1, 0.01)
    await utils.retry_limited(lambda: t2.done, 1, 0.01)
    await utils.retry_limited(lambda: t3.done, 1, 0.01)
    runner.stop()
    done = asyncio.ensure_future(runner.join())
    assert not done.done()
    t6.go()
    await done
    assert t6.done
    assert not t7.done
