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
import re

import pytest
import tornado
from pyformance import gauge, timer
from tornado.httpserver import HTTPServer
from tornado.web import url

from inmanta.reporter import AsyncReporter, InfluxReporter
from inmanta.server.services.metricservice import CPUMicroBenchMark


class QueryMockHandler(tornado.web.RequestHandler):
    def initialize(self, parent):
        self.parent = parent

    def get(self, *args, **kwargs):
        self.parent.querycount += 1
        try:
            assert self.request.query_arguments["q"] == [b"CREATE DATABASE metrics"]
        except Exception as e:
            # carry over  failures
            self.parent.failure = e


influxlineprotocol = re.compile(r"\w+(,\w+=\w+)* (\w+=[\d.e+-]*)(,\w+=[\d.e+-]*)* \d+")


class WriteMockHandler(tornado.web.RequestHandler):
    def initialize(self, parent):
        self.parent = parent

    def post(self, *args, **kwargs):
        self.parent.writecount += 1
        try:
            for line in self.request.body.decode().split("\n"):
                print(line)
                assert influxlineprotocol.match(line)
                self.parent.lines.append(line)
        except Exception as e:
            # carry over  failures
            self.parent.failure = e


class InfluxdbMock(object):
    def __init__(self, socket):
        self.querycount = 0
        self.writecount = 0
        self.failure = None
        self.lines = []

        self.app = tornado.web.Application(
            [
                url(r"/query", QueryMockHandler, kwargs={"parent": self}),
                url(r"/write", WriteMockHandler, kwargs={"parent": self}),
            ]
        )

        self.server = HTTPServer(self.app)
        self.server.add_sockets([socket])
        _addr, port = socket.getsockname()
        self.port = port


class MockReporter(AsyncReporter):
    def __init__(self, interval):
        super().__init__(None, interval)
        self.waiter = asyncio.locks.Semaphore(0)
        self.in_count = 0
        self.count = 0

    async def report_now(self, registry=None, timestamp=None) -> None:
        self.in_count += 1
        await self.waiter.acquire()
        self.count += 1


@pytest.fixture
def influxdb(event_loop, free_socket):
    ifl = InfluxdbMock(free_socket())
    yield ifl
    ifl.server.stop()


@pytest.mark.asyncio
async def test_influxdb(influxdb):
    rep = InfluxReporter(port=influxdb.port, tags={"mark": "X"}, autocreate_database=True)
    with timer("test").time():
        pass

    with timer("test2").time():
        pass

    cpu_micro = CPUMicroBenchMark()
    gauge("CPU", cpu_micro)
    await rep.report_now()

    assert influxdb.querycount == 1
    assert influxdb.writecount == 1

    # cpu micro has none-empty cache
    assert cpu_micro.last_value is not None

    if influxdb.failure:
        raise influxdb.failure

    for line in influxdb.lines:
        assert "mark=X" in line


@pytest.mark.asyncio
async def test_timing():
    # Attempt to deploy every 0.01 seconds,
    # Deploy hangs on a semaphore, so test case can control progress
    mr = MockReporter(0.01)
    mr.start()

    # no deploy done
    assert mr.count == 0
    # wait for deploy
    await asyncio.sleep(0.01)
    # one is waiting
    assert mr.in_count == 1
    # release
    mr.waiter.release()
    # wait 0 to allow reporter to make progress
    await asyncio.sleep(0.0)
    # one deploy done
    assert mr.count == 1

    # allow to run free to test timing
    for i in range(5):
        mr.waiter.release()

    # wait 0 to allow reporter to make progress
    await asyncio.sleep(0)
    # how many are we now?
    base = mr.count
    # should be sufficiently far of the lock
    # otherwise test always succeeds
    assert base < 4
    # wait for one more
    await asyncio.sleep(0.01)
    assert mr.count == base + 1
    mr.stop()
