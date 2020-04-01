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
import asyncio
import datetime
import typing
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from inmanta import data
from inmanta.agent import Agent
from inmanta.protocol import Result
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.server.agentmanager import AgentManager, SessionManager
from inmanta.server.protocol import Session
from utils import UNKWN, assert_equal_ish, retry_limited


class Collector(object):
    def __init__(self):
        self.values = []

    def __call__(self, arg):
        self.values.append(arg)

    async def proccess(self):
        while len(self.values) > 0:
            x = self.values
            self.values = []
            await asyncio.gather(*x)


async def empty_future(*args, **kwargs):
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


@pytest.mark.asyncio(timeout=30)
async def test_primary_selection(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="testenv", project=project.id)
    await env.insert()

    await data.Agent(environment=env.id, name="agent1", paused=True).insert()
    await data.Agent(environment=env.id, name="agent2", paused=False).insert()
    await data.Agent(environment=env.id, name="agent3", paused=False).insert()

    server = Mock()
    futures = Collector()
    server.add_background_task.side_effect = futures
    am = AgentManager(server, False)
    am.add_background_task = futures
    am.running = True

    async def assert_agent(name: str, state: str, sid: UUID):
        agent = await data.Agent.get(env.id, name)

        assert agent.get_status() == state
        if state == "paused":
            assert agent.primary is None
            assert agent.paused
        elif state == "down":
            assert agent.primary is None
            assert not agent.paused
        elif state == "up":
            assert agent.primary is not None
            agent_instance = await data.AgentInstance.get_by_id(agent.primary)
            agent_proc = await data.AgentProcess.get_one(sid=agent_instance.process)
            assert agent_proc.sid == sid
            assert agent.get_status() == "up"

    async def assert_agents(s1, s2, s3, sid1=None, sid2=None, sid3=None):
        await assert_agent("agent1", s1, sid1)
        await assert_agent("agent2", s2, sid2)
        await assert_agent("agent3", s3, sid3)

    # one session
    ts1 = MockSession(uuid4(), env.id, ["agent1", "agent2"], "ts1")
    await am.new_session(ts1)
    await futures.proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True)
    ts1.get_client().reset_mock()
    await assert_agents("paused", "up", "down", sid2=ts1.id)

    # test is_primary
    assert am.is_primary(env, ts1.id, "agent2")
    assert not am.is_primary(env, ts1.id, "agent1")
    assert not am.is_primary(env, uuid4(), "agent2")

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    await futures.proccess()
    assert len(am.sessions) == 1
    await assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = MockSession(uuid4(), env.id, ["agent3", "agent2"], "ts2")
    await am.new_session(ts2)
    await futures.proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True)
    ts2.get_client().reset_mock()
    await assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # test is_primary
    assert not am.is_primary(env, ts2.id, "agent1")
    assert not am.is_primary(env, ts1.id, "agent1")
    assert am.is_primary(env, ts1.id, "agent2")
    assert am.is_primary(env, ts2.id, "agent3")

    # expire first
    am.expire(ts1, 100)
    await futures.proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True)
    ts2.get_client().reset_mock()
    await assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    # expire second
    am.expire(ts2, 100)
    await futures.proccess()
    assert len(am.sessions) == 0
    await assert_agents("paused", "down", "down")

    # test is_primary
    assert not am.is_primary(env, ts1.id, "agent2")
    assert not am.is_primary(env, ts2.id, "agent3")


