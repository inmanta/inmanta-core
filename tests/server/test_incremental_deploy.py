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
import time
import uuid
from collections import defaultdict
from datetime import datetime
from re import sub
from typing import Any, Dict, List
from uuid import UUID, uuid4

import pytest

import utils
from inmanta import config, const, data
from inmanta.agent.agent import Agent
from inmanta.const import ResourceAction, ResourceState
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_SERVER
from inmanta.server.server import Server


class MultiVersionSetup(object):
    """
      create scenarios by describing the history of a resource, from newest to oldest state

      V = void, nothing
      A - available/skipped/unavailable
      E - error
      D - deployed
      d - deploying
      p - processing events
      S - skipped for undefined
      U - undefined
    """

    def __init__(self):
        self.firstversion: int = 100
        self.versions: List[List[Dict[str, Any]]] = [[] for _ in range(100)]
        self.states: Dict[str, ResourceState] = {}
        self.results: Dict[str, List[str]] = defaultdict(lambda: [])
        self.sid = uuid4()

    def get_version(self, v: int) -> List[Dict[str, Any]]:
        return self.versions[v]

    def expand_code(self, code: str) -> ResourceState:
        if code == "A":
            return ResourceState.available

        if code == "E":
            return ResourceState.failed

        if code == "D":
            return ResourceState.deployed

        if code == "d":
            return ResourceState.deploying

        if code == "p":
            return ResourceState.processing_events

        if code == "S":
            return ResourceState.skipped_for_undefined

        if code == "U":
            return ResourceState.undefined

        assert False

    def make_resource(
        self, name: str, value: str, version: int, agent: str = "agent1", requires: List[str] = [], send_event: bool = False
    ) -> str:
        """
            requires: list of resource identifiers
        """
        id = "test::Resource[%s,key=%s],v=%d" % (agent, name, version)
        res = {
            "key": value,
            "id": id,
            "send_event": send_event,
            "purged": False,
            "requires": ["%s,v=%d" % (r, version) for r in requires],
        }
        self.get_version(version).append(res)
        return id

    def add_resource(
        self, name: str, scenario: str, increment: bool, agent="agent1", requires=[], send_event: bool = False
    ) -> str:
        v = self.firstversion
        rid = "test::Resource[%s,key=%s]" % (agent, name)

        if increment:
            self.results[agent].append(rid)

        for step in scenario.split():
            v -= 1
            code = step[0]
            if code == "V":
                continue
            value = step[1:]
            rvid = self.make_resource(name, value, v, agent, requires, send_event)
            self.states[rvid] = self.expand_code(code)
        return rid

    async def setup_agent(self, server, environment):

        agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

        endpoints = list(self.results.keys())

        config.Config.set("config", "agent-deploy-interval", "0")
        config.Config.set("config", "agent-repair-interval", "0")

        a = Agent(hostname="node1", environment=environment, agent_map={e: "localhost" for e in endpoints}, code_loader=False)
        for e in endpoints:
            a.add_end_point_name(e)
        await a.start()
        await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

        return a

    async def setup(self, serverdirect: Server, env: UUID, sid: UUID):
        for version in range(0, len(self.versions)):
            if self.versions[version]:
                res = await serverdirect.put_version(
                    env=env, version=version, resources=self.versions[version], unknowns=[], version_info={}, resource_state={}
                )
                assert res == 200

                result, _ = await serverdirect.release_version(env, version, False)
                assert result == 200
        for rid, state in self.states.items():
            # Start the deploy
            action_id = uuid.uuid4()
            now = datetime.now()
            if state == const.ResourceState.available:
                # initial state can not be set
                continue
            if state not in const.TRANSIENT_STATES:
                finished = now
            else:
                finished = None
            result = await serverdirect.resource_action_update(
                env,
                [rid],
                action_id,
                ResourceAction.deploy,
                now,
                finished,
                status=state,
                messages=[],
                changes={},
                change=None,
                send_events=False,
            )
            assert result == 200

        allresources = {}

        for agent, results in self.results.items():
            result, payload = await serverdirect.get_resources_for_agent(
                env, agent, version=None, incremental_deploy=True, sid=sid
            )

            assert sorted([x["resource_id"] for x in payload["resources"]]) == sorted(results)
            allresources.update({r["resource_id"]: r for r in payload["resources"]})

        return allresources


