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

import time

from utils import retry_limited
from tornado.gen import sleep
import pytest
from unittest.mock import Mock
from inmanta.server.agentmanager import AgentManager
from datetime import date, datetime
from uuid import uuid4, UUID
from motorengine.connection import connect, disconnect
from conftest import DEFAULT_PORT_ENVVAR
from inmanta.data import Environment, Agent
from tornado import gen


class Collector():

    def __init__(self):
        self.values = []

    def __call__(self, arg):
        self.values.append(arg)


@gen.coroutine
def emptyFuture(*args):
    pass


class TestSession(object):
    """
        An environment that segments agents connected to the server
    """

    def __init__(self, sid, tid, endpoint_names, nodename):
        self._sid = sid
        self.tid = tid
        self.endpoint_names = endpoint_names
        self.nodename = nodename
        self.client = Mock()
        self.client.set_state.side_effect = emptyFuture

    def get_id(self):
        return self._sid

    id = property(get_id)

    def get_client(self):
        return self.client


@pytest.mark.gen_test(timeout=30)
def test_primary_selection(mongo_db):
    connect("test_inmanta", host="127.0.0.1", port=mongo_db.port)

    env = Environment(uuid=uuid4(), name="testenv", project_id=uuid4())
    env = yield env.save()
    yield Agent(environment=env, name="agent1", paused=True).save()
    yield Agent(environment=env, name="agent2", paused=False).save()
    yield Agent(environment=env, name="agent3", paused=False).save()

    server = Mock()
    futures = Collector()
    server.add_future.side_effect = futures
    am = AgentManager(server, False)

    @gen.coroutine
    def assert_agent(name: str, state: str, sid: UUID):
        agent = yield Agent.get(env, name)
        yield agent.load_references()
        assert agent.get_status() == state
        if state == "paused":
            assert agent.primary is None
            assert agent.paused
        elif state == "down":
            assert agent.primary is None
            assert not agent.paused
        elif state == "up":
            assert agent.primary is not None
            yield agent.primary.load_references()
            assert agent.primary.process.sid == sid
            assert agent.get_status() == "up"

    @gen.coroutine
    def assert_agents(s1, s2, s3, sid1=None, sid2=None, sid3=None):
        yield assert_agent("agent1", s1, sid1)
        yield assert_agent("agent2", s2, sid2)
        yield assert_agent("agent3", s3, sid3)

    @gen.coroutine
    def proccess():
        while len(futures.values) > 0:
            x = futures.values
            futures.values = []
            yield x

    # one session
    ts1 = TestSession(uuid4(), env.uuid, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    yield proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True, 0)
    ts1.get_client().reset_mock()
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    yield proccess()
    assert len(am.sessions) == 1
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = TestSession(uuid4(), env.uuid, ["agent3", "agent2"], "ts2")
    am.new_session(ts2)
    yield proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # expire first
    am.expire(ts1)
    yield proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    # expire second
    am.expire(ts2)
    yield proccess()
    assert len(am.sessions) == 0
    yield assert_agents("paused", "down", "down")
    disconnect()


@pytest.mark.gen_test(timeout=30)
def test_DB_Clean(mongo_db):
    connect("test_inmanta", host="127.0.0.1", port=mongo_db.port)

    env = Environment(uuid=uuid4(), name="testenv", project_id=uuid4())
    env = yield env.save()
    yield Agent(environment=env, name="agent1", paused=True).save()
    yield Agent(environment=env, name="agent2", paused=False).save()
    yield Agent(environment=env, name="agent3", paused=False).save()

    server = Mock()
    futures = Collector()
    server.add_future.side_effect = futures
    am = AgentManager(server, False)

    @gen.coroutine
    def assert_agent(name: str, state: str, sid: UUID):
        agent = yield Agent.get(env, name)
        yield agent.load_references()
        assert agent.get_status() == state
        if state == "paused":
            assert agent.primary is None
            assert agent.paused
        elif state == "down":
            assert agent.primary is None
            assert not agent.paused
        elif state == "up":
            assert agent.primary is not None
            yield agent.primary.load_references()
            assert agent.primary.process.sid == sid
            assert agent.get_status() == "up"

    @gen.coroutine
    def assert_agents(s1, s2, s3, sid1=None, sid2=None, sid3=None):
        yield assert_agent("agent1", s1, sid1)
        yield assert_agent("agent2", s2, sid2)
        yield assert_agent("agent3", s3, sid3)

    @gen.coroutine
    def proccess():
        while len(futures.values) > 0:
            x = futures.values
            futures.values = []
            yield x

    # one session
    ts1 = TestSession(uuid4(), env.uuid, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    yield proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True, 0)
    ts1.get_client().reset_mock()
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    yield proccess()
    assert len(am.sessions) == 1
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = TestSession(uuid4(), env.uuid, ["agent3", "agent2"], "ts2")
    am.new_session(ts2)
    yield proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # expire first
    am.expire(ts1)
    yield proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    #failover
    am = AgentManager(server, False)
    yield am.clean_db()

    # one session
    ts1 = TestSession(uuid4(), env.uuid, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    yield proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True, 0)
    ts1.get_client().reset_mock()
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    yield proccess()
    assert len(am.sessions) == 1
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = TestSession(uuid4(), env.uuid, ["agent3", "agent2"], "ts2")
    am.new_session(ts2)
    yield proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # expire first
    am.expire(ts1)
    yield proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    # expire second
    am.expire(ts2)
    yield proccess()
    assert len(am.sessions) == 0
    yield assert_agents("paused", "down", "down")
    disconnect()
