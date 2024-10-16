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

import asyncio
import dataclasses
import json
import logging
import os
import time
import uuid
from collections.abc import Mapping
from functools import partial
from itertools import groupby
from logging import DEBUG
from typing import Any, Collection, Coroutine, Optional
from uuid import UUID

import psutil
import pytest
from psutil import NoSuchProcess, Process

import utils
from agent_server.conftest import ResourceContainer, _deploy_resources, get_agent, wait_for_n_deployed_resources
from inmanta import agent, config, const, data, execute
from inmanta.agent import config as agent_config
from inmanta.agent import executor
from inmanta.agent.agent import Agent, DeployRequest, DeployRequestAction, deploy_response_matrix
from inmanta.agent.executor import ResourceInstallSpec
from inmanta.ast import CompilerException
from inmanta.config import Config
from inmanta.const import AgentAction, AgentStatus, ParameterSource, ResourceState
from inmanta.data import (
    AUTOSTART_AGENT_DEPLOY_INTERVAL,
    AUTOSTART_AGENT_REPAIR_INTERVAL,
    ENVIRONMENT_AGENT_TRIGGER_METHOD,
    PipConfig,
    Setting,
    convert_boolean,
)
from inmanta.protocol import Client
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_ENVIRONMENT,
    SLICE_PARAM,
    SLICE_SESSION_MANAGER,
)
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.protocol import Server
from inmanta.server.services.environmentservice import EnvironmentService
from inmanta.util import get_compiler_version
from utils import (
    UNKWN,
    ClientHelper,
    LogSequence,
    _wait_until_deployment_finishes,
    assert_equal_ish,
    log_contains,
    log_index,
    resource_action_consistency_check,
    retry_limited,
    wait_until_logs_are_available,
)

logger = logging.getLogger("inmanta.test.server_agent")


async def test_deploy_empty(server, client, clienthelper, environment, no_agent_backoff, async_finalizer):
    """
    Test deployment of empty model
    """
    agent = await get_agent(server, environment, "agent1", "agent2")
    async_finalizer(agent.stop)

    version = await clienthelper.get_version()

    resources = []

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 0
    assert result.result["model"]["result"] == const.VersionState.success.name