@pytest.mark.asyncio(timeout=30)
async def test_api(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="testenv", project=project.id)
    await env.insert()
    env2 = data.Environment(name="testenv2", project=project.id)
    await env2.insert()
    env3 = data.Environment(name="testenv3", project=project.id)
    await env3.insert()
    await data.Agent(environment=env.id, name="agent1", paused=True).insert()
    await data.Agent(environment=env.id, name="agent2", paused=False).insert()
    await data.Agent(environment=env.id, name="agent3", paused=False).insert()
    await data.Agent(environment=env2.id, name="agent4", paused=False).insert()

    server = Mock()
    futures = Collector()
    server.add_background_task.side_effect = futures
    am = AgentManager(server, False)
    am.add_background_task = futures
    am.running = True

    # one session
    ts1 = MockSession(uuid4(), env.id, ["agent1", "agent2"], "ts1")
    await am.new_session(ts1)
    # second session
    ts2 = MockSession(uuid4(), env.id, ["agent3", "agent2"], "ts2")
    await am.new_session(ts2)
    # third session
    ts3 = MockSession(uuid4(), env3.id, ["agentx"], "ts3")
    await am.new_session(ts3)

    await futures.proccess()
    assert len(am.sessions) == 3

    code, all_agents = await am.list_agent_processes(None, None)
    assert code == 200

    shouldbe = {
        "processes": [
            {
                "first_seen": UNKWN,
                "expired": None,
                "hostname": "ts1",
                "last_seen": UNKWN,
                "endpoints": [
                    {"id": UNKWN, "name": "agent1", "process": UNKWN},
                    {"id": UNKWN, "name": "agent2", "process": UNKWN},
                ],
                "environment": env.id,
            },
            {
                "first_seen": UNKWN,
                "expired": None,
                "hostname": "ts2",
                "last_seen": UNKWN,
                "endpoints": [
                    {"id": UNKWN, "name": "agent2", "process": UNKWN},
                    {"id": UNKWN, "name": "agent3", "process": UNKWN},
                ],
                "environment": env.id,
            },
            {
                "first_seen": UNKWN,
                "expired": None,
                "hostname": "ts3",
                "last_seen": UNKWN,
                "endpoints": [{"id": UNKWN, "name": "agentx", "process": UNKWN}],
                "environment": env3.id,
            },
        ]
    }

    assert_equal_ish(shouldbe, all_agents, sortby=["hostname", "name"])
    agentid = all_agents["processes"][0]["sid"]

    code, all_agents = await am.list_agent_processes(env.id, None)
    assert code == 200

    shouldbe = {
        "processes": [
            {
                "first_seen": UNKWN,
                "expired": None,
                "hostname": "ts1",
                "last_seen": UNKWN,
                "endpoints": [
                    {"id": UNKWN, "name": "agent1", "process": UNKWN},
                    {"id": UNKWN, "name": "agent2", "process": UNKWN},
                ],
                "environment": env.id,
            },
            {
                "first_seen": UNKWN,
                "expired": None,
                "hostname": "ts2",
                "last_seen": UNKWN,
                "endpoints": [
                    {"id": UNKWN, "name": "agent2", "process": UNKWN},
                    {"id": UNKWN, "name": "agent3", "process": UNKWN},
                ],
                "environment": env.id,
            },
        ]
    }

    assert_equal_ish(shouldbe, all_agents, sortby=["hostname", "name"])

    code, all_agents = await am.list_agent_processes(env2.id, None)
    assert code == 200

    shouldbe = {"processes": []}

    assert_equal_ish(shouldbe, all_agents)

    async def dummy_status():
        return Result(200, "X")

    ts1.get_client().get_status.side_effect = dummy_status
    report = await am.get_agent_process_report(agentid)
    assert (200, "X") == report

    report = await am.get_agent_process_report(uuid4())
    assert 404 == report[0]

    code, all_agents = await am.list_agents(None)
    assert code == 200
    shouldbe = {
        "agents": [
            {"name": "agent1", "paused": True, "last_failover": "", "primary": "", "environment": env.id, "state": "paused"},
            {"name": "agent2", "paused": False, "last_failover": UNKWN, "primary": UNKWN, "environment": env.id, "state": "up"},
            {"name": "agent3", "paused": False, "last_failover": UNKWN, "primary": UNKWN, "environment": env.id, "state": "up"},
            {"name": "agent4", "paused": False, "last_failover": "", "primary": "", "environment": env2.id, "state": "down"},
        ]
    }
    assert_equal_ish(shouldbe, all_agents, sortby=["name"])

    code, all_agents = await am.list_agents(env2)
    assert code == 200
    shouldbe = {
        "agents": [
            {"name": "agent4", "paused": False, "last_failover": "", "primary": "", "environment": env2.id, "state": "down"}
        ]
    }
    assert_equal_ish(shouldbe, all_agents)


