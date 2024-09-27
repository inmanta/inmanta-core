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

import asyncio
import logging
import time
import uuid
from uuid import UUID

import pytest

from inmanta import const, data
from inmanta.config import Config
from inmanta.util import get_compiler_version
from utils import _wait_until_deployment_finishes, resource_action_consistency_check, retry_limited

logger = logging.getLogger("inmanta.test.server_agent")


@pytest.mark.parametrize("auto_start_agent", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_auto_deploy_no_splay(server, client, clienthelper, resource_container, environment, no_agent_backoff):
    """
    Verify that the new scheduler can actually fork
    """
    resource_container.Provider.reset()
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": ""})
    await env.set(data.AUTOSTART_ON_START, True)

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    # set auto deploy and push
    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200

    await clienthelper.put_version_simple(resources, version)

    # check deploy
    await _wait_until_deployment_finishes(client, environment, version)
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 2
    assert result.result["model"]["result"] == "failed"

    # check if agent 1 is started by the server
    # deploy will fail because handler code is not uploaded to the server
    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while len(result.result["agents"]) == 0 or result.result["agents"][0]["state"] == "down":
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == const.AGENT_SCHEDULER_ID


@pytest.mark.parametrize(
    "agent_deploy_interval",
    ["2", "*/2 * * * * * *"],
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

        assert not result.result["model"]["deployed"]
        assert result.result["model"]["released"]
        assert result.result["model"]["total"] == 1
        assert result.result["model"]["result"] == "deploying"

        result = await client.get_version(env_id, version)
        assert result.code == 200

        await clienthelper.wait_for_deployed()

        await clienthelper.wait_full_success(env_id)

        duration = time.time() - start

        result = await client.get_version(env_id, version)
        assert result.result["model"]["done"] == 1

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

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    result = await client.get_version(env_id, version)
    assert result.code == 200

    await clienthelper.wait_full_success(env_id)

    async def verify_deployment_result():
        result = await client.get_version(env_id, version)
        # A repair run may put one resource from the deployed state to the deploying state.
        assert len(resources) - 1 <= result.result["model"]["done"] <= len(resources)

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