async def test_deploy_with_undefined(server, client, resource_container, async_finalizer, no_agent_backoff):
    """
    Test deploy of resource with undefined
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    Config.set("config", "agent-deploy-interval", "100")

    resource_container.Provider.reset()
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]
    env = await data.Environment.get_by_id(uuid.UUID(env_id))
    await env.set(data.AUTO_DEPLOY, False)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, False)
    await env.set(data.AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY, const.AgentTriggerMethod.push_full_deploy)

    resource_container.Provider.set_skip("agent2", "key1", 1)

    agent = Agent(
        hostname="node1", environment=env_id, agent_map={"agent1": "localhost", "agent2": "localhost"}, code_loader=False
    )
    async_finalizer.add(agent.stop)
    await agent.add_end_point_name("agent2")
    await agent.start()

    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    clienthelper = ClientHelper(client, env_id)

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent2,key=key1],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key2],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key4",
            "value": execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key4],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "requires": ["test::Resource[agent2,key=key1],v=%d" % version, "test::Resource[agent2,key=key2],v=%d" % version],
            "purged": False,
        },
        {
            "key": "key5",
            "value": "val",
            "id": "test::Resource[agent2,key=key5],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "requires": ["test::Resource[agent2,key=key4],v=%d" % version],
            "purged": False,
        },
    ]

    status = {
        "test::Resource[agent2,key=key4]": const.ResourceState.undefined,
        "test::Resource[agent2,key=key2]": const.ResourceState.undefined,
    }
    result = await client.put_version(
        tid=env_id,
        version=version,
        resources=resources,
        resource_state=status,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["result"] == "deploying"

    # The server will mark the full version as deployed even though the agent has not done anything yet.
    result = await client.get_version(env_id, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, env_id, version)

    result = await client.get_version(env_id, version)
    assert result.result["model"]["done"] == len(resources)
    assert result.code == 200

    actions = await data.ResourceAction.get_list()
    assert len([x for x in actions if x.status == const.ResourceState.undefined]) >= 1

    result = await client.get_version(env_id, version)
    assert result.code == 200

    assert resource_container.Provider.changecount("agent2", "key4") == 0
    assert resource_container.Provider.changecount("agent2", "key5") == 0
    assert resource_container.Provider.changecount("agent2", "key1") == 0

    assert resource_container.Provider.readcount("agent2", "key4") == 0
    assert resource_container.Provider.readcount("agent2", "key5") == 0
    assert resource_container.Provider.readcount("agent2", "key1") == 1

    # Do a second deploy of the same model on agent2 with undefined resources
    await agent.trigger_update("env_id", "agent2", incremental_deploy=False)

    result = await client.get_version(env_id, version, include_logs=True)

    def done():
        return (
            resource_container.Provider.changecount("agent2", "key4") == 0
            and resource_container.Provider.changecount("agent2", "key5") == 0
            and resource_container.Provider.changecount("agent2", "key1") == 1
            and resource_container.Provider.readcount("agent2", "key4") == 0
            and resource_container.Provider.readcount("agent2", "key5") == 0
            and resource_container.Provider.readcount("agent2", "key1") == 2
        )

    await retry_limited(done, 100)
    await resource_action_consistency_check()


async def test_server_restart(
    resource_container, server, agent, environment, clienthelper, postgres_db, client, no_agent_backoff, async_finalizer
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
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

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

    await _wait_until_deployment_finishes(client, env_id, version)

    result = await client.get_version(env_id, version)
    assert result.result["model"]["done"] == len(resources)

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert not resource_container.Provider.isset("agent1", "key3")


@pytest.mark.parametrize(
    "agent_deploy_interval",
    ["2", "*/2 * * * * * *"],
)
async def test_spontaneous_deploy(
    resource_container,
    server,
    client,
    environment,
    clienthelper,
    no_agent_backoff,
    async_finalizer,
    caplog,
    agent_deploy_interval,
):
    """
    dryrun and deploy a configuration model
    """
    start = time.time()
    with caplog.at_level(DEBUG):
        resource_container.Provider.reset()

        env_id = UUID(environment)

        Config.set("config", "agent-deploy-interval", agent_deploy_interval)
        Config.set("config", "agent-deploy-splay-time", "2")
        Config.set("config", "agent-repair-interval", "0")

        agent = await get_agent(server, environment, "agent1", "node1")
        async_finalizer(agent.stop)

        resource_container.Provider.set("agent1", "key2", "incorrect_value")
        resource_container.Provider.set("agent1", "key3", "value")

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
        result = await client.release_version(env_id, version, False)
        assert result.code == 200
        assert not result.result["model"]["deployed"]
        assert result.result["model"]["released"]
        assert result.result["model"]["total"] == 3
        assert result.result["model"]["result"] == "deploying"

        result = await client.get_version(env_id, version)
        assert result.code == 200

        await _wait_until_deployment_finishes(client, env_id, version)

        result = await client.get_version(env_id, version)
        assert result.result["model"]["done"] == len(resources)

        assert resource_container.Provider.isset("agent1", "key1")
        assert resource_container.Provider.get("agent1", "key1") == "value1"
        assert resource_container.Provider.get("agent1", "key2") == "value2"
        assert not resource_container.Provider.isset("agent1", "key3")

    duration = time.time() - start

    # approximate check, the number of heartbeats can vary, but not by a factor of 10
    beats = [message for logger_name, log_level, message in caplog.record_tuples if "Received heartbeat from" in message]
    assert (
        len(beats) < duration * 10
    ), f"Sent {len(beats)} heartbeats over a time period of {duration} seconds, sleep mechanism is broken"


@pytest.mark.parametrize(
    "agent_repair_interval",
    [
        "2",
        "*/2 * * * * * *",
    ],
)
async def test_spontaneous_repair(
    resource_container, environment, client, clienthelper, no_agent_backoff, async_finalizer, server, agent_repair_interval
):
    """
    Test that a repair run is executed every 2 seconds as specified in the agent_repair_interval (using a cron or not)
    """
    resource_container.Provider.reset()
    env_id = environment

    Config.set("config", "agent-repair-interval", agent_repair_interval)
    Config.set("config", "agent-repair-splay-time", "2")
    Config.set("config", "agent-deploy-interval", "0")

    agent = await get_agent(server, environment, "agent1", "node1")
    async_finalizer(agent.stop)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

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

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 3
    assert result.result["model"]["result"] == "deploying"

    result = await client.get_version(env_id, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, env_id, version)

    async def verify_deployment_result():
        result = await client.get_version(env_id, version)
        # A repair run may put one resource from the deployed state to the deploying state.
        assert len(resources) - 1 <= result.result["model"]["done"] <= len(resources)

        assert resource_container.Provider.isset("agent1", "key1")
        assert resource_container.Provider.get("agent1", "key1") == "value1"
        assert resource_container.Provider.get("agent1", "key2") == "value2"
        assert not resource_container.Provider.isset("agent1", "key3")

    await verify_deployment_result()

    # Manual change
    resource_container.Provider.set("agent1", "key2", "another_value")
    # Wait until repair restores the state
    now = time.time()
    while resource_container.Provider.get("agent1", "key2") != "value2":
        if time.time() > now + 10:
            raise Exception("Timeout occurred while waiting for repair run")
        await asyncio.sleep(0.1)

    await verify_deployment_result()
    await resource_action_consistency_check()


@pytest.mark.parametrize(
    "interval_code",
    [(2, 200), ("2", 200), ("*/2 * * * * * *", 200), ("", 400)],
)
async def test_env_setting_wiring_to_autostarted_agent(
    resource_container, environment, client, clienthelper, no_agent_backoff, async_finalizer, server, interval_code
):
    """
    Test that the AUTOSTART_AGENT_DEPLOY_INTERVAL and AUTOSTART_AGENT_REPAIR_INTERVAL
    env settings are properly wired through to auto-started agents.
    """
    env_id = UUID(environment)
    interval, expected_code = interval_code
    result = await client.set_setting(environment, AUTOSTART_AGENT_DEPLOY_INTERVAL, interval)
    assert result.code == expected_code
    result = await client.set_setting(environment, AUTOSTART_AGENT_REPAIR_INTERVAL, interval)
    assert result.code == expected_code

    if expected_code == 200:
        env = await data.Environment.get_by_id(env_id)
        autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)

        config = await autostarted_agent_manager._make_agent_config(env, connection=None)

        assert f"agent-deploy-interval={interval}" in config
        assert f"agent-repair-interval={interval}" in config


async def test_failing_deploy_no_handler(
    resource_container, agent, environment, client, clienthelper, async_finalizer, no_agent_backoff
):
    """
    dryrun and deploy a configuration model
    """
    resource_container.Provider.reset()

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Noprov[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "receive_events": False,
            "requires": [],
        }
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
    assert result.result["model"]["total"] == 1

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    result = await client.get_version(environment, version)
    assert result.result["model"]["done"] == len(resources)

    result = await client.get_version(environment, version, include_logs=True)

    logs = result.result["resources"][0]["actions"][0]["messages"]
    assert any("traceback" in log["kwargs"] for log in logs), "\n".join(result.result["resources"][0]["actions"][0]["messages"])


async def test_dual_agent(resource_container, server, client, clienthelper, environment, no_agent_backoff, async_finalizer):
    """
    dryrun and deploy a configuration model
    """
    resource_container.Provider.reset()
    myagent = agent.Agent(
        hostname="node1", environment=environment, agent_map={"agent1": "localhost", "agent2": "localhost"}, code_loader=False
    )
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    await myagent.add_end_point_name("agent1")
    await myagent.add_end_point_name("agent2")
    await myagent.start()
    async_finalizer(myagent.stop)
    await retry_limited(lambda: len(server.get_slice(SLICE_SESSION_MANAGER)._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key1", "incorrect_value")
    resource_container.Provider.set("agent2", "key1", "incorrect_value")

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Wait[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "receive_events": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value1",
            "id": "test::Wait[agent1,key=key2],v=%d" % version,
            "purged": False,
            "send_event": False,
            "receive_events": False,
            "requires": ["test::Wait[agent1,key=key1],v=%d" % version],
        },
        {
            "key": "key1",
            "value": "value2",
            "id": "test::Wait[agent2,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "receive_events": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Wait[agent2,key=key2],v=%d" % version,
            "purged": False,
            "send_event": False,
            "receive_events": False,
            "requires": ["test::Wait[agent2,key=key1],v=%d" % version],
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 4

    result = await resource_container.wait_for_done_with_waiters(client, environment, version)

    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["result"] == const.VersionState.success.name

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent2", "key1") == "value2"
    assert resource_container.Provider.get("agent1", "key2") == "value1"
    assert resource_container.Provider.get("agent2", "key2") == "value2"

    await myagent.stop()


async def test_server_agent_api(
    resource_container, client, server, environment, clienthelper, no_agent_backoff, async_finalizer
):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    env_id = environment

    agent = Agent(environment=env_id, hostname="agent1", agent_map={"agent1": "localhost"}, code_loader=False)
    await agent.start()
    async_finalizer(agent.stop)

    agent2 = Agent(environment=env_id, hostname="agent2", agent_map={"agent2": "localhost"}, code_loader=False)
    await agent2.start()
    async_finalizer(agent2.stop)

    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)
    assert len(agentmanager.sessions) == 2

    result = await client.list_agent_processes(env_id)
    assert result.code == 200

    while len(result.result["processes"]) != 2:
        result = await client.list_agent_processes(env_id)
        assert result.code == 200
        await asyncio.sleep(0.1)

    assert len(result.result["processes"]) == 2
    agents = ["agent1", "agent2"]
    for proc in result.result["processes"]:
        assert proc["environment"] == env_id
        assert len(proc["endpoints"]) == 1
        assert proc["endpoints"][0]["name"] in agents
        agents.remove(proc["endpoints"][0]["name"])

    assert_equal_ish(
        {
            "processes": [
                {
                    "expired": None,
                    "environment": env_id,
                    "endpoints": [{"name": UNKWN, "process": UNKWN, "id": UNKWN}],
                    "hostname": UNKWN,
                    "first_seen": UNKWN,
                    "last_seen": UNKWN,
                },
                {
                    "expired": None,
                    "environment": env_id,
                    "endpoints": [{"name": UNKWN, "process": UNKWN, "id": UNKWN}],
                    "hostname": UNKWN,
                    "first_seen": UNKWN,
                    "last_seen": UNKWN,
                },
            ]
        },
        result.result,
        ["name", "first_seen"],
    )

    print(result.__dict__)
    agent_sid = result.result["processes"][0]["sid"]
    endpointid = [x["endpoints"][0]["id"] for x in result.result["processes"] if x["endpoints"][0]["name"] == "agent1"][0]

    result = await client.get_agent_process(id=agent_sid)
    assert result.code == 200

    result = await client.get_agent_process(id=uuid.uuid4())
    assert result.code == 404

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": "test::Resource[agent1,key=key],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key2",
            "value": "value",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    result = await client.list_agents(tid=env_id)
    assert result.code == 200

    shouldbe = {
        "agents": [
            {
                "last_failover": UNKWN,
                "environment": env_id,
                "paused": False,
                "primary": endpointid,
                "name": "agent1",
                "state": "up",
            }
        ]
    }

    assert_equal_ish(shouldbe, result.result)

    result = await client.list_agents(tid=uuid.uuid4())
    assert result.code == 404


async def test_get_set_param(resource_container, environment, client, server):
    """
    Test getting and setting params
    """
    resource_container.Provider.reset()
    await client.set_setting(environment, data.SERVER_COMPILE, False)

    result = await client.set_param(tid=environment, id="key10", value="value10", source=ParameterSource.user)
    assert result.code == 200

    result = await client.get_param(tid=environment, id="key10")
    assert result.code == 200
    assert result.result["parameter"]["value"] == "value10"

    result = await client.delete_param(tid=environment, id="key10")
    assert result.code == 200


async def test_register_setting(environment, client, server, caplog):
    """
    Test registering a new setting.
    """
    caplog.set_level(logging.WARNING)
    new_setting: Setting = Setting(
        name="a new boolean setting",
        default=False,
        typ="bool",
        validator=convert_boolean,
        doc="a new setting",
    )
    env_slice: EnvironmentService = server.get_slice(SLICE_ENVIRONMENT)
    caplog.clear()
    await env_slice.register_setting(new_setting)

    log_contains(
        caplog,
        "py.warnings",
        logging.WARNING,
        "Registering environment settings via the inmanta.server.services.environmentservice.register_setting endpoint "
        "is deprecated.",
    )
    result = await client.get_setting(tid=environment, id="a new boolean setting")
    assert result.code == 200
    assert result.result["value"] is False


@pytest.mark.parametrize("halted", [True, False])
async def test_unknown_parameters(
    resource_container, environment, client, server, clienthelper, agent, no_agent_backoff, halted, caplog
):
    """
    Test retrieving facts from the agent
    """

    caplog.set_level(logging.DEBUG)
    resource_container.Provider.reset()
    await client.set_setting(environment, data.SERVER_COMPILE, False)

    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": resource_id,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        }
    ]

    unknowns = [{"resource": resource_id_wov, "parameter": "length", "source": "fact"}]

    if halted:
        result = await client.halt_environment(environment)
        assert result.code == 200

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=unknowns,
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await server.get_slice(SLICE_PARAM).renew_facts()

    env_id = uuid.UUID(environment)
    if not halted:
        params = await data.Parameter.get_list(environment=env_id, resource_id=resource_id_wov)
        while len(params) < 3:
            params = await data.Parameter.get_list(environment=env_id, resource_id=resource_id_wov)
            await asyncio.sleep(0.1)

        result = await client.get_param(env_id, "length", resource_id_wov)
        assert result.code == 200
        msg = f"Requesting value for unknown parameter length of resource test::Resource[agent1,key=key] in env {environment}"
        log_contains(caplog, "inmanta.server.services.paramservice", logging.DEBUG, msg)

    else:
        msg = (
            "Not Requesting value for unknown parameter length of resource test::Resource[agent1,key=key] "
            f"in env {environment} as the env is halted"
        )
        log_contains(caplog, "inmanta.server.services.paramservice", logging.DEBUG, msg)


async def test_fail(resource_container, client, agent, environment, clienthelper, async_finalizer, no_agent_backoff):
    """
    Test results when a step fails
    """
    resource_container.Provider.reset()

    resource_container.Provider.set("agent1", "key", "value")

    env_id = environment

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": "test::Fail[agent1,key=key],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key2",
            "value": "value",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "requires": ["test::Fail[agent1,key=key],v=%d" % version],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key3",
            "value": "value",
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "requires": ["test::Fail[agent1,key=key],v=%d" % version],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key4",
            "value": "value",
            "id": "test::Resource[agent1,key=key4],v=%d" % version,
            "requires": ["test::Resource[agent1,key=key3],v=%d" % version],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key5",
            "value": "value",
            "id": "test::Resource[agent1,key=key5],v=%d" % version,
            "requires": ["test::Resource[agent1,key=key4],v=%d" % version, "test::Fail[agent1,key=key],v=%d" % version],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
    ]

    await clienthelper.put_version_simple(resources, version)

    # deploy and wait until done
    result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    result = await client.get_version(env_id, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, env_id, version)

    result = await client.get_version(env_id, version)
    assert result.result["model"]["done"] == len(resources)

    states = {x["id"]: x["status"] for x in result.result["resources"]}

    assert states["test::Fail[agent1,key=key],v=%d" % version] == "failed"
    assert states["test::Resource[agent1,key=key2],v=%d" % version] == "skipped"
    assert states["test::Resource[agent1,key=key3],v=%d" % version] == "skipped"
    assert states["test::Resource[agent1,key=key4],v=%d" % version] == "skipped"
    assert states["test::Resource[agent1,key=key5],v=%d" % version] == "skipped"


async def test_multi_instance(resource_container, client, clienthelper, server, environment, no_agent_backoff, async_finalizer):
    """
    Test for multi threaded deploy
    """
    env_id = environment

    resource_container.Provider.reset()

    # setup agent
    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost", "agent2": "localhost", "agent3": "localhost"},
        code_loader=False,
    )
    await agent.add_end_point_name("agent1")
    await agent.add_end_point_name("agent2")
    await agent.add_end_point_name("agent3")

    await agent.start()
    async_finalizer(agent.stop)

    # wait for agent
    await retry_limited(lambda: len(server.get_slice(SLICE_SESSION_MANAGER)._sessions) == 1, 10)

    # set the deploy environment
    resource_container.Provider.set("agent1", "key", "value")
    resource_container.Provider.set("agent2", "key", "value")
    resource_container.Provider.set("agent3", "key", "value")

    async def make_version():
        version = await clienthelper.get_version()
        resources = []
        for agent in ["agent1", "agent2", "agent3"]:
            resources.extend(
                [
                    {
                        "key": "key",
                        "value": "value",
                        "id": "test::Wait[%s,key=key],v=%d" % (agent, version),
                        "requires": ["test::Resource[%s,key=key3],v=%d" % (agent, version)],
                        "purged": False,
                        "send_event": False,
                        "receive_events": False,
                    },
                    {
                        "key": "key2",
                        "value": "value",
                        "id": "test::Resource[%s,key=key2],v=%d" % (agent, version),
                        "requires": ["test::Wait[%s,key=key],v=%d" % (agent, version)],
                        "purged": False,
                        "send_event": False,
                        "receive_events": False,
                    },
                    {
                        "key": "key3",
                        "value": "value",
                        "id": "test::Resource[%s,key=key3],v=%d" % (agent, version),
                        "requires": [],
                        "purged": False,
                        "send_event": False,
                        "receive_events": False,
                    },
                    {
                        "key": "key4",
                        "value": "value",
                        "id": "test::Resource[%s,key=key4],v=%d" % (agent, version),
                        "requires": ["test::Resource[%s,key=key3],v=%d" % (agent, version)],
                        "purged": False,
                        "send_event": False,
                        "receive_events": False,
                    },
                    {
                        "key": "key5",
                        "value": "value",
                        "id": "test::Resource[%s,key=key5],v=%d" % (agent, version),
                        "requires": [
                            "test::Resource[%s,key=key4],v=%d" % (agent, version),
                            "test::Wait[%s,key=key],v=%d" % (agent, version),
                        ],
                        "purged": False,
                        "send_event": False,
                        "receive_events": False,
                    },
                ]
            )
        return version, resources

    async def wait_for_resources(version, n):
        result = await client.get_version(env_id, version)
        assert result.code == 200

        def done_per_agent(result):
            done = [x for x in result.result["resources"] if x["status"] == "deployed"]
            peragent = groupby(done, lambda x: x["agent"])
            return {agent: len([x for x in grp]) for agent, grp in peragent}

        def mindone(result):
            alllist = done_per_agent(result).values()
            if len(alllist) == 0:
                return 0
            return min(alllist)

        while mindone(result) < n:
            await asyncio.sleep(0.1)
            result = await client.get_version(env_id, version)
        assert mindone(result) >= n

    logger.info("setup done")

    version1, resources = await make_version()
    result = await client.put_version(
        tid=env_id, version=version1, resources=resources, unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    logger.info("first version pushed")

    # deploy and wait until one is ready
    result = await client.release_version(env_id, version1, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    logger.info("first version released")
    # timeout on single thread!
    await wait_for_resources(version1, 1)

    await resource_container.wait_for_done_with_waiters(client, env_id, version1)

    logger.info("first version complete")
    await agent.stop()
    await resource_action_consistency_check()


async def test_cross_agent_deps(
    resource_container,
    server,
    client,
    environment,
    clienthelper,
    no_agent_backoff,
    async_finalizer,
    caplog,
):
    """
    deploy a configuration model with cross host dependency

    This test also verifies correct handling of spaces in url parameters on the return channel
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    # config for recovery mechanism
    Config.set("config", "agent-deploy-interval", "10")

    env_id = environment

    agent = Agent(hostname="node1", environment=env_id, agent_map={"agent 1": "localhost"}, code_loader=False)
    await agent.add_end_point_name("agent 1")
    async_finalizer(agent.stop)
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    agent2 = Agent(hostname="node2", environment=env_id, agent_map={"agent2": "localhost"}, code_loader=False)
    await agent2.add_end_point_name("agent2")
    async_finalizer(agent2.stop)
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)

    resource_container.Provider.set("agent 1", "key2", "incorrect_value")
    resource_container.Provider.set("agent 1", "key3", "value")

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent 1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "receive_events": False,
            "requires": ["test::Wait[agent 1,key=key2],v=%d" % version, "test::Resource[agent2,key=key3],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Wait[agent 1,key=key2],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key3",
            "value": "value3",
            "id": "test::Resource[agent2,key=key3],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
        {
            "key": "key4",
            "value": "value4",
            "id": "test::Resource[agent2,key=key4],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        },
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 4
    assert result.result["model"]["result"] == const.VersionState.deploying.name

    result = await client.get_version(env_id, version)
    assert result.code == 200

    while result.result["model"]["done"] == 0:
        result = await client.get_version(env_id, version)
        await asyncio.sleep(0.1)

    result = await resource_container.wait_for_done_with_waiters(client, env_id, version)

    async def is_success() -> bool:
        result = await client.get_version(env_id, version)
        assert result.code == 200
        return result.result["model"]["result"] == const.VersionState.success.name

    assert result.result["model"]["done"] == len(resources)
    await retry_limited(is_success, timeout=1)

    assert resource_container.Provider.isset("agent 1", "key1")
    assert resource_container.Provider.get("agent 1", "key1") == "value1"
    assert resource_container.Provider.get("agent 1", "key2") == "value2"
    assert resource_container.Provider.get("agent2", "key3") == "value3"
    # CAD's involve some background tasks of which the exceptions don't propagate
    # It is also sufficiently redundant to succeed if they fail, be it slowly
    utils.no_error_in_logs(caplog)


@pytest.mark.parametrize(
    "agent_trigger_method, read_resource1, change_resource1, read_resource2, change_resource2",
    [(const.AgentTriggerMethod.push_incremental_deploy, 1, 1, 2, 2), (const.AgentTriggerMethod.push_full_deploy, 2, 1, 2, 2)],
)
async def test_auto_deploy(
    agent,
    client,
    resource_container,
    environment,
    agent_trigger_method,
    read_resource1,
    change_resource1,
    read_resource2,
    change_resource2,
    no_agent_backoff,
    clienthelper,
):
    """
    dryrun and deploy a configuration model automatically
    """
    resource_container.Provider.reset()

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    def get_resources(version, value_resource_two):
        return [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
            },
            {
                "key": "key2",
                "value": value_resource_two,
                "id": "test::Resource[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "requires": [],
                "purged": False,
            },
            {
                "key": "key3",
                "value": None,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "requires": [],
                "purged": True,
            },
        ]

    initial_version = await clienthelper.get_version()
    second_version = await clienthelper.get_version()
    for version, value_resource_two in [(initial_version, "value1"), (second_version, "value2")]:
        resources = get_resources(version, value_resource_two)

        # set auto deploy and push
        result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
        assert result.code == 200
        result = await client.set_setting(environment, data.PUSH_ON_AUTO_DEPLOY, True)
        assert result.code == 200
        result = await client.set_setting(environment, data.AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY, agent_trigger_method)
        assert result.code == 200

        await clienthelper.put_version_simple(resources, version, wait_for_released=True)

        # check deploy
        result = await client.get_version(environment, version)
        assert result.code == 200
        assert result.result["model"]["released"]
        assert result.result["model"]["total"] == 3
        assert result.result["model"]["result"] in ["deploying", "success"]

        await _wait_until_deployment_finishes(client, environment, version)

        result = await client.get_version(environment, version)
        assert result.result["model"]["done"] == len(resources)

        assert resource_container.Provider.isset("agent1", "key1")
        assert resource_container.Provider.get("agent1", "key1") == "value1"
        assert resource_container.Provider.get("agent1", "key2") == value_resource_two
        assert not resource_container.Provider.isset("agent1", "key3")

    async def check_final() -> bool:
        return (
            (resource_container.Provider.readcount("agent1", "key1") == read_resource1)
            and (resource_container.Provider.changecount("agent1", "key1") == change_resource1)
            and (resource_container.Provider.readcount("agent1", "key2") == read_resource2)
            and (resource_container.Provider.changecount("agent1", "key2") == change_resource2)
        )

    await retry_limited(check_final, 1)


async def test_auto_deploy_no_splay(server, client, clienthelper, resource_container, environment, no_agent_backoff):
    """
    dryrun and deploy a configuration model automatically with agent autostart
    """
    resource_container.Provider.reset()
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": ""})
    await env.set(data.AUTOSTART_ON_START, True)

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        },
    ]

    # set auto deploy and push
    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200
    result = await client.set_setting(environment, data.PUSH_ON_AUTO_DEPLOY, True)
    assert result.code == 200
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, 0)
    assert result.code == 200

    await clienthelper.put_version_simple(resources, version)

    # check deploy
    await _wait_until_deployment_finishes(client, environment, version)
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 2
    assert result.result["model"]["result"] == "failed"

    # check if agent 1 is started by the server
    # deploy will fail because handler code is not uploaded to the server
    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while len(result.result["agents"]) == 0 or result.result["agents"][0]["state"] == "down":
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == "agent1"


