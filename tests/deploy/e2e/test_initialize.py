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
import datetime
import logging
import uuid
from collections.abc import Mapping

import pytest

import utils
from inmanta import config, const, data
from inmanta.agent.agent_new import Agent
from inmanta.deploy.state import Blocked, Compliance, DeployResult, ResourceState


@pytest.fixture
async def server_pre_start(server_config):
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")


async def test_agent_disconnect(
    resource_container, environment, server, client, clienthelper, async_finalizer, caplog, agent_no_state_check: Agent
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
        return not agent_no_state_check.scheduler._running

    await utils.retry_limited(disconnected, 1)

    utils.log_index(caplog, "inmanta.scheduler", logging.WARNING, "Connection to server lost, stopping scheduler")


@pytest.mark.parametrize("reset_state", (True, False))
async def test_scheduler_initialization(
    agent, resource_container, clienthelper, server, client, environment, reset_state: bool
) -> None:
    """
    Ensure that when the scheduler starts, it only deploys the resources that need to be deployed,
    i.e. the resources that are not up-to-date or have outstanding events.
    """
    if reset_state:
        await client.set_setting(environment, data.RESET_DEPLOY_PROGRESS_ON_START, True)

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

    # get deploy timestamps
    async def get_last_deployed() -> dict[int, datetime.datetime]:
        result: dict[str, datetime.datetime] = {}
        for i in range(1, 4):
            rid = f"test::Resource[agent1,key=key{i}]"
            rps = await data.ResourcePersistentState.get_one(environment=environment, resource_id=rid)
            assert rps is not None
            result[i] = rps.last_deploy
        return result

    last_deployed: Mapping[str, datetime.datetime] = await get_last_deployed()

    # Pause the agent to stop the scheduler
    # We cannot call halt_environment / resume_environment as it will try to create the scheduler but will fail
    # because auto_start_agent is not set to `True`
    await data.Agent.pause(env=uuid.UUID(environment), endpoint=const.AGENT_SCHEDULER_ID, paused=True)
    result, _ = await agent.set_state(const.AGENT_SCHEDULER_ID, enabled=False)
    assert result == 200
    # also pause the nominal agent agent1 so we can assert scheduler state after initialization but before work starts
    result = await client.agent_action(environment, "agent1", const.AgentAction.pause.name)
    assert result.code == 200, result.result

    await data.Agent.pause(env=uuid.UUID(environment), endpoint=const.AGENT_SCHEDULER_ID, paused=False)
    result, _ = await agent.set_state(const.AGENT_SCHEDULER_ID, enabled=True)
    assert result == 200

    assert agent.scheduler._state.resource_state == {
        "test::Resource[agent1,key=key1]": ResourceState(
            compliance=Compliance.COMPLIANT,
            last_deploy_result=DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED,
            last_deployed=last_deployed[1],
        ),
        "test::Resource[agent1,key=key2]": ResourceState(
            compliance=Compliance.NON_COMPLIANT if not reset_state else Compliance.HAS_UPDATE,
            last_deploy_result=DeployResult.FAILED if not reset_state else DeployResult.NEW,
            blocked=Blocked.NOT_BLOCKED,
            last_deployed=last_deployed[2],
        ),
        "test::Resource[agent1,key=key3]": ResourceState(
            compliance=Compliance.NON_COMPLIANT if not reset_state else Compliance.HAS_UPDATE,
            last_deploy_result=DeployResult.SKIPPED if not reset_state else DeployResult.NEW,
            blocked=Blocked.NOT_BLOCKED,  # we don't restore TRANSIENT status atm
            last_deployed=last_deployed[3],
        ),
    }

    # unpause agent1 -> start deploying
    result = await client.agent_action(environment, "agent1", const.AgentAction.unpause.name)
    assert result.code == 200, result.result

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
        assert result.result["data"][i]["resource_version_ids"] == [f"test::Resource[agent1,key=key{3 - i}],v=1"]

    # verify that key2 and key3 got deployed while key1 did not because it was already in a good state
    last_deployed_after: Mapping[str, datetime.datetime] = await get_last_deployed()
    assert last_deployed_after[1] == last_deployed[1]
    assert last_deployed_after[2] > last_deployed[2]
    assert last_deployed_after[3] > last_deployed[3]
