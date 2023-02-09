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
import logging
import typing
import uuid
from asyncio import subprocess
from typing import Dict, List, Optional, Set, Tuple
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from inmanta import config, data
from inmanta.agent import Agent, agent
from inmanta.agent import config as agent_config
from inmanta.const import AgentAction, AgentStatus
from inmanta.protocol import Result
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_AUTOSTARTED_AGENT_MANAGER
from inmanta.server.agentmanager import AgentManager, AutostartedAgentManager, SessionAction, SessionManager
from inmanta.server.protocol import Session
from utils import UNKWN, assert_equal_ish, retry_limited

LOGGER = logging.getLogger(__name__)


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


async def api_call_future(*args, **kwargs) -> Result:
    """
    Mock implementation of Client methods
    """
    return Result(200, "X")


class MockSession(object):
    """
    An environment that segments agents connected to the server
    """

    def __init__(self, sid, tid, endpoint_names: Set[str], nodename):
        self._sid = sid
        self.tid = tid
        self.endpoint_names = endpoint_names
        self.nodename = nodename
        self.client = Mock()
        self.client.set_state.side_effect = empty_future
        self.client.get_status = api_call_future

    def get_id(self):
        return self._sid

    id = property(get_id)

    def get_client(self):
        return self.client

    async def expire_and_abort(self, timeout: float):
        # Only called on teardown
        pass


async def assert_agent_state(env_id: UUID, name: str, state: AgentStatus, sid: Optional[UUID]) -> None:
    agent = await data.Agent.get(env_id, name)

    assert agent.get_status() == state
    if state == AgentStatus.paused:
        assert agent.primary is None
        assert agent.paused
    elif state == AgentStatus.down:
        assert agent.primary is None
        assert not agent.paused
    elif state == AgentStatus.up:
        assert agent.primary is not None
        agent_instance = await data.AgentInstance.get_by_id(agent.primary)
        agent_proc = await data.AgentProcess.get_one(sid=agent_instance.process)
        assert agent_proc.sid == sid
        assert agent.get_status() == AgentStatus.up


async def assert_state_agents(
    env_id: UUID,
    s1: AgentStatus,
    s2: AgentStatus,
    s3: AgentStatus,
    sid1: Optional[UUID] = None,
    sid2: Optional[UUID] = None,
    sid3: Optional[UUID] = None,
) -> None:
    await assert_agent_state(env_id, "agent1", s1, sid1)
    await assert_agent_state(env_id, "agent2", s2, sid2)
    await assert_agent_state(env_id, "agent3", s3, sid3)


def assert_state_agents_retry(
    env_id: UUID,
    s1: AgentStatus,
    s2: AgentStatus,
    s3: AgentStatus,
    sid1: Optional[UUID] = None,
    sid2: Optional[UUID] = None,
    sid3: Optional[UUID] = None,
) -> typing.Callable[[], None]:
    async def func() -> bool:
        try:
            await assert_state_agents(env_id, s1, s2, s3, sid1, sid2, sid3)
        except AssertionError:
            return False
        return True

    return func


async def test_primary_selection(server, environment):
    env_id = UUID(environment)
    env = await data.Environment.get_by_id(env_id)
    am = server.get_slice(SLICE_AGENT_MANAGER)

    # second env to detect crosstalk
    project = data.Project(name="test_x")
    await project.insert()
    env2 = data.Environment(name="testenv_x", project=project.id)
    await env2.insert()

    await data.Agent(environment=env.id, name="agent1", paused=True).insert()
    await data.Agent(environment=env.id, name="agent2", paused=False).insert()
    await data.Agent(environment=env.id, name="agent3", paused=False).insert()

    # one session
    ts1 = MockSession(uuid4(), env.id, {"agent1", "agent2"}, "ts1")
    await am.new_session(ts1, set(ts1.endpoint_names))
    await am._session_listener_actions.join()
    assert len(am.sessions) == 1

    # cross talk session
    ts2 = MockSession(uuid4(), env2.id, {"agent1", "agent2"}, "ts2")
    await am.new_session(ts2, set(ts2.endpoint_names))
    await am._session_listener_actions.join()
    assert len(am.sessions) == 2

    ts1.get_client().set_state.assert_called_with("agent2", enabled=True)
    ts1.get_client().reset_mock()
    await retry_limited(
        assert_state_agents_retry(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.down, sid2=ts1.id), 10
    )

    # test is_primary
    assert am.is_primary(env, ts1.id, "agent2")
    assert not am.is_primary(env, ts1.id, "agent1")
    assert not am.is_primary(env, uuid4(), "agent2")

    # alive
    await am.seen(ts1, set(ts1.endpoint_names))
    await am._session_listener_actions.join()
    assert len(am.sessions) == 2
    await retry_limited(
        assert_state_agents_retry(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.down, sid2=ts1.id), 10
    )

    # second session
    ts2 = MockSession(uuid4(), env.id, {"agent3", "agent2"}, "ts2")
    await am.new_session(ts2, set(ts2.endpoint_names))
    await am._session_listener_actions.join()
    assert len(am.sessions) == 3
    ts2.get_client().set_state.assert_called_with("agent3", enabled=True)
    ts2.get_client().reset_mock()
    await retry_limited(
        assert_state_agents_retry(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.up, sid2=ts1.id, sid3=ts2.id), 10
    )

    # test is_primary
    assert not am.is_primary(env, ts2.id, "agent1")
    assert not am.is_primary(env, ts1.id, "agent1")
    assert am.is_primary(env, ts1.id, "agent2")
    assert am.is_primary(env, ts2.id, "agent3")

    # expire first
    await am.expire(ts1, set(ts1.endpoint_names))
    await am._session_listener_actions.join()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent2", enabled=True)
    ts2.get_client().reset_mock()
    await retry_limited(
        assert_state_agents_retry(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.up, sid2=ts2.id, sid3=ts2.id), 10
    )

    # expire second
    await am.expire(ts2, set(ts2.endpoint_names))
    await am._session_listener_actions.join()
    assert len(am.sessions) == 1
    await retry_limited(assert_state_agents_retry(env.id, AgentStatus.paused, AgentStatus.down, AgentStatus.down), 10)

    # test is_primary
    assert not am.is_primary(env, ts1.id, "agent2")
    assert not am.is_primary(env, ts2.id, "agent3")