@pytest.mark.asyncio
async def test_deploy(server, agent: Agent, environment, caplog):
    """
        Test basic deploy mechanism mocking
    """
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        serverdirect = server.get_slice(SLICE_SERVER)
        sid = agent.sessionid

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        version = int(time.time())

        def make_resources(version):
            return [
                {
                    "key": "key1",
                    "id": "test::Resource[agent1,key=key1],v=%d" % version,
                    "send_event": False,
                    "purged": False,
                    "requires": [],
                },
                {
                    "key": "key2",
                    "id": "test::Resource[agent1,key=key2],v=%d" % version,
                    "send_event": False,
                    "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
                    "purged": False,
                },
                {
                    "key": "key3",
                    "id": "test::Resource[agent1,key=key3],v=%d" % version,
                    "send_event": False,
                    "requires": ["test::Resource[agent2,key=key4],v=%d" % version],
                    "purged": True,
                },
                {"key": "key4", "id": "test::Resource[agent2,key=key4],v=%d" % version, "send_event": False, "requires": []},
            ]

        resources = make_resources(version)
        res = await serverdirect.put_version(
            env=env, version=version, resources=resources, unknowns=[], version_info={}, resource_state={}
        )
        assert res == 200

        result, _ = await serverdirect.release_version(env, version, False)
        assert result == 200

        resource_ids = [x["id"] for x in resources]

        # Start the deploy
        action_id = uuid.uuid4()
        now = datetime.now()
        result = await serverdirect.resource_action_update(
            env,
            resource_ids,
            action_id,
            const.ResourceAction.deploy,
            now,
            now,
            status=ResourceState.deployed,
            messages=[],
            changes={},
            change=None,
            send_events=False,
        )
        assert result == 200

        result, payload = await serverdirect.get_version(env, version)
        assert result == 200
        assert payload["model"].done == len(resources)

        # second, identical check_version
        v2 = version + 1
        resources = make_resources(v2)
        res = await serverdirect.put_version(
            env=env, version=v2, resources=resources, unknowns=[], version_info={}, resource_state={}
        )
        assert res == 200

        result, payload = await serverdirect.get_resources_for_agent(
            env, "agent1", version=None, incremental_deploy=True, sid=sid
        )
        assert len(payload["resources"]) == 0

        # Cannot request increment for specific version
        result, _ = await serverdirect.get_resources_for_agent(env, "agent1", version=version, incremental_deploy=True, sid=sid)
        assert result == 500
        result, _ = await serverdirect.get_resources_for_agent(env, "agent1", version=v2, incremental_deploy=True, sid=sid)
        assert result == 500

    for record in caplog.records:
        assert record.levelname != "WARNING"


def strip_version(v):
    return sub(",v=[0-9]+", "", v)


@pytest.mark.asyncio
async def test_deploy_scenarios(server, agent: Agent, environment, caplog):
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        serverdirect = server.get_slice(SLICE_SERVER)
        sid = agent.sessionid

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        setup = MultiVersionSetup()

        setup.add_resource("R1", "A1 A1 V1 D1", True)
        setup.add_resource("R2", "A1 E1 D1", True)
        setup.add_resource("R3", "A1 E1 E1 A1", True)
        setup.add_resource("R4", "A1 D1", False)
        setup.add_resource("R5", "A1 A2 D1", False)
        setup.add_resource("R6", "A1 D2", True)
        setup.add_resource("R7", "A1 D2 D1", True)
        setup.add_resource("R8", "D1 A1 E1 D1", False)
        setup.add_resource("R9", "A1 E2 D1", True)
        setup.add_resource("R10", "A1 A1 D1", False)
        setup.add_resource("R13", "A1 A1 A1 A1 A1", True)
        setup.add_resource("R14", "A1 A1 d1 D1", True)
        setup.add_resource("R15", "A1 A1 p1 D1", True)
        setup.add_resource("R16", "S1 A1", False)
        setup.add_resource("R17", "A1 S1 A1", True)
        setup.add_resource("R18", "D1 S1 A1", False)
        setup.add_resource("R19", "U1 A1", False)
        setup.add_resource("R20", "U1 D1", False)
        setup.add_resource("R21", "A1 U1", True)

        await setup.setup(serverdirect, env, sid)

    for record in caplog.records:
        assert record.levelname != "WARNING"


