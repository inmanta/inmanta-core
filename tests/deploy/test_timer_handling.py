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

import datetime
import hashlib
import json
import uuid
from asyncio import Event
from datetime import timedelta
from typing import Union, Optional

import pytest

from deploy.scheduler_mocks import DummyManager, TestScheduler, FAIL_DEPLOY
from deploy.test_scheduler_agent import make_resource_minimal, retry_limited_fast
from inmanta import const
from inmanta.deploy import state
from inmanta.deploy.scheduler import ModelVersion
from inmanta.protocol.common import custom_json_encoder
from inmanta.types import ResourceIdStr

from inmanta.deploy.timers import ResourceTimer, TimerManager
from inmanta.deploy.work import TaskPriority
from inmanta.util import Scheduler, TaskMethod, TaskSchedule, ScheduledTask, IntervalSchedule
from inmanta.agent import config
from utils import make_requires


class RecordingTimer(ResourceTimer):
    # Timer that doens't really execute anything

    def __init__(self, resource: ResourceIdStr):
        super().__init__(resource, None)
        self.when: datetime.datetime | None = None
        self.interval: datetime.timedelta | None = None

    def set_timer(
        self,
        when: datetime.datetime,
        reason: str,
        priority: TaskPriority,
    ) -> None:
        self.when = when
        self.interval = when - datetime.datetime.now().astimezone()
        self.reason = reason
        self.priority = priority

    def cancel(self) -> None:
        self.when = None

class MockScheduler(Scheduler):

    def __init__(self) -> None:
        self.all_tasks: set[ScheduledTask] = set()

    def add_action(
        self,
        action: TaskMethod,
        schedule: Union[TaskSchedule, int],  # int for backward compatibility,
        cancel_on_stop: bool = True,
        quiet_mode: bool = False,
    ) -> Optional[ScheduledTask]:
        schedule_typed: TaskSchedule
        if isinstance(schedule, int):
            schedule_typed = IntervalSchedule(schedule)
        else:
            schedule_typed = schedule
        task_spec: ScheduledTask = ScheduledTask(action, schedule_typed)
        self.all_tasks.add(task_spec)
        return task_spec

    def remove(self, task: ScheduledTask) -> None:
        self.all_tasks.remove(task)

    async def stop(self) -> None:
        pass



class MockTimerManager(TimerManager):

    def __init__(self, environment: uuid.UUID) -> None:
        self.executor_manager = DummyManager()
        scheduler = TestScheduler(environment, self.executor_manager, None)
        scheduler._timer_manager = self
        super().__init__(scheduler)
        self._cron_scheduler = MockScheduler()

    def _make_resource_timer(self, resource: ResourceIdStr) -> ResourceTimer:
        return RecordingTimer(resource)


async def test_time_manager_basics():
    class MockTimer(ResourceTimer):

        def __init__(self):
            super().__init__("the_resource", None)
            self.activated_at: datetime.datetime | None = None
            self.activation_lock: Event = Event()

        def _activate(self) -> None:
            self.activated_at = datetime.datetime.now()
            self.activation_lock.set()

    start_time = datetime.datetime.now()

    def set_time(delta: int) -> tuple[MockTimer, datetime.datetime]:
        t = MockTimer()
        call_in = timedelta(milliseconds=delta)
        call_at = start_time + call_in
        t.set_timer(call_at, "I say so", TaskPriority.DRYRUN)
        return t, call_at

    t1 = set_time(5)
    t2 = set_time(5)
    t3 = set_time(15)
    t4 = set_time(15)
    t3[0].cancel()
    t5 = set_time(10)

    await t4[0].activation_lock.wait()

    def assert_fired(timer: MockTimer, at: datetime.datetime) -> None:
        assert timedelta(milliseconds=-1) < (timer.activated_at - at) < timedelta(milliseconds=1)

    assert_fired(*t1)
    assert_fired(*t2)
    assert_fired(*t4)
    assert_fired(*t5)
    assert t3[0].activated_at is None

@pytest.fixture
def environment() -> uuid.UUID:
    return uuid.UUID("83d604a0-691a-11ef-ae04-c8f750463317")

@pytest.fixture
def make_resource_minimal(environment):
    def make_resource_minimal(
        rid: ResourceIdStr,
        values: dict[str, object],
        requires: list[str],
        status: state.ComplianceStatus = state.ComplianceStatus.HAS_UPDATE,
    ) -> state.ResourceDetails:
        """Produce a resource that is valid to the scheduler"""
        attributes = dict(values)
        attributes["requires"] = requires
        character = json.dumps(
            {k: v for k, v in attributes.items() if k not in ["requires", "provides", "version"]},
            default=custom_json_encoder,
            sort_keys=True,  # sort the keys for stable hashes when using dicts, see #5306
        )
        m = hashlib.md5()
        m.update(rid.encode("utf-8"))
        m.update(character.encode("utf-8"))
        attribute_hash = m.hexdigest()

        return state.ResourceDetails(resource_id=rid, attributes=attributes, attribute_hash=attribute_hash)

    return make_resource_minimal


async def test_config_update(inmanta_config, make_resource_minimal, environment):
    config.agent_deploy_interval.set("60")
    config.agent_repair_interval.set("3600")

    tm = MockTimerManager(environment)
    scheduler: TestScheduler = tm._resource_scheduler

    await scheduler.start()
    await tm.initialize()

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent2,name=2]"
    rid3 = "test::Resource[agent3,name=3]"

    # one deployed
    # one failed
    # one undeployable
    resources = {
        ResourceIdStr(rid1): make_resource_minimal(
            rid1,
            values={"value": "vx", const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False, FAIL_DEPLOY: False},
            requires={},
        ),
        ResourceIdStr(rid2): make_resource_minimal(
            rid2,
            values={"value": "vx", const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False, FAIL_DEPLOY: True},
            requires={},
        ),
        ResourceIdStr(rid3): make_resource_minimal(
            rid3,
            values={"value": "vx", const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False, FAIL_DEPLOY: False},
            requires={},
        ),
    }

    await scheduler._new_version(
        [ModelVersion(version=5, resources=resources, requires=make_requires(resources), undefined={ResourceIdStr(rid3)})]
    )

    def done():
        for queue in scheduler._work.agent_queues._agent_queues.values():
            if queue._unfinished_tasks != 0:
                return False
        if not scheduler._work.agent_queues._agent_queues:
           return False
        return True
    await retry_limited_fast(done)

    def is_approx(time: timedelta, seconds: int) -> bool:
        return abs(time - timedelta(seconds=seconds)) < timedelta(milliseconds=1)

    assert tm.global_periodic_repair_task is None
    assert tm.global_periodic_deploy_task is None
    assert is_approx(tm.resource_timers[rid1].interval, 3600)
    assert is_approx(tm.resource_timers[rid2].interval, 60)
    assert rid3 not in tm.resource_timers

    config.agent_deploy_interval.set("600")
    config.agent_repair_interval.set("36000")

    await tm.reload_config()

    assert tm.global_periodic_repair_task is None
    assert tm.global_periodic_deploy_task is None
    assert is_approx(tm.resource_timers[rid1].interval, 36000)
    assert is_approx(tm.resource_timers[rid2].interval, 600)
    assert rid3 not in tm.resource_timers