async def test_api(init_dataclasses_and_load_schema):
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="testenv", project=project.id)
    await env.insert()
    env2 = data.Environment(name="testenv2", project=project.id)
    await env2.insert()
    env3 = data.Environment(name="testenv3", project=project.id)
    await env3.insert()
    # Exact replica of one to detect crosstalk
    env4 = data.Environment(name="testenv4", project=project.id)
    await env4.insert()
    env5 = data.Environment(name="testenv5", project=project.id)
    await env5.insert()

    await data.Agent(environment=env.id, name="agent1", paused=True).insert()
    await data.Agent(environment=env.id, name="agent2", paused=False).insert()
    await data.Agent(environment=env.id, name="agent3", paused=False).insert()
    await data.Agent(environment=env2.id, name="agent4", paused=False).insert()
    await data.Agent(environment=env4.id, name="agent1", paused=True).insert()
    await data.Agent(environment=env4.id, name="agent2", paused=False).insert()
    await data.Agent(environment=env4.id, name="agent3", paused=False).insert()
    await data.Agent(environment=env5.id, name="agent1", paused=False).insert()

    server = Mock()
    futures = Collector()
    server.add_background_task.side_effect = futures
    am = AgentManager(server, False)
    am.add_background_task = futures
    am.running = True

    # one session
    ts1 = MockSession(uuid4(), env.id, {"agent1", "agent2"}, "ts1")
    await am._register_session(ts1, set(ts1.endpoint_names), datetime.datetime.now())
    # second session
    ts2 = MockSession(uuid4(), env.id, ["agent3", "agent2"], "ts2")
    await am._register_session(ts2, set(ts2.endpoint_names), datetime.datetime.now())
    # third session
    ts3 = MockSession(uuid4(), env3.id, ["agentx"], "ts3")
    await am._register_session(ts3, set(ts3.endpoint_names), datetime.datetime.now())
    # fourth session
    ts4 = MockSession(uuid4(), env4.id, {"agent1", "agent2"}, "ts4")
    await am._register_session(ts4, set(ts4.endpoint_names), datetime.datetime.now())
    # fifth session
    ts5 = MockSession(uuid4(), env5.id, {"agent1"}, "ts5")
    await am._register_session(ts5, set(ts5.endpoint_names), datetime.datetime.now())

    await futures.proccess()
    assert len(am.sessions) == 5

    # Getting all non expired agent processes
    code, all_agents_processes = await am.list_agent_processes(environment=None, expired=False)
    assert code == 200
    assert len(all_agents_processes["processes"]) == 5

    # Getting all agent processes (including expired)
    code, all_agents_processes = await am.list_agent_processes(environment=None, expired=True)
    assert code == 200
    assert len(all_agents_processes["processes"]) == 5

    # Making fifth session expire
    expiration = datetime.datetime.now().astimezone()
    await am._expire_session(ts5, set(ts5.endpoint_names), expiration)

    await futures.proccess()
    assert len(am.sessions) == 4

    # Getting all non expired agent processes
    code, all_agents_processes = await am.list_agent_processes(environment=None, expired=False)
    assert code == 200
    assert len(all_agents_processes["processes"]) == 4
    for agent_process in all_agents_processes["processes"]:
        assert agent_process["expired"] is None

    # Getting all agent processes (including expired)
    code, all_agents_processes = await am.list_agent_processes(environment=None, expired=True)
    assert code == 200
    assert len(all_agents_processes["processes"]) == 5

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
            {
                "first_seen": UNKWN,
                "expired": None,
                "hostname": "ts4",
                "last_seen": UNKWN,
                "endpoints": [
                    {"id": UNKWN, "name": "agent1", "process": UNKWN},
                    {"id": UNKWN, "name": "agent2", "process": UNKWN},
                ],
                "environment": env4.id,
            },
            {
                "first_seen": UNKWN,
                "expired": expiration,
                "hostname": "ts5",
                "last_seen": UNKWN,
                "endpoints": [
                    {"expired": expiration, "id": UNKWN, "name": "agent1", "process": UNKWN},
                ],
                "environment": env5.id,
            },
        ]
    }

    assert_equal_ish(shouldbe, all_agents_processes, sortby=["hostname", "name"])
    # There is 5 agent processes, we take the 3rd one and will select the two before, and two after it.
    agentid = sorted(all_agents_processes["processes"], key=lambda p: p["sid"])[2]["sid"]

    start = agentid
    code, all_agents_processes = await am.list_agent_processes(environment=None, expired=True, start=start)
    assert code == 200
    assert len(all_agents_processes["processes"]) == 2
    for agent_process in all_agents_processes["processes"]:
        assert (
            agent_process["sid"] > start
        ), f"List of agent processes should not contain a sid (={agent_process['sid']}) before or equal to start (={start})"

    end = agentid
    code, all_agents_processes = await am.list_agent_processes(environment=None, expired=True, end=end)
    assert code == 200
    assert len(all_agents_processes["processes"]) == 2
    for agent_process in all_agents_processes["processes"]:
        assert (
            agent_process["sid"] < end
        ), f"List of agent processes should not contain a sid (={agent_process['sid']}) after or equal to end (={end})"

    code, all_agents = await am.list_agent_processes(environment=env.id, expired=False)
    assert code == 200
    agentid1 = all_agents["processes"][0]["sid"]
    agentid2 = all_agents["processes"][1]["sid"]

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

    code, all_agents = await am.list_agent_processes(environment=env2.id, expired=False)
    assert code == 200

    shouldbe = {"processes": []}

    assert_equal_ish(shouldbe, all_agents)

    report = await am.get_agent_process_report(agentid1)
    assert (200, "X") == report

    report = await am.get_agent_process_report(agentid2)
    assert (200, "X") == report

    result, _ = await am.get_agent_process_report(uuid4())
    assert result == 404

    code, all_agents = await am.list_agents(None)
    assert code == 200
    shouldbe = {
        "agents": [
            {"name": "agent1", "paused": True, "last_failover": "", "primary": "", "environment": env.id, "state": "paused"},
            {
                "name": "agent1",
                "paused": False,
                "last_failover": expiration,
                "primary": "",
                "environment": env5.id,
                "state": "down",
            },
            {"name": "agent2", "paused": False, "last_failover": UNKWN, "primary": UNKWN, "environment": env.id, "state": "up"},
            {"name": "agent3", "paused": False, "last_failover": UNKWN, "primary": UNKWN, "environment": env.id, "state": "up"},
            {"name": "agent1", "paused": True, "last_failover": "", "primary": "", "environment": env4.id, "state": "paused"},
            {
                "name": "agent2",
                "paused": False,
                "last_failover": UNKWN,
                "primary": UNKWN,
                "environment": env4.id,
                "state": "up",
            },
            {"name": "agent3", "paused": False, "last_failover": "", "primary": "", "environment": env4.id, "state": "down"},
            {"name": "agent4", "paused": False, "last_failover": "", "primary": "", "environment": env2.id, "state": "down"},
        ]
    }
    assert_equal_ish(shouldbe, all_agents, sortby=["environment", "name"])

    start = "agent2"
    code, all_agents = await am.list_agents(env=None, start=start)
    assert code == 200
    assert len(all_agents["agents"]) == 3
    for a in all_agents["agents"]:
        assert a["name"] > start, f"List of agent should not contain a name (={a['name']}) before or equal to start (={start})"

    end = "agent2"
    code, all_agents = await am.list_agents(env=None, end=end)
    assert code == 200
    assert len(all_agents["agents"]) == 3
    for a in all_agents["agents"]:
        assert a["name"] < end, f"List of agent should not contain a name (={a['name']}) after or equal to end (={end})"

    code, all_agents = await am.list_agents(env2)
    assert code == 200
    shouldbe = {
        "agents": [
            {"name": "agent4", "paused": False, "last_failover": "", "primary": "", "environment": env2.id, "state": "down"}
        ]
    }
    assert_equal_ish(shouldbe, all_agents)


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

    # one session
    ts1 = MockSession(uuid4(), env.id, {"agent1", "agent2"}, "ts1")
    await am._register_session(ts1, set(ts1.endpoint_names), datetime.datetime.now())
    await futures.proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", enabled=True)
    ts1.get_client().reset_mock()
    await assert_state_agents(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.down, sid2=ts1.id)

    # alive
    await am._seen_session(ts1, set(ts1.endpoint_names))
    await futures.proccess()
    assert len(am.sessions) == 1
    await assert_state_agents(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.down, sid2=ts1.id)

    # second session
    ts2 = MockSession(uuid4(), env.id, {"agent3", "agent2"}, "ts2")
    await am._register_session(ts2, set(ts2.endpoint_names), datetime.datetime.now())
    await futures.proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", enabled=True)
    ts2.get_client().reset_mock()
    await assert_state_agents(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.up, sid2=ts1.id, sid3=ts2.id)

    # expire first
    await am._expire_session(ts1, set(ts1.endpoint_names), datetime.datetime.now())
    await futures.proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", enabled=True)
    ts2.get_client().reset_mock()
    await assert_state_agents(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.up, sid2=ts2.id, sid3=ts2.id)

    # failover
    am = AgentManager(server, False)
    am.add_background_task = futures
    am.running = True
    await am._expire_all_sessions_in_db()
    await assert_state_agents(env.id, AgentStatus.paused, AgentStatus.down, AgentStatus.down)

    # one session
    ts1 = MockSession(uuid4(), env.id, {"agent1", "agent2"}, "ts1")
    await am._register_session(ts1, set(ts1.endpoint_names), datetime.datetime.now())
    await futures.proccess()
    assert len(am.sessions) == 1
    ts1.get_client().set_state.assert_called_with("agent2", enabled=True)
    ts1.get_client().reset_mock()
    await assert_state_agents(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.down, sid2=ts1.id)

    # alive
    await am._seen_session(ts1, set(ts1.endpoint_names))
    await futures.proccess()
    assert len(am.sessions) == 1
    await assert_state_agents(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.down, sid2=ts1.id)

    # second session
    ts2 = MockSession(uuid4(), env.id, {"agent3", "agent2"}, "ts2")
    await am._register_session(ts2, set(ts2.endpoint_names), datetime.datetime.now())
    await futures.proccess()
    assert len(am.sessions) == 2
    ts2.get_client().set_state.assert_called_with("agent3", enabled=True)
    ts2.get_client().reset_mock()
    await assert_state_agents(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.up, sid2=ts1.id, sid3=ts2.id)

    # expire first
    await am._expire_session(ts1, set(ts1.endpoint_names), datetime.datetime.now())
    await futures.proccess()
    assert len(am.sessions) == 1
    ts2.get_client().set_state.assert_called_with("agent2", enabled=True)
    ts2.get_client().reset_mock()
    await assert_state_agents(env.id, AgentStatus.paused, AgentStatus.up, AgentStatus.up, sid2=ts2.id, sid3=ts2.id)

    # expire second
    await am._expire_session(ts2, set(ts2.endpoint_names), datetime.datetime.now())
    await futures.proccess()
    assert len(am.sessions) == 0
    await assert_state_agents(env.id, AgentStatus.paused, AgentStatus.down, AgentStatus.down)


