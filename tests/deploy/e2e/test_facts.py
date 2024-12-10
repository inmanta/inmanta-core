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

# Copied from old tests


import asyncio
import logging
import uuid
from typing import Any

import pytest

from inmanta import const, data, resources
from inmanta.const import ParameterSource
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_PARAM
from inmanta.util import get_compiler_version
from utils import (
    _deploy_resources,
    get_done_count,
    no_error_in_logs,
    retry_limited,
    wait_for_n_deployed_resources,
    wait_until_deployment_finishes,
    wait_until_logs_are_available,
)


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

    async def has_params():
        params = await data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
        return len(params) >= 3

    await retry_limited(has_params, 5)

    result = await client.get_param(env_id, "key1", resource_id_wov)
    assert result.code == 200
    no_error_in_logs(caplog)


async def test_purged_facts(resource_container, client, clienthelper, agent, environment, caplog):
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

    async def wait_for_three_params():
        params = await data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
        return len(params) >= 3

    await retry_limited(wait_for_three_params, 10)

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

    await wait_until_deployment_finishes(client, environment)

    assert await get_done_count(client, environment) == len(resources)

    # The resource facts should be purged
    result = await client.get_param(environment, "length", resource_id_wov)
    assert result.code == 503

    no_error_in_logs(caplog)


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
        "test::Fact[agent1,key=key4]": const.ResourceState.undefined,
        "test::Fact[agent1,key=key1]": const.ResourceState.undefined,
        "test::Fact[agent1,key=key5]": const.ResourceState.undefined,
    }

    async def get_fact(rid, result_code=200, limit=10, lower_limit=2):
        lower_limit = limit - lower_limit
        result = await client.get_param(environment, "fact", rid)

        # add minimal nr of reps or failure cases
        while (result.code != result_code and limit > 0) or limit > lower_limit:
            limit -= 1
            await asyncio.sleep(0.1)
            result = await client.get_param(environment, "fact", rid)

        assert result.code == result_code, result.result
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

    # THIS IS A BEHAVIOR CHANGE: NO FACTS IF NOT RELEASED
    # await get_fact("test::Fact[agent1,key=key1]", 503)  # undeployable
    # await get_fact("test::Fact[agent1,key=key2]")  # normal
    # await get_fact("test::Fact[agent1,key=key3]", 503)  # not present
    # await get_fact("test::Fact[agent1,key=key4]", 503)  # unknown
    # await get_fact("test::Fact[agent1,key=key5]", 503)  # broken
    # f6 = await get_fact("test::Fact[agent1,key=key6]")  # normal
    # f7 = await get_fact("test::Fact[agent1,key=key7]")  # normal
    #
    # assert f6.result["parameter"]["value"] == "None"
    # assert f7.result["parameter"]["value"] == ""

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await wait_until_deployment_finishes(client, environment)

    await get_fact("test::Fact[agent1,key=key1]", 503, lower_limit=0)  # undeployable
    await get_fact("test::Fact[agent1,key=key2]")  # normal
    await get_fact("test::Fact[agent1,key=key3]")  # not present -> present
    pytest.skip("No unknowns yet!")
    await get_fact("test::Fact[agent1,key=key4]", 503)  # unknown
    await get_fact("test::Fact[agent1,key=key5]", 503)  # broken


