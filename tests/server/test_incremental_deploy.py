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
import pytest
import time
from inmanta.server import SLICE_SERVER
import uuid
from datetime import datetime
from inmanta import data, const
from inmanta.const import ResourceState, ResourceAction
import logging


class MultiVersionSetup(object):
    """
      create scenarios by describing the history of a resource, from newest to oldest state

      V = void, nothing
      A - available/skipped/unavailable
      E - error
      D - deployed
      S - skipped for undefined
      U - undefined
    """

    def __init__(self):
        self.firstversion = 100
        self.versions = [[] for _ in range(100)]
        self.states = {}
        self.results = []

    def get_version(self, v):
        return self.versions[v]

    def expand_code(self, code):
        if code == "A":
            return ResourceState.available

        if code == "E":
            return ResourceState.failed

        if code == "D":
            return ResourceState.deployed

        if code == "S":
            return ResourceState.skipped_for_undefined

        if code == "U":
            return ResourceState.undefined

        assert False

    def make_resource(self, name, value, version, agent="agent1"):
        id = "test::Resource[%s,key=%s],v=%d" % (agent, name, version)
        res = {
            "key": value,
            "id": id,
            "send_event": False,
            "purged": False,
            "requires": [],
        }
        self.get_version(version).append(res)
        return id

    def add_resource(self, name, scenario, increment, agent="agent1"):
        v = self.firstversion
        rid = "test::Resource[%s,key=%s]" % (agent, name)

        if increment:
            self.results.append(rid)

        for step in scenario.split():
            v -= 1
            code = step[0]
            if code == "V":
                continue
            value = step[1:]
            rvid = self.make_resource(name, value, v, agent)
            self.states[rvid] = self.expand_code(code)

    async def setup(self, serverdirect, env):
        for version in range(0, len(self.versions)):
            if self.versions[version]:
                res = await serverdirect.put_version(
                    env=env,
                    version=version,
                    resources=self.versions[version],
                    unknowns=[],
                    version_info={},
                    resource_state={},
                )
                assert res == 200

                result, _ = await serverdirect.release_version(env, version, push=False)
                assert result == 200
        for rid, state in self.states.items():
            # Start the deploy
            action_id = uuid.uuid4()
            now = datetime.now()
            result = await serverdirect.resource_action_update(
                env,
                [rid],
                action_id,
                ResourceAction.deploy,
                now,
                now,
                status=state,
                messages=[],
                changes={},
                change=None,
                send_events=False,
            )
            assert result == 200

        result, payload = await serverdirect.get_resource_increment_for_agent(
            env, "agent1"
        )
        print(sorted([x["resource_id"] for x in payload["resources"]]))
        assert sorted([x["resource_id"] for x in payload["resources"]]) == sorted(self.results)


@pytest.mark.asyncio
async def test_deploy(server, environment, caplog):
    """
        Test basic deploy mechanism mocking
    """
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        serverdirect = server.get_endpoint(SLICE_SERVER)

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
                {
                    "key": "key4",
                    "id": "test::Resource[agent2,key=key4],v=%d" % version,
                    "send_event": False,
                    "requires": [],
                },
            ]

        resources = make_resources(version)
        res = await serverdirect.put_version(
            env=env,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
            resource_state={},
        )
        assert res == 200

        result, _ = await serverdirect.release_version(env, version, push=False)
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
            env=env,
            version=v2,
            resources=resources,
            unknowns=[],
            version_info={},
            resource_state={},
        )
        assert res == 200

        result, payload = await serverdirect.get_resource_increment_for_agent(
            env, "agent1"
        )
        assert len(payload["resources"]) == 0

    for record in caplog.records:
        assert record.levelname != "WARNING"


@pytest.mark.asyncio
async def test_deploy_scenarios(server, environment, caplog):
    with caplog.at_level(logging.WARNING):
        # acquire raw server
        serverdirect = server.get_endpoint(SLICE_SERVER)

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

        await setup.setup(serverdirect, env)

    for record in caplog.records:
        assert record.levelname != "WARNING"