async def assert_agent_db_state(
    tid: UUID, nr_procs: int, nr_non_expired_procs: int, nr_agent_instances: int, nr_non_expired_instances: int
) -> typing.Callable:
    """
    The database log is updated asynchronously. This method waits until
    the desired database state is reached.
    """

    async def is_db_state_reached():
        result = await data.AgentProcess.get_list(environment=tid)
        if len(result) != nr_procs:
            return False
        result = await data.AgentProcess.get_list(environment=tid, expired=None)
        if len(result) != nr_non_expired_procs:
            return False
        result = await data.AgentInstance.get_list(tid=tid)
        if len(result) != nr_agent_instances:
            return False
        result = await data.AgentInstance.get_list(tid=tid, expired=None)
        if len(result) != nr_non_expired_instances:
            return False
        return True

    await retry_limited(is_db_state_reached, 10)


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
        sessionstore=session_manager,
        sid=sid,
        hang_interval=1,
        timout=1,
        tid=tid,
        endpoint_names=[endpoint],
        nodename="test",
        disable_expire_check=True,
    )

    await assert_agent_db_state(tid, nr_procs=0, nr_non_expired_procs=0, nr_agent_instances=0, nr_non_expired_instances=0)
    await agent_manager._register_session(
        session=session, endpoint_names_snapshot=set(session.endpoint_names), now=datetime.datetime.now()
    )
    await assert_agent_db_state(tid, nr_procs=1, nr_non_expired_procs=1, nr_agent_instances=1, nr_non_expired_instances=1)
    await agent_manager._expire_session(
        session=session, endpoint_names_snapshot=set(session.endpoint_names), now=datetime.datetime.now()
    )
    await assert_agent_db_state(tid, nr_procs=1, nr_non_expired_procs=0, nr_agent_instances=1, nr_non_expired_instances=0)
    await agent_manager._register_session(
        session=session, endpoint_names_snapshot=set(session.endpoint_names), now=datetime.datetime.now()
    )
    await assert_agent_db_state(tid, nr_procs=1, nr_non_expired_procs=1, nr_agent_instances=1, nr_non_expired_instances=1)


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
        sessionstore=session_manager,
        sid=sid,
        hang_interval=1,
        timout=1,
        tid=tid,
        endpoint_names=[endpoint],
        nodename="node1",
        disable_expire_check=True,
    )

    await assert_agent_db_state(tid, nr_procs=0, nr_non_expired_procs=0, nr_agent_instances=0, nr_non_expired_instances=0)
    await agent_manager._register_session(
        session=session, endpoint_names_snapshot=set(session.endpoint_names), now=datetime.datetime.now()
    )
    await assert_agent_db_state(tid, nr_procs=1, nr_non_expired_procs=1, nr_agent_instances=1, nr_non_expired_instances=1)
    await agent_manager._expire_session(
        session=session, endpoint_names_snapshot=set(session.endpoint_names), now=datetime.datetime.now()
    )
    await assert_agent_db_state(tid, nr_procs=1, nr_non_expired_procs=0, nr_agent_instances=1, nr_non_expired_instances=0)
    await agent_manager._register_session(
        session=session, endpoint_names_snapshot=set(session.endpoint_names), now=datetime.datetime.now()
    )
    await assert_agent_db_state(tid, nr_procs=1, nr_non_expired_procs=1, nr_agent_instances=1, nr_non_expired_instances=1)
    await agent_manager._expire_session(
        session=session, endpoint_names_snapshot=set(session.endpoint_names), now=datetime.datetime.now()
    )
    await assert_agent_db_state(tid, nr_procs=1, nr_non_expired_procs=0, nr_agent_instances=1, nr_non_expired_instances=0)

    # Make database corrupt
    instances = await data.AgentInstance.get_list(tid=tid)
    assert len(instances) == 1
    await instances[0].update(expired=None)
    # Assert corruption
    await assert_agent_db_state(tid, nr_procs=1, nr_non_expired_procs=0, nr_agent_instances=1, nr_non_expired_instances=1)

    # Session registration should fix the inconsistency
    await agent_manager._register_session(
        session=session, endpoint_names_snapshot=session.endpoint_names, now=datetime.datetime.now()
    )
    await assert_agent_db_state(tid, nr_procs=1, nr_non_expired_procs=1, nr_agent_instances=1, nr_non_expired_instances=1)


