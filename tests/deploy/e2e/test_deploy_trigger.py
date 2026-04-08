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
from inmanta.types import ResourceIdStr
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
                f"All agents got a trigger to run repair for all resources in environment {environment}",
            )
            agents = ["agent1", "agent2", "agent3"]  # this also includes paused agents
        else:
            log_contains(
                caplog,
                "inmanta.scheduler",
                logging.INFO,
                f"Agent agent1 got a trigger to run repair for all resources in environment {environment}",
            )
        log_doesnt_contain(
            caplog, "inmanta.scheduler", logging.INFO, f"Agent agent5 got a trigger to run repair for all resources in environment {environment}"
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


async def test_deploy_trigger_specific_resources(
    server, client, clienthelper, resource_container, environment, caplog, agent
):
    """
    Verify that the deploy endpoint correctly forwards a resource filter to the scheduler via the trigger method.

    When a list of resources is given:
    - repair (full deploy): only the specified resources are deployed, even if compliant
    - incremental deploy: only dirty resources that are also in the list are deployed
    """
    caplog.set_level(logging.INFO)
    version = await clienthelper.get_version()

    resources = [
        get_resource(version, key="key1", agent="agent1"),
        get_resource(version, key="key2", agent="agent1"),
        get_resource(version, key="key1", agent="agent2"),
        get_resource(version, key="key2", agent="agent2"),
    ]

    await clienthelper.put_version_simple(resources, version)
    result = await client.release_version(environment, version, True)
    assert result.code == 200
    await clienthelper.wait_for_deployed(version)

    r_agent1_key1 = ResourceIdStr("test::Resource[agent1,key=key1]")
    r_agent1_key2 = ResourceIdStr("test::Resource[agent1,key=key2]")
    r_agent2_key1 = ResourceIdStr("test::Resource[agent2,key=key1]")
    r_agent2_key2 = ResourceIdStr("test::Resource[agent2,key=key2]")

    assert resource_container.Provider.readcount("agent1", "key1") == 1
    assert resource_container.Provider.readcount("agent1", "key2") == 1
    assert resource_container.Provider.readcount("agent2", "key1") == 1
    assert resource_container.Provider.readcount("agent2", "key2") == 1

    # repair with a specific resource list: only those resources should be re-deployed, even though all are compliant
    result = await client.deploy(
        environment,
        agent_trigger_method=const.AgentTriggerMethod.push_full_deploy,
        resources=[r_agent1_key1, r_agent2_key2],
    )
    assert result.code == 200

    await retry_limited(
        lambda: resource_container.Provider.readcount("agent1", "key1") == 2
        and resource_container.Provider.readcount("agent2", "key2") == 2,
        10,
    )

    log_contains(
        caplog,
        "inmanta.scheduler",
        logging.INFO,
        f"All agents got a trigger to run repair for 2 resources in environment {environment}",
    )
    caplog.clear()

    assert resource_container.Provider.readcount("agent1", "key1") == 2
    assert resource_container.Provider.readcount("agent1", "key2") == 1  # not in the resource list, not re-deployed
    assert resource_container.Provider.readcount("agent2", "key1") == 1  # not in the resource list, not re-deployed
    assert resource_container.Provider.readcount("agent2", "key2") == 2

    # set up for incremental deploy: make agent1/key2 and agent2/key2 fail on the next deploy attempt
    resource_container.Provider.set_fail("agent1", "key2", 1)
    resource_container.Provider.set_fail("agent2", "key2", 1)

    result = await client.deploy(environment, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    # wait until all resources have been attempted: successful ones go up by 1, failing ones go up by 1 then stay dirty
    await retry_limited(
        lambda: resource_container.Provider.readcount("agent1", "key1") == 3  # successfully re-deployed
        and resource_container.Provider.readcount("agent1", "key2") == 2  # deploy attempted, failed -> dirty
        and resource_container.Provider.readcount("agent2", "key1") == 2  # successfully re-deployed
        and resource_container.Provider.readcount("agent2", "key2") == 3,  # deploy attempted, failed -> dirty
        10,
    )

    log_contains(
        caplog,
        "inmanta.scheduler",
        logging.INFO,
        f"All agents got a trigger to run repair for all resources in environment {environment}",
    )
    caplog.clear()

    # now trigger an incremental deploy for only [r_agent1_key2, r_agent2_key1]:
    # - r_agent1_key1: compliant, not in the list -> not deployed
    # - r_agent1_key2: dirty and in the list -> gets re-deployed
    # - r_agent2_key1: compliant and in the list -> not deployed
    # - r_agent2_key2: dirty, not in the list -> not deployed
    result = await client.deploy(
        environment,
        agent_trigger_method=const.AgentTriggerMethod.push_incremental_deploy,
        resources=[r_agent1_key2, r_agent2_key1],
    )
    assert result.code == 200

    await retry_limited(
        lambda: resource_container.Provider.readcount("agent1", "key2") == 3,
        10,
    )

    log_contains(
        caplog,
        "inmanta.scheduler",
        logging.INFO,
        f"All agents got a trigger to run deploy for 2 resources in environment {environment}",
    )
    caplog.clear()

    assert resource_container.Provider.readcount("agent1", "key1") == 3  # not in incremental list, unchanged
    assert resource_container.Provider.readcount("agent1", "key2") == 3  # dirty and in the list, re-deployed
    assert resource_container.Provider.readcount("agent2", "key1") == 2  # compliant and in the list, skipped
    assert resource_container.Provider.readcount("agent2", "key2") == 3  # dirty but not in incremental list

    # repair with both agent and resources filters: only the intersection is deployed
    # resources=[r_agent1_key2, r_agent2_key2] but agents=["agent1"] -> only r_agent1_key2 qualifies
    result = await client.deploy(
        environment,
        agent_trigger_method=const.AgentTriggerMethod.push_full_deploy,
        agents=["agent1"],
        resources=[r_agent1_key2, r_agent2_key2],
    )
    assert result.code == 200

    await retry_limited(
        lambda: resource_container.Provider.readcount("agent1", "key2") == 4,
        10,
    )

    log_contains(
        caplog,
        "inmanta.scheduler",
        logging.INFO,
        f"Agent agent1 got a trigger to run repair for 2 resources in environment {environment}",
    )
    caplog.clear()

    assert resource_container.Provider.readcount("agent1", "key1") == 3  # not in resources list
    assert resource_container.Provider.readcount("agent1", "key2") == 4  # in both agent and resources filter
    assert resource_container.Provider.readcount("agent2", "key1") == 2  # agent2 not triggered
    assert resource_container.Provider.readcount("agent2", "key2") == 3  # agent2 not triggered