def ps_diff_inmanta_agent_processes(original: list[psutil.Process], current_process: psutil.Process, diff: int = 0) -> None:
    current = _get_inmanta_agent_child_processes(current_process)

    def is_terminated(proc):
        try:
            Process(proc.pid)
        except NoSuchProcess:
            return True
        except Exception:
            return False
        return False

    if not len(original) + diff == len(current):
        # can be in terminated state apparently
        current = [c for c in current if not is_terminated(c)]
        original = [c for c in original if not is_terminated(c)]

    assert len(original) + diff == len(
        current
    ), """procs found:
        pre:{}
        post:{}""".format(
        original,
        current,
    )


async def test_autostart_mapping(server, client, clienthelper, resource_container, environment, no_agent_backoff):
    """
    Test whether an autostarted agent updates its agent-map correctly when the autostart_agent_map is updated on the server.

    The handler code in the resource_container is not available to the autostarted agent. When the agent loads these
    resources it will mark them as unavailable. There is only one agent started when deploying is checked.
    """
    env_uuid = uuid.UUID(environment)
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)
    current_process = psutil.Process()
    agent_processes_pre: list[psutil.Process] = _get_inmanta_agent_child_processes(current_process)
    resource_container.Provider.reset()
    env = await data.Environment.get_by_id(env_uuid)
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": ""})
    await env.set(data.AUTO_DEPLOY, True)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    await env.set(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, 0)
    await env.set(data.AUTOSTART_ON_START, True)

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent2,key=key1],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        },
    ]

    await clienthelper.put_version_simple(resources, version, wait_for_released=True)
    # check deploy
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 2
    assert result.result["model"]["result"] == "deploying"

    result = await client.list_agents(tid=environment)
    assert result.code == 200

    def wait_for_nr_of_agents_in_up_state(nr_agents: int) -> None:
        async def _check_wait_condition() -> bool:
            result = await client.list_agents(tid=environment)
            assert result.code == 200
            return len([x for x in result.result["agents"] if x["state"] == "up"]) == nr_agents

        return _check_wait_condition

    async def assert_session_state(expected_agent_states: dict[str, AgentStatus], expected_agent_instances: list[str]) -> None:
        result = await data.AgentProcess.get_list()
        assert len(result) == 1
        sid = result[0].sid
        assert result[0].expired is None

        result = await data.Agent.get_list()
        assert len(result) == 2
        agents = {r.name: r for r in result}
        for agent_name, state in expected_agent_states.items():
            assert agents[agent_name].get_status() == state

        result = await data.AgentInstance.get_list()
        agents = {r.name: r for r in result}
        for agent_name, state in expected_agent_states.items():
            if agent_name not in expected_agent_instances:
                assert agent_name not in agents
            elif state == AgentStatus.down:
                assert agents[agent_name].expired is not None
            else:
                assert agents[agent_name].expired is None

        assert len(agent_manager.sessions) == 1
        assert sid in agent_manager.sessions
        for agent_name, state in expected_agent_states.items():
            if state == AgentStatus.down:
                assert (env_uuid, agent_name) not in agent_manager.tid_endpoint_to_session
            else:
                assert (env_uuid, agent_name) in agent_manager.tid_endpoint_to_session

    await retry_limited(wait_for_nr_of_agents_in_up_state(1), 10)

    await assert_session_state({"agent1": AgentStatus.up, "agent2": AgentStatus.down}, ["agent1"])

    # Add entry to autostart_agent_map
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": "", "agent2": ""})
    assert result.code == 200

    await retry_limited(wait_for_nr_of_agents_in_up_state(2), 10)
    await assert_session_state({"agent1": AgentStatus.up, "agent2": AgentStatus.up}, ["agent1", "agent2"])

    # Remove entry from autostart agent_map
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": ""})
    assert result.code == 200

    await retry_limited(wait_for_nr_of_agents_in_up_state(1), 10)
    await assert_session_state({"agent1": AgentStatus.up, "agent2": AgentStatus.down}, ["agent1", "agent2"])

    # Stop server
    await asyncio.wait_for(server.stop(), timeout=15)

    agent_processes: list[psutil.Process] = _get_inmanta_agent_child_processes(current_process)
    new_agent_processes = set(agent_processes) - set(agent_processes_pre)

    assert len(new_agent_processes) == 0, new_agent_processes


@pytest.mark.parametrize("autostarted", (True, False))
async def test_autostart_mapping_overrides_config(server, client, environment, async_finalizer, caplog, autostarted: bool):
    """
    Verify that the use_autostart_agent_map setting takes precedence over agents configured in the config file.
    When the option is set the server's agent map should be the authority for which agents to manage.
    """
    # configure agent as an autostarted agent or not
    agent_config.use_autostart_agent_map.set(str(autostarted).lower())
    # also configure the agent with an explicit agent config and agent map, which should be ignored
    configured_agent: str = "configured_agent"
    agent_config.agent_names.set(configured_agent)

    env_uuid = uuid.UUID(environment)
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)

    # configure server's autostarted agent map
    autostarted_agent: str = "autostarted_agent"
    result = await client.set_setting(
        env_uuid,
        data.AUTOSTART_AGENT_MAP,
        {"internal": "localhost", autostarted_agent: "localhost"},
    )
    assert result.code == 200

    # Start agent
    a = agent.Agent(environment=env_uuid, code_loader=False)
    await a.start()
    async_finalizer(a.stop)

    # Wait until agents are up
    await retry_limited(lambda: len(agent_manager.tid_endpoint_to_session) == (2 if autostarted else 1), timeout=2)

    endpoint_sessions: Mapping[str, UUID] = {
        key[1]: session.id for key, session in agent_manager.tid_endpoint_to_session.items()
    }
    assert endpoint_sessions == (
        {
            "internal": a.sessionid,
            autostarted_agent: a.sessionid,
        }
        if autostarted
        else {
            configured_agent: a.sessionid,
        }
    )


async def test_autostart_mapping_update_uri(
    server, client, clienthelper, environment, async_finalizer, resource_container, caplog, no_agent_backoff
):
    caplog.set_level(logging.INFO)
    agent_config.use_autostart_agent_map.set("true")
    env_uuid = uuid.UUID(environment)
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)
    agent_name = "internal"

    # Start agent
    a = agent.Agent(hostname=agent_name, environment=env_uuid, code_loader=False)
    await a.start()
    async_finalizer(a.stop)

    # Wait until agent is up
    async def agent_in_db() -> bool:
        return len(await data.AgentInstance.get_list()) == 1

    await retry_limited(lambda: (env_uuid, agent_name) in agent_manager.tid_endpoint_to_session, 10)
    await retry_limited(agent_in_db, 10)

    async def deploy_one():
        version = await clienthelper.get_version()

        resources = [
            {
                "key": "key1",
                "value": f"value{version}",
                "id": f"test::Resource[{agent_name},key=key1],v={version}",
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
        ]

        await clienthelper.put_version_simple(resources, version)
        await client.release_version(environment, version, push=True)
        await clienthelper.wait_for_deployed(version)

    await deploy_one()

    # Update agentmap
    caplog.clear()
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_MAP, {agent_name: "localhost"})
    assert result.code == 200

    await retry_limited(lambda: f"Updating the URI of the endpoint {agent_name} from local: to localhost" in caplog.text, 10)

    await deploy_one()

    # this can fail in the background, #7641
    LogSequence(caplog).no_more_errors()

    # Pause agent
    result = await client.agent_action(tid=env_uuid, name="internal", action=const.AgentAction.pause.value)
    assert result.code == 200

    # Update agentmap when internal agent is paused
    caplog.clear()
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_MAP, {agent_name: "local:"})
    assert result.code == 200

    await retry_limited(lambda: f"Updating the URI of the endpoint {agent_name} from localhost to local:" in caplog.text, 10)