async def test_session_creation_fails(server, environment, async_finalizer, caplog):
    """
    Verify that:
     * Session creation works correctly when the connectivity to the database works.
     * Session creation is refused when the connectivity to the database doesn't work.
       In that case the server state should stay consistent.
    """
    env_id = UUID(environment)
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    a = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await a.add_end_point_name("agent1")
    async_finalizer(a.stop)
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
    await session.expire(0)

    # Wait until session expired
    await retry_limited(lambda: len(agentmanager.tid_endpoint_to_session) == 0, 10)

    # Verify session expiry
    assert len(agentmanager.sessions) == 0
    assert len(agentmanager.tid_endpoint_to_session) == 0
    assert len(session_manager._sessions) == 0

    # Remove connectivity to the database
    await data.disconnect()
    caplog.clear()

    a = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await a.add_end_point_name("agent1")
    await a.start()
    async_finalizer(a.stop)

    # Verify that session creation fails and server state is stays consistent
    await retry_limited(lambda: "Heartbeat failed" in caplog.text, 10)
    assert len(agentmanager.sessions) == 0
    assert len(agentmanager.tid_endpoint_to_session) == 0
    assert len(session_manager._sessions) == 0


async def test_agent_actions(server, client, async_finalizer):
    """
    Test the agent_action() and the all_agents_action() API call.
    """
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)

    result = await client.create_project("test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="test1")
    env1_id = UUID(result.result["environment"]["id"])
    result = await client.create_environment(project_id=project_id, name="test2")
    env2_id = UUID(result.result["environment"]["id"])

    env_to_agent_map: Dict[UUID, agent.Agent] = {}

    async def start_agent(env_id: UUID, agent_names: List[str]) -> None:
        for agent_name in agent_names:
            await data.Agent(environment=env_id, name=agent_name, paused=False).insert()

        agent_map = {agent_name: "localhost" for agent_name in agent_names}
        a = agent.Agent(hostname="node1", environment=env_id, agent_map=agent_map, code_loader=False)
        for agent_name in agent_names:
            await a.add_end_point_name(agent_name)
        await a.start()
        async_finalizer(a.stop)
        env_to_agent_map[env_id] = a

        async def has_primary(agent_name: str) -> bool:
            agent: data.Agent = await data.Agent.get_one(environment=env_id, name=agent_name)
            return agent.primary is not None

        await asyncio.gather(*(retry_limited(has_primary, timeout=10, agent_name=agent_name) for agent_name in agent_names))

    await asyncio.gather(start_agent(env1_id, ["agent1", "agent2"]), start_agent(env2_id, ["agent1"]))

    async def assert_agents_paused(expected_statuses: Dict[Tuple[UUID, str], bool]) -> None:
        async def _does_expected_status_match_actual_status() -> bool:
            for (env_id, agent_name), paused in expected_statuses.items():
                # Check in-memory session state
                live_session_found = (env_id, agent_name) in agent_manager.tid_endpoint_to_session
                if live_session_found == paused:
                    LOGGER.info(
                        "live_session_found=%s for agent %s in environment %s, while expected paused state is %s",
                        live_session_found,
                        agent_name,
                        env_id,
                        paused,
                    )
                    return False
                # Check database state
                agent_from_db = await data.Agent.get_one(environment=env_id, name=agent_name)
                if agent_from_db.paused != paused:
                    LOGGER.info(
                        "Agent paused state in database is %s for agent %s in environment %s while %s was expected",
                        agent_from_db.paused,
                        agent_name,
                        env_id,
                        paused,
                    )
                    return False
                if (agent_from_db.primary is None) != paused:
                    LOGGER.info(
                        "Agent %s in environment %s has primary %s, while paused state is expected to be %s",
                        agent_name,
                        env_id,
                        agent_from_db.primary,
                        paused,
                    )
                    return False
                if not paused:
                    live_session = agent_manager.tid_endpoint_to_session[(env_id, agent_name)]
                    agent_instance: Optional[data.AgentInstance] = await data.AgentInstance.get_by_id(agent_from_db.primary)
                    if agent_instance is None:
                        LOGGER.info("Agent %s in environment %s is not paused, but no AgentInstance exists", agent_name, env_id)
                        return False
                    if agent_instance.process != live_session.id:
                        LOGGER.info(
                            "ID of live session %s doesn't match the ID on the AgentInstance %s for agent %s in environment %s",
                            live_session.id,
                            agent_instance.process,
                            agent_name,
                            env_id,
                        )
                        return False
                # Check agent state
                if env_to_agent_map[env_id]._instances[agent_name].is_enabled() == paused:
                    LOGGER.info(
                        "Agent %s in environment %s has enabled state %s (expected %s)",
                        agent_name,
                        env_id,
                        env_to_agent_map[env_id]._instances[agent_name].is_enabled(),
                        not paused,
                    )
                    return False
            return True

        # It may take some time until the in-memory and in-database session state converges.
        await retry_limited(_does_expected_status_match_actual_status, timeout=10)

    await assert_agents_paused(
        expected_statuses={(env1_id, "agent1"): False, (env1_id, "agent2"): False, (env2_id, "agent1"): False}
    )
    # Pause agent1 and pause again
    for _ in range(2):
        result = await client.agent_action(tid=env1_id, name="agent1", action=AgentAction.pause.value)
        assert result.code == 200
        await assert_agents_paused(
            expected_statuses={(env1_id, "agent1"): True, (env1_id, "agent2"): False, (env2_id, "agent1"): False}
        )

    # Unpause agent1 and unpause again
    for _ in range(2):
        result = await client.agent_action(tid=env1_id, name="agent1", action=AgentAction.unpause.value)
        assert result.code == 200
        await assert_agents_paused(
            expected_statuses={(env1_id, "agent1"): False, (env1_id, "agent2"): False, (env2_id, "agent1"): False}
        )

    # Pause all agents in env1 and pause again
    for _ in range(2):
        result = await client.all_agents_action(tid=env1_id, action=AgentAction.pause.value)
        assert result.code == 200
        await assert_agents_paused(
            expected_statuses={(env1_id, "agent1"): True, (env1_id, "agent2"): True, (env2_id, "agent1"): False}
        )

    # Unpause all agents in env1 and unpause again
    for _ in range(2):
        result = await client.all_agents_action(tid=env1_id, action=AgentAction.unpause.value)
        assert result.code == 200
        await assert_agents_paused(
            expected_statuses={(env1_id, "agent1"): False, (env1_id, "agent2"): False, (env2_id, "agent1"): False}
        )

    # set up for halt test
    async def assert_agents_halt_state(env_id: UUID, agents_running: Dict[str, bool], halted: bool) -> None:
        """
        :param agents_running: dictionary of agents that were running before environment halting.
        """
        for agent_name, running in agents_running.items():
            db_agent: data.Agent = await data.Agent.get_one(environment=env_id, name=agent_name)
            assert db_agent.unpause_on_resume is (running if halted else None)

    result = await client.agent_action(tid=env1_id, name="agent1", action=AgentAction.pause.value)
    assert result.code == 200
    await assert_agents_paused(
        expected_statuses={(env1_id, "agent1"): True, (env1_id, "agent2"): False, (env2_id, "agent1"): False}
    )
    await assert_agents_halt_state(env1_id, {"agent1": False, "agent2": True}, False)
    await assert_agents_halt_state(env2_id, {"agent1": True}, False)

    # halt environment
    result = await client.halt_environment(env1_id)
    assert result.code == 200
    await assert_agents_paused(
        expected_statuses={(env1_id, "agent1"): True, (env1_id, "agent2"): True, (env2_id, "agent1"): False}
    )
    await assert_agents_halt_state(env1_id, {"agent1": False, "agent2": True}, True)
    await assert_agents_halt_state(env2_id, {"agent1": True}, False)

    # verify agent actions are not allowed in halted state
    result = await client.agent_action(tid=env1_id, name="agent1", action=AgentAction.unpause.value)
    assert result.code == 403
    assert "message" in result.result
    assert result.result["message"] == "Access denied: Can not pause or unpause agents when the environment has been halted."
    result = await client.agent_action(tid=env1_id, name="agent2", action=AgentAction.pause.value)
    assert result.code == 403
    result = await client.agent_action(tid=env2_id, name="agent1", action=AgentAction.pause.value)
    assert result.code == 200

    # resume environment, make sure only agents that were already running are unpaused
    result = await client.resume_environment(env1_id)
    assert result.code == 200
    await assert_agents_paused(
        expected_statuses={(env1_id, "agent1"): True, (env1_id, "agent2"): False, (env2_id, "agent1"): True}
    )
    await assert_agents_halt_state(env1_id, {"agent1": False, "agent2": True}, False)
    await assert_agents_halt_state(env2_id, {"agent1": False}, False)


async def test_agent_on_resume_actions(server, environment, client, agent_factory) -> None:
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)

    await agent_factory(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost", "agent2": "localhost", "agent3": "localhost"},
        code_loader=False,
        agent_names=["agent1", "agent2", "agent3"],
    )

    env_id = uuid.UUID(environment)
    env = await data.Environment.get_by_id(env_id)
    await agent_manager.ensure_agent_registered(env=env, nodename="agent1")
    await agent_manager.ensure_agent_registered(env=env, nodename="agent2")
    await agent_manager.ensure_agent_registered(env=env, nodename="agent3")
    # The keep_paused_on_resume and unpause_on_resume actions are only allowed when the environment is halted
    result = await client.agent_action(environment, name="agent1", action=AgentAction.keep_paused_on_resume.value)
    assert result.code == 403
    result = await client.agent_action(environment, name="agent1", action=AgentAction.unpause_on_resume.value)
    assert result.code == 403

    result = await client.agent_action(environment, name="agent1", action="unknown_action")
    assert result.code == 400

    result = await client.agent_action(environment, name="agent2", action=AgentAction.pause.value)
    assert result.code == 200

    async def assert_agents_on_resume_state(agent_states: Dict[str, Optional[bool]]) -> None:
        for agent_name, on_resume in agent_states.items():
            agent_from_db = await data.Agent.get_one(environment=env_id, name=agent_name)
            assert agent_from_db.unpause_on_resume is on_resume

    async def assert_agents_paused_state(agent_states: Dict[str, bool]) -> None:
        for agent_name, paused in agent_states.items():
            agent_from_db = await data.Agent.get_one(environment=env_id, name=agent_name)
            assert agent_from_db.paused is paused

    await assert_agents_on_resume_state({"agent1": None, "agent2": None, "agent3": None})
    await assert_agents_paused_state({"agent1": False, "agent2": True, "agent3": False})

    # Halt the environment and check the on_resume state
    result = await client.halt_environment(environment)
    assert result.code == 200

    await assert_agents_on_resume_state({"agent1": True, "agent2": False, "agent3": True})
    await assert_agents_paused_state({"agent1": True, "agent2": True, "agent3": True})

    result = await client.agent_action(environment, name="agent1", action=AgentAction.keep_paused_on_resume.value)
    assert result.code == 200

    result = await client.agent_action(environment, name="agent2", action=AgentAction.unpause_on_resume.value)
    assert result.code == 200

    # The on_resume actions don't start the agents immediately, just manipulate the 'unpause_on_resume' flag
    await assert_agents_paused_state({"agent1": True, "agent2": True, "agent3": True})
    await assert_agents_on_resume_state({"agent1": False, "agent2": True, "agent3": True})

    result = await client.resume_environment(environment)
    assert result.code == 200

    await assert_agents_paused_state({"agent1": True, "agent2": False, "agent3": False})
    await assert_agents_on_resume_state({"agent1": None, "agent2": None, "agent3": None})

    # The keep_paused_on_resume and unpause_on_resume actions are only allowed when the environment is halted
    result = await client.all_agents_action(environment, action=AgentAction.keep_paused_on_resume.value)
    assert result.code == 403
    result = await client.all_agents_action(environment, action=AgentAction.unpause_on_resume.value)
    assert result.code == 403

    result = await client.halt_environment(environment)
    assert result.code == 200
    await assert_agents_on_resume_state({"agent1": False, "agent2": True, "agent3": True})

    result = await client.all_agents_action(environment, action=AgentAction.unpause_on_resume.value)
    assert result.code == 200
    await assert_agents_on_resume_state({"agent1": True, "agent2": True, "agent3": True})

    result = await client.all_agents_action(environment, action=AgentAction.keep_paused_on_resume.value)
    assert result.code == 200
    await assert_agents_on_resume_state({"agent1": False, "agent2": False, "agent3": False})

    result = await client.agent_action(environment, name="agent3", action=AgentAction.unpause_on_resume.value)
    assert result.code == 200
    await assert_agents_on_resume_state({"agent1": False, "agent2": False, "agent3": True})

    result = await client.resume_environment(environment)
    assert result.code == 200

    await assert_agents_paused_state({"agent1": True, "agent2": True, "agent3": False})
    await assert_agents_on_resume_state({"agent1": None, "agent2": None, "agent3": None})