@pytest.mark.asyncio(timeout=30)
async def test_expire_all_sessions_in_db(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="testenv", project=project.id)
    await env.insert()
    await data.Agent(environment=env.id, name="agent1", paused=True).insert()
    await data.Agent(environment=env.id, name="agent2", paused=False).insert()
    await data.Agent(environment=env.id, name="agent3", paused=False).insert()

    server = Mock()
    futures = Collector()
    server.add_background_task.side_effect = futures
    am = AgentManager(server, False)
    am.add_background_task = futures
    am.running = True

    async def assert_agent(name: str, state: str, sid: UUID):
        agent = await data.Agent.get(env.id, name)
        assert agent.get_status() == state
        if state == "paused":
            assert agent.primary is None
            assert agent.paused
        elif state == "down":
            assert agent.primary is None
            assert not agent.paused
        elif state == "up":
            assert agent.primary is not None
            agent_instance = await data.AgentInstance.get_by_id(agent.primary)
            agent_proc = await data.AgentProcess.get_one(sid=agent_instance.process)
            assert agent_proc.sid == sid
            assert agent.get_status() == "up"

    async def assert_agents(s1, s2, s3, sid1=None, sid2=None, sid3=None):
        await assert_agent("agent1", s1, sid1)
        await assert_agent("agent2", s2, sid2)
        await assert_agent("agent3", s3, sid3)

    # one session
    ts1 = MockSession(uuid4(), env.id, ["agent1", "agent2"], "ts1")
    await am.new_session(ts1)
    await futures.proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True)
    ts1.get_client().reset_mock()
    await assert_agents("paused", "up", "down", sid2=ts1.id)

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    await futures.proccess()
    assert len(am.sessions) == 1
    await assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = MockSession(uuid4(), env.id, ["agent3", "agent2"], "ts2")
    await am.new_session(ts2)
    await futures.proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True)
    ts2.get_client().reset_mock()
    await assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # expire first
    am.expire(ts1, 100)
    await futures.proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True)
    ts2.get_client().reset_mock()
    await assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    # failover
    am = AgentManager(server, False)
    am.add_background_task = futures
    am.running = True
    await am._expire_all_sessions_in_db()

    # one session
    ts1 = MockSession(uuid4(), env.id, ["agent1", "agent2"], "ts1")
    await am.new_session(ts1)
    await futures.proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", True)
    ts1.get_client().reset_mock()
    await assert_agents("paused", "up", "down", sid2=ts1.id)

    # alive
    am.seen(ts1, ["agent1", "agent2"])
    await futures.proccess()
    assert len(am.sessions) == 1
    await assert_agents("paused", "up", "down", sid2=ts1.id)

    # second session
    ts2 = MockSession(uuid4(), env.id, ["agent3", "agent2"], "ts2")
    await am.new_session(ts2)
    await futures.proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", True)
    ts2.get_client().reset_mock()
    await assert_agents("paused", "up", "up", sid2=ts1.id, sid3=ts2.id)

    # expire first
    am.expire(ts1, 100)
    await futures.proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", True)
    ts2.get_client().reset_mock()
    await assert_agents("paused", "up", "up", sid2=ts2.id, sid3=ts2.id)

    # expire second
    am.expire(ts2, 100)
    await futures.proccess()
    assert len(am.sessions) == 0
    await assert_agents("paused", "down", "down")


async def assert_agent_db_state(
    tid: UUID, sid: UUID, endpoint: str, nr_procs: int, nr_live_procs: int, nr_agent_instances: int, nr_live_instances: int
) -> typing.Callable:
    """
        The database log is updated asynchronously. This method waits until
        the desired database state is reached.
    """

    async def is_db_state_reached():
        result = await data.AgentProcess.get_list(sid=sid)
        if len(result) != nr_procs:
            return False
        result = await data.AgentProcess.get_live(environment=tid)
        if len(result) != nr_live_procs:
            return False
        result = await data.AgentInstance.get_list(tid=tid)
        if len(result) != nr_agent_instances:
            return False
        result = await data.AgentInstance.active_for(tid=tid, endpoint=endpoint)
        if len(result) != nr_live_instances:
            return False
        return True

    await retry_limited(is_db_state_reached, 10)


@pytest.mark.asyncio
async def test_session_renewal(init_dataclasses_and_load_schema):
    """
        Agent got timeout but agent process was still running (e.g, network connectivity was disrupted).
        So the same agent process connects to the server with the same session id. This test verifies
        that the database state is updated correctly when an expired session is renewed.
    """
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="testenv", project=project.id)
    await env.insert()

    agent_manager = AgentManager()
    agent_manager._stopped = False
    agent_manager._stopping = False

    session_manager = SessionManager()
    sid = uuid4()
    tid = env.id
    endpoint = "vm1"
    session = Session(
        sessionstore=session_manager, sid=sid, hang_interval=1, timout=1, tid=tid, endpoint_names=[endpoint], nodename="test"
    )

    await assert_agent_db_state(tid, sid, endpoint, nr_procs=0, nr_live_procs=0, nr_agent_instances=0, nr_live_instances=0)
    await agent_manager._register_session(session=session, now=datetime.datetime.now())
    await assert_agent_db_state(tid, sid, endpoint, nr_procs=1, nr_live_procs=1, nr_agent_instances=1, nr_live_instances=1)
    await agent_manager._expire_session(session=session, now=datetime.datetime.now())
    await assert_agent_db_state(tid, sid, endpoint, nr_procs=1, nr_live_procs=0, nr_agent_instances=1, nr_live_instances=0)
    await agent_manager._register_session(session=session, now=datetime.datetime.now())
    await assert_agent_db_state(tid, sid, endpoint, nr_procs=1, nr_live_procs=1, nr_agent_instances=2, nr_live_instances=1)


