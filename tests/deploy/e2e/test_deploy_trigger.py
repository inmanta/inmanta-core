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

import pytest

from inmanta import const, data
from inmanta.const import AgentAction
from utils import get_resource, log_contains, log_doesnt_contain, resource_action_consistency_check, retry_limited


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

    # Pause agent3
    result = await client.agent_action(tid=environment, name="agent3", action=AgentAction.pause.name)
    assert result.code == 200

    async def verify(result, a1=0, code=200, warnings=[], agents=None):
        assert result.code == code

        def is_deployed():
            return resource_container.Provider.readcount("agent1", "key1") == a1

        await retry_limited(is_deployed, 1)
        if not agents:
            log_contains(
                caplog,
                "inmanta.scheduler",
                logging.INFO,
                f"All agents got a trigger to run repair in environment {environment}",
            )
            agents = ["agent1", "agent2", "agent3"]  # this also includes paused agents
        else:
            log_contains(
                caplog,
                "inmanta.scheduler",
                logging.INFO,
                f"Agent agent1 got a trigger to run repair in environment {environment}",
            )
        log_doesnt_contain(
            caplog, "inmanta.scheduler", logging.INFO, f"Agent agent5 got a trigger to run repair in environment {environment}"
        )

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
    await verify(result, a1=2)

    # only agent1
    result = await client.deploy(environment, agents=["agent1"])
    await verify(result, agents=["agent1"], a1=3)

    # only agent5 (not in model)
    result = await client.deploy(environment, agents=["agent5"])
    await verify_failed(result, 404, "No agent could be reached", warnings=[])

    # All of it
    result = await client.deploy(environment, agents=["agent1", "agent2", "agent5"])
    await verify(
        result,
        a1=4,
        agents=["agent1", "agent2"],
        warnings=["Model version 1 does not contain agents named [agent5]"],
    )


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

    result = await client.set_setting(environment, data.AUTOSTART_AGENT_REPAIR_INTERVAL, agent_repair_interval)
    assert result.code == 200
    # Disable deploys
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_INTERVAL, 0)
    assert result.code == 200

    timer_manager = agent.scheduler._timer_manager
    await timer_manager.initialize()

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
    result = await client.release_version(
        tid=env_id, id=version, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy
    )
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