async def test_autostart_clear_environment(server, client, resource_container, environment, no_agent_backoff):
    """
    Test clearing an environment with autostarted agents. After clearing, autostart should still work

    The handler code in the resource_container is not available to the autostarted agent. When the agent loads these
    resources it will mark them as unavailable. This will make the deploy fail.
    """
    resource_container.Provider.reset()
    current_process = psutil.Process()
    inmanta_agent_child_processes: list[psutil.Process] = _get_inmanta_agent_child_processes(current_process)
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": ""})
    await env.set(data.AUTO_DEPLOY, True)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    await env.set(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, 0)
    await env.set(data.AUTOSTART_ON_START, True)

    clienthelper = ClientHelper(client, environment)
    version = await clienthelper.get_version()
    await clienthelper.put_version_simple(
        [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            }
        ],
        version,
    )

    # check deploy
    await _wait_until_deployment_finishes(client, environment, version)
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "failed"

    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 1:
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert len([x for x in result.result["agents"] if x["state"] == "up"]) == 1
    # One autostarted agent should running as a subprocess
    ps_diff_inmanta_agent_processes(original=inmanta_agent_child_processes, current_process=current_process, diff=1)

    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
    venv_dir_agent1 = os.path.join(
        autostarted_agent_manager._get_state_dir_for_agent_in_env(uuid.UUID(environment)), "agent", "env"
    )

    # clear environment
    assert os.path.exists(venv_dir_agent1)
    result = await client.clear_environment(environment)
    assert result.code == 200
    assert not os.path.exists(venv_dir_agent1)

    # Autostarted agent should be terminated after clearing the environment
    ps_diff_inmanta_agent_processes(original=inmanta_agent_child_processes, current_process=current_process, diff=0)
    items = await data.ConfigurationModel.get_list()
    assert len(items) == 0
    items = await data.Resource.get_list()
    assert len(items) == 0
    items = await data.ResourceAction.get_list()
    assert len(items) == 0
    items = await data.Code.get_list()
    assert len(items) == 0
    items = await data.Agent.get_list()
    assert len(items) == 0
    items = await data.AgentInstance.get_list()
    assert len(items) == 0
    items = await data.AgentProcess.get_list()
    assert len(items) == 0

    # Do a deploy again
    version = await clienthelper.get_version()
    await clienthelper.put_version_simple(
        [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            }
        ],
        version,
    )

    # check deploy
    await _wait_until_deployment_finishes(client, environment, version)
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "failed"

    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 1:
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert len([x for x in result.result["agents"] if x["state"] == "up"]) == 1

    # One autostarted agent should running as a subprocess
    ps_diff_inmanta_agent_processes(original=inmanta_agent_child_processes, current_process=current_process, diff=1)


@pytest.mark.parametrize("delete_project", [True, False])
async def test_autostart_clear_agent_venv_on_delete(
    server, client, resource_container, project_default: str, environment: str, no_agent_backoff, delete_project: bool
) -> None:
    """
    Ensure that the venv of an auto-started agent gets cleaned up when its environment or project is deleted.
    """
    resource_container.Provider.reset()
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": ""})
    await env.set(data.AUTO_DEPLOY, True)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    await env.set(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, 0)
    await env.set(data.AUTOSTART_ON_START, True)

    clienthelper = ClientHelper(client, environment)
    version = await clienthelper.get_version()
    await clienthelper.put_version_simple(
        [
            {
                "key": "key1",
                "value": "value1",
                "id": f"test::Resource[agent1,key=key1],v={version}",
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            }
        ],
        version,
    )

    # check deploy
    await _wait_until_deployment_finishes(client, environment, version)

    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
    venv_dir_agent1 = os.path.join(
        autostarted_agent_manager._get_state_dir_for_agent_in_env(uuid.UUID(environment)), "agent", "env"
    )

    assert os.path.exists(venv_dir_agent1)

    result = await client.delete_environment(environment)
    assert result.code == 200

    if delete_project:
        result = await client.delete_project(project_default)
        assert result.code == 200

    assert not os.path.exists(venv_dir_agent1)


async def setup_environment_with_agent(client, project_name):
    """
    1) Create a project with name project_name and create an environment.
    2) Deploy a model which requires one autostarted agent. The agent does not have code so it will mark the version as
       failed.
    3) Wait until the autostarted agent is up.
    """
    create_project_result = await client.create_project(project_name)
    assert create_project_result.code == 200
    project_id = create_project_result.result["project"]["id"]

    create_environment_result = await client.create_environment(project_id=project_id, name="dev")
    assert create_environment_result.code == 200
    env_id = create_environment_result.result["environment"]["id"]
    env = await data.Environment.get_by_id(uuid.UUID(env_id))

    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": ""})
    await env.set(data.AUTO_DEPLOY, True)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    await env.set(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, 0)
    await env.set(data.AUTOSTART_ON_START, True)

    clienthelper = ClientHelper(client, env_id)
    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        }
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    # check deploy
    await _wait_until_deployment_finishes(client, env_id, version)
    result = await client.get_version(env_id, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "failed"

    result = await client.list_agents(tid=env_id)
    assert result.code == 200

    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 1:
        result = await client.list_agents(tid=env_id)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert len([x for x in result.result["agents"] if x["state"] == "up"]) == 1

    return project_id, env_id


def _get_inmanta_agent_child_processes(parent_process: psutil.Process) -> list[psutil.Process]:
    def try_get_cmd(p: psutil.Process) -> str:
        try:
            return p.cmdline()
        except Exception:
            logger.warning("A child process is gone! pid=%d", p.pid)
            """If a child process is gone, p.cmdline() raises an exception"""
            return ""

    return [p for p in parent_process.children(recursive=True) if "inmanta.app" in try_get_cmd(p) and "agent" in try_get_cmd(p)]


async def test_stop_autostarted_agents_on_environment_removal(server, client, resource_container, no_agent_backoff):
    current_process = psutil.Process()
    inmanta_agent_child_processes: list[psutil.Process] = _get_inmanta_agent_child_processes(current_process)
    resource_container.Provider.reset()
    (project_id, env_id) = await setup_environment_with_agent(client, "proj")

    # One autostarted agent should running as a subprocess
    ps_diff_inmanta_agent_processes(original=inmanta_agent_child_processes, current_process=current_process, diff=1)

    result = await client.delete_environment(id=env_id)
    assert result.code == 200, result.result

    # The autostarted agent should be terminated when its environment is deleted.
    ps_diff_inmanta_agent_processes(original=inmanta_agent_child_processes, current_process=current_process, diff=0)


async def test_export_duplicate(resource_container, snippetcompiler):
    """
    The exported should provide a compilation error when a resource is defined twice in a model
    """
    snippetcompiler.setup_for_snippet(
        """
        import test

        test::Resource(key="test", value="foo")
        test::Resource(key="test", value="bar")
    """,
        autostd=True,
    )

    with pytest.raises(CompilerException) as exc:
        snippetcompiler.do_export()

    assert "exists more than once in the configuration model" in str(exc.value)


class ResourceProvider:
    def __init__(self, index, name, producer, state=None):
        self.name = name
        self.producer = producer
        self.state = state
        self.index = index

    def get_resource(
        self, resource_container: ResourceContainer, agent: str, key: str, version: str, requires: list[str]
    ) -> tuple[dict[str, str], Optional[const.ResourceState]]:
        base = {
            "key": key,
            "value": "value1",
            "id": "test::Resource[%s,key=%s],v=%d" % (agent, key, version),
            "send_event": True,
            "receive_events": False,
            "purged": False,
            "requires": requires,
        }

        self.producer(resource_container.Provider, agent, key)

        state = None
        if self.state is not None:
            state = (f"test::Resource[{agent},key={key}]", self.state)

        return base, state

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


# for events, self is the consuming node
# dep is the producer/required node
self_states = [
    ResourceProvider(0, "skip", lambda p, a, k: p.set_skip(a, k, 1)),
    ResourceProvider(1, "fail", lambda p, a, k: p.set_fail(a, k, 1)),
    ResourceProvider(2, "success", lambda p, a, k: None),
    ResourceProvider(3, "undefined", lambda p, a, k: None, const.ResourceState.undefined),
]

dep_states = [
    ResourceProvider(0, "skip", lambda p, a, k: p.set_skip(a, k, 1)),
    ResourceProvider(1, "fail", lambda p, a, k: p.set_fail(a, k, 1)),
    ResourceProvider(2, "success", lambda p, a, k: None),
]


def make_matrix(matrix, valueparser):
    """
    Expect matrix of the form

        header1    header2     header3
    row1    y    y    n
    """
    unparsed = [[v for v in row.split()][1:] for row in matrix.strip().split("\n")][1:]

    return [[valueparser(nsv) for nsv in nv] for nv in unparsed]


# self state on X axis
# dep state on the Y axis
dorun = make_matrix(
    """
        skip    fail    success    undef
skip    n    n    n    n
fail    n    n    n    n
succ    y    y    y    n
""",
    lambda x: x == "y",
)

dochange = make_matrix(
    """
        skip    fail    success    undef
skip    n    n    n    n
fail    n    n    n    n
succ    n    n    y    n
""",
    lambda x: x == "y",
)


@pytest.mark.parametrize("self_state", self_states, ids=lambda x: x.name)
@pytest.mark.parametrize("dep_state", dep_states, ids=lambda x: x.name)
async def test_deploy_and_events(
    client, agent, clienthelper, environment, resource_container, self_state, dep_state, async_finalizer, no_agent_backoff
):
    resource_container.Provider.reset()

    version = await clienthelper.get_version()

    (dep, dep_status) = dep_state.get_resource(resource_container, "agent1", "key2", version, [])
    (own, own_status) = self_state.get_resource(
        resource_container,
        "agent1",
        "key3",
        version,
        ["test::Resource[agent1,key=key2],v=%d" % version, "test::Resource[agent1,key=key1],v=%d" % version],
    )

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": True,
            "receive_events": False,
            "purged": False,
            "requires": [],
        },
        dep,
        own,
    ]

    status = {x[0]: x[1] for x in [dep_status, own_status] if x is not None}
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state=status,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 3
    assert result.result["model"]["result"] == "deploying"

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    result = await client.get_version(environment, version)
    assert result.result["model"]["done"] == len(resources)

    # verify against result matrices
    assert dorun[dep_state.index][self_state.index] == (resource_container.Provider.readcount("agent1", "key3") > 0)
    assert dochange[dep_state.index][self_state.index] == (resource_container.Provider.changecount("agent1", "key3") > 0)


dep_states_reload = [
    ResourceProvider(0, "skip", lambda p, a, k: p.set_skip(a, k, 1)),
    ResourceProvider(0, "fail", lambda p, a, k: p.set_fail(a, k, 1)),
    ResourceProvider(0, "nochange", lambda p, a, k: p.set(a, k, "value1")),
    ResourceProvider(1, "changed", lambda p, a, k: None),
]


@pytest.mark.parametrize("dep_state", dep_states_reload, ids=lambda x: x.name)
async def test_reload(
    server, client, clienthelper, environment, resource_container, dep_state, no_agent_backoff, async_finalizer
):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await agent.add_end_point_name("agent1")
    async_finalizer(agent.stop)
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = await clienthelper.get_version()

    (dep, dep_status) = dep_state.get_resource(resource_container, "agent1", "key1", version, [])

    resources = [
        {
            "key": "key2",
            "value": "value1",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": True,
            "receive_events": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
        },
        dep,
    ]

    status = {x[0]: x[1] for x in [dep_status] if x is not None}
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state=status,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 2
    assert result.result["model"]["result"] == "deploying"

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    result = await client.get_version(environment, version)
    assert result.result["model"]["done"] == len(resources)

    assert dep_state.index == resource_container.Provider.reloadcount("agent1", "key2")


