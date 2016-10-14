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
from unittest.mock import Mock
from uuid import uuid4, UUID

import pytest
from inmanta.server.agentmanager import AgentManager
from inmanta.data import Environment, Agent
from tornado import gen
from inmanta.protocol import Result


class Collector():

    def __init__(self):
        self.values = []

    def __call__(self, arg):
        self.values.append(arg)

    @gen.coroutine
    def proccess(self):
        while len(self.values) > 0:
            x = self.values
            self.values = []
            yield x


@gen.coroutine
def emptyFuture(*args):
    pass


class MockSession(object):
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
def test_primary_selection(motorengine):

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

    # one session
    ts1 = MockSession(uuid4(), env.uuid, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True, 0)
    ts1.get_client().reset_mock()
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    yield futures.proccess()
    assert len(am.sessions) == 1
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = MockSession(uuid4(), env.uuid, ["agent3", "agent2"], "ts2")
    am.new_session(ts2)
    yield futures.proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # expire first
    am.expire(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    # expire second
    am.expire(ts2)
    yield futures.proccess()
    assert len(am.sessions) == 0
    yield assert_agents("paused", "down", "down")


UNKWN = object()


def assertEqualIsh(minimal, actual):
    if isinstance(minimal, dict):
        for k in minimal.keys():
            assertEqualIsh(minimal[k], actual[k])
    elif isinstance(minimal, list):
        assert len(minimal) == len(actual)
        for (m, a) in zip(minimal, actual):
            assertEqualIsh(m, a)
    elif minimal is UNKWN:
        return
    else:
        assert minimal == actual


@pytest.mark.gen_test(timeout=30)
def test_API(motorengine):
    env = Environment(uuid=uuid4(), name="testenv", project_id=uuid4())
    env = yield env.save()
    env2 = Environment(uuid=uuid4(), name="testenv2", project_id=uuid4())
    env2 = yield env2.save()
    yield Agent(environment=env, name="agent1", paused=True).save()
    yield Agent(environment=env, name="agent2", paused=False).save()
    yield Agent(environment=env, name="agent3", paused=False).save()
    yield Agent(environment=env2, name="agent4", paused=False).save()

    server = Mock()
    futures = Collector()
    server.add_future.side_effect = futures
    am = AgentManager(server, False)

    # one session
    ts1 = MockSession(uuid4(), env.uuid, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    # second session
    ts2 = MockSession(uuid4(), env.uuid, ["agent3", "agent2"], "ts2")
    am.new_session(ts2)
    yield futures.proccess()
    assert len(am.sessions) == 2

    code, all_agents = yield am.list_agent_processes(None)
    assert code == 200

    shouldbe = {'processes': [{'id': UNKWN, 'first_seen': UNKWN, 'expired': None, 'hostname': 'ts1',
                               'last_seen': UNKWN, 'endpoints': ['agent1', 'agent2'], 'environment': str(env.uuid)},
                              {'id': UNKWN, 'first_seen': UNKWN, 'expired': None, 'hostname': 'ts2',
                               'last_seen': UNKWN, 'endpoints': ['agent3', 'agent2'], 'environment': str(env.uuid)}]}

    assertEqualIsh(shouldbe, all_agents)
    agentid = all_agents['processes'][0]['id']

    code, all_agents = yield am.list_agent_processes(env.uuid)
    assert code == 200

    shouldbe = {'processes': [{'id': UNKWN, 'first_seen': UNKWN, 'expired': None, 'hostname': 'ts1',
                               'last_seen': UNKWN, 'endpoints': ['agent1', 'agent2'], 'environment': str(env.uuid)},
                              {'id': UNKWN, 'first_seen': UNKWN, 'expired': None, 'hostname': 'ts2',
                               'last_seen': UNKWN, 'endpoints': ['agent3', 'agent2'], 'environment': str(env.uuid)}]}

    assertEqualIsh(shouldbe, all_agents)

    code, all_agents = yield am.list_agent_processes(env2.uuid)
    assert code == 200

    shouldbe = {'processes': []}

    assertEqualIsh(shouldbe, all_agents)

    @gen.coroutine
    def dummy_status():
        return Result(False, 200, "X")

    ts1.get_client().get_status.side_effect = dummy_status
    report = yield am.get_agent_process_report(agentid)
    assert (200, "X") == report

    report = yield am.get_agent_process_report(uuid4())
    assert 404 == report[0]


@pytest.mark.gen_test(timeout=30)
def test_DB_Clean(motorengine):
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

    # one session
    ts1 = MockSession(uuid4(), env.uuid, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True, 0)
    ts1.get_client().reset_mock()
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    yield futures.proccess()
    assert len(am.sessions) == 1
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = MockSession(uuid4(), env.uuid, ["agent3", "agent2"], "ts2")
    am.new_session(ts2)
    yield futures.proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # expire first
    am.expire(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    # failover
    am = AgentManager(server, False)
    yield am.clean_db()

    # one session
    ts1 = MockSession(uuid4(), env.uuid, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True, 0)
    ts1.get_client().reset_mock()
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    yield futures.proccess()
    assert len(am.sessions) == 1
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = MockSession(uuid4(), env.uuid, ["agent3", "agent2"], "ts2")
    am.new_session(ts2)
    yield futures.proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # expire first
    am.expire(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True, 0)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    # expire second
    am.expire(ts2)
    yield futures.proccess()
    assert len(am.sessions) == 0
    yield assert_agents("paused", "down", "down")
