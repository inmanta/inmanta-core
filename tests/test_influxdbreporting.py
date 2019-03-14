import pytest
import tornado
from tornado.web import url

from tornado.httpserver import HTTPServer
from inmanta.reporter import InfluxReporter
from pyformance import timer
import re


class QueryMockHandler(tornado.web.RequestHandler):

    def initialize(self, parent):
        self.parent = parent

    def get(self, *args, **kwargs):
        self.parent.querycount += 1
        try:
            assert self.request.query_arguments["q"] == [b'CREATE DATABASE metrics']
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
        except Exception as e:
            # carry over  failures
            self.parent.failure = e


class InfluxdbMock(object):

    def __init__(self, socket):
        self.querycount = 0
        self.writecount = 0
        self.failure = None

        self.app = tornado.web.Application(
            [
                url(r"/query", QueryMockHandler, kwargs={"parent": self}),
                url(r"/write", WriteMockHandler, kwargs={"parent": self})
            ])

        self.server = HTTPServer(self.app)
        self.server.add_sockets([socket])
        _addr, port = socket.getsockname()
        self.port = port


@pytest.fixture
def influxdb(event_loop, free_socket):
    ifl = InfluxdbMock(free_socket)
    yield ifl
    ifl.server.stop()


@pytest.mark.asyncio
async def test_influxdb(influxdb):
    rep = InfluxReporter(port=influxdb.port, tags={"mark": "X"}, autocreate_database=True)
    with timer("test").time():
        pass

    with timer("test2").time():
        pass

    await rep.report_now()

    assert influxdb.querycount == 1
    assert influxdb.writecount == 1

    if influxdb.failure:
        raise influxdb.failure
