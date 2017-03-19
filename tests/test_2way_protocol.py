"""
    Copyright 2016 Inmanta

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

import logging
import sys
import uuid

import colorlog
from inmanta import methods
from tornado import gen
import pytest
from tornado.gen import sleep
from utils import retry_limited
from tornado.ioloop import IOLoop

LOGGER = logging.getLogger(__name__)


class StatusMethod(methods.Method):
    __method_name__ = "status"

    @methods.protocol(operation="GET", index=True)
    def get_status_x(self, tid: uuid.UUID):
        pass

    @methods.protocol(operation="GET", id=True, server_agent=True, timeout=10)
    def get_agent_status(self, id):
        pass


# Methods need to be defined before the Client class is loaded by Python
from inmanta import protocol  # NOQA


class Server(protocol.ServerEndpoint):

    def __init__(self, name, io_loop, interval=60):
        protocol.ServerEndpoint.__init__(self, name, io_loop, interval=interval)
        self.expires = 0

    @protocol.handle(StatusMethod.get_status_x)
    @gen.coroutine
    def get_status_x(self, tid):
        status_list = []
        for session in self._sessions.values():
            client = session.get_client()
            status = yield client.get_agent_status("x")
            if status is not None and status.code == 200:
                status_list.append(status.result)

        return 200, {"agents": status_list}

    def expire(self, session, timeout):
        protocol.ServerEndpoint.expire(self, session, timeout)
        print(session._sid)
        self.expires += 1


class Agent(protocol.AgentEndPoint):

    @protocol.handle(StatusMethod.get_agent_status)
    @gen.coroutine
    def get_agent_status(self, id):
        return 200, {"status": "ok", "agents": self.end_point_names}


def test_2way_protocol(free_port, logs=False):

    from inmanta.config import Config

    import inmanta.agent.config  # nopep8
    import inmanta.server.config  # nopep8

    if logs:
        # set logging to sensible defaults
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s %(green)s%(name)s %(blue)s%(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            }
        )

        stream = logging.StreamHandler()
        stream.setLevel(logging.DEBUG)

        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            stream.setFormatter(formatter)

        logging.root.handlers = []
        logging.root.addHandler(stream)
        logging.root.setLevel(logging.DEBUG)

    Config.load_config()
    Config.set("server_rest_transport", "port", free_port)
    Config.set("agent_rest_transport", "port", free_port)
    Config.set("compiler_rest_transport", "port", free_port)
    Config.set("client_rest_transport", "port", free_port)
    Config.set("cmdline_rest_transport", "port", free_port)

    io_loop = IOLoop.current()
    server = Server("server", io_loop)
    server.start()

    agent = Agent("agent", io_loop)
    agent.add_end_point_name("agent")
    agent.set_environment(uuid.uuid4())
    agent.start()

    @gen.coroutine
    def do_call():
        client = protocol.Client("client")
        status = yield client.get_status_x(str(agent.environment))
        assert status.code == 200
        assert "agents" in status.result
        assert len(status.result["agents"]) == 1
        assert status.result["agents"][0]["status"], "ok"
        server.stop()
        io_loop.stop()

    io_loop.add_callback(do_call)
    io_loop.add_timeout(io_loop.time() + 2, lambda: io_loop.stop())
    try:
        io_loop.start()
    except KeyboardInterrupt:
        io_loop.stop()
    server.stop()
    agent.stop()


@gen.coroutine
def check_sessions(sessions):
    for s in sessions:
        a = yield s.client.get_agent_status("X")
        assert a.get_result()['status'] == 'ok'


@pytest.mark.slowtest
def test_timeout(free_port):

    from inmanta.config import Config
    import inmanta.agent.config  # nopep8
    import inmanta.server.config  # nopep8

    io_loop = IOLoop.current()

    # start server
    Config.load_config()
    Config.set("server_rest_transport", "port", free_port)
    Config.set("agent_rest_transport", "port", free_port)
    Config.set("compiler_rest_transport", "port", free_port)
    Config.set("client_rest_transport", "port", free_port)
    Config.set("cmdline_rest_transport", "port", free_port)
    server = Server("server", io_loop, interval=2)
    server.start()

    env = uuid.uuid4()

    # agent 1
    agent = Agent("agent", io_loop)
    agent.add_end_point_name("agent")
    agent.set_environment(env)
    agent.start()

    @gen.coroutine
    def do_call():
        # wait till up
        yield retry_limited(lambda: len(server._sessions) == 1, 0.1)
        assert len(server._sessions) == 1

        # agent 2
        agent2 = Agent("agent", io_loop)
        agent2.add_end_point_name("agent")
        agent2.set_environment(env)
        agent2.start()

        # wait till up
        yield retry_limited(lambda: len(server._sessions) == 2, 0.1)
        assert len(server._sessions) == 2

        # see if it stays up
        yield(check_sessions(server._sessions.values()))
        yield sleep(2)
        assert len(server._sessions) == 2
        yield(check_sessions(server._sessions.values()))

        # take it down
        agent2.stop()

        # timout
        yield sleep(2)
        # check if down
        assert len(server._sessions) == 1
        print(server._sessions)
        yield(check_sessions(server._sessions.values()))
        assert server.expires == 1
        agent.stop()
        server.stop()

        io_loop.stop()

    io_loop.add_callback(do_call)
    io_loop.add_timeout(io_loop.time() + 2, lambda: io_loop.stop())
    try:
        io_loop.start()
    except KeyboardInterrupt:
        io_loop.stop()
    server.stop()
    agent.stop()
