import pytest
import tornado
from tornado.web import url

from tornado.httpserver import HTTPServer
from inmanta.reporter import InfluxReporter, AsyncReporter
from pyformance import timer
import asyncio
import re


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
    ifl = InfluxdbMock(free_socket)
    yield ifl
    ifl.server.stop()


@pytest.mark.asyncio
async def test_influxdb(influxdb):
    rep = InfluxReporter(
        port=influxdb.port, tags={"mark": "X"}, autocreate_database=True
    )
    with timer("test").time():
        pass

    with timer("test2").time():
        pass

    await rep.report_now()

    assert influxdb.querycount == 1
    assert influxdb.writecount == 1

    if influxdb.failure:
        raise influxdb.failure

    for line in influxdb.lines:
        assert "mark=X" in line


@pytest.mark.asyncio
async def test_timing():
    mr = MockReporter(0.01)
    mr.start()
    assert mr.count == 0
    await asyncio.sleep(0.01)
    assert mr.in_count == 1
    mr.waiter.release()
    await asyncio.sleep(0.0)
    assert mr.count == 1

    # allow to run multiple times
    for i in range(5):
        mr.waiter.release()
    await asyncio.sleep(0.0)
    base = mr.count
    assert base < 4
    await asyncio.sleep(0.01)
    assert mr.count == base + 1
    mr.stop()
