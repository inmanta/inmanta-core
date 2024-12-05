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

import logging
import time
from uuid import UUID

import pytest

from inmanta import const
from inmanta.config import Config
from utils import get_resource, log_contains, log_doesnt_contain, resource_action_consistency_check, retry_limited


@pytest.mark.skip("Broken")
async def test_deploy_trigger(server, client, clienthelper, resource_container, environment, caplog, agent):
    """
    Test deployment of empty model
    """
    caplog.set_level(logging.INFO)

    version = await clienthelper.get_version()

    resources = [
        get_resource(version, agent="agent1"),
        get_resource(version, agent="agent2"),
        get_resource(version, agent="agent3"),
    ]

    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    await clienthelper.wait_for_deployed(version)

    async def verify(result, a1=0, code=200, warnings=["Could not reach agents named [agent2,agent3]"], agents=["agent1"]):
        assert result.code == code

        def is_deployed():
            return resource_container.Provider.readcount("agent1", "key1") == a1

        await retry_limited(is_deployed, 1)
        log_contains(caplog, "agent", logging.INFO, f"Agent agent1 got a trigger to update in environment {environment}")
        log_doesnt_contain(caplog, "agent", logging.INFO, f"Agent agent5 got a trigger to update in environment {environment}")

        assert result.result["agents"] == agents
        if warnings:
            assert sorted(result.result["metadata"]["warnings"]) == sorted(warnings)
        caplog.clear()

    async def verify_failed(result, code=400, message="", warnings=["Could not reach agents named [agent2,agent3]"]):
        assert result.code == code

        log_doesnt_contain(caplog, "agent", logging.INFO, "got a trigger to update")
        if warnings:
            assert sorted(result.result["metadata"]["warnings"]) == sorted(warnings)
        assert result.result["message"] == message
        caplog.clear()

    # normal
    result = await client.deploy(environment)
    await verify(result, a1=1)

    # only agent1
    result = await client.deploy(environment, agents=["agent1"])
    await verify(result, a1=2, warnings=None)

    # only agent5 (not in model)
    result = await client.deploy(environment, agents=["agent5"])
    await verify_failed(
        result, 404, "No agent could be reached", warnings=[f"Model version {version} does not contain agents named [agent5]"]
    )

    # only agent2 (not alive)
    result = await client.deploy(environment, agents=["agent2"])
    await verify_failed(result, 404, "No agent could be reached", warnings=["Could not reach agents named [agent2]"])

    # All of it
    result = await client.deploy(environment, agents=["agent1", "agent2", "agent5"])
    await verify(
        result,
        a1=3,
        agents=["agent1"],
        warnings=["Could not reach agents named [agent2]", f"Model version {version} does not contain agents named [agent5]"],
    )


@pytest.mark.parametrize(
    "agent_deploy_interval",
    [
        "2",
        "*/2 * * * * * *"
    ],
)
async def test_spontaneous_deploy(
    server,
    client,
    agent,
    resource_container,
    environment,
    clienthelper,
    caplog,
    agent_deploy_interval,
):
    """
    Test that a deploy run is executed every 2 seconds in the new agent
     as specified in the agent_repair_interval (using a cron or not)
    """
    # result = await agent.scheduler.get_resource_state()

    with caplog.at_level(logging.DEBUG):
        resource_container.Provider.reset()

        env_id = UUID(environment)

        Config.set("config", "agent-deploy-interval", agent_deploy_interval)
        Config.set("config", "agent-deploy-splay-time", "2")
        Config.set("config", "agent-repair-interval", "0")

        # This is just so we can reuse the agent from the fixtures with the new config options
        agent._set_deploy_and_repair_intervals()
        agent._enable_time_triggers()

        resource_container.Provider.set_fail("agent1", "key1", 1)

        version = await clienthelper.get_version()

        resources = [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "purged": False,
                "send_event": False,
                "requires": [],
            }
        ]

        await clienthelper.put_version_simple(resources, version)

        # do a deploy
        start = time.time()

        result = await client.release_version(env_id, version, False)
        assert result.code == 200

        # result = await client.get_compile_data(uuid.UUID(environment))
        # assert result.code == 200, result

        assert result.result["model"]["released"]

        result = await client.get_version(env_id, version)
        assert result.code == 200

        result = await client.get_scheduler_status(env_id)
        assert result.code == 200, result

        await clienthelper.wait_for_deployed()

        await clienthelper.wait_full_success()

        duration = time.time() - start

        assert await clienthelper.done_count() == 1

        assert resource_container.Provider.isset("agent1", "key1")

    # approximate check, the number of heartbeats can vary, but not by a factor of 10
    beats = [message for logger_name, log_level, message in caplog.record_tuples if "Received heartbeat from" in message]
    assert (
        len(beats) < duration * 10
    ), f"Sent {len(beats)} heartbeats over a time period of {duration} seconds, sleep mechanism is broken"


@pytest.mark.parametrize(
    "agent_repair_interval",
    [
        "2",
        "*/2 * * * * * *",
    ],
)
async def test_spontaneous_repair(server, client, agent, resource_container, environment, clienthelper, agent_repair_interval):
    """
    Test that a repair run is executed every 2 seconds in the new agent
     as specified in the agent_repair_interval (using a cron or not)
    """
    resource_container.Provider.reset()
    env_id = environment

    Config.set("config", "agent-repair-interval", agent_repair_interval)
    Config.set("config", "agent-repair-splay-time", "2")
    Config.set("config", "agent-deploy-interval", "0")

    # This is just so we can reuse the agent from the fixtures with the new config options
    agent._set_deploy_and_repair_intervals()
    agent._enable_time_triggers()
    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # do a deploy
    result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert result.result["model"]["released"]

    result = await client.get_version(env_id, version)
    assert result.code == 200

    await clienthelper.wait_full_success()

    async def verify_deployment_result():
        # A repair run may put one resource from the deployed state to the deploying state.
        assert len(resources) - 1 <= await clienthelper.done_count() <= len(resources)

        assert resource_container.Provider.isset("agent1", "key1")
        assert resource_container.Provider.get("agent1", "key1") == "value1"

    await verify_deployment_result()

    # Manual change
    resource_container.Provider.set("agent1", "key1", "another_value")

    # Wait until repair restores the state
    def repaired() -> bool:
        return resource_container.Provider.get("agent1", "key1") == "value1"

    await retry_limited(repaired, 10)

    await verify_deployment_result()
    await resource_action_consistency_check()
