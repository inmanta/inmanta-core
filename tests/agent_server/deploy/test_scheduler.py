"""
    Copyright 2024 Inmanta

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

import copy
import logging
import typing
import uuid

import inmanta.execute.util
from inmanta import const, data
from inmanta.config import Config
from inmanta.deploy.scheduler import ResourceScheduler
from inmanta.util import get_compiler_version, retry_limited
from utils import UNKWN, ClientHelper, assert_equal_ish

logger = logging.getLogger("inmanta.test.server_agent")


async def test_deploy_new_scheduler(server, client, async_finalizer, no_agent_backoff):
    """
    This tests make sure the resource scheduler is working as expected for these parts:
        - Construction of initial model state
        - Retrieval of data when a new version is released
    """
    # First part - test the ResourceScheduler (retrieval of data from DB)
    Config.set("config", "agent-deploy-interval", "100")
    Config.set("server", "new-resource-scheduler", "True")

    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]
    env = await data.Environment.get_by_id(uuid.UUID(env_id))
    await env.set(data.AUTO_DEPLOY, False)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, False)
    await env.set(data.AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY, const.AgentTriggerMethod.push_full_deploy)

    clienthelper = ClientHelper(client, env_id)

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent2,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": inmanta.execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key4",
            "value": inmanta.execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key4],v=%d" % version,
            "send_event": False,
            "requires": ["test::Resource[agent2,key=key1],v=%d" % version, "test::Resource[agent2,key=key2],v=%d" % version],
            "purged": False,
        },
        {
            "key": "key5",
            "value": "val",
            "id": "test::Resource[agent2,key=key5],v=%d" % version,
            "send_event": False,
            "requires": ["test::Resource[agent2,key=key4],v=%d" % version],
            "purged": False,
        },
    ]

    status = {
        "test::Resource[agent2,key=key4]": const.ResourceState.undefined,
        "test::Resource[agent2,key=key2]": const.ResourceState.undefined,
    }
    result = await client.put_version(
        tid=env_id,
        version=version,
        resources=resources,
        resource_state=status,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    scheduler = ResourceScheduler(env_id)
    await scheduler.start()

    for resource in resources:
        id_without_version, _, _ = resource["id"].partition(",v=")
        assert id_without_version in scheduler._state.resources
        expected_resource_attributes = copy.deepcopy(resource)
        expected_resource_attributes.pop("id")
        current_attributes = scheduler._state.resources[id_without_version].attributes

        if current_attributes["value"] == "<<undefined>>" and isinstance(
            expected_resource_attributes["value"], inmanta.execute.util.Unknown
        ):
            expected_resource_attributes["value"] = "<<undefined>>"
        new_requires = []
        for require in expected_resource_attributes["requires"]:
            require_without_version, _, _ = require.partition(",v=")
            new_requires.append(require_without_version)
        expected_resource_attributes["requires"] = new_requires
        assert current_attributes == expected_resource_attributes
        # This resource has no requirements
        if id_without_version not in scheduler._state.requires._primary:
            assert expected_resource_attributes["requires"] == []
        else:
            assert scheduler._state.requires._primary[id_without_version] == set(expected_resource_attributes["requires"])

    version = await ClientHelper(client, env_id).get_version()

    # TODO: port this part

    # The purged status has been changed for: - `test::Resource[agent2,key=key2]` and `test::Resource[agent2,key=key4]`
    updated_resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent2,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": inmanta.execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key2],v=%d" % version,
            "send_event": False,
            "purged": True,
            "requires": [],
        },
        {
            "key": "key4",
            "value": inmanta.execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key4],v=%d" % version,
            "send_event": False,
            "requires": ["test::Resource[agent2,key=key1],v=%d" % version, "test::Resource[agent2,key=key2],v=%d" % version],
            "purged": True,
        },
        {
            "key": "key5",
            "value": "val",
            "id": "test::Resource[agent2,key=key5],v=%d" % version,
            "send_event": False,
            "requires": ["test::Resource[agent2,key=key4],v=%d" % version],
            "purged": False,
        },
    ]
    result = await client.put_version(
        tid=env_id,
        version=version,
        resources=updated_resources,
        resource_state=status,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # We test the new_version method the ResourceScheduler
    await scheduler.new_version()

    for resource in updated_resources:
        id_without_version, _, _ = resource["id"].partition(",v=")
        assert id_without_version in scheduler._state.resources
        expected_resource_attributes = copy.deepcopy(resource)
        expected_resource_attributes.pop("id")
        current_attributes = scheduler._state.resources[id_without_version].attributes

        if current_attributes["value"] == "<<undefined>>" and isinstance(
            expected_resource_attributes["value"], inmanta.execute.util.Unknown
        ):
            expected_resource_attributes["value"] = "<<undefined>>"
        new_requires = []
        for require in expected_resource_attributes["requires"]:
            require_without_version, _, _ = require.partition(",v=")
            new_requires.append(require_without_version)
        expected_resource_attributes["requires"] = new_requires
        assert current_attributes == expected_resource_attributes
        if id_without_version not in scheduler._state.requires._primary:
            assert expected_resource_attributes["requires"] == []
        else:
            assert scheduler._state.requires._primary[id_without_version] == set(expected_resource_attributes["requires"])

    # Now we make sure that the agent is up and running for this environment
    result = await client.list_agent_processes(env_id)
    assert result.code == 200

    async def done() -> bool:
        result = await client.list_agent_processes(env_id)
        assert result.code == 200
        return len(result.result["processes"]) == 1

    await retry_limited(done, 5)

    result = await client.list_agent_processes(env_id)
    assert len(result.result["processes"]) == 1

    endpoint_id: typing.Optional[uuid.UUID] = None
    for proc in result.result["processes"]:
        assert proc["environment"] == env_id
        assert len(proc["endpoints"]) == 1
        assert proc["endpoints"][0]["name"] == const.AGENT_SCHEDULER_ID
        endpoint_id = proc["endpoints"][0]["id"]
    assert endpoint_id is not None

    assert_equal_ish(
        {
            "processes": [
                {
                    "expired": None,
                    "environment": env_id,
                    "endpoints": [{"name": UNKWN, "process": UNKWN, "id": UNKWN}],
                    "hostname": UNKWN,
                    "first_seen": UNKWN,
                    "last_seen": UNKWN,
                },
            ]
        },
        result.result,
        ["name", "first_seen"],
    )

    # The agent was there because `ensure_agent_registered` was called each time we release a new version or call
    # `put_version` + `AUTO_DEPLOY` set to `True`
    # But this will be tested later in the test to make sure that when we create a new environment, everything is started and
    # registered correctly
    result = await client.list_agents(tid=env_id)
    assert result.code == 200

    expected_agent = {
        "agents": [
            {
                "last_failover": UNKWN,
                "environment": env_id,
                "paused": False,
                "primary": endpoint_id,
                "name": const.AGENT_SCHEDULER_ID,
                "state": "up",
            }
        ]
    }

    assert_equal_ish(expected_agent, result.result)

    # We test the creation of this new agent on another environment
    result = await client.create_environment(project_id=project_id, name="dev2")
    new_env_id = result.result["environment"]["id"]

    result = await client.list_agent_processes(new_env_id)
    assert result.code == 200

    async def done() -> bool:
        result = await client.list_agent_processes(new_env_id)
        assert result.code == 200
        return len(result.result["processes"]) == 1

    await retry_limited(done, 5)

    result = await client.list_agent_processes(new_env_id)
    assert len(result.result["processes"]) == 1

    new_endpoint_id: typing.Optional[uuid.UUID] = None
    for proc in result.result["processes"]:
        assert proc["environment"] == new_env_id
        assert len(proc["endpoints"]) == 1
        assert proc["endpoints"][0]["name"] == const.AGENT_SCHEDULER_ID
        new_endpoint_id = proc["endpoints"][0]["id"]
    assert new_endpoint_id is not None

    assert_equal_ish(
        {
            "processes": [
                {
                    "expired": None,
                    "environment": new_env_id,
                    "endpoints": [{"name": UNKWN, "process": UNKWN, "id": UNKWN}],
                    "hostname": UNKWN,
                    "first_seen": UNKWN,
                    "last_seen": UNKWN,
                },
            ]
        },
        result.result,
        ["name", "first_seen"],
    )

    result = await client.list_agents(tid=new_env_id)
    assert result.code == 200

    expected_agent = {
        "agents": [
            {
                "last_failover": UNKWN,
                "environment": new_env_id,
                "paused": False,
                "primary": new_endpoint_id,
                "name": const.AGENT_SCHEDULER_ID,
                "state": "up",
            }
        ]
    }

    assert_equal_ish(expected_agent, result.result)

    Config.set("server", "new-resource-scheduler", "False")