@pytest.mark.asyncio
async def test_fix_corrupted_database(init_dataclasses_and_load_schema):
    """
        When the database connection is lost, the agent session information might get
        corrupted. This inconsistency should be fixed when a new session is registered.
        This test case verifies this behavior.
    """
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="testenv", project=project.id)
    await env.insert()

    agent_manager = AgentManager()
    agent_manager._stopped = False
    agent_manager._stopping = False

    session_manager = SessionManager()
    sid = uuid4()
    tid = env.id
    endpoint = "vm1"
    session = Session(
        sessionstore=session_manager, sid=sid, hang_interval=1, timout=1, tid=tid, endpoint_names=[endpoint], nodename="test"
    )

    await assert_agent_db_state(tid, sid, endpoint, nr_procs=0, nr_live_procs=0, nr_agent_instances=0, nr_live_instances=0)
    await agent_manager._register_session(session=session, now=datetime.datetime.now())
    await assert_agent_db_state(tid, sid, endpoint, nr_procs=1, nr_live_procs=1, nr_agent_instances=1, nr_live_instances=1)
    await agent_manager._expire_session(session=session, now=datetime.datetime.now())
    await assert_agent_db_state(tid, sid, endpoint, nr_procs=1, nr_live_procs=0, nr_agent_instances=1, nr_live_instances=0)

    # Make database corrupt
    instances = await data.AgentInstance.get_list(tid=tid, process=sid)
    assert len(instances) == 1
    instance = instances[0]
    await instance.update(expired=None)
    # Assert corruption
    await assert_agent_db_state(tid, sid, endpoint, nr_procs=1, nr_live_procs=0, nr_agent_instances=1, nr_live_instances=1)

    # Session registration should fix the inconsistency
    await agent_manager._register_session(session=session, now=datetime.datetime.now())
    await assert_agent_db_state(tid, sid, endpoint, nr_procs=1, nr_live_procs=1, nr_agent_instances=2, nr_live_instances=1)
    instance = await data.AgentInstance.get_by_id(instance.id)
    assert instance.expired is not None


@pytest.mark.asyncio
async def test_session_creation_fails(server, environment, caplog):
    """
        Verify that:
         * Session creation works correctly when the connectivity to the database works.
         * Session creation is refused when the connectivity to the database doesn't work.
           In that case the server state should stay consistent.
    """
    env_id = UUID(environment)
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    a = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    a.add_end_point_name("agent1")
    await a.start()

    # Wait until session is created
    await retry_limited(lambda: (env_id, "agent1") in agentmanager.tid_endpoint_to_session, 10)

    # Verify that the session is created correctly
    session = agentmanager.tid_endpoint_to_session[(env_id, "agent1")]
    session_manager = session._sessionstore
    assert len(agentmanager.sessions) == 1
    assert session in agentmanager.sessions.values()
    assert len(session_manager._sessions) == 1
    assert session in session_manager._sessions.values()
    assert "Heartbeat failed" not in caplog.text

    await a.stop()
    session.expire(0)

    # Wait until session expired
    await retry_limited(lambda: len(agentmanager.tid_endpoint_to_session) == 0, 10)

    # Verify session expiration
    assert len(agentmanager.sessions) == 0
    assert len(agentmanager.tid_endpoint_to_session) == 0
    assert len(session_manager._sessions) == 0

    # Remove connectivity to the database
    await data.disconnect()
    caplog.clear()

    a = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    a.add_end_point_name("agent1")
    await a.start()

    # Verify that session creation fails and server state is stays consistent
    await retry_limited(lambda: "Heartbeat failed" in caplog.text, 10)
    assert len(agentmanager.sessions) == 0
    assert len(agentmanager.tid_endpoint_to_session) == 0
    assert len(session_manager._sessions) == 0
