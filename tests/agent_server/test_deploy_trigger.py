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

import inmanta.data
import utils
from agent_server.conftest import _deploy_resources, get_agent
from utils import get_resource, log_contains, log_doesnt_contain, retry_limited


async def test_deploy_trigger(
    server, client, clienthelper, resource_container, environment, caplog, no_agent_backoff, async_finalizer
):
    """
    Test deployment of empty model
    """
    caplog.set_level(logging.INFO)

    agent = await get_agent(server, environment, "agent1", "agent5")
    async_finalizer(agent.stop)

    version = await clienthelper.get_version()

    resources = [
        get_resource(version, agent="agent1"),
        get_resource(version, agent="agent2"),
        get_resource(version, agent="agent3"),
    ]

    await _deploy_resources(client, environment, resources, version, False)

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


async def test_update_agent_map(server, client, environment, agent_factory, resource_container, clienthelper):
    """
    If the URI of an enabled agent changes, it should still be enabled after the change
    """
    agent_map = {"node1": "localhost"}

    result = await client.set_setting(environment, inmanta.data.AUTO_DEPLOY, True)
    assert result.code == 200
    result = await client.set_setting(environment, inmanta.data.PUSH_ON_AUTO_DEPLOY, True)
    assert result.code == 200

    version = await clienthelper.get_version()
    await clienthelper.put_version_simple([utils.get_resource(version, agent="node2")], version, wait_for_released=True)

    agent1 = await agent_factory(hostname="node1", environment=environment, agent_map=agent_map)
    assert agent1.agent_map == agent_map

    await agent1._update_agent_map({"node1": "localhost2", "node2": "local:"})

    assert agent1._instances["node1"].is_enabled()

    await clienthelper.wait_for_deployed(version)