async def test_s_repair_postponed_due_to_running_deploy(
    resource_container, agent, client, clienthelper, environment, no_agent_backoff, caplog
):
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"
    myagent_instance = agent._instances[agent_name]

    resource_container.Provider.set("agent1", "key1", "value1")

    version1 = await clienthelper.get_version()

    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key2", "value1")
    resource_container.Provider.set("agent1", "key3", "value1")

    def get_resources(version, value_resource_three):
        return [
            {
                "key": "key1",
                "value": "value2",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::Wait[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
            },
        ]

    resources_version_1 = get_resources(version1, "a")

    # Put a new version of the configurationmodel
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    # Make the agent pickup the new version
    # key3: Readcount=1; writecount=1
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(
            reason="Deploy",
            is_full_deploy=False,
            is_periodic=False,
        )
    )
    # key3: Readcount=2; writecount=1
    await myagent_instance.get_latest_version_for_agent(DeployRequest(is_full_deploy=True, reason="Repair", is_periodic=False))

    async def wait_condition():
        return not (
            resource_container.Provider.readcount(agent_name, "key3") == 2
            and resource_container.Provider.changecount(agent_name, "key3") == 1
        )

    await resource_container.wait_for_condition_with_waiters(wait_condition)

    assert resource_container.Provider.readcount(agent_name, "key3") == 2
    assert resource_container.Provider.changecount(agent_name, "key3") == 1

    assert resource_container.Provider.get("agent1", "key1") == "value2"

    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Deferring run 'Repair' for 'Deploy'")
    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Resuming run 'Repair'")


debug_timeout = 10


async def test_s_repair_interrupted_by_deploy_request(
    resource_container, agent, client, clienthelper, environment, no_agent_backoff, caplog
):
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"

    myagent_instance = agent._instances[agent_name]

    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key2", "value1")
    resource_container.Provider.set("agent1", "key3", "value1")

    def get_resources(version, value_resource_three):
        return [
            {
                "key": "key1",
                "value": "value2",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::Wait[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
            },
        ]

    version1 = await clienthelper.get_version()
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Deploy 1", is_full_deploy=False, is_periodic=False)
    )
    await resource_container.wait_for_done_with_waiters(client, environment, version1, timeout=debug_timeout)

    # counts:  read/write
    # key1: 1/1
    # key3: 1/1

    # Interrupt repair with deploy
    # Repair
    await myagent_instance.get_latest_version_for_agent(DeployRequest(reason="Repair", is_full_deploy=True, is_periodic=False))

    # wait for key1 to be deployed
    async def condition_x():
        return resource_container.Provider.readcount(agent_name, "key1") == 2

    await retry_limited(condition_x, timeout=debug_timeout)

    # counts:  read/write
    # key1: 2/1
    # key3: 1/1

    # Set marker
    resource_container.Provider.set("agent1", "key1", "BAD!")

    # Increment
    version2 = await clienthelper.get_version()
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, False)

    print("Interrupt")
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Deploy 2", is_full_deploy=False, is_periodic=False)
    )
    print("Deploy")
    await resource_container.wait_for_done_with_waiters(client, environment, version2, timeout=debug_timeout)

    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Interrupting run 'Repair' for 'Deploy 2'")

    # counts:  read/write
    # key1: 2/1
    # key3: 2/2

    assert resource_container.Provider.readcount(agent_name, "key1") >= 2
    assert resource_container.Provider.changecount(agent_name, "key1") >= 1
    assert resource_container.Provider.readcount(agent_name, "key3") >= 2
    assert resource_container.Provider.changecount(agent_name, "key3") >= 2

    async def wait_condition():
        print(20 * "-")
        print("k1 R", resource_container.Provider.readcount(agent_name, "key1"))
        print("k1 C", resource_container.Provider.changecount(agent_name, "key1"))
        print("k3 R", resource_container.Provider.readcount(agent_name, "key3"))
        print("k3 C", resource_container.Provider.changecount(agent_name, "key3"))
        return not (
            resource_container.Provider.readcount(agent_name, "key1") == 3
            and resource_container.Provider.changecount(agent_name, "key1") == 2
            and resource_container.Provider.readcount(agent_name, "key3") == 3
            and resource_container.Provider.changecount(agent_name, "key3") == 2
        )

    await resource_container.wait_for_condition_with_waiters(wait_condition, timeout=debug_timeout)

    # counts:  read/write
    # key1: 3/2
    # key3: 3/2

    assert resource_container.Provider.readcount(agent_name, "key1") == 3
    assert resource_container.Provider.changecount(agent_name, "key1") == 2
    assert resource_container.Provider.readcount(agent_name, "key3") == 3
    assert resource_container.Provider.changecount(agent_name, "key3") == 2

    assert resource_container.Provider.get("agent1", "key1") == "value2"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert resource_container.Provider.get("agent1", "key3") == "value3"

    log_contains(
        caplog, "inmanta.agent.agent.agent1", logging.INFO, "for reason: Restarting run 'Repair', interrupted for 'Deploy 2'"
    )
    log_contains(
        caplog, "inmanta.agent.agent.agent1", logging.INFO, "Resuming run 'Restarting run 'Repair', interrupted for 'Deploy 2''"
    )


async def test_s_repair_during_repair(resource_container, agent, client, clienthelper, environment, no_agent_backoff, caplog):
    caplog.set_level(logging.INFO)
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
            "receive_events": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Wait[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
        },
        {
            "key": "key3",
            "value": "value2",
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
        },
    ]

    # Initial deploy
    await _deploy_resources(client, environment, resources, version, False)
    await myagent_instance.get_latest_version_for_agent(DeployRequest(reason="Deploy", is_full_deploy=False, is_periodic=False))
    await resource_container.wait_for_done_with_waiters(client, environment, version)

    # Interrupt repair with a repair
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Repair 1", is_full_deploy=True, is_periodic=False)
    )
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Repair 2", is_full_deploy=True, is_periodic=False)
    )

    async def wait_condition():
        return (
            resource_container.Provider.readcount(agent_name, "key1") != 3
            or resource_container.Provider.changecount(agent_name, "key1") != 1
            or resource_container.Provider.readcount(agent_name, "key3") != 2
            or resource_container.Provider.changecount(agent_name, "key3") != 1
        )

    await resource_container.wait_for_condition_with_waiters(wait_condition)

    # Initial deployment:
    #   * All resources are deployed successfully
    # First repair run:
    #   * test::Resource[agent1,key=key1] deployed successfully
    #   * test::Resource[agent1,key=key2] and test::Resource[agent1,key=key3] are cancelled
    # Second repair run:
    #   * All resources are deployed successfully
    assert resource_container.Provider.readcount(agent_name, "key1") == 3
    assert resource_container.Provider.changecount(agent_name, "key1") == 1
    assert resource_container.Provider.readcount(agent_name, "key3") == 2
    assert resource_container.Provider.changecount(agent_name, "key3") == 1

    assert resource_container.Provider.get("agent1", "key1") == "value2"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert resource_container.Provider.get("agent1", "key3") == "value2"

    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Terminating run 'Repair 1' for 'Repair 2'")


async def test_s_deploy_during_deploy(resource_container, agent, client, clienthelper, environment, no_agent_backoff, caplog):
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"
    myagent_instance = agent._instances[agent_name]

    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key1", "value1")

    def get_resources(version, value_resource_three):
        return [
            {
                "key": "key1",
                "value": "value2",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::Wait[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
            },
        ]

    version1 = await clienthelper.get_version()
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Deploy 1", is_full_deploy=False, is_periodic=False)
    )

    # Make sure that resource key1 is fully deployed before triggering the interrupt
    timeout_time = time.time() + 10
    while (await client.get_version(environment, version1)).result["model"]["done"] < 1 and time.time() < timeout_time:
        await asyncio.sleep(0.1)

    version2 = await clienthelper.get_version()
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, False)
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Deploy 2", is_full_deploy=False, is_periodic=False)
    )

    await resource_container.wait_for_done_with_waiters(client, environment, version2)

    # Deployment version1:
    #   * test::Resource[agent1,key=key1] is deployed successfully;
    #   * test::Resource[agent1,key=key2] and test::Resource[agent1,key=key3] are cancelled
    # Deployment version2:
    #   * test::Resource[agent1,key=key1] is not included in the increment
    #   * test::Resource[agent1,key=key2] and test::Resource[agent1,key=key3] are deployed
    assert resource_container.Provider.readcount(agent_name, "key1") == 1
    assert resource_container.Provider.changecount(agent_name, "key1") == 1
    assert resource_container.Provider.readcount(agent_name, "key3") == 1
    assert resource_container.Provider.changecount(agent_name, "key3") == 1

    assert resource_container.Provider.get("agent1", "key1") == "value2"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert resource_container.Provider.get("agent1", "key3") == "value3"

    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Terminating run 'Deploy 1' for 'Deploy 2'")


async def test_s_full_deploy_waits_for_incremental_deploy(
    resource_container, agent, client, clienthelper, environment, no_agent_backoff, caplog
):
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"

    myagent_instance = agent._instances[agent_name]

    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key1", "value1")

    def get_resources(version, value_resource_three):
        return [
            {
                "key": "key1",
                "value": "value2",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::Wait[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
            },
        ]

    version1 = await clienthelper.get_version()
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Initial Deploy", is_full_deploy=False, is_periodic=False)
    )

    # Make sure that resource key1 is fully deployed before triggering the interrupt
    timeout_time = time.time() + 10
    while (await client.get_version(environment, version1)).result["model"]["done"] < 1 and time.time() < timeout_time:
        await asyncio.sleep(0.1)

    version2 = await clienthelper.get_version()
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, False)
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Second Deploy", is_full_deploy=True, is_periodic=False)
    )

    await resource_container.wait_for_done_with_waiters(client, environment, version2)

    # Incremental deploy
    #   * All resources are deployed successfully:
    # Full deploy:
    #   * All resources are deployed successfully
    assert resource_container.Provider.readcount(agent_name, "key1") == 2
    assert resource_container.Provider.changecount(agent_name, "key1") == 1
    assert resource_container.Provider.readcount(agent_name, "key3") == 2
    assert resource_container.Provider.changecount(agent_name, "key3") == 2

    assert resource_container.Provider.get("agent1", "key1") == "value2"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert resource_container.Provider.get("agent1", "key3") == "value3"

    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Deferring run 'Second Deploy' for 'Initial Deploy'")


async def test_s_incremental_deploy_interrupts_full_deploy(
    resource_container, client, agent, environment, clienthelper, no_agent_backoff, caplog
):
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    agent_name = "agent1"

    myagent_instance = agent._instances[agent_name]

    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key2", "value1")
    resource_container.Provider.set("agent1", "key3", "value1")

    def get_resources(version, value_resource_three):
        return [
            {
                "key": "key1",
                "value": "value2",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::Wait[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
            },
        ]

    version1 = await clienthelper.get_version()
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Initial Deploy", is_full_deploy=True, is_periodic=False)
    )

    # Make sure that resource key1 is fully deployed before triggering the interrupt
    timeout_time = time.time() + 10
    while (await client.get_version(environment, version1)).result["model"]["done"] < 1 and time.time() < timeout_time:
        await asyncio.sleep(0.1)

    version2 = await clienthelper.get_version()
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, False)
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Second Deploy", is_full_deploy=False, is_periodic=False)
    )

    async def should_wait_for_all_deploys_done() -> bool:
        """
        Return true iff we should continue waiting for all deploys to finish.
        """
        result = await client.resource_logs(environment, "test::Resource[agent1,key=key3]", filter={"action": ["deploy"]})
        assert result.code == 200
        end_run_lines = [line for line in result.result["data"] if "End run" in line.get("msg", "")]
        # incremental deploy + full deploy resumed
        return len(end_run_lines) < 2

    await resource_container.wait_for_condition_with_waiters(
        wait_condition=should_wait_for_all_deploys_done,
        timeout=2,
    )

    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Interrupting run 'Initial Deploy' for 'Second Deploy'")

    # Full deploy:
    #   * test::Resource[agent1,key=key1] is deployed successfully;
    #   * test::Resource[agent1,key=key2] is cancelled after deploy
    #   * test::Resource[agent1,key=key3] is cancelled
    # Incremental deploy:
    #   * test::Resource[agent1,key=key1] is not included in the increment
    #   * test::Resource[agent1,key=key2] and test::Resource[agent1,key=key3] are deployed successfully
    # Full deploy (resumed):
    #     #   * test::Resource[agent1,key=key1] is deployed successfully;
    #     #   * test::Resource[agent1,key=key2] is deployed successfully;
    #     #   * test::Resource[agent1,key=key3] is deployed successfully;
    assert resource_container.Provider.readcount(agent_name, "key1") == 2
    assert resource_container.Provider.changecount(agent_name, "key1") == 1
    assert resource_container.Provider.readcount(agent_name, "key3") == 2
    assert resource_container.Provider.changecount(agent_name, "key3") == 1

    assert resource_container.Provider.get("agent1", "key1") == "value2"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert resource_container.Provider.get("agent1", "key3") == "value3"


