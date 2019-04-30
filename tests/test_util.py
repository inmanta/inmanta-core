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
import logging

import pytest

from inmanta import util
from inmanta.util import ensure_future_and_handle_exception
from utils import LogSequence, log_contains, no_error_in_logs

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_scheduler_remove(caplog):
    sched = util.Scheduler("remove")

    i = []

    async def action():
        i.append(0)

    sched.add_action(action, 0.05, 0)

    while len(i) == 0:
        await asyncio.sleep(0.01)

    sched.remove(action)
    length = len(i)
    await asyncio.sleep(0.1)
    assert len(i) == length
    no_error_in_logs(caplog)


@pytest.mark.asyncio
async def test_scheduler_stop(caplog):
    sched = util.Scheduler("stop")

    i = []

    async def action():
        i.append(0)
        return "A"

    sched.add_action(action, 0.05, 0)

    while len(i) == 0:
        await asyncio.sleep(0.01)

    sched.stop()

    length = len(i)
    await asyncio.sleep(0.1)
    assert len(i) == length
    no_error_in_logs(caplog)


@pytest.mark.asyncio
async def test_scheduler_async_run_fail(caplog):
    sched = util.Scheduler("xxx")

    i = []

    async def action():
        i.append(0)
        await asyncio.sleep(0)
        raise Exception("Marker")

    sched.add_action(action, 0.05, 0)

    while len(i) == 0:
        await asyncio.sleep(0.01)

    sched.stop()

    length = len(i)
    await asyncio.sleep(0.1)
    assert len(i) == length

    print(caplog.messages)

    log_contains(
        caplog,
        "inmanta.util",
        logging.ERROR,
        "Uncaught exception while executing scheduled action",
    )


@pytest.mark.asyncio
async def test_scheduler_run_async(caplog):
    sched = util.Scheduler("xxx")

    i = []

    async def action():
        i.append(0)

    sched.add_action(action, 0.05, 0)

    while len(i) == 0:
        await asyncio.sleep(0.01)

    sched.stop()

    length = len(i)
    await asyncio.sleep(0.1)
    assert len(i) == length
    no_error_in_logs(caplog)


@pytest.mark.asyncio
async def test_ensure_future_and_handle_exception(caplog):
    caplog.set_level(logging.INFO)

    async def success():
        LOGGER.info("Success")

    async def fail():
        LOGGER.info("Fail")
        raise Exception("message F")

    ensure_future_and_handle_exception(LOGGER, "marker 1", success())
    ensure_future_and_handle_exception(LOGGER, "marker 2", fail())

    await asyncio.sleep(0.2)

    LogSequence(caplog).log_contains("test_util", logging.INFO, "Success")
    final = (
        LogSequence(caplog)
        .log_contains("test_util", logging.INFO, "Fail")
        .log_contains("test_util", logging.ERROR, "marker 2")
        .index
    )
    exception = caplog.get_records("call")[final].exc_info[1]
    assert str(exception) == "message F"
