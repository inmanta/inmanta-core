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
from inmanta import data
from tornado import gen
from inmanta.protocol import Result
from utils import assert_equal_ish, UNKWN


class Collector(object):

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
def empty_future(*args, **kwargs):
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
        self.client.set_state.side_effect = empty_future

    def get_id(self):
        return self._sid

    id = property(get_id)

    def get_client(self):
        return self.client


@pytest.mark.gen_test(timeout=30)
def test_primary_selection(motor):
    data.use_motor(motor)

    env = data.Environment(name="testenv", project=uuid4())
    yield env.insert()

    yield data.Agent(environment=env.id, name="agent1", paused=True).insert()
    yield data.Agent(environment=env.id, name="agent2", paused=False).insert()
    yield data.Agent(environment=env.id, name="agent3", paused=False).insert()

    server = Mock()
    futures = Collector()
    server.add_future.side_effect = futures
    am = AgentManager(server, False)

    @gen.coroutine
    def assert_agent(name: str, state: str, sid: UUID):
        agent = yield data.Agent.get(env.id, name)

        assert agent.get_status() == state
        if state == "paused":
            assert agent.primary is None
            assert agent.paused
        elif state == "down":
            assert agent.primary is None
            assert not agent.paused
        elif state == "up":
            assert agent.primary is not None
            agent_instance = yield data.AgentInstance.get_by_id(agent.primary)
            agent_proc = yield data.AgentProcess.get_by_id(agent_instance.process)
            assert agent_proc.sid == sid
            assert agent.get_status() == "up"

    @gen.coroutine
    def assert_agents(s1, s2, s3, sid1=None, sid2=None, sid3=None):
        yield assert_agent("agent1", s1, sid1)
        yield assert_agent("agent2", s2, sid2)
        yield assert_agent("agent3", s3, sid3)

    # one session
    ts1 = MockSession(uuid4(), env.id, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True)
    ts1.get_client().reset_mock()
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    yield futures.proccess()
    assert len(am.sessions) == 1
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = MockSession(uuid4(), env.id, ["agent3", "agent2"], "ts2")
    am.new_session(ts2)
    yield futures.proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # expire first
    am.expire(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    # expire second
    am.expire(ts2)
    yield futures.proccess()
    assert len(am.sessions) == 0
    yield assert_agents("paused", "down", "down")


@pytest.mark.gen_test(timeout=30)
def test_api(motor):
    data.use_motor(motor)

    env = data.Environment(name="testenv", project=uuid4())
    yield env.insert()
    env2 = data.Environment(name="testenv2", project=uuid4())
    yield env2.insert()
    yield data.Agent(environment=env.id, name="agent1", paused=True).insert()
    yield data.Agent(environment=env.id, name="agent2", paused=False).insert()
    yield data.Agent(environment=env.id, name="agent3", paused=False).insert()
    yield data.Agent(environment=env2.id, name="agent4", paused=False).insert()

    server = Mock()
    futures = Collector()
    server.add_future.side_effect = futures
    am = AgentManager(server, False)

    # one session
    ts1 = MockSession(uuid4(), env.id, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    # second session
    ts2 = MockSession(uuid4(), env.id, ["agent3", "agent2"], "ts2")
    am.new_session(ts2)
    # third session
    env3 = uuid4()
    ts3 = MockSession(uuid4(), env3, ["agentx"], "ts3")
    am.new_session(ts3)

    yield futures.proccess()
    assert len(am.sessions) == 3

    code, all_agents = yield am.list_agent_processes(None, None)
    assert code == 200

    shouldbe = {'processes': [{'id': UNKWN, 'first_seen': UNKWN, 'expired': None, 'hostname': 'ts1',
                               'last_seen': UNKWN, 'endpoints':
                               [{'id': UNKWN, 'name': 'agent1', 'process': UNKWN},
                                {'id': UNKWN, 'name': 'agent2', 'process': UNKWN}],
                               'environment': env.id},
                              {'id': UNKWN, 'first_seen': UNKWN, 'expired': None, 'hostname': 'ts2',
                               'last_seen': UNKWN, 'endpoints':
                               [{'id': UNKWN, 'name': 'agent2', 'process': UNKWN},
                                {'id': UNKWN, 'name': 'agent3', 'process': UNKWN}],
                               'environment': env.id},
                              {'id': UNKWN, 'first_seen': UNKWN, 'expired': None, 'hostname': 'ts3',
                               'last_seen': UNKWN, 'endpoints':
                               [{'id': UNKWN, 'name': 'agentx', 'process': UNKWN}],
                               'environment': env3}]}

    assert_equal_ish(shouldbe, all_agents, ['hostname', 'name'])
    agentid = all_agents['processes'][0]['id']

    code, all_agents = yield am.list_agent_processes(env.id, None)
    assert code == 200

    shouldbe = {'processes': [{'id': UNKWN, 'first_seen': UNKWN, 'expired': None, 'hostname': 'ts1',
                               'last_seen': UNKWN, 'endpoints':
                               [{'id': UNKWN, 'name': 'agent1', 'process': UNKWN},
                                {'id': UNKWN, 'name': 'agent2', 'process': UNKWN}],
                               'environment': env.id},
                              {'id': UNKWN, 'first_seen': UNKWN, 'expired': None, 'hostname': 'ts2',
                               'last_seen': UNKWN, 'endpoints':
                               [{'id': UNKWN, 'name': 'agent3', 'process': UNKWN},
                                {'id': UNKWN, 'name': 'agent2', 'process': UNKWN}],
                               'environment': env.id}]}

    assert_equal_ish(shouldbe, all_agents)

    code, all_agents = yield am.list_agent_processes(env2.id, None)
    assert code == 200

    shouldbe = {'processes': []}

    assert_equal_ish(shouldbe, all_agents)

    @gen.coroutine
    def dummy_status():
        return Result(False, 200, "X")

    ts1.get_client().get_status.side_effect = dummy_status
    report = yield am.get_agent_process_report(agentid)
    assert (200, "X") == report

    report = yield am.get_agent_process_report(uuid4())
    assert 404 == report[0]

    code, all_agents = yield am.list_agents(None)
    assert code == 200
    shouldbe = {'agents': [{'name': 'agent1', 'paused': True, 'last_failover': '', 'primary': '',
                            'environment': env.id, "state": "paused"},
                           {'name': 'agent2', 'paused': False, 'last_failover': UNKWN,
                               'primary': UNKWN, 'environment': env.id, "state": "up"},
                           {'name': 'agent3', 'paused': False, 'last_failover': UNKWN,
                               'primary': UNKWN, 'environment': env.id, "state": "up"},
                           {'name': 'agent4', 'paused': False, 'last_failover': '', 'primary': '',
                            'environment': env2.id, "state": "down"}]}
    assert_equal_ish(shouldbe, all_agents, ['name'])

    code, all_agents = yield am.list_agents(env2.id)
    assert code == 200
    shouldbe = {
        'agents': [{'name': 'agent4', 'paused': False, 'last_failover': '', 'primary': '',
                    'environment': env2.id, "state": "down"}]}
    assert_equal_ish(shouldbe, all_agents)


@pytest.mark.gen_test(timeout=30)
def test_db_clean(motor):
    data.use_motor(motor)

    env = data.Environment(name="testenv", project=uuid4())
    yield env.insert()
    yield data.Agent(environment=env.id, name="agent1", paused=True).insert()
    yield data.Agent(environment=env.id, name="agent2", paused=False).insert()
    yield data.Agent(environment=env.id, name="agent3", paused=False).insert()

    server = Mock()
    futures = Collector()
    server.add_future.side_effect = futures
    am = AgentManager(server, False)

    @gen.coroutine
    def assert_agent(name: str, state: str, sid: UUID):
        agent = yield data.Agent.get(env.id, name)
        assert agent.get_status() == state
        if state == "paused":
            assert agent.primary is None
            assert agent.paused
        elif state == "down":
            assert agent.primary is None
            assert not agent.paused
        elif state == "up":
            assert agent.primary is not None
            agent_instance = yield data.AgentInstance.get_by_id(agent.primary)
            agent_proc = yield data.AgentProcess.get_by_id(agent_instance.process)
            assert agent_proc.sid == sid
            assert agent.get_status() == "up"

    @gen.coroutine
    def assert_agents(s1, s2, s3, sid1=None, sid2=None, sid3=None):
        yield assert_agent("agent1", s1, sid1)
        yield assert_agent("agent2", s2, sid2)
        yield assert_agent("agent3", s3, sid3)

    # one session
    ts1 = MockSession(uuid4(), env.id, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True)
    ts1.get_client().reset_mock()
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    yield futures.proccess()
    assert len(am.sessions) == 1
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = MockSession(uuid4(), env.id, ["agent3", "agent2"], "ts2")
    am.new_session(ts2)
    yield futures.proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # expire first
    am.expire(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    # failover
    am = AgentManager(server, False)
    yield am.clean_db()

    # one session
    ts1 = MockSession(uuid4(), env.id, ["agent1", "agent2"], "ts1")
    am.new_session(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True)
    ts1.get_client().reset_mock()
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    yield futures.proccess()
    assert len(am.sessions) == 1
    yield assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = MockSession(uuid4(), env.id, ["agent3", "agent2"], "ts2")
    am.new_session(ts2)
    yield futures.proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # expire first
    am.expire(ts1)
    yield futures.proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True)
    ts2.get_client().reset_mock()
    yield assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    # expire second
    am.expire(ts2)
    yield futures.proccess()
    assert len(am.sessions) == 0
    yield assert_agents("paused", "down", "down")
