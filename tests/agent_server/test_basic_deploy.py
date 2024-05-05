import logging

from agent_server.conftest import ResourceContainer, _deploy_resources, get_agent, wait_for_n_deployed_resources
from inmanta import config
from inmanta.agent.agent import Agent, DeployRequest, DeployRequestAction, deploy_response_matrix


async def test_basic_deploy(resource_container, agent, client, clienthelper, environment, no_agent_backoff):
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"
    myagent_instance = agent._instances[agent_name]

    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key1", "value1")

    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value2",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
        },
        {
            "key": "key3",
            "value": "value2",
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key4",
            "value": "value2",
            "id": "test::Resource[agent1,key=key4],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    # Initial deploy
    await _deploy_resources(client, environment, resources, version, False)
    await myagent_instance.get_latest_version_for_agent(DeployRequest(reason="Deploy", is_full_deploy=False, is_periodic=False))
    await wait_for_n_deployed_resources(client, environment, version, 4)
