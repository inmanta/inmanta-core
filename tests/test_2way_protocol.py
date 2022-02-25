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
import uuid
from typing import Set

import pytest
from pytest import fixture
from tornado.gen import sleep

# Methods need to be defined before the Client class is loaded by Python
from inmanta import protocol  # NOQA
from inmanta import data
from inmanta.protocol import method
from inmanta.protocol.methods import ENV_OPTS
from inmanta.server import SLICE_SESSION_MANAGER
from inmanta.server.protocol import Server, ServerSlice, SessionListener
from utils import configure, retry_limited

LOGGER = logging.getLogger(__name__)


@method(path="/status", operation="GET")
def get_status_x(tid: uuid.UUID):
    pass


@method(path="/status/<id>", operation="GET", server_agent=True, timeout=10)
def get_agent_status_x(id: str):
    pass


class SessionSpy(SessionListener, ServerSlice):
    def __init__(self):
        ServerSlice.__init__(self, "sessionspy")
        self.expires = 0
        self.__sessions = []

    async def new_session(self, session, endpoint_names_snapshot: Set[str]):
        self.__sessions.append(session)

    @protocol.handle(get_status_x)
    async def get_status_x(self, tid):
        status_list = []
        for session in self.__sessions:
            client = session.get_client()
            status = await client.get_agent_status_x("x")
            if status is not None and status.code == 200:
                status_list.append(status.result)

        return 200, {"agents": status_list}

    async def expire(self, session, endpoint_names_snapshot: Set[str]):
        self.__sessions.remove(session)
        print(session._sid)
        self.expires += 1

    def get_sessions(self):
        return self.__sessions


class Agent(protocol.SessionEndpoint):
    def __init__(self, name: str, timeout: int = 120, reconnect_delay: int = 5):
        super(Agent, self).__init__(name, timeout, reconnect_delay)
        self.reconnect = 0
        self.disconnect = 0

    @protocol.handle(get_agent_status_x)
    async def get_agent_status_x(self, id):
        return 200, {"status": "ok", "agents": list(self.end_point_names)}

    async def on_reconnect(self) -> None:
        self.reconnect += 1

    async def on_disconnect(self) -> None:
        self.disconnect += 1


async def get_environment(env: uuid.UUID, metadata: dict):
    return data.Environment(from_postgres=True, id=env, name="test", project=env, repo_url="xx", repo_branch="xx")


@fixture
def no_tid_check():
    # Disable validation of envs
    old_get_env = ENV_OPTS["tid"].getter
    ENV_OPTS["tid"].getter = get_environment
    yield
    ENV_OPTS["tid"].getter = old_get_env


async def assert_agent_counter(agent: Agent, reconnect: int, disconnected: int) -> None:
    def is_same():
        return agent.disconnect == disconnected and agent.reconnect == reconnect

    await retry_limited(is_same, 10)


async def test_2way_protocol(unused_tcp_port, no_tid_check, postgres_db, database_name):
    configure(unused_tcp_port, database_name, postgres_db.port)

    rs = Server()
    server = SessionSpy()
    rs.get_slice(SLICE_SESSION_MANAGER).add_listener(server)
    rs.add_slice(server)
    await rs.start()

    agent = Agent("agent")
    await agent.add_end_point_name("agent")
    agent.set_environment(uuid.uuid4())
    await agent.start()

    await retry_limited(lambda: len(server.get_sessions()) == 1, 10)
    assert len(server.get_sessions()) == 1
    await assert_agent_counter(agent, 1, 0)

    client = protocol.Client("client")
    status = await client.get_status_x(str(agent.environment))
    assert status.code == 200
    assert "agents" in status.result
    assert len(status.result["agents"]) == 1
    assert status.result["agents"][0]["status"], "ok"
    await server.stop()

    await rs.stop()
    await agent.stop()
    await assert_agent_counter(agent, 1, 0)


async def check_sessions(sessions):
    for s in sessions:
        a = await s.client.get_agent_status_x("X")
        result = a.get_result()
        assert result["status"] == "ok", result


@pytest.mark.slowtest
async def test_agent_timeout(unused_tcp_port, no_tid_check, async_finalizer, postgres_db, database_name):
    from inmanta.config import Config

    configure(unused_tcp_port, database_name, postgres_db.port)

    Config.set("server", "agent-timeout", "1")

    rs = Server()
    server = SessionSpy()
    rs.get_slice(SLICE_SESSION_MANAGER).add_listener(server)
    rs.add_slice(server)
    await rs.start()
    async_finalizer(rs.stop)

    env = uuid.uuid4()

    # agent 1
    agent = Agent("agent")
    await agent.add_end_point_name("agent")
    agent.set_environment(env)
    await agent.start()
    async_finalizer(agent.stop)

    # wait till up
    await retry_limited(lambda: len(server.get_sessions()) == 1, timeout=10)
    assert len(server.get_sessions()) == 1
    await assert_agent_counter(agent, 1, 0)

    # agent 2
    agent2 = Agent("agent")
    await agent2.add_end_point_name("agent")
    agent2.set_environment(env)
    await agent2.start()
    async_finalizer(agent2.stop)

    # wait till up
    await retry_limited(lambda: len(server.get_sessions()) == 2, timeout=10)
    assert len(server.get_sessions()) == 2
    await assert_agent_counter(agent, 1, 0)
    await assert_agent_counter(agent2, 1, 0)

    # see if it stays up
    await check_sessions(server.get_sessions())
    await sleep(1.1)
    assert len(server.get_sessions()) == 2
    await check_sessions(server.get_sessions())

    # take it down
    await agent2.stop()

    # Timeout=2
    # -> 1sec: Wait for agent-timeout
    # -> 1sec: Wait until session bookkeeping is updated
    await retry_limited(lambda: len(server.get_sessions()) == 1, timeout=2)
    print(server.get_sessions())
    await check_sessions(server.get_sessions())
    assert server.expires == 1
    await assert_agent_counter(agent, 1, 0)
    await assert_agent_counter(agent2, 1, 0)


@pytest.mark.slowtest
async def test_server_timeout(unused_tcp_port, no_tid_check, async_finalizer, postgres_db, database_name):
    from inmanta.config import Config

    configure(unused_tcp_port, database_name, postgres_db.port)

    Config.set("server", "agent-timeout", "1")

    async def start_server():
        rs = Server()
        server = SessionSpy()
        rs.get_slice(SLICE_SESSION_MANAGER).add_listener(server)
        rs.add_slice(server)
        await rs.start()
        async_finalizer(rs.stop)
        return server, rs

    server, rs = await start_server()

    env = uuid.uuid4()

    # agent 1
    agent = Agent("agent")
    await agent.add_end_point_name("agent")
    agent.set_environment(env)
    await agent.start()
    async_finalizer(agent.stop)

    # wait till up
    await retry_limited(lambda: len(server.get_sessions()) == 1, 10)
    assert len(server.get_sessions()) == 1

    await assert_agent_counter(agent, 1, 0)

    await rs.stop()

    # timeout
    await sleep(1.1)

    # check agent disconnected
    await assert_agent_counter(agent, 1, 1)

    # recover
    server, rs = await start_server()
    await retry_limited(lambda: len(server.get_sessions()) == 1, 10)
    assert len(server.get_sessions()) == 1

    await assert_agent_counter(agent, 2, 1)