async def test_purged_resources(resource_container, client, clienthelper, server, environment, agent):
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

    await wait_until_deployment_finishes(client, environment)

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

    # Create version 3 to be able to delete version 2
    version = await clienthelper.get_version()
    assert version == 3

    await clienthelper.put_version_simple([], version)

    result = await client.release_version(
        environment, version, push=False, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

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

    await wait_until_deployment_finishes(client, environment)

    # make sure the code to load the resource is no longer available
    resources.resource.reset()

    response = await client.get_param(env_id, "length", resource_id_wov)
    assert response.code == 503

    # The resource state and its logs are not set atomically. This call prevents a race condition.
    await wait_until_logs_are_available(client, environment, resource_id, expect_nr_of_logs=3)

    response = await client.get_resource(environment, resource_id, logs=True)
    assert response.code == 200
    result = response.result
    log_entry = result["logs"][0]
    assert log_entry["action"] == "getfact"
    assert log_entry["status"] == "unavailable"
    assert "Unable to deserialize" in log_entry["messages"][0]["msg"]


async def test_bad_post_get_facts(resource_container, server, client, agent, clienthelper, environment, caplog):
    """
    Test retrieving facts from the agent
    """
    caplog.set_level(logging.ERROR)

    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::BadPost[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": resource_id,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        }
    ]

    await clienthelper.put_version_simple(resources, version)

    caplog.clear()

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await wait_until_deployment_finishes(client, environment)

    assert "An error occurred after deployment of test::BadPost[agent1,key=key]" in caplog.text
    caplog.clear()

    result = await client.get_param(environment, "length", resource_id_wov)
    assert result.code == 503

    env_uuid = uuid.UUID(environment)

    async def has_at_least_three_parameters() -> bool:
        params = await data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
        return len(params) >= 3

    await retry_limited(has_at_least_three_parameters, timeout=10)

    result = await client.get_param(environment, "key1", resource_id_wov)
    assert result.code == 200

    assert "An error occurred after getting facts about test::BadPost" in caplog.text


async def test_set_fact_in_handler(server, client, environment, agent, clienthelper, resource_container):
    """
    Test whether facts set in the handler via the ctx.set_fact() method arrive on the server.
    """

    def get_resources(version: str, params: list[data.Parameter]) -> list[dict[str, Any]]:
        return [
            {
                "key": param.name,
                "value": param.value,
                "metadata": param.metadata,
                "id": f"{param.resource_id},v={version}",
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "purge_on_delete": False,
                "requires": [],
            }
            for param in params
        ]

    def compare_params(actual_params: list[data.Parameter], expected_params: list[data.Parameter]) -> None:
        actual_params = sorted(actual_params, key=lambda p: p.name)
        expected_params = sorted(expected_params, key=lambda p: p.name)
        assert len(expected_params) == len(actual_params)
        for i in range(len(expected_params)):
            for attr_name in ["name", "value", "environment", "resource_id", "source", "metadata"]:
                assert getattr(expected_params[i], attr_name) == getattr(actual_params[i], attr_name)

    # Assert initial state
    params = await data.Parameter.get_list()
    assert len(params) == 0

    param1 = data.Parameter(
        name="key1",
        value="value1",
        environment=uuid.UUID(environment),
        resource_id="test::SetFact[agent1,key=key1]",
        source=ParameterSource.fact.value,
        expires=True,
    )
    param2 = data.Parameter(
        name="key2",
        value="value2",
        environment=uuid.UUID(environment),
        resource_id="test::SetFact[agent1,key=key2]",
        source=ParameterSource.fact.value,
        expires=True,
    )

    version = await clienthelper.get_version()
    resources = get_resources(version, [param1, param2])

    # Ensure that facts are pushed when ctx.set_fact() is called during resource deployment
    await _deploy_resources(client, environment, resources, version, push=True)
    await wait_for_n_deployed_resources(client, environment, version, n=2)

    params = await data.Parameter.get_list()
    compare_params(params, [param1, param2])

    # Ensure that:
    # * Facts set in the handler.facts() method via ctx.set_fact() method are pushed to the Inmanta server.
    # * Facts returned via the handler.facts() method are pushed to the Inmanta server.
    await asyncio.gather(*[p.delete() for p in params])
    params = await data.Parameter.get_list()
    assert len(params) == 0
    agent_manager = server.get_slice(name=SLICE_AGENT_MANAGER)
    agent_manager._fact_resource_block = 0

    result = await client.get_param(tid=environment, id="key1", resource_id="test::SetFact[agent1,key=key1]")
    assert result.code == 503
    result = await client.get_param(tid=environment, id="key2", resource_id="test::SetFact[agent1,key=key2]")
    assert result.code == 503

    async def _wait_until_facts_are_available():
        params = await data.Parameter.get_list()
        return len(params) == 4

    await retry_limited(_wait_until_facts_are_available, 10)

    param3 = data.Parameter(
        name="returned_fact_key1",
        value="test",
        environment=uuid.UUID(environment),
        resource_id="test::SetFact[agent1,key=key1]",
        source=ParameterSource.fact.value,
        expires=True,
    )
    param4 = data.Parameter(
        name="returned_fact_key2",
        value="test",
        environment=uuid.UUID(environment),
        resource_id="test::SetFact[agent1,key=key2]",
        source=ParameterSource.fact.value,
        expires=True,
    )

    params = await data.Parameter.get_list()
    compare_params(params, [param1, param2, param3, param4])


async def test_set_non_expiring_fact_in_handler_6560(server, client, environment, agent, clienthelper, resource_container):
    """
    Check that getting a non expiring fact doesn't trigger a parameter request from the agent.
    In this test:
        - create 2 facts, one that expires, one that doesn't expire
        - wait for the _fact_expire delay
        - when getting the facts back, check that only the fact that does expire triggers a refresh from the agent
    """

    # Setup a high fact expiry rate:
    param_service = server.get_slice(SLICE_PARAM)
    param_service._fact_expire = 0.1

    def get_resources(version: str, params: list[data.Parameter]) -> list[dict[str, Any]]:
        return [
            {
                "key": param.name,
                "value": param.value,
                "metadata": param.metadata,
                "id": f"{param.resource_id},v={version}",
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "purge_on_delete": False,
                "requires": [],
            }
            for param in params
        ]

    def compare_params(actual_params: list[data.Parameter], expected_params: list[data.Parameter]) -> None:
        actual_params = sorted(actual_params, key=lambda p: p.name)
        expected_params = sorted(expected_params, key=lambda p: p.name)
        assert len(expected_params) == len(actual_params), f"{expected_params=} {actual_params=}"
        for i in range(len(expected_params)):
            for attr_name in ["name", "value", "environment", "resource_id", "source", "metadata", "expires"]:
                expected = getattr(expected_params[i], attr_name)
                actual = getattr(actual_params[i], attr_name)
                assert expected == actual, f"{expected=} {actual=}"

    # Assert initial state
    params = await data.Parameter.get_list()
    assert len(params) == 0

    param1 = data.Parameter(
        name="non_expiring",
        value="value1",
        environment=uuid.UUID(environment),
        resource_id="test::SetNonExpiringFact[agent1,key=non_expiring]",
        source=ParameterSource.fact.value,
        expires=False,
    )
    param2 = data.Parameter(
        name="expiring",
        value="value2",
        environment=uuid.UUID(environment),
        resource_id="test::SetNonExpiringFact[agent1,key=expiring]",
        source=ParameterSource.fact.value,
        expires=True,
    )

    version = await clienthelper.get_version()
    resources = get_resources(version, [param1, param2])

    # Ensure that facts are pushed when ctx.set_fact() is called during resource deployment
    await _deploy_resources(client, environment, resources, version, push=True)
    await wait_for_n_deployed_resources(client, environment, version, n=2, timeout=10)

    params = await data.Parameter.get_list()
    compare_params(params, [param1, param2])

    # Ensure that:
    # * Facts set in the handler.facts() method via ctx.set_fact() method are pushed to the Inmanta server.
    # * Facts returned via the handler.facts() method are pushed to the Inmanta server.
    await asyncio.gather(*[p.delete() for p in params])
    params = await data.Parameter.get_list()
    assert len(params) == 0

    result = await client.get_param(
        tid=environment, id="non_expiring", resource_id="test::SetNonExpiringFact[agent1,key=non_expiring]"
    )
    assert result.code == 503
    result = await client.get_param(tid=environment, id="expiring", resource_id="test::SetNonExpiringFact[agent1,key=expiring]")
    assert result.code == 503

    async def _wait_until_facts_are_available():
        params = await data.Parameter.get_list()
        return len(params) == 2

    await retry_limited(_wait_until_facts_are_available, 10)

    # Wait for a bit to let facts expire
    await asyncio.sleep(0.5)

    # Non expiring fact is returned straight away
    result = await client.get_param(
        tid=environment, id="non_expiring", resource_id="test::SetNonExpiringFact[agent1,key=non_expiring]"
    )
    assert result.code == 200
    # Expired fact has to be refreshed
    result = await client.get_param(tid=environment, id="expiring", resource_id="test::SetNonExpiringFact[agent1,key=expiring]")
    assert result.code == 503

    await retry_limited(_wait_until_facts_are_available, 10)

    params = await data.Parameter.get_list()
    compare_params(params, [param1, param2])