@dataclasses.dataclass
class Result:
    wait_for: int
    values: tuple[int, int, int]
    msg: str


ignore = Result(
    wait_for=0,
    values=("value2", "value2", "value2"),
    msg="Ignoring new run 'Second Deploy' in favor of current 'Initial Deploy'",
)
terminate = Result(
    wait_for=1, values=("value2", "value2", "value3"), msg="Terminating run 'Initial Deploy' for 'Second Deploy'"
)
interrupt = Result(
    wait_for=1, values=("value2", "value2", "value3"), msg="Interrupting run 'Initial Deploy' for 'Second Deploy'"
)
defer = Result(wait_for=1, values=("value2", "value2", "value3"), msg="Deferring run 'Second Deploy' for 'Initial Deploy'")


@pytest.mark.parametrize(
    ["first_full", "first_periodic", "second_full", "second_periodic", "action", "deploy_counts"],
    [
        [True, True, True, True, ignore, (1, 1, 1, 1)],  # Full periodic ignored by full periodic #6202
        [True, False, True, True, ignore, (1, 1, 1, 1)],  # Full periodic ignored by full #6202
        [True, True, True, False, terminate, (2, 1, 1, 1)],  # Full terminates full periodic
        [True, False, True, False, terminate, (2, 1, 1, 1)],  # Full terminates full
        [False, True, False, True, terminate, (1, 1, 1, 1)],  # Increment * terminates Increment *
        [False, True, False, False, terminate, (1, 1, 1, 1)],
        [False, False, False, True, terminate, (1, 1, 1, 1)],
        [False, False, False, False, terminate, (1, 1, 1, 1)],
        [True, True, False, True, ignore, (1, 1, 1, 1)],  # periodic increment ignored by periodic full  #6202
        [True, False, False, True, ignore, (1, 1, 1, 1)],  # periodic increment ignored by full #6202
        [False, True, True, True, terminate, (2, 1, 1, 1)],  # Incremental periodic terminated by full periodic
        [False, True, True, False, terminate, (2, 1, 1, 1)],  # Incremental periodic terminated by full
        [False, False, True, True, defer, (2, 1, 2, 2)],  # Incremental defers full periodic
        [False, False, True, False, defer, (2, 1, 2, 2)],  # Incremental defers full
        # requires more complex waiting see test_s_repair_interrupted_by_deploy_request
        # [True, False, False, False, interrupt, (2,1,2,1)],  # full interrupted by increment
        # [True, True, False, False, interrupt,(2,1,2,1)], # periodic full interrupted by increment
    ],
)
async def test_s_periodic_Vs_full(
    resource_container,
    agent,
    client,
    clienthelper,
    environment,
    no_agent_backoff,
    caplog,
    first_full,
    first_periodic,
    second_full,
    second_periodic,
    action: Result,
    deploy_counts,
):
    # ongoing periodic repair is not interrupted by periodic repair
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"

    myagent_instance = agent._instances[agent_name]

    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key2", "value1")
    resource_container.Provider.set("agent1", "key3", "value1")

    def get_resources(version, value_resource_three):
        return [
            {
                "key": "key1",
                "value": "value2",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::Wait[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
            },
        ]

    version1 = await clienthelper.get_version()
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, push=False)
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Initial Deploy", is_full_deploy=first_full, is_periodic=first_periodic)
    )

    # Make sure that resource key1 is fully deployed before triggering the interrupt
    timeout_time = time.time() + 10
    while (await client.get_version(environment, version1)).result["model"]["done"] < 1 and time.time() < timeout_time:
        await asyncio.sleep(0.1)

    version2 = await clienthelper.get_version()
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, push=False)
    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Second Deploy", is_full_deploy=second_full, is_periodic=second_periodic)
    )

    versions = [version1, version2]
    await resource_container.wait_for_done_with_waiters(client, environment, versions[action.wait_for])
    # cache has no versions in flight
    # for issue #1883

    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, action.msg)

    # Full deploy
    #   * All resources are deployed successfully:
    # Full deploy:
    #   * ignored
    assert resource_container.Provider.readcount(agent_name, "key1") == deploy_counts[0]
    assert resource_container.Provider.changecount(agent_name, "key1") == deploy_counts[1]
    assert resource_container.Provider.readcount(agent_name, "key3") == deploy_counts[2]
    assert resource_container.Provider.changecount(agent_name, "key3") == deploy_counts[3]

    assert resource_container.Provider.get("agent1", "key1") == action.values[0]
    assert resource_container.Provider.get("agent1", "key2") == action.values[1]
    assert resource_container.Provider.get("agent1", "key3") == action.values[2]


async def test_bad_post_get_facts(
    resource_container, server, client, agent, clienthelper, environment, caplog, no_agent_backoff
):
    """
    Test retrieving facts from the agent
    """
    caplog.set_level(logging.ERROR)

    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::BadPost[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": resource_id,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        }
    ]

    await clienthelper.put_version_simple(resources, version)

    caplog.clear()

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    assert "An error occurred after deployment of test::BadPost[agent1,key=key]" in caplog.text
    caplog.clear()

    result = await client.get_param(environment, "length", resource_id_wov)
    assert result.code == 503

    env_uuid = uuid.UUID(environment)

    async def has_at_least_three_parameters() -> bool:
        params = await data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
        return len(params) >= 3

    await retry_limited(has_at_least_three_parameters, timeout=10)

    result = await client.get_param(environment, "key1", resource_id_wov)
    assert result.code == 200

    assert "An error occurred after getting facts about test::BadPost" in caplog.text

    await agent.stop()


async def test_inprogress(resource_container, server, client, clienthelper, environment, no_agent_backoff, async_finalizer):
    """
    Test retrieving facts from the agent
    """
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await agent.add_end_point_name("agent1")
    async_finalizer(agent.stop)
    await agent.start()
    await retry_limited(lambda: len(server.get_slice(SLICE_SESSION_MANAGER)._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::Wait[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": resource_id,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        }
    ]

    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    async def in_progress():
        result = await client.get_version(environment, version)
        assert result.code == 200
        res = result.result["resources"][0]
        status = res["status"]
        return status == "deploying"

    await retry_limited(in_progress, 30)

    await resource_container.wait_for_done_with_waiters(client, environment, version)


@pytest.mark.parametrize("use_agent_trigger_method_setting", [(True,), (False)])
async def test_push_incremental_deploy(
    resource_container,
    environment,
    server,
    client,
    clienthelper,
    no_agent_backoff,
    async_finalizer,
    use_agent_trigger_method_setting,
):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await agent.add_end_point_name("agent1")
    await agent.start()
    async_finalizer(agent.stop)
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = await clienthelper.get_version()

    def get_resources(version, value_second_resource):
        return [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": value_second_resource,
                "id": "test::Resource[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "requires": [],
                "purged": False,
            },
        ]

    # Make sure some resources are deployed
    resources = get_resources(version, "value1")
    await clienthelper.put_version_simple(resources, version)

    if use_agent_trigger_method_setting:
        # Set the ENVIRONMENT_AGENT_TRIGGER_METHOD to full and leave the param None in the release_version call
        result = await client.environment_settings_set(
            environment, ENVIRONMENT_AGENT_TRIGGER_METHOD, const.AgentTriggerMethod.push_full_deploy
        )
        assert result.code == 200
        result = await client.release_version(environment, version, True)
        assert result.code == 200
    else:
        result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
        assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value1"

    # Second version deployed with incremental deploy
    version2 = await clienthelper.get_version()
    resources_version2 = get_resources(version2, "value2")

    result = await client.put_version(
        tid=environment,
        version=version2,
        resources=resources_version2,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    if use_agent_trigger_method_setting:
        # Set the ENVIRONMENT_AGENT_TRIGGER_METHOD to incremental and leave the param None in the release_version call
        result = await client.environment_settings_set(
            environment, ENVIRONMENT_AGENT_TRIGGER_METHOD, const.AgentTriggerMethod.push_incremental_deploy
        )
        assert result.code == 200
        result = await client.release_version(environment, version2, True)
        assert result.code == 200
    else:
        result = await client.release_version(environment, version2, True, const.AgentTriggerMethod.push_incremental_deploy)
        assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version2)

    # Make sure increment was deployed
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"

    assert resource_container.Provider.readcount("agent1", "key1") == 1
    assert resource_container.Provider.changecount("agent1", "key1") == 1
    assert resource_container.Provider.readcount("agent1", "key2") == 2
    assert resource_container.Provider.changecount("agent1", "key2") == 2

    await agent.stop()


@pytest.mark.parametrize("push, agent_trigger_method", [(True, const.AgentTriggerMethod.push_full_deploy)])
async def test_push_full_deploy(
    resource_container, environment, server, client, clienthelper, no_agent_backoff, push, agent_trigger_method, async_finalizer
):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await agent.add_end_point_name("agent1")
    await agent.start()
    async_finalizer(agent.stop)
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = await clienthelper.get_version()

    def get_resources(version, value_second_resource):
        return [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": value_second_resource,
                "id": "test::Resource[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "requires": [],
                "purged": False,
            },
        ]

    # Make sure some resources are deployed
    resources = get_resources(version, "value1")
    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(environment, version, push, agent_trigger_method)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value1"

    # Second version deployed with incremental deploy
    version2 = await clienthelper.get_version()
    resources_version2 = get_resources(version2, "value2")

    result = await client.put_version(
        tid=environment,
        version=version2,
        resources=resources_version2,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    result = await client.release_version(environment, version2, push, agent_trigger_method)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version2)

    # Make sure increment was deployed
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"

    assert resource_container.Provider.readcount("agent1", "key1") == 2
    assert resource_container.Provider.changecount("agent1", "key1") == 1
    assert resource_container.Provider.readcount("agent1", "key2") == 2
    assert resource_container.Provider.changecount("agent1", "key2") == 2

    await agent.stop()


