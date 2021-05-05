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
import datetime
import logging
import uuid

import pytest

from inmanta import util
from inmanta.util import CycleException, ensure_future_and_handle_exception, stable_depth_first
from utils import LogSequence, get_product_meta_data, log_contains, no_error_in_logs

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

    caplog.clear()
    sched.add_action(action, 0.05, 0)
    assert "Scheduling action 'action', while scheduler is stopped" in caplog.messages


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

    log_contains(caplog, "inmanta.util", logging.ERROR, "Uncaught exception while executing scheduled action")


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
    """ Basic smoke test for testing utils"""
    assert get_product_meta_data() is not None
