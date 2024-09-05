"""
    Copyright 2017 Inmanta

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
import copy
import logging
import uuid

import inmanta.execute.util
from inmanta import const, data
from inmanta.config import Config
from inmanta.deploy.scheduler import ResourceScheduler
from inmanta.util import get_compiler_version
from utils import UNKWN, ClientHelper, assert_equal_ish

logger = logging.getLogger("inmanta.test.server_agent")


async def test_deploy_new_scheduler(server, client, async_finalizer, no_agent_backoff):
    """
    Test deploy of resource with undefined
    """
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

    scheduler = ResourceScheduler()
    await scheduler.start()
    for resource in resources:
        id_without_version, _, _ = resource["id"].partition(",v=")
        assert id_without_version in scheduler._state.resources
        expected_resource_attributes = copy.deepcopy(resource)
        expected_resource_attributes.pop("id")
        current_attributes = scheduler._state.resources[id_without_version].attributes
        # TODO h ResourceScheduler -> Unknown == undefined?
        # TODO h ResourceScheduler -> loose version information on requires?

        # Already a todo for that
        # TODO h ResourceScheduler -> undefined status lost in the process -> has update / new only?
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
        assert scheduler._state.requires._primary[id_without_version] == set(expected_resource_attributes["requires"])

    version = await ClientHelper(client, env_id).get_version()

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
    await scheduler.new_version(env_id)
    # TODO h ResourceScheduler crashing on -> self._agent_queues["TODO"].put_nowait(item)

    for resource in updated_resources:
        id_without_version, _, _ = resource["id"].partition(",v=")
        assert id_without_version in scheduler._state.resources
        expected_resource_attributes = copy.deepcopy(resource)
        expected_resource_attributes.pop("id")
        current_attributes = scheduler._state.resources[id_without_version].attributes
        # TODO h ResourceScheduler -> Unknown == undefined?
        # TODO h ResourceScheduler -> loose version information on requires?

        # Already a todo for that
        # TODO h ResourceScheduler -> undefined status lost in the process -> has update / new only?
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
        assert scheduler._state.requires._primary[id_without_version] == set(expected_resource_attributes["requires"])

    result = await client.list_agent_processes(env_id)
    assert result.code == 200

    while len(result.result["processes"]) != 1:
        result = await client.list_agent_processes(env_id)
        assert result.code == 200
        await asyncio.sleep(0.1)

    assert len(result.result["processes"]) == 1
    for proc in result.result["processes"]:
        assert proc["environment"] == env_id
        assert len(proc["endpoints"]) == 1
        assert proc["endpoints"][0]["name"] == const.AGENT_SCHEDULER_ID

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

    endpointid = [
        x["endpoints"][0]["id"] for x in result.result["processes"] if x["endpoints"][0]["name"] == const.AGENT_SCHEDULER_ID
    ][0]

    result = await client.list_agents(tid=env_id)
    assert result.code == 200

    expected_agent = {
        "agents": [
            {
                "last_failover": UNKWN,
                "environment": env_id,
                "paused": False,
                "primary": endpointid,
                "name": const.AGENT_SCHEDULER_ID,
                "state": "up",
            }
        ]
    }

    assert_equal_ish(expected_agent, result.result)

    result = await client.create_environment(project_id=project_id, name="dev2")
    new_env_id = result.result["environment"]["id"]

    result = await client.list_agent_processes(new_env_id)
    assert result.code == 200

    while len(result.result["processes"]) != 1:
        result = await client.list_agent_processes(new_env_id)
        assert result.code == 200
        await asyncio.sleep(0.1)

    assert len(result.result["processes"]) == 1
    for proc in result.result["processes"]:
        assert proc["environment"] == new_env_id
        assert len(proc["endpoints"]) == 1
        assert proc["endpoints"][0]["name"] == const.AGENT_SCHEDULER_ID

    new_endpoint_id = [
        x["endpoints"][0]["id"] for x in result.result["processes"] if x["endpoints"][0]["name"] == const.AGENT_SCHEDULER_ID
    ][0]

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
