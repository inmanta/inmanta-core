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

import logging

from inmanta import config
from inmanta.const import AgentAction, ResourceState
from utils import retry_limited, wait_for_n_deployed_resources, wait_until_deployment_finishes

logger = logging.getLogger("inmanta.test.server_agent")


async def test_agent_stop_deploying_when_paused(server, client, environment, clienthelper, resource_container, agent):
    """
    This test case verifies that an agent, which is executing a deployment, stops
    its deploy operations when the agent is paused.
    """
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    await clienthelper.set_auto_deploy()

    agent1 = "agent1"
    agent2 = "agent2"

    version = await clienthelper.get_version()

    def _get_resources(agent_name: str) -> list[dict]:
        return [
            {
                "key": "key1",
                "value": "value1",
                "id": f"test::Resource[{agent_name},key=key1],v={version}",
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": f"test::Wait[{agent_name},key=key2],v={version}",
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [f"test::Resource[{agent_name},key=key1],v={version}"],
            },
            {
                "key": "key3",
                "value": "value3",
                "id": f"test::Resource[{agent_name},key=key3],v={version}",
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [f"test::Wait[{agent_name},key=key2],v={version}"],
            },
        ]

    resources = _get_resources(agent1) + _get_resources(agent2)

    await clienthelper.put_version_simple(resources, version, True)

    # Wait until the deployment blocks on the test::Wait resources
    await wait_for_n_deployed_resources(client, environment, version, n=2)

    # Pause agent1
    result = await client.agent_action(tid=environment, name=agent1, action=AgentAction.pause.name)
    assert result.code == 200

    # Continue the deployment. Only 5 resources will be deployed because agent1 cancelled its deployment.
    await resource_container.wait_for_done_with_waiters(
        client, environment, version, wait_for_this_amount_of_resources_in_done=5
    )

    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200

    rvid_to_actual_states_dct = {resource["resource_version_id"]: resource["status"] for resource in result.result["data"]}

    # Agent1:
    #   * test::Resource[agent1,key=key1],v=1: Was deployed before the agent got paused.
    #   * test::Wait[agent1,key=key2],v=1: Was already in flight and will be deployed.
    #   * test::Resource[agent1,key=key3],v=1: Will not be deployed because the agent is paused.
    # Agent2: This agent is not paused. All resources will be deployed.
    rvis_to_expected_states = {
        "test::Resource[agent1,key=key1],v=1": ResourceState.deployed.value,
        "test::Wait[agent1,key=key2],v=1": ResourceState.deployed.value,
        "test::Resource[agent1,key=key3],v=1": ResourceState.available.value,
        "test::Resource[agent2,key=key1],v=1": ResourceState.deployed.value,
        "test::Wait[agent2,key=key2],v=1": ResourceState.deployed.value,
        "test::Resource[agent2,key=key3],v=1": ResourceState.deployed.value,
    }

    assert rvid_to_actual_states_dct == rvis_to_expected_states


async def test_agent_paused_while_idle_does_not_deploy(server, client, environment, clienthelper, resource_container, agent):
    """
    An agent that is paused while it waits for work must not deploy the next version.

    The task runner of the agent only checks its status before it waits for the next task, so a pause that arrives
    while it waits used to let one more deploy through.
    """
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    await clienthelper.set_auto_deploy()

    async def put_version(value: str) -> int:
        version = await clienthelper.get_version()
        resources = [
            {
                "key": "key1",
                "value": value,
                "id": f"test::Resource[{agent_name},key=key1],v={version}",
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            }
            for agent_name in ("agent1", "agent2")
        ]
        await clienthelper.put_version_simple(resources, version, wait_for_released=True)
        return version

    await put_version("value1")
    await wait_until_deployment_finishes(client, environment)
    assert resource_container.Provider.get("agent1", "key1") == "value1"

    # agent1 is idle: its task runner waits for the next task
    scheduler = agent.scheduler
    await retry_limited(lambda: not scheduler._work.agent_queues.in_progress, timeout=10)

    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.pause.name)
    assert result.code == 200
    await retry_limited(lambda: not scheduler._workers["agent1"].is_running(), timeout=10)

    version = await put_version("value2")
    # agent2 is not paused and deploys the new version
    await retry_limited(lambda: resource_container.Provider.get("agent2", "key1") == "value2", timeout=10)
    await retry_limited(lambda: not scheduler._work.agent_queues.in_progress, timeout=10)

    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.changecount("agent1", "key1") == 1

    # once unpaused, agent1 deploys the new version
    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.unpause.name)
    assert result.code == 200
    await wait_until_deployment_finishes(client, environment, version=version)
    assert resource_container.Provider.get("agent1", "key1") == "value2"
