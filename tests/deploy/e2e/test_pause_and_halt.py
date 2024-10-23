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

import pytest

from inmanta import config
from inmanta.const import AgentAction, ResourceState
from utils import _deploy_resources, wait_for_n_deployed_resources

logger = logging.getLogger("inmanta.test.server_agent")


@pytest.mark.skip("When pause is implemented")
async def test_agent_stop_deploying_when_paused(server, client, environment, clienthelper, resource_container, agent):
    """
    This test case verifies that an agent, which is executing a deployment, stops
    its deploy operations when the agent is paused.
    """
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

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

    # Initial deploy
    await _deploy_resources(client, environment, resources, version, push=True)

    # Wait until the deployment blocks on the test::Wait resources
    await wait_for_n_deployed_resources(client, environment, version, n=2)

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["done"] == 2

    # Pause agent1
    result = await client.agent_action(tid=environment, name=agent1, action=AgentAction.pause.name)
    assert result.code == 200

    # Continue the deployment. Only 5 resources will be deployed because agent1 cancelled its deployment.
    result = await resource_container.wait_for_done_with_waiters(
        client, environment, version, wait_for_this_amount_of_resources_in_done=5
    )

    rvid_to_actual_states_dct = {resource["resource_version_id"]: resource["status"] for resource in result.result["resources"]}

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


@pytest.mark.skip("Unclaar if need this")
async def test_agentinstance_stops_deploying_when_stopped(server, client, environment, agent, clienthelper, resource_container):
    """
    Test whether the ResourceActions scheduled on an AgentInstance are cancelled when the AgentInstance is stopped.
    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": f"test::Resource[agent1,key=key1],v={version}",
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": f"test::Wait[agent1,key=key2],v={version}",
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key1],v={version}"],
        },
        {
            "key": "key3",
            "value": "value3",
            "id": f"test::Wait[agent1,key=key3],v={version}",
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [f"test::Wait[agent1,key=key2],v={version}"],
        },
    ]

    await _deploy_resources(client, environment, resources, version, push=True)

    # Wait until agent has scheduled the deployment on its ResourceScheduler
    await wait_for_n_deployed_resources(client, environment, version, n=1)

    assert "agent1" in agent._instances
    agent_instance = agent._instances["agent1"]
    assert not agent_instance._nq.finished()
    assert agent_instance.is_enabled()
    assert not agent_instance.is_stopped()

    await agent.remove_end_point_name("agent1")

    assert "agent1" not in agent._instances
    assert agent_instance._nq.finished()
    assert not agent_instance.is_enabled()
    assert agent_instance.is_stopped()

    # Agent cannot be unpaused after it is stopped
    result, _ = agent_instance.unpause()
    assert result == 403
    assert agent_instance._nq.finished()
    assert not agent_instance.is_enabled()
    assert agent_instance.is_stopped()

    # Cleanly stop in flight coroutines
    await resource_container.wait_for_done_with_waiters(
        client, environment, version, wait_for_this_amount_of_resources_in_done=2
    )
