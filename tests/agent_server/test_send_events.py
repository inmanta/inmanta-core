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

import pytest

from agent_server.conftest import _wait_for_n_deploying
from inmanta import config, const
from inmanta.agent.agent import Agent
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.util import get_compiler_version
from utils import _wait_until_deployment_finishes, log_doesnt_contain, retry_limited

logger = logging.getLogger("inmanta.test.send_events")


@pytest.mark.asyncio
async def test_send_events(resource_container, environment, server, client, agent, clienthelper):
    """
    Send and receive events within one agent
    """
    resource_container.Provider.reset()

    version = await clienthelper.get_version()

    res_id_1 = "test::Resource[agent1,key=key1],v=%d" % version
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": res_id_1,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": True,
            "requires": [],
            "purged": False,
        },
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    events = resource_container.Provider.getevents("agent1", "key1")
    assert len(events) == 1
    for res_id, res in events[0].items():
        assert res_id.agent_name == "agent1"
        assert res_id.attribute_value == "key2"
        assert res["status"] == const.ResourceState.deployed
        assert res["change"] == const.Change.created


@pytest.mark.asyncio
async def test_send_events_cross_agent(resource_container, environment, server, client, async_finalizer, clienthelper):
    """
    Send and receive events over agents
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    async_finalizer.add(agent.stop)
    await agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    agent2 = Agent(hostname="node2", environment=environment, agent_map={"agent2": "localhost"}, code_loader=False)
    async_finalizer.add(agent2.stop)
    await agent2.add_end_point_name("agent2")
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)

    version = await clienthelper.get_version()

    res_id_1 = "test::Resource[agent1,key=key1],v=%d" % version
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": res_id_1,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent2,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent2,key=key2],v=%d" % version,
            "send_event": True,
            "requires": [],
            "purged": False,
        },
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent2", "key2") == "value2"

    events = resource_container.Provider.getevents("agent1", "key1")
    assert len(events) == 1
    for res_id, res in events[0].items():
        assert res_id.agent_name == "agent2"
        assert res_id.attribute_value == "key2"
        assert res["status"] == const.ResourceState.deployed
        assert res["change"] == const.Change.created


@pytest.mark.asyncio
async def test_send_events_cross_agent_deploying(
    resource_container, environment, server, client, no_agent_backoff, async_finalizer, clienthelper
):
    """
    Send and receive events over agents
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    async_finalizer.add(agent.stop)
    await agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    agent2 = Agent(hostname="node2", environment=environment, agent_map={"agent2": "localhost"}, code_loader=False)
    async_finalizer.add(agent2.stop)
    await agent2.add_end_point_name("agent2")
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)

    version = await clienthelper.get_version()

    res_id_1 = "test::Resource[agent1,key=key1],v=%d" % version
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": res_id_1,
            "send_event": False,
            "purged": False,
            "requires": ["test::Wait[agent2,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Wait[agent2,key=key2],v=%d" % version,
            "send_event": True,
            "requires": [],
            "purged": False,
        },
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_for_n_deploying(client, environment, version, 1)

    # restart deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await resource_container.wait_for_done_with_waiters(client, environment, version)

    # incorrect CAD handling causes skip, which completes deploy without writing
    assert resource_container.Provider.get("agent1", "key1") == "value1"


