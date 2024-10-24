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
from functools import partial

from inmanta import config, const
from inmanta.agent.agent_new import Agent
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.server.bootloader import InmantaBootloader
import pytest
import utils


@pytest.fixture
async def server_pre_start(server_config):
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")


async def test_agent_disconnect(
    resource_container, environment, server, client, clienthelper, async_finalizer, caplog, agent: Agent
):
    caplog.set_level(logging.INFO)
    config.Config.set("config", "server-timeout", "1")
    config.Config.set("config", "agent-reconnect-delay", "1")

    version = await clienthelper.get_version()
    await clienthelper.put_version_simple([utils.get_resource(version)], version)

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    await asyncio.wait_for(server.stop(), timeout=15)

    def disconnected():
        return not agent.scheduler._running

    await utils.retry_limited(disconnected, 1)

    utils.log_index(caplog, "inmanta.scheduler", logging.WARNING, "Connection to server lost, stopping scheduler")


async def test_server_restart(
    resource_container, server, agent, environment, clienthelper, postgres_db, client, async_finalizer
):
    """
    Test if agent reconnects correctly after server restart
    """
    resource_container.Provider.reset()
    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    await asyncio.wait_for(server.stop(), timeout=15)
    ibl = InmantaBootloader(configure_logging=False)
    server = ibl.restserver
    async_finalizer.add(agent.stop)
    async_finalizer.add(partial(ibl.stop, timeout=15))
    await ibl.start()

    env_id = environment

    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "receive_events": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key3",
            "value": None,
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "requires": [],
            "purged": True,
            "send_event": False,
            "receive_events": False,
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # do a deploy
    result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 3
    assert result.result["model"]["result"] == "deploying"

    result = await client.get_version(env_id, version)
    assert result.code == 200

    await utils.wait_until_deployment_finishes(client, env_id, version)

    result = await client.get_version(env_id, version)
    assert result.result["model"]["done"] == len(resources)

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert not resource_container.Provider.isset("agent1", "key3")


async def test_scheduler_initialization(agent, resource_container, clienthelper, server, client, environment) -> None:
    """
    Ensure that when the scheduler starts, it only deploys the resources that need to be deployed,
    i.e. the resources that are not up-to-date or have outstanding events.
    """
    resource_container.Provider.reset()
    resource_container.Provider.set(agent="agent1", key="key", value="key1")
    resource_container.Provider.set(agent="agent1", key="key", value="key2")
    resource_container.Provider.set(agent="agent1", key="key", value="key3")
    resource_container.Provider.set_fail(agent="agent1", key="key2", failcount=1)

    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "val1",
            "id": f"test::Resource[agent1,key=key1],v={version}",
            "requires": [],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key2",
            "value": "val2",
            "id": f"test::Resource[agent1,key=key2],v={version}",
            "requires": [f"test::Resource[agent1,key=key1],v={version}"],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key3",
            "value": "val3",
            "id": f"test::Resource[agent1,key=key3],v={version}",
            "requires": [f"test::Resource[agent1,key=key2],v={version}"],
            "purged": False,
            "send_event": False,
        },
    ]
    # Deploy and release version
    await clienthelper.put_version_simple(version=version, resources=resources)
    result = await client.release_version(environment, version)
    assert result.code == 200
    await clienthelper.wait_for_deployed()

    for rid, expected_status in [
        ("test::Resource[agent1,key=key1]", const.ResourceState.deployed),
        ("test::Resource[agent1,key=key2]", const.ResourceState.failed),
        ("test::Resource[agent1,key=key3]", const.ResourceState.skipped),
    ]:
        result = await client.resource_details(tid=environment, rid=rid)
        assert result.code == 200
        assert result.result["data"]["status"] == expected_status.value

    result = await client.get_resource_actions(
        tid=environment,
        resource_type="test::Resource",
        agent="agent1",
        exclude_changes=[const.Change.nochange.value],
    )
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["resource_version_ids"] == ["test::Resource[agent1,key=key1],v=1"]

    # Pause the agent to stop the scheduler
    result = await client.agent_action(tid=environment, name=const.AGENT_SCHEDULER_ID, action=const.AgentAction.pause.value)
    assert result.code == 200
    result = await client.agent_action(tid=environment, name=const.AGENT_SCHEDULER_ID, action=const.AgentAction.unpause.value)
    assert result.code == 200
    await utils.retry_limited(utils.is_agent_done, scheduler=agent.scheduler, agent_name="agent1", timeout=10, interval=0.05)

    for rid, expected_status in [
        ("test::Resource[agent1,key=key1]", const.ResourceState.deployed),
        ("test::Resource[agent1,key=key2]", const.ResourceState.deployed),
        ("test::Resource[agent1,key=key3]", const.ResourceState.deployed),
    ]:
        result = await client.resource_details(tid=environment, rid=rid)
        assert result.code == 200
        assert result.result["data"]["status"] == expected_status.value, f"{rid} has unexpected state"

    result = await client.get_resource_actions(
        tid=environment,
        resource_type="test::Resource",
        agent="agent1",
        exclude_changes=[const.Change.nochange.value],
    )
    assert result.code == 200
    assert len(result.result["data"]) == 3
    for i in range(3):
        assert result.result["data"][i]["resource_version_ids"] == [f"test::Resource[agent1,key=key{3-i}],v=1"]
