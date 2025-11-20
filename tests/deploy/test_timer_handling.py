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
from typing import Optional, Union
from uuid import UUID

import pytest

from deploy.scheduler_mocks import FAIL_DEPLOY, DummyManager, TestScheduler
from deploy.test_scheduler_agent import retry_limited_fast
from inmanta import const, data
from inmanta.deploy import state
from inmanta.deploy.scheduler import ModelVersion
from inmanta.deploy.timers import ResourceTimer, TimerManager
from inmanta.deploy.work import TaskPriority
from inmanta.protocol.common import custom_json_encoder
from inmanta.types import ResourceIdStr
from inmanta.util import CronSchedule, IntervalSchedule, ScheduledTask, Scheduler, TaskMethod, TaskSchedule
from tests.deploy.scheduler_mocks import NON_COMPLIANT_DEPLOY
from utils import make_requires


class RecordingTimer(ResourceTimer):
    # Timer that doesn't really execute anything

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
        self.reason = reason
        self.priority = priority

    def cancel(self) -> None:
        self.when = None
        self.interval = None


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
        return t, call_at if delta >= 0 else start_time

    t1 = set_time(30)
    t2 = set_time(30)
    t3 = set_time(100)
    t4 = set_time(100)
    t3[0].cancel()
    t5 = set_time(80)
    t6 = set_time(-10_000)

    await t4[0].activation_lock.wait()

    def assert_fired(timer: MockTimer, at: datetime.datetime) -> None:
        assert timedelta(milliseconds=0) < (timer.activated_at - at) < timedelta(milliseconds=10)

    assert_fired(*t1)
    assert_fired(*t2)
    assert_fired(*t4)
    assert_fired(*t5)
    assert t3[0].activated_at is None
    assert_fired(*t6)


@pytest.fixture
def environment_mock() -> uuid.UUID:
    return uuid.UUID("83d604a0-691a-11ef-ae04-c8f750463317")


@pytest.fixture
def make_resource_minimal(environment_mock):
    def make_resource_minimal(
        rid: ResourceIdStr,
        values: dict[str, object],
        requires: list[str],
    ) -> state.ResourceIntent:
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

        return state.ResourceIntent(resource_id=rid, attributes=attributes, attribute_hash=attribute_hash)

    return make_resource_minimal


async def test_config_update(inmanta_config, make_resource_minimal, environment, server, client):
    """
    Test that the TimerManager correctly responds to changes to the config for deploy and repair timers.
    Test that reporting resources receive the correct timers
    """
    env_id = UUID(environment)

    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_INTERVAL, "60")
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_REPAIR_INTERVAL, "3600")
    assert result.code == 200

    tm = MockTimerManager(env_id)
    scheduler: TestScheduler = tm._resource_scheduler

    await scheduler.start()
    await tm.initialize()

    rid1 = "test::Resource[agent1,name=1]"
    rid2 = "test::Resource[agent2,name=2]"
    rid3 = "test::Resource[agent3,name=3]"
    rid4 = "test::Resource[agent4,name=4]"
    rid5 = "test::Resource[agent5,name=5]"
    rid6 = "test::Resource[agent6,name=6]"

    # one deployed
    # one failed
    # one undeployable
    # -- reporting resources --
    # one compliant
    # one non-compliant
    # one failed
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
        ResourceIdStr(rid4): make_resource_minimal(
            rid4,
            values={
                "value": "vx",
                const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False,
                const.RESOURCE_ATTRIBUTE_REPORT_ONLY: True,
                FAIL_DEPLOY: False,
            },
            requires={},
        ),
        ResourceIdStr(rid5): make_resource_minimal(
            rid5,
            values={
                "value": "vx",
                const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False,
                const.RESOURCE_ATTRIBUTE_REPORT_ONLY: True,
                NON_COMPLIANT_DEPLOY: True,
            },
            requires={},
        ),
        ResourceIdStr(rid6): make_resource_minimal(
            rid6,
            values={
                "value": "vx",
                const.RESOURCE_ATTRIBUTE_SEND_EVENTS: False,
                const.RESOURCE_ATTRIBUTE_REPORT_ONLY: True,
                FAIL_DEPLOY: True,
            },
            requires={},
        ),
    }

    await scheduler._new_version(
        [
            ModelVersion(
                version=5,
                resources=resources,
                requires=make_requires(resources),
                undefined={ResourceIdStr(rid3)},
                resource_sets={None: set(resources.keys())},
                partial=False,
            )
        ]
    )

    def done():
        for queue in scheduler._work.agent_queues._agent_queues.values():
            if queue._unfinished_tasks != 0:
                return False
        if not scheduler._work.agent_queues._agent_queues:
            return False
        return True

    await retry_limited_fast(done, timeout=5)
    last_deploy_time_approx = datetime.datetime.now().astimezone()

    def is_approx(rid: str, seconds: int) -> None:
        time = tm.resource_timers[rid].when
        assert abs(time - last_deploy_time_approx - timedelta(seconds=seconds)) < timedelta(milliseconds=100)

    def is_disabled(rid) -> None:
        assert rid not in tm.resource_timers or tm.resource_timers[rid].when is None

    # Repeat same pattern: update config, check all timers

    # All per resource
    assert tm.global_periodic_repair_task is None
    assert tm.global_periodic_deploy_task is None
    is_approx(rid1, 3600)
    is_approx(rid2, 60)
    is_disabled(rid3)
    is_approx(rid4, 3600)
    is_approx(rid5, 60)
    is_approx(rid6, 60)

    # Updated timers
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_INTERVAL, "600")
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_REPAIR_INTERVAL, "36000")
    assert result.code == 200
    await tm.reload_config()

    assert tm.global_periodic_repair_task is None
    assert tm.global_periodic_deploy_task is None
    is_approx(rid1, 36000)
    is_approx(rid2, 600)
    is_disabled(rid3)
    is_approx(rid4, 36000)
    is_approx(rid5, 600)
    is_approx(rid6, 600)

    # Repair on cron job
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_INTERVAL, "60")
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_REPAIR_INTERVAL, "* * * * *")
    assert result.code == 200
    await tm.reload_config()

    assert tm.global_periodic_repair_task.schedule == CronSchedule("* * * * *")
    assert tm.global_periodic_deploy_task is None
    is_disabled(rid1)
    is_approx(rid2, 60)
    is_disabled(rid3)

    # Deploy on cron job
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_INTERVAL, "* * * * 1")
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_REPAIR_INTERVAL, "360")
    assert result.code == 200
    await tm.reload_config()

    assert tm.global_periodic_repair_task is None
    assert tm.global_periodic_deploy_task.schedule == CronSchedule("* * * * 1")
    is_approx(rid1, 360)
    is_approx(rid2, 360)
    is_disabled(rid3)

    # All on cron
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_INTERVAL, "* * * * 1")
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_REPAIR_INTERVAL, "* * * * 2")
    assert result.code == 200
    await tm.reload_config()
    assert tm.global_periodic_repair_task.schedule == CronSchedule("* * * * 2")
    assert tm.global_periodic_deploy_task.schedule == CronSchedule("* * * * 1")
    is_disabled(rid1)
    is_disabled(rid2)
    is_disabled(rid3)

    # back to start
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_INTERVAL, "600")
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_REPAIR_INTERVAL, "36000")
    assert result.code == 200
    await tm.reload_config()

    assert tm.global_periodic_repair_task is None
    assert tm.global_periodic_deploy_task is None
    is_approx(rid1, 36000)
    is_approx(rid2, 600)
    is_disabled(rid3)
