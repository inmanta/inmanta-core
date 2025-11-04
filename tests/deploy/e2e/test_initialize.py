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
import datetime
import logging
import uuid
from collections.abc import Mapping

import pytest

import inmanta.server
import utils
from inmanta import config, const, data
from inmanta.agent.agent_new import Agent
from inmanta.deploy.state import Blocked, Compliance, DeployResult, ResourceState
from inmanta.util import get_compiler_version


@pytest.fixture
async def server_pre_start(server_config):
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")


async def test_agent_disconnect(
    resource_container, environment, server, client, clienthelper, caplog, agent_no_state_check: Agent
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
    agent,
    resource_container,
    clienthelper,
    server,
    client,
    environment,
    reset_state: bool,
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
    resource_container.Provider.set(agent="agent1", key="key", value="key4")
    resource_container.Provider.set(agent="agent1", key="key", value="key5")
    resource_container.Provider.set(agent="agent1", key="key", value="key6")
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
        {
            "key": "key4",
            "value": "val4",
            "id": f"test::Resource[agent1,key=key4],v={version}",
            "requires": [],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key5",
            "value": "val5",
            "id": f"test::Resource[agent1,key=key5],v={version}",
            "requires": [],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key6",
            "value": "val6",
            "id": f"test::Resource[agent1,key=key6],v={version}",
            "requires": [f"test::Resource[agent1,key=key5],v={version}"],
            "purged": False,
            "send_event": False,
        },
    ]
    # Deploy and release version
    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={"test::Resource[agent1,key=key5]": const.ResourceState.undefined},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        module_version_info={},
    )
    assert res.code == 200, res.result
    result = await client.release_version(environment, version)
    assert result.code == 200
    await clienthelper.wait_for_deployed()

    for rid, expected_status in [
        ("test::Resource[agent1,key=key1]", const.ResourceState.deployed),
        ("test::Resource[agent1,key=key2]", const.ResourceState.failed),
        ("test::Resource[agent1,key=key3]", const.ResourceState.skipped),
        ("test::Resource[agent1,key=key4]", const.ResourceState.deployed),
        ("test::Resource[agent1,key=key5]", const.ResourceState.undefined),
        ("test::Resource[agent1,key=key6]", const.ResourceState.skipped_for_undefined),
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
    result_data = result.result["data"]
    assert len(result_data) == 2
    resource_version_ids = sorted(result_data[0]["resource_version_ids"] + result_data[1]["resource_version_ids"])
    assert resource_version_ids == ["test::Resource[agent1,key=key1],v=1", "test::Resource[agent1,key=key4],v=1"]

    # get deploy timestamps
    async def get_last_deployed() -> dict[int, datetime.datetime]:
        result: dict[str, datetime.datetime] = {}
        for i in range(1, 7):
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

    # Deliberately introduce a bug in the scheduler
    rps = await data.ResourcePersistentState.get_one(environment=environment, resource_id="test::Resource[agent1,key=key4]")
    assert rps is not None
    await rps.update_fields(blocked=Blocked.BLOCKED)

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
            compliance=Compliance.HAS_UPDATE if reset_state else Compliance.COMPLIANT,
            last_deploy_result=DeployResult.NEW if reset_state else DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED,
            last_deployed=None if reset_state else last_deployed[1],
        ),
        "test::Resource[agent1,key=key2]": ResourceState(
            compliance=Compliance.HAS_UPDATE if reset_state else Compliance.NON_COMPLIANT,
            last_deploy_result=DeployResult.NEW if reset_state else DeployResult.FAILED,
            blocked=Blocked.NOT_BLOCKED,
            last_deployed=None if reset_state else last_deployed[2],
        ),
        "test::Resource[agent1,key=key3]": ResourceState(
            compliance=Compliance.HAS_UPDATE if reset_state else Compliance.NON_COMPLIANT,
            last_deploy_result=DeployResult.NEW if reset_state else DeployResult.SKIPPED,
            blocked=Blocked.NOT_BLOCKED,  # we don't restore TRANSIENT status atm
            last_deployed=None if reset_state else last_deployed[3],
        ),
        "test::Resource[agent1,key=key4]": ResourceState(
            compliance=Compliance.HAS_UPDATE if reset_state else Compliance.COMPLIANT,
            last_deploy_result=DeployResult.NEW if reset_state else DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED if reset_state else Blocked.BLOCKED,
            last_deployed=None if reset_state else last_deployed[4],
        ),
        # If reset_state=True we will reset the blocked status to NOT_BLOCKED
        "test::Resource[agent1,key=key5]": ResourceState(
            compliance=Compliance.UNDEFINED,
            last_deploy_result=DeployResult.NEW,
            blocked=Blocked.BLOCKED,
            last_deployed=last_deployed[5],
        ),
        "test::Resource[agent1,key=key6]": ResourceState(
            compliance=Compliance.HAS_UPDATE,
            last_deploy_result=DeployResult.NEW,
            blocked=Blocked.BLOCKED,
            last_deployed=last_deployed[6],
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
        (
            "test::Resource[agent1,key=key4]",
            const.ResourceState.deployed if reset_state else const.ResourceState.skipped_for_undefined,
        ),  # blocked but not undefined
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
    assert len(result.result["data"]) == 4
    sorted_ids = sorted([rvid for item in result.result["data"] for rvid in item["resource_version_ids"]])
    assert sorted_ids == [
        "test::Resource[agent1,key=key1],v=1",
        "test::Resource[agent1,key=key2],v=1",
        "test::Resource[agent1,key=key3],v=1",
        "test::Resource[agent1,key=key4],v=1",
    ]

    # verify that key2 and key3 got deployed while key1 did not because it was already in a good state
    last_deployed_after: Mapping[str, datetime.datetime] = await get_last_deployed()

    # Assert that the first 4 results are deployed
    for i in range(6):
        if i < 4:
            assert last_deployed_after[i + 1] is not None
        else:
            assert last_deployed_after[i + 1] is None

    # If we don't reset the state, assert that the last_deployed states remain consistent
    if not reset_state:
        assert last_deployed_after[1] == last_deployed[1]
        assert last_deployed_after[2] > last_deployed[2]
        assert last_deployed_after[3] > last_deployed[3]
        assert last_deployed_after[4] == last_deployed[4]

    assert last_deployed_after[5] == last_deployed[5]
    assert last_deployed_after[6] == last_deployed[6]

    # Assert that the reset fixed the bug in the database
    assert agent.scheduler._state.resource_state == {
        "test::Resource[agent1,key=key1]": ResourceState(
            compliance=Compliance.COMPLIANT,
            last_deploy_result=DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED,
            last_deployed=last_deployed_after[1],
        ),
        "test::Resource[agent1,key=key2]": ResourceState(
            compliance=Compliance.COMPLIANT,
            last_deploy_result=DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED,
            last_deployed=last_deployed_after[2],
        ),
        "test::Resource[agent1,key=key3]": ResourceState(
            compliance=Compliance.COMPLIANT,
            last_deploy_result=DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED,  # we don't restore TRANSIENT status atm
            last_deployed=last_deployed_after[3],
        ),
        "test::Resource[agent1,key=key4]": ResourceState(
            compliance=Compliance.COMPLIANT,
            last_deploy_result=DeployResult.DEPLOYED,
            blocked=Blocked.NOT_BLOCKED if reset_state else Blocked.BLOCKED,
            last_deployed=last_deployed_after[4],
        ),
        "test::Resource[agent1,key=key5]": ResourceState(
            compliance=Compliance.UNDEFINED,
            last_deploy_result=DeployResult.NEW,
            blocked=Blocked.BLOCKED,
            last_deployed=last_deployed_after[5],
        ),
        "test::Resource[agent1,key=key6]": ResourceState(
            compliance=Compliance.HAS_UPDATE,
            last_deploy_result=DeployResult.NEW,
            blocked=Blocked.BLOCKED,
            last_deployed=last_deployed_after[6],
        ),
    }


@pytest.mark.parametrize("no_agent", (True,))
@pytest.mark.parametrize("reset_state", (True, False))
async def test_scheduler_initialize_multiple_versions(
    agent_factory,
    resource_container,
    clienthelper,
    server,
    client,
    environment,
    reset_state: bool,
) -> None:
    """
    Verify processing of multiple versions when the scheduler initializes from an empty state (first start for an
    environment or reset_state). Concretely, verify that resources from the first version that are orphaned by the
    second, are in fact marked as orphans.

    :param reset_state: If True, achieve empty state through state reset. Otherwise achieve it via an empty environment.
    """
    if reset_state:
        await client.set_setting(environment, data.RESET_DEPLOY_PROGRESS_ON_START, True)

    async def start_agent() -> Agent:
        agentmanager = server.get_slice(inmanta.server.SLICE_AGENT_MANAGER)

        agent: Agent = await agent_factory(uuid.UUID(environment))
        await utils.retry_limited(lambda: len(agentmanager.sessions) == 1, 10)
        return agent

    rid1: str = "test::Resource[agent1,key=key1]"
    rid2: str = "test::Resource[agent1,key=key2]"
    agent: Agent | None = None

    def resources(version: int, *, r2: bool = True) -> list[dict[str, object]]:
        def res(n: int) -> None:
            return {
                "key": f"key{n}",
                # force change of intent for each version for easier "deploy done" waiting
                "value": f"val{n},version={version}",
                "id": f"test::Resource[agent1,key=key{n}],v={version}",
                "requires": [],
                "purged": False,
                "send_event": False,
            }

        return [res(1), res(2)] if r2 else [res(1)]

    version = await clienthelper.get_version()
    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources(version),
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        module_version_info={},
    )
    assert res.code == 200, res.result
    result = await client.release_version(environment, version)
    assert result.code == 200

    if reset_state:
        # set up initial state: make sure there is something to reset
        # start the agent, deploy the first version, then halt the agent again
        agent = await start_agent()
        await clienthelper.wait_for_deployed(version)

        for rid in (rid1, rid2):
            assert (await client.resource_details(tid=environment, rid=rid).value()).status == const.ResourceState.deployed
        await agent.scheduler.stop()

    # release second version, dropping r2
    version = await clienthelper.get_version()
    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources(version, r2=False),
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
        module_version_info={},
    )
    assert res.code == 200, res.result
    result = await client.release_version(environment, version)
    assert result.code == 200

    for rid in (rid1, rid2):
        status = (await client.resource_details(tid=environment, rid=rid).value()).status
        assert status == const.ResourceState.deployed if reset_state else const.ResourceState.available

    # start / resume agent
    if agent is None:
        agent = await start_agent()
    else:
        await agent.scheduler.start()

    await clienthelper.wait_for_deployed(version)

    assert (await client.resource_details(tid=environment, rid=rid1).value()).status == const.ResourceState.deployed
    assert (await client.resource_details(tid=environment, rid=rid2).value()).status == "orphaned"
