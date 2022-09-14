"""
    Copyright 2022 Inmanta

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
import dataclasses
import datetime
import logging
import uuid
from functools import partial
from typing import Optional

import pytest

import inmanta
from inmanta import util
from inmanta.util import (
    CronSchedule,
    CycleException,
    IntervalSchedule,
    NamedLock,
    ScheduledTask,
    TaskSchedule,
    ensure_future_and_handle_exception,
    stable_depth_first,
)
from utils import LogSequence, get_product_meta_data, log_contains, no_error_in_logs

LOGGER = logging.getLogger(__name__)


def test_interval_schedule() -> None:
    """
    Verifies that the IntervalSchedule class' primary methods work as expected.
    """
    simple: TaskSchedule = IntervalSchedule(interval=1.0)
    assert simple.get_initial_delay() == 1.0
    assert simple.get_next_delay() == 1.0
    with_delay: TaskSchedule = IntervalSchedule(interval=1.0, initial_delay=0.0)
    assert with_delay.get_initial_delay() == 0.0
    assert with_delay.get_next_delay() == 1.0


def test_interval_schedule_equals() -> None:
    """
    Verifies that the IntervalSchedule class' equality checks work as expected.
    """
    assert IntervalSchedule(interval=1.0) == IntervalSchedule(interval=1.0)
    assert IntervalSchedule(interval=1.0) != IntervalSchedule(interval=2.0)
    assert IntervalSchedule(interval=1.0, initial_delay=0.5) == IntervalSchedule(interval=1.0, initial_delay=0.5)
    assert IntervalSchedule(interval=1.0, initial_delay=0.5) != IntervalSchedule(interval=1.0, initial_delay=0.0)


def test_cron_schedule(monkeypatch) -> None:
    """
    Verifies that the CronSchedule class' primary methods work as expected.
    """

    def freeze_time(time: datetime.datetime) -> None:
        """
        Freeze time to a given value to avoid race conditions.
        """

        class frozendatetime(datetime.datetime):
            @classmethod
            def now(cls, tz: Optional[datetime.tzinfo] = None) -> datetime.datetime:
                if tz is None:
                    return time if time.tzinfo is None else time.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                else:
                    aware: datetime.datetime = time if time.tzinfo is not None else time.replace(tzinfo=datetime.timezone.utc)
                    return aware.astimezone(tz)

        monkeypatch.setattr(datetime, "datetime", frozendatetime)

    # min hour day month dow
    schedule: TaskSchedule = CronSchedule(cron="1 2 * * *")

    # year month day hour min sec ms
    now: datetime.datetime = datetime.datetime(2022, 6, 16, 10, 15, 3, 0)
    freeze_time(now)
    next_delta: datetime.timedelta = datetime.datetime(2022, 6, 17, 2, 1, 0, 0) - now
    assert schedule.get_initial_delay() == schedule.get_next_delay() == next_delta.total_seconds()

    tomorrow: datetime.datetime = now + datetime.timedelta(days=1, seconds=42)
    freeze_time(tomorrow)
    assert schedule.get_initial_delay() == schedule.get_next_delay() == next_delta.total_seconds() - 42


def test_cron_schedule_equals() -> None:
    """
    Verifies that the CronSchedule class' equality checks work as expected.
    """
    assert CronSchedule(cron="1 2 * * *") == CronSchedule(cron="1 2 * * *")
    assert CronSchedule(cron="1 2 * * *") != CronSchedule(cron="0 2 * * *")


async def test_scheduler_remove(caplog):
    scheduler = util.Scheduler("remove")

    i = []

    async def action():
        i.append(0)

    schedule: IntervalSchedule = IntervalSchedule(0.05, 0)
    scheduler.add_action(action, schedule)

    while len(i) == 0:
        await asyncio.sleep(0.01)

    assert ScheduledTask(action=action, schedule=schedule) in scheduler._scheduled
    scheduler.remove(ScheduledTask(action=action, schedule=schedule))
    length = len(i)
    await asyncio.sleep(0.1)
    assert len(i) == length
    assert not scheduler._executing_tasks[action]
    assert not (action, schedule) in scheduler._scheduled
    no_error_in_logs(caplog)


async def test_scheduler_remove_same_action() -> None:
    """
    Verify that removing an action from the scheduler works as intended in the presence of other similar scheduled actions.
    As long as there exists no other scheduled action for exactly the same action and schedule, removal should be unambiguous.
    This test includes verification of potential edge cases such as `partial` of the same function, locally defined functions
    within a body that gets evaluated twice, ...
    """

    scheduler = util.Scheduler("remove_same_action")

    async def myaction() -> None:
        pass

    schedule_one: TaskSchedule = IntervalSchedule(100)
    schedule_two: TaskSchedule = IntervalSchedule(200)

    # same action, different schedule => expect distinct tasks
    scheduler.add_action(myaction, schedule_one)
    scheduler.add_action(myaction, schedule_two)

    # same action wrapped in `partial`, same schedule => expect distinct tasks
    partial_one = partial(myaction)
    partial_two = partial(myaction)
    assert partial_one != partial_two
    scheduler.add_action(partial_one, schedule_one)
    scheduler.add_action(partial_two, schedule_one)

    locally_defined: list[object] = []

    def add_locally_defined() -> None:
        async def myaction() -> None:
            pass

        assert ScheduledTask(action=myaction, schedule=schedule_one) not in scheduler._scheduled
        scheduler.add_action(myaction, schedule_one)
        locally_defined.append(myaction)

    add_locally_defined()
    add_locally_defined()

    scheduler.add_action(myaction, schedule_two)
    assert ScheduledTask(action=myaction, schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=myaction, schedule=schedule_two) in scheduler._scheduled
    assert ScheduledTask(action=partial_one, schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=partial_two, schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=locally_defined[0], schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=locally_defined[1], schedule=schedule_one) in scheduler._scheduled

    scheduler.remove(ScheduledTask(action=myaction, schedule=schedule_one))
    assert ScheduledTask(action=myaction, schedule=schedule_one) not in scheduler._scheduled
    assert ScheduledTask(action=myaction, schedule=schedule_two) in scheduler._scheduled
    assert ScheduledTask(action=partial_one, schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=partial_two, schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=locally_defined[0], schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=locally_defined[1], schedule=schedule_one) in scheduler._scheduled

    scheduler.remove(ScheduledTask(action=myaction, schedule=schedule_two))
    assert ScheduledTask(action=myaction, schedule=schedule_two) not in scheduler._scheduled
    assert ScheduledTask(action=partial_one, schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=partial_two, schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=locally_defined[0], schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=locally_defined[1], schedule=schedule_one) in scheduler._scheduled

    scheduler.remove(ScheduledTask(action=partial_one, schedule=schedule_one))
    assert ScheduledTask(action=partial_one, schedule=schedule_one) not in scheduler._scheduled
    assert ScheduledTask(action=partial_two, schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=locally_defined[0], schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=locally_defined[1], schedule=schedule_one) in scheduler._scheduled

    scheduler.remove(ScheduledTask(action=partial_two, schedule=schedule_one))
    assert ScheduledTask(action=partial_two, schedule=schedule_one) not in scheduler._scheduled
    assert ScheduledTask(action=locally_defined[0], schedule=schedule_one) in scheduler._scheduled
    assert ScheduledTask(action=locally_defined[1], schedule=schedule_one) in scheduler._scheduled

    scheduler.remove(ScheduledTask(action=locally_defined[0], schedule=schedule_one))
    assert ScheduledTask(action=locally_defined[0], schedule=schedule_one) not in scheduler._scheduled
    assert ScheduledTask(action=locally_defined[1], schedule=schedule_one) in scheduler._scheduled

    scheduler.remove(ScheduledTask(action=locally_defined[1], schedule=schedule_one))
    assert ScheduledTask(action=locally_defined[1], schedule=schedule_one) not in scheduler._scheduled


async def test_scheduler_stop(caplog):
    sched = util.Scheduler("stop")

    i = []

    async def action():
        i.append(0)
        return "A"

    sched.add_action(action, IntervalSchedule(0.05, 0))

    while len(i) == 0:
        await asyncio.sleep(0.01)

    await sched.stop()

    length = len(i)
    await asyncio.sleep(0.1)
    assert len(i) == length
    no_error_in_logs(caplog)

    caplog.clear()
    sched.add_action(action, IntervalSchedule(0.05, 0))
    assert "Scheduling action 'action', while scheduler is stopped" in caplog.messages
    assert not sched._executing_tasks[action]


async def test_scheduler_async_run_fail(caplog):
    sched = util.Scheduler("xxx")

    i = []

    async def action():
        i.append(0)
        await asyncio.sleep(0)
        raise Exception("Marker")

    sched.add_action(action, IntervalSchedule(0.05, 0))

    while len(i) == 0:
        await asyncio.sleep(0.01)

    await sched.stop()

    length = len(i)
    await asyncio.sleep(0.1)
    assert len(i) == length
    assert not sched._executing_tasks[action]

    print(caplog.messages)

    log_contains(caplog, "inmanta.util", logging.ERROR, "Uncaught exception while executing scheduled action")


async def test_scheduler_run_async(caplog):
    sched = util.Scheduler("xxx")

    i = []

    async def action():
        i.append(0)

    sched.add_action(action, IntervalSchedule(0.05, 0))

    while len(i) == 0:
        await asyncio.sleep(0.01)

    await sched.stop()

    length = len(i)
    await asyncio.sleep(0.1)
    assert len(i) == length
    assert not sched._executing_tasks[action]
    no_error_in_logs(caplog)


async def test_scheduler_cancel_executing_tasks() -> None:
    """
    Verify that executing tasks are cancelled when the scheduler is stopped.
    """

    @dataclasses.dataclass
    class TaskStatus:
        task_is_executing: bool = False
        task_was_cancelled: bool = False

    task_status = TaskStatus()

    async def action():
        task_status.task_is_executing = True
        try:
            await asyncio.sleep(1000)
        except asyncio.CancelledError:
            task_status.task_was_cancelled = True
            raise

    sched = util.Scheduler("xxx")
    sched.add_action(action, IntervalSchedule(interval=1000, initial_delay=0))
    await util.retry_limited(lambda: task_status.task_is_executing, timeout=10)
    assert task_status.task_is_executing
    assert not task_status.task_was_cancelled
    assert sched._executing_tasks[action]
    await sched.stop()
    await util.retry_limited(lambda: task_status.task_was_cancelled, timeout=10)
    assert not sched._executing_tasks[action]


@pytest.mark.parametrize("cancel_on_stop", [True, False])
async def test_scheduler_waits_on_shutdown(cancel_on_stop) -> None:
    """
    Verify that tasks can be tagged to be awaited when the scheduler is stopped.
    """

    @dataclasses.dataclass
    class TaskStatus:
        task_is_executing: bool = False
        task_was_cancelled: bool = False
        task_was_executed: bool = False

    task_status = TaskStatus()

    async def action():
        task_status.task_is_executing = True
        try:
            await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            task_status.task_was_cancelled = True
            raise
        task_status.task_was_executed = True

    sched = util.Scheduler("test_await_tasks_on_shutdown")
    sched.add_action(action, IntervalSchedule(interval=1000, initial_delay=0), cancel_on_stop=cancel_on_stop)
    await util.retry_limited(lambda: task_status.task_is_executing, timeout=3)

    await sched.stop()

    if cancel_on_stop:
        await util.retry_limited(lambda: task_status.task_was_cancelled, timeout=3)
        assert not task_status.task_was_executed
    else:
        await util.retry_limited(lambda: task_status.task_was_executed, timeout=3)
        assert not task_status.task_was_cancelled


async def test_ensure_future_and_handle_exception(caplog):
    caplog.set_level(logging.INFO)

    async def success():
        LOGGER.info("Success")

    async def fail():
        LOGGER.info("Fail")
        raise Exception("message F")

    ensure_future_and_handle_exception(LOGGER, "marker 1", success(), notify_done_callback=lambda x: None)
    ensure_future_and_handle_exception(LOGGER, "marker 2", fail(), notify_done_callback=lambda x: None)

    await asyncio.sleep(0.2)

    LogSequence(caplog).contains("test_util", logging.INFO, "Success")
    final = (
        LogSequence(caplog).contains("test_util", logging.INFO, "Fail").contains("test_util", logging.ERROR, "marker 2").index
        - 1
    )
    exception = caplog.get_records("call")[final].exc_info[1]
    assert str(exception) == "message F"


def test_stable_dfs():
    def expand_graph(gs):
        """expand a graph od the form
        a: a b c d
        """
        nodes = set()
        edges = {}

        for line in gs.split("\n"):
            if not line.strip():
                continue
            f, t = line.split(":")
            f = f.strip()
            if not f:
                continue
            nodes.add(f)
            t = t.strip()
            if not t:
                continue
            ts = [target.strip() for target in t.split(" ") if target.strip()]
            for target in ts:
                nodes.add(target)
            edges[f] = ts
        return list(nodes), edges

    graph = expand_graph(
        """
    e: f
    a: b c
    b: c d
    h: i
    0:
    """
    )
    seq = stable_depth_first(*graph)
    assert seq == ["0", "c", "d", "b", "a", "f", "e", "i", "h"]

    graph = expand_graph(
        """
        e: f
        b: c d
        a: c b
        h: i
        0:
        """
    )
    seq = stable_depth_first(*graph)
    assert seq == ["0", "c", "d", "b", "a", "f", "e", "i", "h"]

    with pytest.raises(CycleException) as e:
        stable_depth_first(*expand_graph("a: a"))

    assert e.value.nodes == ["a"]

    with pytest.raises(CycleException) as e:
        stable_depth_first(
            *expand_graph(
                """a: b
        b: a"""
            )
        )

    assert e.value.nodes == ["b", "a"]

    # missing nodes
    graph, edges = expand_graph("""a: b""")
    graph.remove("b")

    seq = stable_depth_first(graph, edges)
    assert seq == ["b", "a"]


def test_is_sub_dict():
    identifier = uuid.uuid4()
    now = datetime.datetime.now()
    dct = {1: 2, "test": False, "date": now, "id": identifier, "str": "string"}

    assert util.is_sub_dict({}, dct)
    assert util.is_sub_dict({1: 2}, dct)
    assert util.is_sub_dict({"test": False}, dct)
    assert util.is_sub_dict({"date": now}, dct)
    assert util.is_sub_dict({"id": identifier}, dct)
    assert util.is_sub_dict({"str": "string"}, dct)
    assert util.is_sub_dict({"test": False, "date": now}, dct)
    assert not util.is_sub_dict({"test": True, "date": now}, dct)
    assert not util.is_sub_dict({"test": False, "date": datetime.datetime.now()}, dct)
    assert not util.is_sub_dict({1: 2, "test": False, "date": now, "id": identifier, "val": "val"}, dct)


def test_get_product_meta_data():
    """Basic smoke test for testing utils"""
    assert get_product_meta_data() is not None


async def test_named_lock():
    lock = NamedLock()
    await lock.acquire("a")
    await lock.acquire("b")
    await lock.release("b")
    fut = asyncio.create_task(lock.acquire("a"))
    assert not fut.done()
    await lock.release("a")
    await fut
    await lock.release("a")
    # Don't leak
    assert not lock._named_locks


def test_running_test_fixture():
    """
    Assert that the RUNNING_TESTS variable is set to True when we run the tests
    """
    assert inmanta.RUNNING_TESTS
