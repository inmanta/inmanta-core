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
from inmanta.config import Config
from tornado import gen
from tornado.ioloop import IOLoop
from nose.tools import assert_equal, assert_in, assert_true

LOGGER = logging.getLogger(__name__)


class StatusMethod(methods.Method):
    __method_name__ = "status"

    @methods.protocol(operation="GET", index=True, mt=True)
    def get_status(self, tid: uuid.UUID):
        pass

    @methods.protocol(operation="GET", id=True)
    def get_agent_status(self, id):
        pass


# Methods need to be defined before the Client class is loaded by Python
from inmanta import protocol  # NOQA


class TestServer(protocol.ServerEndpoint):
    @protocol.handle(StatusMethod.get_status)
    @gen.coroutine
    def get_status(self, tid):
        status_list = []
        for agent in self.get_agents(tid):
            client = self.get_agent_client(tid, agent)
            status = yield client.get_agent_status(agent)
            if status is not None and status.code == 200:
                status_list.append(status.result)

        return 200, {"agents": status_list}


class TestAgent(protocol.AgentEndPoint):
    @protocol.handle(StatusMethod.get_agent_status)
    @gen.coroutine
    def get_agent_status(self, id):
        return 200, {"status": "ok", "agents": self.end_point_names}


def test_2way_protocol(logs=False):
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

    io_loop = IOLoop.current()
    Config.load_config()
    server = TestServer("server", io_loop)
    server.start()

    agent = TestAgent("agent", io_loop)
    agent.add_end_point_name("agent")
    agent.set_environment(uuid.uuid4())
    agent.start()

    @gen.coroutine
    def do_call():
        client = protocol.Client("client")
        status = yield client.get_status(str(agent.environment))
        assert_equal(status.code, 200)
        assert_in("agents", status.result)
        assert_true(len(status.result["agents"]), 1)
        assert_equal(status.result["agents"][0]["status"], "ok")

        io_loop.stop()

    io_loop.add_callback(do_call)
    io_loop.add_timeout(io_loop.time() + 2, lambda: io_loop.stop())
    try:
        io_loop.start()
    except KeyboardInterrupt:
        io_loop.stop()


if __name__ == "__main__":
    test_2way_protocol(logs=True)
