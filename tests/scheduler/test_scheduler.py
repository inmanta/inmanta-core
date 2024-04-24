import asyncio

from inmanta.scheduler import scheduler
async def test_very_basics():

    queue = scheduler.TaskQueue()

    t1 = scheduler.Task("t1",100)
    t2 = scheduler.Task("t2",100)
    t3 = scheduler.Task("t3",100)
    t4 = scheduler.Task("t4",1)
    t5 = scheduler.Task("t5",100)
    t2.wait_for(t5)
    t6 = scheduler.Task("t6", 50)
    t7 = scheduler.Task("t7", 50)
    t7.wait_for(t6)

    await queue.put(t1)
    await queue.put(t2)
    await queue.put(t3)
    await queue.put(t4)
    await queue.put(t5)

    assert t4 == await queue.do_next()
    assert t1 == await queue.do_next()
    assert t3 == await queue.do_next()
    assert t5 == await queue.do_next()
    assert t2 == await queue.do_next()

    t6 = scheduler.Task("t6", 50)
    t7 = scheduler.Task("t7", 50)
    t7.wait_for(t6)
    await queue.put(t6)
    assert t6 == await queue.do_next()
    await queue.put(t7)
    assert t7 == await queue.do_next()

    t6 = scheduler.Task("t6", 50)
    t7 = scheduler.Task("t7", 50)
    t7.wait_for(t6)
    await queue.put(t7)
    # queue empty
    when_done = asyncio.ensure_future(queue.do_next())
    await asyncio.sleep(0)
    assert not when_done.done()
    await queue.put(t6)
    assert t6 == await when_done
    assert t7 == await queue.do_next()
