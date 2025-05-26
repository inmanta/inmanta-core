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

import pytest

from inmanta import const, data, util
from inmanta.agent.executor import DeployReport
from inmanta.const import Change, ResourceState
from inmanta.deploy import persistence, state
from inmanta.resources import Id
from inmanta.server import SLICE_ORCHESTRATION, SLICE_RESOURCE
from inmanta.server.services.orchestrationservice import OrchestrationService
from inmanta.server.services.resourceservice import ResourceService
from inmanta.types import ResourceVersionIdStr
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
    SU - skipped for undefined
    UD - undefined
    """

    scenario_step_regex = re.compile(r"(A|E|D|d|S|SU|UA|UD)([0-9]+)")

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

    async def setup(self, client, serverdirect: OrchestrationService, resource_service: ResourceService, env: data.Environment):
        latest_released_version = -1
        update_manager = persistence.ToDbUpdateManager(client, env.id)
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
                    module_version_info={},
                )
                assert res == 200

                result, _ = await serverdirect.release_version(env, version, False)
                assert result == 200
                latest_released_version = version

            for rid, resource_state in self.states_per_version[version].items():
                # Start the deploy
                action_id = uuid.uuid4()
                now = datetime.now()
                if resource_state == const.ResourceState.available:
                    # initial state can not be set
                    continue
                parsed_rid = Id.parse_id(rid)
                await update_manager.send_in_progress(action_id, parsed_rid)
                if resource_state not in const.TRANSIENT_STATES:
                    # Handler resource state
                    match resource_state:
                        case const.ResourceState.deployed:
                            handler_resource_state = const.HandlerResourceState.deployed
                        case const.ResourceState.failed:
                            handler_resource_state = const.HandlerResourceState.failed
                        case const.ResourceState.unavailable:
                            handler_resource_state = const.HandlerResourceState.unavailable
                        case _:
                            handler_resource_state = const.HandlerResourceState.skipped
                    # Compliance
                    match resource_state:
                        case const.ResourceState.deployed:
                            compliance = state.Compliance.COMPLIANT
                        case const.ResourceState.undefined:
                            compliance = state.Compliance.UNDEFINED
                        case _:
                            compliance = state.Compliance.NON_COMPLIANT
                    await update_manager.send_deploy_done(
                        attribute_hash=util.make_attribute_hash(
                            resource_id=parsed_rid.resource_str(), attributes=self.versions[version][0]
                        ),
                        result=DeployReport(
                            rvid=parsed_rid.resource_version_str(),
                            action_id=action_id,
                            resource_state=handler_resource_state,
                            messages=[],
                            changes={},
                            change=const.Change.nochange,
                        ),
                        state=state.ResourceState(
                            compliance=compliance,
                            last_deploy_result=state.DeployResult.DEPLOYED,
                            blocked=(
                                state.Blocked.BLOCKED
                                if handler_resource_state is const.HandlerResourceState.skipped
                                else state.Blocked.NOT_BLOCKED
                            ),
                            last_deployed=now,
                        ),
                        started=now,
                        finished=now,
                    )

        assert latest_released_version != -1

        # increments are disjoint
        pos, neg = await data.ConfigurationModel.get_increment(env.id, version)
        assert set(pos).isdisjoint(set(neg)), set(pos).intersection(set(neg))

        # increments are complements, without the undeployables
        assert {
            Id.parse_id(resource["id"]).resource_str()
            for resource in self.versions[version]
            if self.states[resource["id"]] not in [ResourceState.skipped_for_undefined, ResourceState.undefined]
        } == set(pos).union(set(neg))


async def test_deploy(server, client, null_agent, environment, caplog, clienthelper):
    """
    Test basic deploy mechanism mocking
    """
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        orchestration_service = server.get_slice(SLICE_ORCHESTRATION)

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        version = await env.get_next_version()

        def make_resources(version: int):
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
            module_version_info={},
        )
        assert res == 200

        result, _ = await orchestration_service.release_version(env, version, False)
        assert result == 200

        # Deploy each resource
        update_manager = persistence.ToDbUpdateManager(client, env.id)
        for resource in resources:
            action_id = uuid.uuid4()
            now = datetime.now()
            rid = Id.parse_id(resource["id"])
            await update_manager.send_in_progress(action_id, rid)

            await update_manager.send_deploy_done(
                attribute_hash=util.make_attribute_hash(resource_id=rid.resource_str(), attributes=resource),
                result=DeployReport(
                    rvid=rid.resource_version_str(),
                    action_id=action_id,
                    resource_state=const.HandlerResourceState.deployed,
                    messages=[],
                    changes={},
                    change=const.Change.updated,
                ),
                state=state.ResourceState(
                    compliance=state.Compliance.COMPLIANT,
                    last_deploy_result=state.DeployResult.DEPLOYED,
                    blocked=state.Blocked.NOT_BLOCKED,
                    last_deployed=now,
                ),
                started=now,
                finished=now,
            )

        result, payload = await orchestration_service.get_version(env, version)
        assert result == 200
        assert await clienthelper.done_count() == len(resources)

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
            module_version_info={},
        )
        assert res == 200

        increment, _ = await data.ConfigurationModel.get_increment(environment, version=v2)
        assert len(increment) == 0

    assert_no_warning(caplog)


def strip_version(v):
    return sub(",v=[0-9]+", "", v)


async def test_deploy_scenarios(server, client, null_agent, environment, caplog):
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        orchestration_service = server.get_slice(SLICE_ORCHESTRATION)
        resource_service = server.get_slice(SLICE_RESOURCE)

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

        await setup.setup(client, orchestration_service, resource_service, env)

    assert_no_warning(caplog)


async def test_deploy_scenarios_added_by_send_event(server, client, null_agent, environment, caplog):
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        orchestration_service = server.get_slice(SLICE_ORCHESTRATION)
        resource_service = server.get_slice(SLICE_RESOURCE)

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        setup = MultiVersionSetup()

        id1 = setup.add_resource("R1", "A1 D2", True, send_event=True)
        id2 = setup.add_resource("R2", "A1 D1", True, requires=[id1])
        id3 = setup.add_resource("R3", "A1 D1", True, requires=[id1], send_event=True)
        setup.add_resource("R4", "A1 D1", True, requires=[id3])
        setup.add_resource("R5", "A1 D1", False, requires=[id2])

        await setup.setup(client, orchestration_service, resource_service, env)

    assert_no_warning(caplog)


async def test_deploy_scenarios_added_by_send_event_cad(server, client, null_agent, environment, caplog):
    # ensure CAD does not change send_event
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        orchestration_service = server.get_slice(SLICE_ORCHESTRATION)
        resource_service = server.get_slice(SLICE_RESOURCE)

        # acquire env object
        env = await data.Environment.get_by_id(uuid.UUID(environment))

        setup = MultiVersionSetup()

        id1 = setup.add_resource("R1", "A1 D2", True, send_event=False)
        id2 = setup.add_resource("R2", "A1 D1", False, requires=[id1])
        id3 = setup.add_resource("R3", "A1 D1", False, requires=[id1], send_event=True)
        setup.add_resource("R4", "A1 D1", False, requires=[id3])
        setup.add_resource("R5", "A1 D1", False, requires=[id2])

        setup.add_resource("R6", "A1 D1", False, requires=[id1], agent="agent2")
        await setup.setup(client, orchestration_service, resource_service, env)

    assert_no_warning(caplog)


async def test_deploy_cad_double(server, null_agent, environment, caplog, client, clienthelper):
    version = await clienthelper.get_version()
    rvid = ResourceVersionIdStr(f"test::Resource[agent1,key=key1],v={version}")
    rvid2 = ResourceVersionIdStr(f"test::Resource[agent2,key=key2],v={version}")

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

    async def deploy(rvid: ResourceVersionIdStr, change: Change = Change.nochange):
        update_manager = persistence.ToDbUpdateManager(client, uuid.UUID(environment))
        action_id = uuid.uuid4()
        start_time: datetime = datetime.now().astimezone()
        rid = Id.parse_id(rvid)
        await update_manager.send_in_progress(action_id, rid)
        await update_manager.send_deploy_done(
            attribute_hash=util.make_attribute_hash(resource_id=rid.resource_str(), attributes=resources[0]),
            result=DeployReport(
                rvid=rvid,
                action_id=action_id,
                resource_state=const.HandlerResourceState.deployed,
                messages=[],
                changes={},
                change=change,
            ),
            state=state.ResourceState(
                compliance=state.Compliance.COMPLIANT,
                last_deploy_result=state.DeployResult.DEPLOYED,
                blocked=state.Blocked.NOT_BLOCKED,
                last_deployed=datetime.now().astimezone(),
            ),
            started=start_time,
            finished=datetime.now().astimezone(),
        )

    async def assert_resources_to_deploy(
        environment: uuid.UUID, agent: str, version: int, expected_nr_of_resources: int
    ) -> None:
        increment, _ = await data.ConfigurationModel.get_increment(environment, version=version)
        resource_for_agent = [rid for rid in increment if Id.parse_id(rid).agent_name == agent]
        assert len(resource_for_agent) == expected_nr_of_resources

    await assert_resources_to_deploy(UUID(environment), agent="agent2", version=version, expected_nr_of_resources=1)

    await deploy(rvid)
    await deploy(rvid2)

    await assert_resources_to_deploy(UUID(environment), agent="agent2", version=version, expected_nr_of_resources=0)

    await deploy(rvid, change=Change.updated)

    await assert_resources_to_deploy(UUID(environment), agent="agent2", version=version, expected_nr_of_resources=1)


@pytest.mark.slowtest
async def test_release_stuck(
    server,
    environment,
    clienthelper,
    client,
    project_default,
):
    async def make_version() -> int:
        version = await clienthelper.get_version()
        rvid = f"test::Resource[agent1,key=key1],v={version}"
        resources = [
            {
                "key": "key1",
                "value": "value1",
                "id": rvid,
                "change": False,
                "send_event": True,
                "purged": False,
                "requires": [],
                "purge_on_delete": False,
            },
        ]
        await clienthelper.put_version_simple(resources, version, wait_for_released=True)
        return version

        # set auto deploy and push

    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200

    #  a version v1 is deploying
    await make_version()

    #  a version v2 is deploying
    await make_version()

    # Delete environment
    result = await client.environment_delete(environment)
    assert result.code == 200

    # Re-create
    result = await client.create_environment(project_id=project_default, name="env", environment_id=environment)
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200

    await make_version()
    # This will time-out when there is a run_ahead_lock still in place
    await make_version()
