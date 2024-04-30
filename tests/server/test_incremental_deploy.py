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
import re
import uuid
from collections import defaultdict
from datetime import datetime
from re import sub
from typing import Any
from uuid import UUID, uuid4

import utils
from inmanta import config, const, data
from inmanta.agent.agent import Agent
from inmanta.const import Change, ResourceAction, ResourceState
from inmanta.resources import Id
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_ORCHESTRATION, SLICE_RESOURCE
from inmanta.server.services.orchestrationservice import OrchestrationService
from inmanta.server.services.resourceservice import ResourceService
from inmanta.util import get_compiler_version
from utils import assert_no_warning


class MultiVersionSetup:
    """
    create scenarios by describing the history of a resource, from newest to oldest state

    V  = void, nothing
    A  - available
    S  - skipped
    UA - unavailable
    E  - error
    D  - deployed
    d  - deploying
    p  - processing events
    SU - skipped for undefined
    UD - undefined
    """

    scenario_step_regex = re.compile(r"(A|E|D|d|p|S|SU|UA|UD)([0-9]+)")

    def __init__(self):
        self.firstversion: int = 100
        self.versions: list[list[dict[str, Any]]] = [[] for _ in range(100)]
        self.states: dict[str, ResourceState] = {}
        self.states_per_version: dict[int, dict[str, ResourceState]] = defaultdict(dict)
        self.results: dict[str, list[str]] = defaultdict(list)
        self.sid = uuid4()

    def get_version(self, v: int) -> list[dict[str, Any]]:
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

        if code == "S":
            return ResourceState.skipped

        if code == "SU":
            return ResourceState.skipped_for_undefined

        if code == "UA":
            return ResourceState.unavailable

        if code == "UD":
            return ResourceState.undefined

        assert False, f"Unknown code {code}"

    def make_resource(
        self, name: str, value: str, version: int, agent: str = "agent1", requires: list[str] = [], send_event: bool = False
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
        rid = f"test::Resource[{agent},key={name}]"

        if increment:
            self.results[agent].append(rid)
        else:
            # make sure it is set in the default dict
            self.results[agent]

        for step in scenario.split():
            v -= 1
            if step.startswith("V"):
                continue
            match = self.scenario_step_regex.fullmatch(step)
            if match is None:
                raise Exception(f"Syntax error in scenario '{scenario}' of resource {name} at '{step}'")
            code = match.group(1)
            value = match.group(2)
            rvid = self.make_resource(name, value, v, agent, requires, send_event)
            state = self.expand_code(code)
            self.states[rvid] = state
            self.states_per_version[v][rvid] = state
        return rid

    async def setup_agent(self, server, environment):
        agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

        endpoints = list(self.results.keys())

        config.Config.set("config", "agent-deploy-interval", "0")
        config.Config.set("config", "agent-repair-interval", "0")

        a = Agent(hostname="node1", environment=environment, agent_map={e: "localhost" for e in endpoints}, code_loader=False)
        for e in endpoints:
            await a.add_end_point_name(e)
        await a.start()
        await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

        return a

    async def setup(
        self, serverdirect: OrchestrationService, resource_service: ResourceService, env: data.Environment, sid: UUID
    ):
        for version in range(0, len(self.versions)):
            # allocate a bunch of versions!
            v = await env.get_next_version()
            assert v == version + 1
            if self.versions[version]:
                res = await serverdirect.put_version(
                    env=env,
                    version=version,
                    resources=self.versions[version],
                    unknowns=[],
                    version_info={},
                    resource_state={},
                    compiler_version=get_compiler_version(),
                )
                assert res == 200

                result, _ = await serverdirect.release_version(env, version, False)
                assert result == 200

            for rid, state in self.states_per_version[version].items():
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
                result = await resource_service.resource_action_update(
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

        # increments are disjoint
        pos, neg = await data.ConfigurationModel.get_increment(env.id, version)
        assert set(pos).isdisjoint(set(neg)), set(pos).intersection(set(neg))

        # increments are complements, without the undeployables
        assert {
            Id.parse_id(resource["id"]).resource_str()
            for resource in self.versions[version]
            if self.states[resource["id"]] not in [ResourceState.skipped_for_undefined, ResourceState.undefined]
        } == set(pos).union(set(neg))

        allresources = {}

        for agent, results in self.results.items():
            result, payload = await resource_service.get_resources_for_agent(
                env, agent, version=None, incremental_deploy=True, sid=sid
            )
            assert result == 200
            assert sorted([x["resource_id"] for x in payload["resources"]]) == sorted(results)
            allresources.update({r["resource_id"]: r for r in payload["resources"]})

        return allresources


async def test_deploy(server, agent: Agent, environment, caplog):
    """
    Test basic deploy mechanism mocking
    """
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        orchestration_service = server.get_slice(SLICE_ORCHESTRATION)
        resource_service = server.get_slice(SLICE_RESOURCE)
        sid = agent.sessionid

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        version = await env.get_next_version()

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
                    "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
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
        res = await orchestration_service.put_version(
            env=env,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
            resource_state={},
            compiler_version=get_compiler_version(),
        )
        assert res == 200

        result, _ = await orchestration_service.release_version(env, version, False)
        assert result == 200

        resource_ids = [x["id"] for x in resources]

        # Start the deploy
        action_id = uuid.uuid4()
        now = datetime.now()
        result = await resource_service.resource_action_update(
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

        result, payload = await orchestration_service.get_version(env, version)
        assert result == 200
        assert payload["model"].done == len(resources)

        # second, identical check_version
        v2 = await env.get_next_version()
        resources = make_resources(v2)
        res = await orchestration_service.put_version(
            env=env,
            version=v2,
            resources=resources,
            unknowns=[],
            version_info={},
            resource_state={},
            compiler_version=get_compiler_version(),
        )
        assert res == 200

        result, payload = await resource_service.get_resources_for_agent(
            env, "agent1", version=None, incremental_deploy=True, sid=sid
        )
        assert len(payload["resources"]) == 0

        # Cannot request increment for specific version
        result, _ = await resource_service.get_resources_for_agent(
            env, "agent1", version=version, incremental_deploy=True, sid=sid
        )
        assert result == 500
        result, _ = await resource_service.get_resources_for_agent(env, "agent1", version=v2, incremental_deploy=True, sid=sid)
        assert result == 500

    assert_no_warning(caplog)


def strip_version(v):
    return sub(",v=[0-9]+", "", v)


async def test_deploy_scenarios(server, agent: Agent, environment, caplog):
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        orchestration_service = server.get_slice(SLICE_ORCHESTRATION)
        resource_service = server.get_slice(SLICE_RESOURCE)
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
        setup.add_resource("R14", "A1 A1 d1 D1", False)  # issue 5434
        setup.add_resource("R15", "SU1 A1", False)
        setup.add_resource("R16", "A1 SU1 A1", True)
        setup.add_resource("R17", "D1 SU1 A1", False)
        setup.add_resource("R18", "UD1 A1", False)
        setup.add_resource("R19", "UD1 D1", False)
        setup.add_resource("R20", "A1 UD1", True)
        setup.add_resource("R21", "S1", True)
        setup.add_resource("R22", "S1 D1", True)
        setup.add_resource("R23", "A1 S1 D1", True)
        setup.add_resource("R24", "UA1", True)
        setup.add_resource("R25", "UA1 D1", True)
        setup.add_resource("R26", "A1 UA1 D1", True)

        await setup.setup(orchestration_service, resource_service, env, sid)

    assert_no_warning(caplog)


async def test_deploy_scenarios_removed_req_by_increment(server, agent: Agent, environment, caplog):
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        orchestration_service = server.get_slice(SLICE_ORCHESTRATION)
        resource_service = server.get_slice(SLICE_RESOURCE)
        sid = agent.sessionid

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        setup = MultiVersionSetup()

        id1 = setup.add_resource("R1", "A1 D1", False)
        id2 = setup.add_resource("R2", "A1 D2", True, requires=[id1])

        resources = await setup.setup(orchestration_service, resource_service, env, sid)
        assert not resources[id2]["attributes"]["requires"]

    assert_no_warning(caplog)


async def test_deploy_scenarios_removed_req_by_increment2(server, environment, caplog):
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        orchestration_service = server.get_slice(SLICE_ORCHESTRATION)
        resource_service = server.get_slice(SLICE_RESOURCE)

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
            resources = await setup.setup(orchestration_service, resource_service, env, sid)
            print(sorted(resources[id2]["attributes"]["requires"]))
            print(sorted(sorted([id3, id4])))
            assert sorted([strip_version(r) for r in resources[id2]["attributes"]["requires"]]) == sorted([id3, id4])

        finally:
            await agent.stop()
    assert_no_warning(caplog)


async def test_deploy_scenarios_added_by_send_event(server, agent: Agent, environment, caplog):
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        orchestration_service = server.get_slice(SLICE_ORCHESTRATION)
        resource_service = server.get_slice(SLICE_RESOURCE)
        sid = agent.sessionid

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        setup = MultiVersionSetup()

        id1 = setup.add_resource("R1", "A1 D2", True, send_event=True)
        id2 = setup.add_resource("R2", "A1 D1", True, requires=[id1])
        id3 = setup.add_resource("R3", "A1 D1", True, requires=[id1], send_event=True)
        setup.add_resource("R4", "A1 D1", True, requires=[id3])
        setup.add_resource("R5", "A1 D1", False, requires=[id2])

        await setup.setup(orchestration_service, resource_service, env, sid)

    assert_no_warning(caplog)


async def test_deploy_scenarios_added_by_send_event_cad(server, agent_factory, environment, caplog):
    agent = await agent_factory(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost", "agent2": "localhost"},
        code_loader=False,
        agent_names=["agent1", "agent2"],
    )
    # ensure CAD does not change send_event
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        orchestration_service = server.get_slice(SLICE_ORCHESTRATION)
        resource_service = server.get_slice(SLICE_RESOURCE)
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
        await setup.setup(orchestration_service, resource_service, env, sid)

    assert_no_warning(caplog)


async def test_deploy_cad_double(server, agent_factory, environment, caplog, client, clienthelper):
    # resource has CAD with send_events B requires A
    # do full deploy
    # then produce a change on A
    # B is once more in the increment
    agent = await agent_factory(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost", "agent2": "localhost"},
        code_loader=False,
        agent_names=["agent1", "agent2"],
    )
    sid = agent.sessionid

    version = await clienthelper.get_version()
    rvid = f"test::Resource[agent1,key=key1],v={version}"
    rvid2 = f"test::Resource[agent2,key=key2],v={version}"

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": rvid,
            "send_event": True,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value1",
            "id": rvid2,
            "send_event": False,
            "purged": False,
            "requires": [rvid],
        },
    ]
    await clienthelper.put_version_simple(resources, version)
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    async def deploy(rid, change: Change = Change.nochange):
        actionid = uuid.uuid4()
        result = await agent._client.resource_deploy_start(environment, rid, actionid)
        assert result.code == 200
        await agent._client.resource_deploy_done(
            environment,
            rid,
            actionid,
            status=ResourceState.deployed,
            messages=[],
            changes={},
            change=change,
        )
        assert result.code == 200

    result = await agent._client.get_resources_for_agent(environment, "agent2", incremental_deploy=True, sid=sid)
    assert result.code == 200, result.result
    assert len(result.result["resources"]) == 1

    await deploy(rvid)
    await deploy(rvid2)

    result = await agent._client.get_resources_for_agent(environment, "agent2", incremental_deploy=True, sid=sid)
    assert result.code == 200, result.result
    assert len(result.result["resources"]) == 0

    await deploy(rvid, change=Change.updated)

    result = await agent._client.get_resources_for_agent(environment, "agent2", incremental_deploy=True, sid=sid)
    assert result.code == 200, result.result
    assert len(result.result["resources"]) == 1