async def test_agent_run_sync(resource_container, environment, server, client, clienthelper, no_agent_backoff, async_finalizer):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await agent.add_end_point_name("agent1")
    await agent.start()
    async_finalizer(agent.stop)
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = await clienthelper.get_version()

    def get_resources(version):
        return [
            {
                "agentname": "agent2",
                "uri": "localhost",
                "autostart": "true",
                "id": "test::AgentConfig[agent1,agentname=agent2],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
                "purge_on_delete": False,
            }
        ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=get_resources(version),
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    assert "agent2" in (await client.get_setting(tid=environment, id=data.AUTOSTART_AGENT_MAP)).result["value"]


async def test_format_token_in_logline(server, agent, client, environment, resource_container, caplog, no_agent_backoff):
    """Deploy a resource that logs a line that after formatting on the agent contains an invalid formatting character."""
    version = (await client.reserve_version(environment)).result["data"]
    resource_container.Provider.set("agent1", "key1", "incorrect_value")

    resource = {
        "key": "key1",
        "value": "Test value %T",
        "id": "test::Resource[agent1,key=key1],v=%d" % version,
        "send_event": False,
        "receive_events": False,
        "purged": False,
        "requires": [],
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[resource],
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )

    assert result.code == 200

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    result = await client.get_version(environment, version)
    assert result.code == 200
    await _wait_until_deployment_finishes(client, environment, version)

    result = await client.get_version(environment, version)
    assert result.result["model"]["done"] == 1

    log_string = "Set key '%(key)s' to value '%(value)s'" % dict(key=resource["key"], value=resource["value"])
    assert log_string in caplog.text


async def test_1016_cache_invalidation(
    server, agent, client, clienthelper, environment, resource_container, no_agent_backoff, caplog
):
    """
    tricky case where the increment cache was not invalidated when a new version was deployed,
    causing subsequent deploys to receive a wrong increment
    """
    resource_container.Provider.set("agent1", "key1", "incorrect_value")
    caplog.set_level(logging.DEBUG)

    async def make_version(version, value="v"):
        resource = {
            "key": "key1",
            "value": "Test value %s" % value,
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        }

        result = await client.put_version(
            tid=environment,
            version=version,
            resources=[resource],
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )

        assert result.code == 200

    ai = agent._instances["agent1"]

    version = await clienthelper.get_version()
    await make_version(version)

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_incremental_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    await _wait_until_deployment_finishes(client, environment, version)

    await ai.get_latest_version_for_agent(DeployRequest(False, False, reason="test deploy"))

    await asyncio.gather(*(e.future for e in ai._nq.generation.values()))

    version = await clienthelper.get_version()
    await make_version(version, "b")

    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_incremental_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    await _wait_until_deployment_finishes(client, environment, version)

    # first 1 full fetch
    idx1 = log_index(caplog, "inmanta.agent.agent.agent1", logging.DEBUG, "Pulled 1 resources because call to trigger_update")
    # then empty increment
    idx2 = log_index(caplog, "inmanta.agent.agent.agent1", logging.DEBUG, "Pulled 0 resources because test deploy", idx1)
    # then non-empty increment deploy
    log_index(caplog, "inmanta.agent.agent.agent1", logging.DEBUG, "Pulled 1 resources because call to trigger_update", idx2)


async def test_agent_lockout(resource_container, environment, server, client, clienthelper, async_finalizer, no_agent_backoff):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    version = await clienthelper.get_version()

    resource = {
        "key": "key1",
        "value": "Test value %T",
        "id": "test::Resource[agent1,key=key1],v=%d" % version,
        "send_event": False,
        "receive_events": False,
        "purged": False,
        "requires": [],
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[resource],
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    async_finalizer.add(agent.stop)
    await agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    agent2 = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    async_finalizer.add(agent2.stop)
    await agent2.add_end_point_name("agent1")
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)

    assert agent._instances["agent1"].is_enabled()
    assert not agent2._instances["agent1"].is_enabled()

    result = await agent2._instances["agent1"].get_client().get_resources_for_agent(tid=environment, agent="agent1")
    assert result.code == 409


async def test_deploy_no_code(resource_container, client, clienthelper, environment, autostarted_agent):
    """
    Test retrieving facts from the agent when there is no handler code available. We use an autostarted agent, these
    do not have access to the handler code for the resource_container.
    """
    resource_container.Provider.reset()
    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": resource_id,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        }
    ]

    await clienthelper.put_version_simple(resources, version)

    await _wait_until_deployment_finishes(client, environment, version, timeout=10)
    # The resource state and its logs are not set atomically. This call prevents a race condition.
    await wait_until_logs_are_available(client, environment, resource_id, expect_nr_of_logs=3)

    response = await client.get_resource(environment, resource_id, logs=True)
    assert response.code == 200
    result = response.result
    assert result["resource"]["status"] == "unavailable"

    logging.getLogger(__name__).warning("Found results: %s", json.dumps(result["logs"], indent=1))

    def is_log_line(log_line):
        return (
            log_line["action"] == "deploy"
            and log_line["status"] == "unavailable"
            and ("failed to load handler code " in log_line["messages"][-1]["msg"])
        )

    # Expected logs:
    #   [0] Deploy action: Failed to load handler code or install handler code
    #   [1] Pull action
    #   [2] Store action
    assert any((is_log_line(line) for line in result["logs"]))


async def test_issue_1662(resource_container, server, client, clienthelper, environment, monkeypatch, async_finalizer):
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)
    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    a = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await a.add_end_point_name("agent1")
    async_finalizer(a.stop)
    await a.start()
    await retry_limited(lambda: len(agent_manager.sessions) == 1, 10)

    async def restart_agents_patch(env):
        def stop_agents_thread_pools():
            # This will hang the test case when the deadlock is present
            a.thread_pool.shutdown(wait=True)
            for i in a._instances.values():
                i.thread_pool.shutdown(wait=True)
                i.provider_thread_pool.shutdown(wait=True)

        # Run off main thread
        await asyncio.get_event_loop().run_in_executor(None, stop_agents_thread_pools)

    monkeypatch.setattr(autostarted_agent_manager, "restart_agents", restart_agents_patch)

    version = await clienthelper.get_version()
    resource_id = f"test::AgentConfig[agent1,agentname=agent2],v={version}"

    resources = [
        {
            "agentname": "agent2",
            "uri": "local:",
            "autostart": "true",
            "id": resource_id,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
            "purge_on_delete": False,
        },
    ]

    await clienthelper.put_version_simple(resources, version)
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version, timeout=10)


async def test_restart_agent_with_outdated_agent_map(server, client, environment):
    """
    Due to a race condition, it is possible that an autostarted agent get's started with an outdated agent_map.
    The agent resolves this inconsistency automatically when is has established a new session with the server.
    This test verifies this behavior.
    """
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)
    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)

    env_id = uuid.UUID(environment)
    env = await data.Environment.get_by_id(env_id)

    await env.set(key=data.AUTOSTART_AGENT_MAP, value={"internal": ""})
    await agent_manager.ensure_agent_registered(env=env, nodename="internal")
    await agent_manager.ensure_agent_registered(env=env, nodename="agent1")
    await autostarted_agent_manager.restart_agents(env)
    # Internal agent should have a session with the server
    await retry_limited(lambda: len(agent_manager.tid_endpoint_to_session) == 1, 10)

    # Keep an old environment object with the outdated agentmap
    old_env = await data.Environment.get_by_id(env_id)
    # Update the agentmap
    await env.set(key=data.AUTOSTART_AGENT_MAP, value={"internal": "", "agent1": ""})

    # Restart agent with an old agent_map
    await autostarted_agent_manager.restart_agents(old_env)

    # The agent should fetch the up-to-date autostart_agent_map from the server after the first heartbeat
    await retry_limited(lambda: len(agent_manager.tid_endpoint_to_session) == 2, 10)


async def test_agent_stop_deploying_when_paused(
    server, client, environment, agent_factory, clienthelper, resource_container, no_agent_backoff
):
    """
    This test case verifies that an agent, which is executing a deployment, stops
    its deploy operations when the agent is paused.
    """
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    agent1 = "agent1"
    agent2 = "agent2"
    for agent_name in [agent1, agent2]:
        await agent_factory(environment=environment, agent_map={agent_name: "localhost"}, agent_names=[agent_name])

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


async def test_agentinstance_stops_deploying_when_stopped(
    server, client, environment, agent, clienthelper, resource_container, no_agent_backoff
):
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


async def test_set_fact_in_handler(server, client, environment, agent, clienthelper, resource_container, no_agent_backoff):
    """
    Test whether facts set in the handler via the ctx.set_fact() method arrive on the server.
    """

    def get_resources(version: str, params: list[data.Parameter]) -> list[dict[str, Any]]:
        return [
            {
                "key": param.name,
                "value": param.value,
                "metadata": param.metadata,
                "id": f"{param.resource_id},v={version}",
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "purge_on_delete": False,
                "requires": [],
            }
            for param in params
        ]

    def compare_params(actual_params: list[data.Parameter], expected_params: list[data.Parameter]) -> None:
        actual_params = sorted(actual_params, key=lambda p: p.name)
        expected_params = sorted(expected_params, key=lambda p: p.name)
        assert len(expected_params) == len(actual_params)
        for i in range(len(expected_params)):
            for attr_name in ["name", "value", "environment", "resource_id", "source", "metadata"]:
                assert getattr(expected_params[i], attr_name) == getattr(actual_params[i], attr_name)

    # Assert initial state
    params = await data.Parameter.get_list()
    assert len(params) == 0

    param1 = data.Parameter(
        name="key1",
        value="value1",
        environment=uuid.UUID(environment),
        resource_id="test::SetFact[agent1,key=key1]",
        source=ParameterSource.fact.value,
        expires=True,
    )
    param2 = data.Parameter(
        name="key2",
        value="value2",
        environment=uuid.UUID(environment),
        resource_id="test::SetFact[agent1,key=key2]",
        source=ParameterSource.fact.value,
        expires=True,
    )

    version = await clienthelper.get_version()
    resources = get_resources(version, [param1, param2])

    # Ensure that facts are pushed when ctx.set_fact() is called during resource deployment
    await _deploy_resources(client, environment, resources, version, push=True)
    await wait_for_n_deployed_resources(client, environment, version, n=2)

    params = await data.Parameter.get_list()
    compare_params(params, [param1, param2])

    # Ensure that:
    # * Facts set in the handler.facts() method via ctx.set_fact() method are pushed to the Inmanta server.
    # * Facts returned via the handler.facts() method are pushed to the Inmanta server.
    await asyncio.gather(*[p.delete() for p in params])
    params = await data.Parameter.get_list()
    assert len(params) == 0
    agent_manager = server.get_slice(name=SLICE_AGENT_MANAGER)
    agent_manager._fact_resource_block = 0

    result = await client.get_param(tid=environment, id="key1", resource_id="test::SetFact[agent1,key=key1]")
    assert result.code == 503
    result = await client.get_param(tid=environment, id="key2", resource_id="test::SetFact[agent1,key=key2]")
    assert result.code == 503

    async def _wait_until_facts_are_available():
        params = await data.Parameter.get_list()
        return len(params) == 4

    await retry_limited(_wait_until_facts_are_available, 10)

    param3 = data.Parameter(
        name="returned_fact_key1",
        value="test",
        environment=uuid.UUID(environment),
        resource_id="test::SetFact[agent1,key=key1]",
        source=ParameterSource.fact.value,
        expires=True,
    )
    param4 = data.Parameter(
        name="returned_fact_key2",
        value="test",
        environment=uuid.UUID(environment),
        resource_id="test::SetFact[agent1,key=key2]",
        source=ParameterSource.fact.value,
        expires=True,
    )

    params = await data.Parameter.get_list()
    compare_params(params, [param1, param2, param3, param4])