async def test_process_already_terminated(server, environment):
    """
    This test case tests whether the termination of autostarted agents (processes) happens correctly,
    when one of the processes has already terminated.
    """
    env_id = UUID(environment)
    env = await data.Environment.get_by_id(env_id)

    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
    await autostarted_agent_manager._ensure_agents(env=env, agents=["internal"])
    assert len(autostarted_agent_manager._agent_procs) == 1

    # Terminate process
    autostarted_agent_manager._agent_procs[env_id].terminate()

    # This call shouldn't raise an exception
    await autostarted_agent_manager._terminate_agents()


async def test_exception_occurs_while_processing_session_action(server, environment, async_finalizer, monkeypatch, caplog):
    """
    This test verifies that the consumer of the _session_listener_actions queue keeps working
    even when the an exception is thrown while handling an action.
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    # Replace the _process_action() method with one that throws an excption
    old_process_action_function = agentmanager._process_action

    async def new_process_action_function(self, action: SessionAction, session: Session, timestamp: datetime):
        raise Exception("Failure")

    monkeypatch.setattr(agentmanager, "_process_action", new_process_action_function)

    assert len(agentmanager.sessions) == 0

    # Start agent
    a = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await a.add_end_point_name("agent1")
    await a.start()
    async_finalizer(a.stop)

    # Verify that an exception is thrown an no session is created
    await retry_limited(lambda: "An exception occurred while handling session action" in caplog.text, 10)
    assert len(agentmanager.sessions) == 0
    await a.stop()

    # Put original method in place.
    monkeypatch.setattr(agentmanager, "_process_action", old_process_action_function)

    # Start new agent
    a = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await a.add_end_point_name("agent1")
    await a.start()
    async_finalizer(a.stop)

    # Verify that session is created successfully -> Consumer didn't crash
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)


async def test_restart_on_environment_setting(server, client, environment, caplog):
    with caplog.at_level(logging.DEBUG):
        response = await client.environment_settings_set(tid=environment, id="autostart_agent_deploy_interval", value=300)
        assert response.code == 200

        def check_log_contains(caplog, loggerpart, level, msg):
            for record in caplog.get_records("call"):
                logger_name, log_level, message = record.name, record.levelno, record.message
                if msg in message and loggerpart in logger_name and level == log_level:
                    return True
            return False

        await retry_limited(
            lambda: check_log_contains(
                caplog, "inmanta.server.agentmanager", logging.DEBUG, "Restarting agents in environment"
            ),
            10,
        )


async def test_failover_doesnt_make_paused_agent_primary(server, client, environment, agent_factory):
    """
    This test verifies that:

     * The standby agent doesn't take over when the agent is paused.
     * Session expiry doesn't make a standby agent primary when the agent is paused.
    """
    agent_name = "agent1"
    agent_config.agent_names.set(agent_name)
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    env_id = UUID(environment)
    env = await data.Environment.get_by_id(env_id)
    await agentmanager.ensure_agent_registered(env, agent_name)

    # Create two agent instances for the same agent (primary + standby agent)
    first_agent = await agent_factory(environment=environment, agent_map={agent_name: ""}, agent_names=[agent_name])
    # Wait until first_agent is elected as primary
    await retry_limited(lambda: len(agentmanager.tid_endpoint_to_session) == 1, timeout=10)
    await agent_factory(environment=environment, agent_map={agent_name: ""}, agent_names=[agent_name])

    # Wait until both agents have a session with the server
    await retry_limited(lambda: len(agentmanager.sessions) == 2, timeout=10)

    # Both agents have a session to the server, first_agent is primary
    assert len(agentmanager.sessions) == 2
    assert len(agentmanager.tid_endpoint_to_session) == 1
    # first_agent is primary
    assert agentmanager.tid_endpoint_to_session[(env_id, agent_name)].id == first_agent.sessionid

    # Pause agent1
    result = await client.agent_action(tid=environment, name=agent_name, action=AgentAction.pause.value)
    assert result.code == 200

    # Two agents have a session to the server, none of them is primary. The agent is paused
    assert len(agentmanager.sessions) == 2
    assert len(agentmanager.tid_endpoint_to_session) == 0

    # Stop one of the agents
    await first_agent.stop()

    # Wait until session expires
    await retry_limited(lambda: len(agentmanager.sessions) == 1 and len(agentmanager.tid_endpoint_to_session) == 0, timeout=10)

    # One agent has a session to the server, none of them is primary. The agent is paused
    assert len(agentmanager.sessions) == 1
    assert len(agentmanager.tid_endpoint_to_session) == 0


async def test_add_internal_agent_when_missing_in_agent_map(server, environment, postgresql_client):
    """
    The internal agent should always be present in the autostart_agent_map. If it is not present, it is added when to
    auto-started agent is started. This test case verifies this behavior.
    """
    # Ensure agent1
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    env = await data.Environment.get_by_id(UUID(environment))
    await agentmanager.ensure_agent_registered(env=env, nodename="agent1")

    # Remove the internal agent from the autostart_agent_map
    query = "UPDATE public.environment SET settings=jsonb_set(settings, $1::text[], to_jsonb($2::jsonb), TRUE)"
    await postgresql_client.execute(query, [data.AUTOSTART_AGENT_MAP], "{}")

    # Assert internal agent not in autostart_agent_map
    env = await data.Environment.get_by_id(UUID(environment))
    autostart_agent_map = await env.get(data.AUTOSTART_AGENT_MAP)
    assert "internal" not in autostart_agent_map

    # Start autostarted agent1
    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
    await autostarted_agent_manager._ensure_agents(env=env, agents=["agent1"])

    # Verify patch on autostart_agent_map
    env = await data.Environment.get_by_id(UUID(environment))
    autostart_agent_map = await env.get(data.AUTOSTART_AGENT_MAP)
    assert "internal" in autostart_agent_map


async def test_error_handling_agent_fork(server, environment, monkeypatch):
    """
    Verifies resolution of issue: inmanta/inmanta-core#2777
    """
    exception_message = "The start of the agent failed"

    async def _dummy_fork_inmanta(
        self, args: List[str], outfile: Optional[str], errfile: Optional[str], cwd: Optional[str] = None
    ) -> subprocess.Process:
        raise Exception(exception_message)

    # Make the _fork_inmanta method raise an Exception
    monkeypatch.setattr(AutostartedAgentManager, "_fork_inmanta", _dummy_fork_inmanta)

    env = await data.Environment.get_by_id(UUID(environment))
    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
    with pytest.raises(Exception) as excinfo:
        await autostarted_agent_manager._ensure_agents(env=env, agents=["internal"], restart=True)

    assert exception_message in str(excinfo.value)


async def test_are_agents_active(server, client, environment, agent_factory) -> None:
    """
    Ensure that the `AgentManager.are_agents_active()` method returns True when an agent
    is in the up or the paused state.
    """
    agent_config.use_autostart_agent_map.set("True")
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    agent_name = "agent1"
    env_id = UUID(environment)
    env = await data.Environment.get_by_id(env_id)

    # The agent is not started yet ->  it should not be active
    assert not await agentmanager.are_agents_active(tid=env_id, endpoints=[agent_name])

    # Start agent
    await agentmanager.ensure_agent_registered(env, agent_name)
    await agent_factory(environment=environment, agent_map={agent_name: ""}, agent_names=[agent_name])

    # Verify agent is active
    await retry_limited(agentmanager.are_agents_active, tid=env_id, endpoints=[agent_name], timeout=10)

    # Pause agent
    result = await client.agent_action(tid=env_id, name=agent_name, action=AgentAction.pause.value)
    assert result.code == 200, result.result

    # Ensure the agent is still active
    await retry_limited(agentmanager.are_agents_active, tid=env_id, endpoints=[agent_name], timeout=10)


async def test_dont_start_paused_agent(server, client, environment, caplog) -> None:
    """
    Ensure that the AutostartedAgentManager doesn't try to start an agent that is paused (inmanta/inmanta-core#4398).
    """
    caplog.set_level(logging.DEBUG)
    env_id = UUID(environment)
    agent_name = "agent1"

    # Register agent in model
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)
    env = await data.Environment.get_by_id(env_id)
    await agent_manager.ensure_agent_registered(env=env, nodename=agent_name)

    # Add agent1 to AUTOSTART_AGENT_MAP
    result = await client.set_setting(tid=environment, id=data.AUTOSTART_AGENT_MAP, value={"internal": "", agent_name: ""})
    assert result.code == 200, result.result

    # Start agent1
    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
    env = await data.Environment.get_by_id(env_id)
    assert (env_id, agent_name) not in agent_manager.tid_endpoint_to_session
    caplog.clear()
    await autostarted_agent_manager._ensure_agents(env=env, agents=[agent_name])
    # Ensure we wait until a primary has been elected for agent1
    assert (env_id, agent_name) in agent_manager.tid_endpoint_to_session
    assert len(autostarted_agent_manager._agent_procs) == 1
    assert "Started new agent with PID" in caplog.text
    # Ensure no timeout happened
    assert "took too long to start" not in caplog.text

    # Pause agent1
    result = await client.agent_action(tid=env_id, name=agent_name, action=AgentAction.pause.value)
    assert result.code == 200, result.result

    # Execute _ensure_agents() again and verify that no restart is triggered
    caplog.clear()
    await autostarted_agent_manager._ensure_agents(env=env, agents=[agent_name])
    assert len(autostarted_agent_manager._agent_procs) == 1
    assert "Started new agent with PID" not in caplog.text
    # Ensure no timeout happened
    assert "took too long to start" not in caplog.text