@pytest.mark.asyncio
async def test_deploy_scenarios_removed_req_by_increment(server, agent: Agent, environment, caplog):
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        serverdirect = server.get_slice(SLICE_SERVER)
        sid = agent.sessionid

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        setup = MultiVersionSetup()

        id1 = setup.add_resource("R1", "A1 D1", False)
        id2 = setup.add_resource("R2", "A1 D2", True, requires=[id1])

        resources = await setup.setup(serverdirect, env, sid)
        assert not resources[id2]["attributes"]["requires"]

    for record in caplog.records:
        assert record.levelname != "WARNING"


@pytest.mark.asyncio
async def test_deploy_scenarios_removed_req_by_increment2(server, environment, caplog):
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        serverdirect = server.get_slice(SLICE_SERVER)

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        setup = MultiVersionSetup()

        id1 = setup.add_resource("R1", "A1 D1", False)
        id3 = setup.add_resource("R3", "A1 D2", True)
        id4 = setup.add_resource("R4", "A1 D2", True, agent="agent2")
        id2 = setup.add_resource("R2", "A1 D2", True, requires=[id1, id3, id4])

        agent = await setup.setup_agent(server, environment)

        sid = agent.sessionid

        try:
            resources = await setup.setup(serverdirect, env, sid)
            print(sorted(resources[id2]["attributes"]["requires"]))
            print(sorted(sorted([id3, id4])))
            assert sorted([strip_version(r) for r in resources[id2]["attributes"]["requires"]]) == sorted([id3, id4])

        finally:
            await agent.stop()
    for record in caplog.records:
        # gets some logs when setting up agent
        assert record.levelname != "WARNING" or record.name == "inmanta.config"


@pytest.mark.asyncio
async def test_deploy_scenarios_added_by_send_event(server, agent: Agent, environment, caplog):
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        serverdirect = server.get_slice(SLICE_SERVER)
        sid = agent.sessionid

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        setup = MultiVersionSetup()

        id1 = setup.add_resource("R1", "A1 D2", True, send_event=True)
        id2 = setup.add_resource("R2", "A1 D1", True, requires=[id1])
        id3 = setup.add_resource("R3", "A1 D1", True, requires=[id1], send_event=True)
        setup.add_resource("R4", "A1 D1", True, requires=[id3])
        setup.add_resource("R5", "A1 D1", False, requires=[id2])

        await setup.setup(serverdirect, env, sid)

    for record in caplog.records:
        assert record.levelname != "WARNING"


@pytest.mark.asyncio
async def test_deploy_scenarios_added_by_send_event_cad(server, agent: Agent, environment, caplog):
    # ensure CAD does not change send_event
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        serverdirect = server.get_slice(SLICE_SERVER)
        sid = agent.sessionid

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        setup = MultiVersionSetup()

        id1 = setup.add_resource("R1", "A1 D2", True, send_event=False)
        id2 = setup.add_resource("R2", "A1 D1", False, requires=[id1])
        id3 = setup.add_resource("R3", "A1 D1", False, requires=[id1], send_event=True)
        setup.add_resource("R4", "A1 D1", False, requires=[id3])
        setup.add_resource("R5", "A1 D1", False, requires=[id2])

        setup.add_resource("R6", "A1 D1", False, requires=[id1], agent="agent2")
        await setup.setup(serverdirect, env, sid)

    for record in caplog.records:
        assert record.levelname != "WARNING"
