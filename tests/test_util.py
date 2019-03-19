"""
    Copyright 2019 Inmanta

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

import pytest

from inmanta import util


@pytest.mark.asyncio
async def test_scheduler_remove():
    sched = util.Scheduler("remove")

    i = []

    def action():
        i.append(0)

    sched.add_action(action, 0.05, 0)

    while len(i) == 0:
        await asyncio.sleep(0.01)

    sched.remove(action)
    length = len(i)
    await asyncio.sleep(0.1)
    assert len(i) == length


@pytest.mark.asyncio
async def test_scheduler_stop():
    sched = util.Scheduler("stop")

    i = []

    def action():
        i.append(0)

    sched.add_action(action, 0.05, 0)

    while len(i) == 0:
        await asyncio.sleep(0.01)

    sched.stop()

    length = len(i)
    await asyncio.sleep(0.1)
    assert len(i) == length
