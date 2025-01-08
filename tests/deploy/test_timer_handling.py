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
from asyncio import Condition, Event
from datetime import timedelta

from inmanta.deploy.timers import ResourceTimer
from inmanta.deploy.work import TaskPriority


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
