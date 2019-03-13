import pytest
import tornado
from tornado.web import url

from stubs.tornado.httpserver import HTTPServer


class QueryMockHandler(tornado.web.RequestHandler):

    def initialize(self, parent):
        self.parent = parent

    def get(self, *args, **kwargs):
        self.parent.querycount += 1
        assert "q" in kwargs


class WriteMockHandler(tornado.web.RequestHandler):

    def initialize(self, parent):
        self.parent = parent

    def post(self, *args, **kwargs):
        self.parent.writecount += 1
        print(args, kwargs)


class InfluxdbMock(object):

    def __init__(self, socket):
        self.querycount = 0
        self.writecount = 0

        self.app = tornado.web.Application(
            [
              url(r"/query", QueryMockHandler, self),
              url(r"/write", WriteMockHandler, self)
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
    
