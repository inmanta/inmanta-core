"""
    Copyright 2019 Inmanta

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
import logging
import uuid

import pytest

from inmanta import const, data, resources
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.util import get_compiler_version
from utils import LogSequence, _wait_until_deployment_finishes, no_error_in_logs, retry_limited, wait_until_logs_are_available


@pytest.mark.asyncio
async def test_get_facts(resource_container, client, clienthelper, environment, agent, caplog):
    """
    Test retrieving facts from the agent
    """
    env_id = environment

    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{"key": "key", "value": "value", "id": resource_id, "requires": [], "purged": False, "send_event": False}]

    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_param(env_id, "length", resource_id_wov)
    assert result.code == 503

    env_uuid = uuid.UUID(env_id)
    params = await data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
    while len(params) < 3:
        params = await data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
        await asyncio.sleep(0.1)

    result = await client.get_param(env_id, "key1", resource_id_wov)
    assert result.code == 200
    no_error_in_logs(caplog)


@pytest.mark.asyncio
async def test_purged_facts(resource_container, client, clienthelper, agent, environment, no_agent_backoff, caplog):
    """
    Test if facts are purged when the resource is purged.
    """
    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()
    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{"key": "key", "value": "value", "id": resource_id, "requires": [], "purged": False, "send_event": False}]

    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_param(environment, "length", resource_id_wov)
    assert result.code == 503

    env_uuid = uuid.UUID(environment)
    params = await data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
    while len(params) < 3:
        params = await data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
        await asyncio.sleep(0.1)

    result = await client.get_param(environment, "key1", resource_id_wov)
    assert result.code == 200

    # Purge the resource
    version = await clienthelper.get_version()
    resources[0]["id"] = "%s,v=%d" % (resource_id_wov, version)
    resources[0]["purged"] = True
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    result = await client.get_version(environment, version)
    assert result.result["model"]["done"] == len(resources)

    # The resource facts should be purged
    result = await client.get_param(environment, "length", resource_id_wov)
    assert result.code == 503

    no_error_in_logs(caplog)


@pytest.mark.asyncio
async def test_get_facts_extended(server, client, agent, clienthelper, resource_container, environment, caplog):
    """
    dryrun and deploy a configuration model automatically
    """
    caplog.set_level(logging.ERROR)
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    # allow very rapid fact refresh
    agentmanager._fact_resource_block = 0.1

    resource_container.Provider.reset()

    version = await clienthelper.get_version()

    # mark some as existing
    resource_container.Provider.set("agent1", "key1", "value")
    resource_container.Provider.set("agent1", "key2", "value")
    resource_container.Provider.set("agent1", "key4", "value")
    resource_container.Provider.set("agent1", "key5", "value")
    resource_container.Provider.set("agent1", "key6", "value")
    resource_container.Provider.set("agent1", "key7", "value")

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Fact[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": True,
            "skipFact": False,
            "factvalue": "fk1",
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value1",
            "id": "test::Fact[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": False,
            "factvalue": "fk2",
            "requires": [],
        },
        {
            "key": "key3",
            "value": "value1",
            "id": "test::Fact[agent1,key=key3],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": False,
            "factvalue": "fk3",
            "requires": [],
        },
        {
            "key": "key4",
            "value": "value1",
            "id": "test::Fact[agent1,key=key4],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": False,
            "factvalue": "fk4",
            "requires": [],
        },
        {
            "key": "key5",
            "value": "value1",
            "id": "test::Fact[agent1,key=key5],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": True,
            "factvalue": None,
            "requires": [],
        },
        {
            "key": "key6",
            "value": "value1",
            "id": "test::Fact[agent1,key=key6],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": False,
            "factvalue": None,
            "requires": [],
        },
        {
            "key": "key7",
            "value": "value1",
            "id": "test::Fact[agent1,key=key7],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": False,
            "factvalue": "",
            "requires": [],
        },
    ]

    resource_states = {
        "test::Fact[agent1,key=key4],v=%d" % version: const.ResourceState.undefined,
        "test::Fact[agent1,key=key5],v=%d" % version: const.ResourceState.undefined,
    }

    async def get_fact(rid, result_code=200, limit=10, lower_limit=2):
        lower_limit = limit - lower_limit
        result = await client.get_param(environment, "fact", rid)

        # add minimal nr of reps or failure cases
        while (result.code != result_code and limit > 0) or limit > lower_limit:
            limit -= 1
            await asyncio.sleep(0.1)
            result = await client.get_param(environment, "fact", rid)

        assert result.code == result_code
        return result

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        resource_state=resource_states,
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    await get_fact("test::Fact[agent1,key=key1]")  # undeployable
    await get_fact("test::Fact[agent1,key=key2]")  # normal
    await get_fact("test::Fact[agent1,key=key3]", 503)  # not present
    await get_fact("test::Fact[agent1,key=key4]")  # unknown
    await get_fact("test::Fact[agent1,key=key5]", 503)  # broken
    f6 = await get_fact("test::Fact[agent1,key=key6]")  # normal
    f7 = await get_fact("test::Fact[agent1,key=key7]")  # normal

    assert f6.result["parameter"]["value"] == "None"
    assert f7.result["parameter"]["value"] == ""

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    await get_fact("test::Fact[agent1,key=key1]")  # undeployable
    await get_fact("test::Fact[agent1,key=key2]")  # normal
    await get_fact("test::Fact[agent1,key=key3]")  # not present -> present
    await get_fact("test::Fact[agent1,key=key4]")  # unknown
    await get_fact("test::Fact[agent1,key=key5]", 503)  # broken

    await agent.stop()

    LogSequence(caplog, allow_errors=False, ignore=["tornado.access"]).contains(
        "inmanta.agent.agent.agent1", logging.ERROR, "Unable to retrieve fact"
    ).contains("inmanta.agent.agent.agent1", logging.ERROR, "Unable to retrieve fact").contains(
        "inmanta.agent.agent.agent1", logging.ERROR, "Unable to retrieve fact"
    ).contains(
        "inmanta.agent.agent.agent1", logging.ERROR, "Unable to retrieve fact"
    ).contains(
        "inmanta.agent.agent.agent1", logging.ERROR, "Unable to retrieve fact"
    ).no_more_errors()


@pytest.mark.asyncio
async def test_purged_resources(resource_container, client, clienthelper, server, environment, agent, no_agent_backoff):
    """
    Test if:
        * Facts are purged when the resource is no longer available in any version.
        * Parameters with no resource attached are not deleted when a version is deleted.
    """
    resource_container.Provider.reset()

    resource_container.Provider.set("agent1", "key1", "value")

    res1 = "test::Resource[agent1,key=key1]"
    res2 = "test::Resource[agent1,key=key2]"

    # Add a resource independent parameter
    result = await client.set_param(
        tid=environment, id="test", source=const.ParameterSource.user, value="val", resource_id=None
    )
    assert result.code == 200

    # Create version 1 with 1 unknown
    version = await clienthelper.get_version()
    assert version == 1

    resources = [
        {"key": "key1", "value": "value", "id": f"{res1},v={version}", "requires": [], "purged": False, "send_event": False},
        {"key": "key2", "value": "value", "id": f"{res2},v={version}", "requires": [], "purged": False, "send_event": False},
    ]

    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    # Make sure we get facts
    result = await client.get_param(environment, "length", res1)
    assert result.code == 503

    result = await client.get_param(environment, "length", res2)
    assert result.code == 503

    env_uuid = uuid.UUID(environment)

    async def params_are_available() -> bool:
        params = await data.Parameter.get_list(environment=env_uuid)
        # 3 facts from res1 + 3 facts from res2 + parameter test
        return len(params) >= 7

    await retry_limited(params_are_available, 10)

    result = await client.get_param(environment, "key1", res1)
    assert result.code == 200

    result = await client.get_param(environment, "key2", res2)
    assert result.code == 200

    result = await client.get_param(environment, "test")
    assert result.code == 200

    # Create version 2
    version = await clienthelper.get_version()
    assert version == 2

    resources = [
        {"key": "key1", "value": "value", "id": f"{res1},v={version}", "requires": [], "purged": False, "send_event": False}
    ]

    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    # Remove version 1
    result = await client.delete_version(tid=environment, id=1)
    assert result.code == 200

    # There should be only one resource
    result = await client.get_environment(id=environment, resources=1)
    assert result.code == 200
    assert len(result.result["environment"]["resources"]) == 1

    # 3 facts from res1 + parameter test
    result = await client.list_params(environment)
    assert result.code == 200
    assert len(result.result["parameters"]) == 4

    # Remove version 2
    result = await client.delete_version(tid=environment, id=2)
    assert result.code == 200

    # Verify there are no resources anymore
    result = await client.get_environment(id=environment, resources=1)
    assert result.code == 200
    assert len(result.result["environment"]["resources"]) == 0

    # Only the resource independent parameter test should exist
    result = await client.list_params(environment)
    assert result.code == 200
    assert len(result.result["parameters"]) == 1


@pytest.mark.asyncio
async def test_get_fact_no_code(resource_container, client, clienthelper, environment, agent):
    """
    Test retrieving facts from the agent when resource cannot be loaded
    """
    env_id = environment
    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    await clienthelper.put_version_simple(
        [{"key": "key", "value": "value", "id": resource_id, "requires": [], "purged": False, "send_event": False}], version
    )

    response = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert response.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    # make sure the code to load the resource is no longer available
    resources.resource.reset()

    response = await client.get_param(env_id, "length", resource_id_wov)
    assert response.code == 503

    # The resource state and its logs are not set atomically. This call prevents a race condition.
    await wait_until_logs_are_available(client, environment, resource_id, expect_nr_of_logs=4)

    response = await client.get_resource(environment, resource_id, logs=True)
    assert response.code == 200
    result = response.result
    assert result["resource"]["status"] == "deployed"
    log_entry = result["logs"][0]
    assert log_entry["action"] == "getfact"
    assert log_entry["status"] == "unavailable"
    assert "Failed to load" in log_entry["messages"][0]["msg"]