async def test_set_non_expiring_fact_in_handler_6560(
    server, client, environment, agent, clienthelper, resource_container, no_agent_backoff
):
    """
    Check that getting a non expiring fact doesn't trigger a parameter request from the agent.
    In this test:
        - create 2 facts, one that expires, one that doesn't expire
        - wait for the _fact_expire delay
        - when getting the facts back, check that only the fact that does expire triggers a refresh from the agent
    """

    # Setup a high fact expiry rate:
    param_service = server.get_slice(SLICE_PARAM)
    param_service._fact_expire = 0.1

    def get_resources(version: str, params: list[data.Parameter]) -> list[dict[str, Any]]:
        return [
            {
                "key": param.name,
                "value": param.value,
                "metadata": param.metadata,
                "id": f"{param.resource_id},v={version}",
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "purge_on_delete": False,
                "requires": [],
            }
            for param in params
        ]

    def compare_params(actual_params: list[data.Parameter], expected_params: list[data.Parameter]) -> None:
        actual_params = sorted(actual_params, key=lambda p: p.name)
        expected_params = sorted(expected_params, key=lambda p: p.name)
        assert len(expected_params) == len(actual_params), f"{expected_params=} {actual_params=}"
        for i in range(len(expected_params)):
            for attr_name in ["name", "value", "environment", "resource_id", "source", "metadata", "expires"]:
                expected = getattr(expected_params[i], attr_name)
                actual = getattr(actual_params[i], attr_name)
                assert expected == actual, f"{expected=} {actual=}"

    # Assert initial state
    params = await data.Parameter.get_list()
    assert len(params) == 0

    param1 = data.Parameter(
        name="non_expiring",
        value="value1",
        environment=uuid.UUID(environment),
        resource_id="test::SetNonExpiringFact[agent1,key=non_expiring]",
        source=ParameterSource.fact.value,
        expires=False,
    )
    param2 = data.Parameter(
        name="expiring",
        value="value2",
        environment=uuid.UUID(environment),
        resource_id="test::SetNonExpiringFact[agent1,key=expiring]",
        source=ParameterSource.fact.value,
        expires=True,
    )

    version = await clienthelper.get_version()
    resources = get_resources(version, [param1, param2])

    # Ensure that facts are pushed when ctx.set_fact() is called during resource deployment
    await _deploy_resources(client, environment, resources, version, push=True)
    await wait_for_n_deployed_resources(client, environment, version, n=2, timeout=10)

    params = await data.Parameter.get_list()
    compare_params(params, [param1, param2])

    # Ensure that:
    # * Facts set in the handler.facts() method via ctx.set_fact() method are pushed to the Inmanta server.
    # * Facts returned via the handler.facts() method are pushed to the Inmanta server.
    await asyncio.gather(*[p.delete() for p in params])
    params = await data.Parameter.get_list()
    assert len(params) == 0

    result = await client.get_param(
        tid=environment, id="non_expiring", resource_id="test::SetNonExpiringFact[agent1,key=non_expiring]"
    )
    assert result.code == 503
    result = await client.get_param(tid=environment, id="expiring", resource_id="test::SetNonExpiringFact[agent1,key=expiring]")
    assert result.code == 503

    async def _wait_until_facts_are_available():
        params = await data.Parameter.get_list()
        return len(params) == 2

    await retry_limited(_wait_until_facts_are_available, 10)

    # Wait for a bit to let facts expire
    await asyncio.sleep(0.5)

    # Non expiring fact is returned straight away
    result = await client.get_param(
        tid=environment, id="non_expiring", resource_id="test::SetNonExpiringFact[agent1,key=non_expiring]"
    )
    assert result.code == 200
    # Expired fact has to be refreshed
    result = await client.get_param(tid=environment, id="expiring", resource_id="test::SetNonExpiringFact[agent1,key=expiring]")
    assert result.code == 503

    await retry_limited(_wait_until_facts_are_available, 10)

    params = await data.Parameter.get_list()
    compare_params(params, [param1, param2])


async def test_deploy_handler_method(server, client, environment, agent, clienthelper, resource_container, no_agent_backoff):
    """
    Test whether the resource states are set correctly when the deploy() method is overridden.
    """

    async def deploy_resource(set_state_to_deployed_in_handler: bool = False) -> const.ResourceState:
        version = await clienthelper.get_version()
        rvid = f"test::Deploy[agent1,key=key1],v={version}"
        resources = [
            {
                "key": "key1",
                "value": "value1",
                "set_state_to_deployed": set_state_to_deployed_in_handler,
                "id": rvid,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
        ]

        await _deploy_resources(client, environment, resources, version, push=True)
        await _wait_until_deployment_finishes(client, environment, version=version)

        result = await client.get_resource(
            tid=environment,
            id=rvid,
            status=True,
        )
        assert result.code == 200
        return result.result["status"]

    # No exception raise + no state set explicitly via Handler Context -> deployed state
    assert const.ResourceState.deployed == await deploy_resource(set_state_to_deployed_in_handler=False)

    # State is set explicitly via HandlerContext to deployed
    assert const.ResourceState.deployed == await deploy_resource(set_state_to_deployed_in_handler=True)

    # SkipResource exception is raised by handler
    resource_container.Provider.set_skip("agent1", "key1", 1)
    assert const.ResourceState.skipped == await deploy_resource()

    # Exception is raised by handler
    resource_container.Provider.set_fail("agent1", "key1", 1)
    assert const.ResourceState.failed == await deploy_resource()


def test_deploy_response_matrix_invariants():
    """This testcase test a number of invariants of the deploy_response_matrix"""
    # From the code
    """
# This matrix describes what do when a new DeployRequest enters before the old one is done
# Format is (old_is_repair, old_is_periodic), (new_is_repair, new_is_periodic)
# The underlying idea is that
# 1. periodic deploys have no time pressure, they can be delayed
# 2. non-periodic deploy should run as soon as possible
# 3. non-periodic incremental deploys take precedence over repairs (as they are smaller)
# 4. Periodic repairs should not interrupt each other to prevent restart loops
# 5. Periodic repairs take precedence over periodic incremental deploys.
# These rules do not full specify the matrix! They are the rules we have to follow.
# A subtle detail is that when we do defer or interrupt, we only over keep one.
# So if a previous deferred run exists, it will be silently dropped
# But, we only defer or interrupt full deploys
# As such, we will always execute a full deploy
# (it may oscillate between periodic and not, but it will execute)
    """
    # Testable invariants
    # we only defer full compiles
    for condition, reaction in deploy_response_matrix.items():
        if reaction == DeployRequestAction.defer:
            assert condition[1][0], "Invariant violation, the defer mechanism has to be redesigned"
    # we only interrupt full compiles
    for condition, reaction in deploy_response_matrix.items():
        if reaction == DeployRequestAction.interrupt:
            assert condition[0][0], "Invariant violation, the defer mechanism has to be redesigned"
    # full deploy can only be ignored or terminated by a full deploy
    for condition, reaction in deploy_response_matrix.items():
        if reaction == DeployRequestAction.ignore and condition[1][0]:
            assert condition[0][0], "Invariant violation: we are losing repairs"
        if reaction == DeployRequestAction.terminate and condition[0][0]:
            assert condition[1][0], "Invariant violation: we are losing repairs"
    # full periodic deploy can not be interrupted/terminated by other periodic things
    for condition, reaction in deploy_response_matrix.items():
        if (reaction in [DeployRequestAction.interrupt, DeployRequestAction.terminate]) and condition[0][0] and condition[0][1]:
            assert not condition[1][1], "Invariant violation, regression on #6202"


async def test_logging_failure_when_creating_venv(
    resource_container,
    agent: Agent,
    client: Client,
    clienthelper: ClientHelper,
    environment: uuid.UUID,
    no_agent_backoff: None,
    caplog,
    monkeypatch,
):
    """
    Test goal: make sure that failed resources are correctly logged by the `resource_action` logger.
    """

    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    agent_name = "agent1"
    myagent_instance = agent._instances[agent_name]

    resource_container.Provider.set("agent1", "key1", "value1")

    def get_resources(version, value_resource_three):
        return [
            {
                "key": "key1",
                "value": "value2",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::AgentConfig[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": ["test::AgentConfig[agent1,key=key2],v=%d" % version],
            },
        ]

    version1 = await clienthelper.get_version()

    # Initial deploy
    await _deploy_resources(client, environment, get_resources(version1, "value2"), version1, push=False)

    async def ensure_code(code: Collection[ResourceInstallSpec]) -> executor.FailedResources:
        raise RuntimeError(f"Failed to install handler `test` version={version1}")

    monkeypatch.setattr(myagent_instance.executor_manager, "ensure_code", ensure_code)

    await myagent_instance.get_latest_version_for_agent(
        DeployRequest(reason="Deploy 1", is_full_deploy=False, is_periodic=False)
    )

    monkeypatch.undo()

    expected_error_message_without_tb = (
        "multiple resources: All resources of type `test::Resource` failed to load handler code or "
        "install handler code dependencies: `Could not set up executor for agent1: Failed to"
        " install handler `test` version=1`"
    )

    idx1 = log_index(
        caplog,
        f"resource_action_logger.{environment}",
        logging.ERROR,
        expected_error_message_without_tb,
    )
    actual_error_message = caplog.record_tuples[idx1][2]
    expected_location = """, in ensure_code
    raise RuntimeError(f"Failed to install handler `test` version={version1}")"""
    assert expected_location in actual_error_message

    # Logs should not appear twice
    with pytest.raises(AssertionError):
        log_index(
            caplog,
            f"resource_action_logger.{environment}",
            logging.ERROR,
            expected_error_message_without_tb,
            idx1 + 1,
        )

    def retrieve_relevant_logs(result) -> str:
        global_logs = result.result["logs"]
        assert len(global_logs) > 1
        relevant_logs = [e for e in global_logs if e["action"] == "deploy"]
        assert len(relevant_logs) == 1
        return "".join([log["msg"] for log in relevant_logs[0]["messages"]])

    # Now let's check that everything is in the DB as well
    # Given that everything is linked together, we can only fetch one resource and see what's present in the DB
    result = await client.get_resource(
        tid=environment,
        id="test::Resource[agent1,key=key3],v=%d" % version1,
        logs=True,
    )

    # Possible error messages that should be in the DB
    expected_error_messages = expected_error_message_without_tb.replace("multiple resources: ", "")

    relevant_logs = retrieve_relevant_logs(result)
    assert expected_error_messages in relevant_logs
    assert expected_location in relevant_logs
    # Make sure we don't find the same record multiple times in the resource logs
    assert relevant_logs.count(expected_error_messages) == 1


async def test_agent_code_loading_with_failure(
    caplog,
    server: Server,
    agent_factory: Coroutine[Any, Any, Agent],
    client: Client,
    environment: uuid.UUID,
    monkeypatch,
    clienthelper: ClientHelper,
) -> None:
    """
    Test goal: make sure that failed resources are correctly returned by `get_code` and `ensure_code` methods.
    The failed resources should have the right exception contained in the returned object.
    """

    caplog.set_level(DEBUG)

    sources = {}

    async def get_version() -> int:
        version = await clienthelper.get_version()
        res = await client.put_version(
            tid=environment,
            version=version,
            resources=[],
            pip_config=PipConfig(),
            compiler_version=get_compiler_version(),
        )
        assert res.code == 200
        return version

    version_1 = await get_version()

    res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test": sources})
    assert res.code == 200

    res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test2": sources})
    assert res.code == 200

    res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test3": sources})
    assert res.code == 200

    old_value_config = config.Config.get("agent", "executor-mode")
    config.Config.set("agent", "executor-mode", "threaded")

    agent: Agent = await agent_factory(
        environment=environment, agent_map={"agent1": "localhost"}, hostname="host", agent_names=["agent1"], code_loader=True
    )

    resource_install_specs_1: list[ResourceInstallSpec]
    resource_install_specs_2: list[ResourceInstallSpec]

    # We want to test
    nonexistent_version = -1
    resource_install_specs_1, invalid_resources_1 = await agent.get_code(
        environment=environment, version=nonexistent_version, resource_types=["test::Test", "test::Test2", "test::Test3"]
    )
    assert len(invalid_resources_1.keys()) == 3
    for resource_type, exception in invalid_resources_1.items():
        assert (
            "Failed to get source code for " + resource_type + " version=-1, result={'message': 'Request or "
            "referenced resource does not exist: The version of the code does not exist. "
            + resource_type
            + ", "
            + str(nonexistent_version)
            + "'}"
        ) == str(exception)

    await agent.executor_manager.ensure_code(
        code=resource_install_specs_1,
    )

    resource_install_specs_2, _ = await agent.get_code(
        environment=environment, version=version_1, resource_types=["test::Test", "test::Test2"]
    )

    async def _install(blueprint: executor.ExecutorBlueprint) -> None:
        raise Exception("MKPTCH: Unable to load code when agent is started with code loading disabled.")

    monkeypatch.setattr(agent.executor_manager, "_install", _install)

    failed_to_load = await agent.executor_manager.ensure_code(
        code=resource_install_specs_2,
    )
    assert len(failed_to_load) == 2
    for handler, exception in failed_to_load.items():
        assert str(exception) == (
            f"Failed to install handler {handler} version=1: "
            f"MKPTCH: Unable to load code when agent is started with code loading disabled."
        )

    monkeypatch.undo()

    idx1 = log_index(
        caplog,
        "inmanta.agent.code_manager",
        logging.ERROR,
        "Failed to get source code for test::Test2 version=-1",
    )

    log_index(caplog, "inmanta.agent.agent", logging.ERROR, "Failed to install handler test::Test version=1", idx1)

    log_index(caplog, "inmanta.agent.agent", logging.ERROR, "Failed to install handler test::Test2 version=1", idx1)

    config.Config.set("agent", "executor-mode", old_value_config)