@pytest.mark.asyncio(timeout=15)
async def test_send_events_cross_agent_restart(
    resource_container, environment, server, client, clienthelper, no_agent_backoff, async_finalizer
):
    """
    Send and receive events over agents with agents starting after deploy
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    resource_container.Provider.reset()

    agent2 = Agent(hostname="node2", environment=environment, agent_map={"agent2": "localhost"}, code_loader=False)
    async_finalizer.add(agent2.stop)
    await agent2.add_end_point_name("agent2")
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = await clienthelper.get_version()

    res_id_1 = "test::Resource[agent1,key=key1],v=%d" % version
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": res_id_1,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent2,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent2,key=key2],v=%d" % version,
            "send_event": True,
            "requires": [],
            "purged": False,
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200

    # wait for agent 2 to finish
    while (result.result["model"]["total"] - result.result["model"]["done"]) > 1:
        result = await client.get_version(environment, version)
        await asyncio.sleep(0.1)

    assert resource_container.Provider.get("agent2", "key2") == "value2"

    # start agent 1 and wait for it to finish
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    async_finalizer.add(agent.stop)
    await agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)

    # Events are only propagated in a full deploy
    await agent._instances["agent1"].get_latest_version_for_agent(
        reason="Repair", incremental_deploy=False, is_repair_run=False
    )

    await _wait_until_deployment_finishes(client, environment, version)

    assert resource_container.Provider.get("agent1", "key1") == "value1"

    events = resource_container.Provider.getevents("agent1", "key1")
    assert len(events) == 1
    for res_id, res in events[0].items():
        assert res_id.agent_name == "agent2"
        assert res_id.attribute_value == "key2"
        assert res["status"] == const.ResourceState.deployed
        assert res["change"] == const.Change.created


@pytest.mark.asyncio
async def test_send_events_cross_agent_fail(resource_container, environment, server, client, async_finalizer, clienthelper):
    """
    Send and receive events over agents, ensure failures are reported correctly
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    async_finalizer.add(agent.stop)
    await agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    agent2 = Agent(hostname="node2", environment=environment, agent_map={"agent2": "localhost"}, code_loader=False)
    async_finalizer.add(agent2.stop)
    await agent2.add_end_point_name("agent2")
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)

    version = await clienthelper.get_version()

    res_id_1 = "test::Resource[agent1,key=key1],v=%d" % version
    fail_r = "test::FailFast[agent2,key=key2],v=%d" % version
    resources = [
        {"key": "key1", "value": "value1", "id": res_id_1, "send_event": False, "purged": False, "requires": [fail_r]},
        {"key": "key2", "value": "value2", "id": fail_r, "send_event": True, "requires": [], "purged": False},
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    # first resource is not executed
    assert resource_container.Provider.get("agent1", "key1") is None

    events = resource_container.Provider.getevents("agent1", "key1")
    assert len(events) == 1
    for res_id, res in events[0].items():
        assert res_id.agent_name == "agent2"
        assert res_id.attribute_value == "key2"
        assert res["status"] == const.ResourceState.failed

    result = await client.get_version(environment, version)
    assert result.code == 200

    r_to_s = {r["resource_version_id"]: r["status"] for r in result.result["resources"]}
    assert r_to_s[res_id_1] == "skipped"
    assert r_to_s[fail_r] == "failed"


@pytest.mark.asyncio
async def test_consistenly_handle_failure_in_process_events(
    resource_container, environment, server, client, async_finalizer, clienthelper, agent_factory
):
    """
    Setting `ctx.set_status(const.ResourceState.failed)` in process events should result
    in the same behavior for local and remote agents.
    """
    # Start agent1 and agent2
    agents = [
        agent_factory(
            environment=environment,
            hostname=f"agent{i}",
            agent_map={f"agent{i}": "localhost"},
            code_loader=False,
            agent_names=[f"agent{i}"],
        )
        for i in range(1, 3)
    ]
    await asyncio.gather(*agents)

    version = await clienthelper.get_version()
    res_id_key1 = f"test::Resource[agent1,key=key1],v={version}"
    res_id_key2 = f"test::Resource[agent2,key=key2],v={version}"
    res_id_key3 = f"test::BadEventsStatus[agent1,key=key3],v={version}"
    res_id_key4 = f"test::Resource[agent1,key=key4],v={version}"
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": res_id_key1,
            "send_event": True,
            "requires": [res_id_key3],
            "purged": False,
        },
        {
            "key": "key2",
            "value": "value2",
            "id": res_id_key2,
            "send_event": True,
            "purged": False,
            "requires": [res_id_key3],
        },
        {
            "key": "key3",
            "value": "value3",
            "id": res_id_key3,
            "send_event": True,
            "requires": [res_id_key4],
            "purged": False,
        },
        {
            "key": "key4",
            "value": "value4",
            "id": res_id_key4,
            "send_event": True,
            "requires": [],
            "purged": False,
        },
    ]

    await clienthelper.put_version_simple(resources, version)
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await resource_container.wait_for_done_with_waiters(
        client, environment, version, wait_for_this_amount_of_resources_in_done=4, timeout=15
    )

    async def assert_deployment_status(res_id: str, expected_state: const.ResourceState) -> None:
        result = await client.get_resource(tid=environment, id=res_id, logs=False, status=True)
        assert result.code == 200
        assert result.result["status"] == expected_state

    await assert_deployment_status(res_id=res_id_key4, expected_state=const.ResourceState.deployed)
    # Failed via ctx.set_status(const.ResourceState.failed) in process_events()
    await assert_deployment_status(res_id=res_id_key3, expected_state=const.ResourceState.failed)
    # Skipped due to failed cross-agent dependency
    await assert_deployment_status(res_id=res_id_key2, expected_state=const.ResourceState.skipped)
    # Skipped due to failed local dependency
    await assert_deployment_status(res_id=res_id_key1, expected_state=const.ResourceState.skipped)


@pytest.mark.asyncio(timeout=15)
async def test_send_events_cross_agent_unavailable(
    resource_container, environment, server, client, clienthelper, no_agent_backoff, async_finalizer, caplog
):
    """
    Having unavailable cross agent dependencies shouldn't result in invalid Event objects (#2501)
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    resource_container.Provider.reset()

    agent2 = Agent(hostname="node2", environment=environment, agent_map={"agent2": "localhost"}, code_loader=False)

    async_finalizer.add(agent2.stop)
    await agent2.add_end_point_name("agent2")
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    async_finalizer.add(agent.stop)
    await agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)

    version = await clienthelper.get_version()

    res_id_1 = "test::Resource[agent1,key=key1],v=%d" % version
    res_id_2 = "test::ResourceNoHandler[agent2,key=key2],v=%d" % version
    res_id_3 = "test::Resource[agent2,key=key3],v=%d" % version
    # resource 1 requires an available and an unavailable resource
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": res_id_1,
            "send_event": True,
            "requires": [res_id_2, res_id_3],
            "purged": False,
        },
        {
            "key": "key2",
            "value": "value2",
            "id": res_id_2,
            "send_event": True,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key3",
            "value": "value3",
            "id": res_id_3,
            "send_event": True,
            "requires": [],
            "purged": False,
        },
    ]
    await clienthelper.put_version_simple(resources, version)

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    async def check_resource_state(environment, id, state):
        result = await client.get_resource(tid=environment, id=id, logs=False, status=True)
        assert result.code == 200
        return result.result["status"] == state

    assert await check_resource_state(environment, res_id_1, "skipped")

    assert await check_resource_state(environment, res_id_2, "unavailable")

    assert await check_resource_state(environment, res_id_3, "deployed")

    log_doesnt_contain(
        caplog, "inmanta.util", logging.ERROR, "An exception occurred while handling a future: 1 validation error for Event"
    )
