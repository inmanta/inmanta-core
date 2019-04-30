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
import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from itertools import groupby
from typing import List, Tuple, Optional, Dict

import psutil
import pytest
from psutil import Process, NoSuchProcess

import inmanta.agent.agent
from agent_server.conftest import (
    ResourceContainer,
    _wait_until_deployment_finishes,
    _deploy_resources,
    get_agent,
    _wait_for_n_deploying,
)
from inmanta import agent, const, execute, config, data
from inmanta.agent.agent import Agent
from inmanta.ast import CompilerException
from inmanta.config import Config
from inmanta.server import SLICE_AGENT_MANAGER, config as server_config
from inmanta.server.bootloader import InmantaBootloader
from utils import retry_limited, assert_equal_ish, UNKWN, log_contains, log_index

logger = logging.getLogger("inmanta.test.server_agent")


@pytest.mark.asyncio(timeout=150)
async def test_dryrun_and_deploy(server_multi, client_multi, resource_container):
    """
        dryrun and deploy a configuration model

        There is a second agent with an undefined resource. The server will shortcut the dryrun and deploy for this resource
        without an agent being present.
    """

    agentmanager = server_multi.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    result = await client_multi.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client_multi.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()

    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key3",
            "value": None,
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "send_event": False,
            "requires": [],
            "purged": True,
        },
        {
            "key": "key4",
            "value": execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key4],v=%d" % version,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key5",
            "value": "val",
            "id": "test::Resource[agent2,key=key5],v=%d" % version,
            "send_event": False,
            "requires": ["test::Resource[agent2,key=key4],v=%d" % version],
            "purged": False,
        },
        {
            "key": "key6",
            "value": "val",
            "id": "test::Resource[agent2,key=key6],v=%d" % version,
            "send_event": False,
            "requires": ["test::Resource[agent2,key=key5],v=%d" % version],
            "purged": False,
        },
    ]

    status = {"test::Resource[agent2,key=key4]": const.ResourceState.undefined}
    result = await client_multi.put_version(
        tid=env_id,
        version=version,
        resources=resources,
        resource_state=status,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    mod_db = await data.ConfigurationModel.get_version(uuid.UUID(env_id), version)
    undep = await mod_db.get_undeployable()
    assert undep == ["test::Resource[agent2,key=key4]"]

    undep = await mod_db.get_skipped_for_undeployable()
    assert undep == [
        "test::Resource[agent2,key=key5]",
        "test::Resource[agent2,key=key6]",
    ]

    # request a dryrun
    result = await client_multi.dryrun_request(env_id, version)
    assert result.code == 200
    assert result.result["dryrun"]["total"] == len(resources)
    assert result.result["dryrun"]["todo"] == len(resources)

    # get the dryrun results
    result = await client_multi.dryrun_list(env_id, version)
    assert result.code == 200
    assert len(result.result["dryruns"]) == 1

    while result.result["dryruns"][0]["todo"] > 0:
        result = await client_multi.dryrun_list(env_id, version)
        await asyncio.sleep(0.1)

    dry_run_id = result.result["dryruns"][0]["id"]
    result = await client_multi.dryrun_report(env_id, dry_run_id)
    assert result.code == 200

    changes = result.result["dryrun"]["resources"]

    assert changes[resources[0]["id"]]["changes"]["purged"]["current"]
    assert not changes[resources[0]["id"]]["changes"]["purged"]["desired"]
    assert changes[resources[0]["id"]]["changes"]["value"]["current"] is None
    assert (
        changes[resources[0]["id"]]["changes"]["value"]["desired"]
        == resources[0]["value"]
    )

    assert (
        changes[resources[1]["id"]]["changes"]["value"]["current"] == "incorrect_value"
    )
    assert (
        changes[resources[1]["id"]]["changes"]["value"]["desired"]
        == resources[1]["value"]
    )

    assert not changes[resources[2]["id"]]["changes"]["purged"]["current"]
    assert changes[resources[2]["id"]]["changes"]["purged"]["desired"]

    # do a deploy
    result = await client_multi.release_version(
        env_id, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 6
    assert result.result["model"]["result"] == "deploying"

    result = await client_multi.get_version(env_id, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client_multi, env_id, version)

    result = await client_multi.get_version(env_id, version)
    assert result.result["model"]["done"] == len(resources)

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert not resource_container.Provider.isset("agent1", "key3")

    actions = await data.ResourceAction.get_list()
    assert (
        sum(
            [
                len(x.resource_version_ids)
                for x in actions
                if x.status == const.ResourceState.undefined
            ]
        )
        == 1
    )
    assert (
        sum(
            [
                len(x.resource_version_ids)
                for x in actions
                if x.status == const.ResourceState.skipped_for_undefined
            ]
        )
        == 2
    )

    await agent.stop()


@pytest.mark.asyncio(timeout=150)
async def test_deploy_empty(server, client, resource_container, environment):
    """
       Test deployment of empty model
    """
    agent = await get_agent(server, environment, "agent1", "agent2")

    version = int(time.time())

    resources = []

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200
    assert result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 0
    assert result.result["model"]["result"] == const.VersionState.success.name

    await agent.stop()


@pytest.mark.asyncio(timeout=100)
async def test_deploy_with_undefined(server_multi, client_multi, resource_container):
    """
         Test deploy of resource with undefined
    """

    # agent backoff makes this test unreliable or slow, so we turn it off
    backoff = inmanta.agent.agent.GET_RESOURCE_BACKOFF
    inmanta.agent.agent.GET_RESOURCE_BACKOFF = 0

    agentmanager = server_multi.get_slice(SLICE_AGENT_MANAGER)

    Config.set("config", "agent-deploy-interval", "100")

    resource_container.Provider.reset()
    result = await client_multi.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client_multi.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    resource_container.Provider.set_skip("agent2", "key1", 1)

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost", "agent2": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent2")
    await agent.start()

    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent2,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key4",
            "value": execute.util.Unknown(source=None),
            "id": "test::Resource[agent2,key=key4],v=%d" % version,
            "send_event": False,
            "requires": [
                "test::Resource[agent2,key=key1],v=%d" % version,
                "test::Resource[agent2,key=key2],v=%d" % version,
            ],
            "purged": False,
        },
        {
            "key": "key5",
            "value": "val",
            "id": "test::Resource[agent2,key=key5],v=%d" % version,
            "send_event": False,
            "requires": ["test::Resource[agent2,key=key4],v=%d" % version],
            "purged": False,
        },
    ]

    status = {
        "test::Resource[agent2,key=key4]": const.ResourceState.undefined,
        "test::Resource[agent2,key=key2]": const.ResourceState.undefined,
    }
    result = await client_multi.put_version(
        tid=env_id,
        version=version,
        resources=resources,
        resource_state=status,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    # do a deploy
    result = await client_multi.release_version(
        env_id, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["result"] == "deploying"

    # The server will mark the full version as deployed even though the agent has not done anything yet.
    result = await client_multi.get_version(env_id, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client_multi, env_id, version)

    result = await client_multi.get_version(env_id, version)
    assert result.result["model"]["done"] == len(resources)
    assert result.code == 200

    actions = await data.ResourceAction.get_list()
    assert len([x for x in actions if x.status == const.ResourceState.undefined]) >= 1

    result = await client_multi.get_version(env_id, version)
    assert result.code == 200

    assert resource_container.Provider.changecount("agent2", "key4") == 0
    assert resource_container.Provider.changecount("agent2", "key5") == 0
    assert resource_container.Provider.changecount("agent2", "key1") == 0

    assert resource_container.Provider.readcount("agent2", "key4") == 0
    assert resource_container.Provider.readcount("agent2", "key5") == 0
    assert resource_container.Provider.readcount("agent2", "key1") == 1

    # Do a second deploy of the same model on agent2 with undefined resources
    await agent.trigger_update("env_id", "agent2", incremental_deploy=False)

    result = await client_multi.get_version(env_id, version, include_logs=True)

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

    await agent.stop()
    inmanta.agent.agent.GET_RESOURCE_BACKOFF = backoff


@pytest.mark.asyncio(timeout=30)
async def test_server_restart(resource_container, server, postgres_db, client):
    """
        dryrun and deploy a configuration model
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    await server.stop()
    ibl = InmantaBootloader()
    server = ibl.restserver
    await ibl.start()

    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key3",
            "value": None,
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "requires": [],
            "purged": True,
            "send_event": False,
        },
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

    # request a dryrun
    result = await client.dryrun_request(env_id, version)
    assert result.code == 200
    assert result.result["dryrun"]["total"] == len(resources)
    assert result.result["dryrun"]["todo"] == len(resources)

    # get the dryrun results
    result = await client.dryrun_list(env_id, version)
    assert result.code == 200
    assert len(result.result["dryruns"]) == 1

    while result.result["dryruns"][0]["todo"] > 0:
        result = await client.dryrun_list(env_id, version)
        await asyncio.sleep(0.1)

    dry_run_id = result.result["dryruns"][0]["id"]
    result = await client.dryrun_report(env_id, dry_run_id)
    assert result.code == 200

    changes = result.result["dryrun"]["resources"]
    assert changes[resources[0]["id"]]["changes"]["purged"]["current"]
    assert not changes[resources[0]["id"]]["changes"]["purged"]["desired"]
    assert changes[resources[0]["id"]]["changes"]["value"]["current"] is None
    assert (
        changes[resources[0]["id"]]["changes"]["value"]["desired"]
        == resources[0]["value"]
    )

    assert (
        changes[resources[1]["id"]]["changes"]["value"]["current"] == "incorrect_value"
    )
    assert (
        changes[resources[1]["id"]]["changes"]["value"]["desired"]
        == resources[1]["value"]
    )

    assert not changes[resources[2]["id"]]["changes"]["purged"]["current"]
    assert changes[resources[2]["id"]]["changes"]["purged"]["desired"]

    # do a deploy
    result = await client.release_version(
        env_id, version, True, const.AgentTriggerMethod.push_full_deploy
    )
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

    await agent.stop()
    await ibl.stop()


@pytest.mark.asyncio(timeout=30)
async def test_spontaneous_deploy(resource_container, server, client):
    """
        dryrun and deploy a configuration model
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    Config.set("config", "agent-deploy-interval", "2")
    Config.set("config", "agent-deploy-splay-time", "2")
    Config.set("config", "agent-repair-interval", "0")

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key3",
            "value": None,
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "requires": [],
            "purged": True,
            "send_event": False,
        },
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

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

    await agent.stop()


@pytest.mark.asyncio(timeout=30)
async def test_spontaneous_repair(resource_container, server, client):
    """
        dryrun and deploy a configuration model
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    Config.set("config", "agent-repair-interval", "2")
    Config.set("config", "agent-repair-splay-time", "2")
    Config.set("config", "agent-deploy-interval", "0")

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key3",
            "value": None,
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "requires": [],
            "purged": True,
            "send_event": False,
        },
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        env_id, version, True, const.AgentTriggerMethod.push_full_deploy
    )
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
            raise Exception("Timeout occured while waiting for repair run")
        await asyncio.sleep(0.1)

    await verify_deployment_result()

    await agent.stop()


@pytest.mark.asyncio(timeout=30)
async def test_failing_deploy_no_handler(resource_container, server, client):
    """
        dryrun and deploy a configuration model
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]
    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Noprov[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        }
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        env_id, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200
    assert result.result["model"]["total"] == 1

    result = await client.get_version(env_id, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, env_id, version)

    result = await client.get_version(env_id, version)
    assert result.result["model"]["done"] == len(resources)

    result = await client.get_version(env_id, version, include_logs=True)

    logs = result.result["resources"][0]["actions"][0]["messages"]
    assert any("traceback" in log["kwargs"] for log in logs), "\n".join(
        result.result["resources"][0]["actions"][0]["messages"]
    )

    await agent.stop()


@pytest.mark.asyncio
async def test_dual_agent(
    resource_container, server, client, environment, no_agent_backoff
):
    """
        dryrun and deploy a configuration model
    """
    resource_container.Provider.reset()
    myagent = agent.Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost", "agent2": "localhost"},
        code_loader=False,
    )
    myagent.add_end_point_name("agent1")
    myagent.add_end_point_name("agent2")
    await myagent.start()
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key1", "incorrect_value")
    resource_container.Provider.set("agent2", "key1", "incorrect_value")

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Wait[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value1",
            "id": "test::Wait[agent1,key=key2],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": ["test::Wait[agent1,key=key1],v=%d" % version],
        },
        {
            "key": "key1",
            "value": "value2",
            "id": "test::Wait[agent2,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Wait[agent2,key=key2],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": ["test::Wait[agent2,key=key1],v=%d" % version],
        },
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 4

    result = await resource_container.wait_for_done_with_waiters(
        client, environment, version
    )

    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["result"] == const.VersionState.success.name

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent2", "key1") == "value2"
    assert resource_container.Provider.get("agent1", "key2") == "value1"
    assert resource_container.Provider.get("agent2", "key2") == "value2"

    await myagent.stop()


@pytest.mark.asyncio
async def test_server_agent_api(resource_container, client, server):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]
    agent = Agent(
        environment=env_id,
        hostname="agent1",
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    await agent.start()

    agent2 = Agent(
        environment=env_id,
        hostname="agent2",
        agent_map={"agent2": "localhost"},
        code_loader=False,
    )
    await agent2.start()

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
    endpointid = [
        x["endpoints"][0]["id"]
        for x in result.result["processes"]
        if x["endpoints"][0]["name"] == "agent1"
    ][0]

    result = await client.get_agent_process(id=agent_sid)
    assert result.code == 200

    result = await client.get_agent_process(id=uuid.uuid4())
    assert result.code == 404

    version = int(time.time())

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": "test::Resource[agent1,key=key],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key2",
            "value": "value",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
        },
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}
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

    await agent.stop()
    await agent2.stop()


@pytest.mark.asyncio
async def test_get_facts(resource_container, client, server):
    """
        Test retrieving facts from the agent
    """
    resource_container.Provider.reset()
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = int(time.time())

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
        }
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200
    result = await client.release_version(
        env_id, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    result = await client.get_param(env_id, "length", resource_id_wov)
    assert result.code == 503

    env_uuid = uuid.UUID(env_id)
    params = await data.Parameter.get_list(
        environment=env_uuid, resource_id=resource_id_wov
    )
    while len(params) < 3:
        params = await data.Parameter.get_list(
            environment=env_uuid, resource_id=resource_id_wov
        )
        await asyncio.sleep(0.1)

    result = await client.get_param(env_id, "key1", resource_id_wov)
    assert result.code == 200
    await agent.stop()


@pytest.mark.asyncio
async def test_purged_facts(
    resource_container, client, server, environment, no_agent_backoff
):
    """
        Test if facts are purged when the resource is purged.
    """
    resource_container.Provider.reset()
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = 1
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
        }
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    result = await client.get_param(environment, "length", resource_id_wov)
    assert result.code == 503

    env_uuid = uuid.UUID(environment)
    params = await data.Parameter.get_list(
        environment=env_uuid, resource_id=resource_id_wov
    )
    while len(params) < 3:
        params = await data.Parameter.get_list(
            environment=env_uuid, resource_id=resource_id_wov
        )
        await asyncio.sleep(0.1)

    result = await client.get_param(environment, "key1", resource_id_wov)
    assert result.code == 200

    # Purge the resource
    version = 2
    resources[0]["id"] = "%s,v=%d" % (resource_id_wov, version)
    resources[0]["purged"] = True
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    result = await client.get_version(environment, version)
    assert result.result["model"]["done"] == len(resources)

    # The resource facts should be purged
    result = await client.get_param(environment, "length", resource_id_wov)
    assert result.code == 503

    await agent.stop()


@pytest.mark.asyncio
async def test_get_facts_extended(server, client, resource_container, environment):
    """
        dryrun and deploy a configuration model automatically
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    # allow very rapid fact refresh
    agentmanager._fact_resource_block = 0.1

    resource_container.Provider.reset()
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    # mark some as existing
    resource_container.Provider.set("agent1", "key1", "value")
    resource_container.Provider.set("agent1", "key2", "value")
    resource_container.Provider.set("agent1", "key4", "value")
    resource_container.Provider.set("agent1", "key5", "value")
    resource_container.Provider.set("agent1", "key6", "value")
    resource_container.Provider.set("agent1", "key7", "value")

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Fact[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": True,
            "skipFact": False,
            "factvalue": "fk1",
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value1",
            "id": "test::Fact[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": False,
            "factvalue": "fk2",
            "requires": [],
        },
        {
            "key": "key3",
            "value": "value1",
            "id": "test::Fact[agent1,key=key3],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": False,
            "factvalue": "fk3",
            "requires": [],
        },
        {
            "key": "key4",
            "value": "value1",
            "id": "test::Fact[agent1,key=key4],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": False,
            "factvalue": "fk4",
            "requires": [],
        },
        {
            "key": "key5",
            "value": "value1",
            "id": "test::Fact[agent1,key=key5],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": True,
            "factvalue": None,
            "requires": [],
        },
        {
            "key": "key6",
            "value": "value1",
            "id": "test::Fact[agent1,key=key6],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": False,
            "factvalue": None,
            "requires": [],
        },
        {
            "key": "key7",
            "value": "value1",
            "id": "test::Fact[agent1,key=key7],v=%d" % version,
            "send_event": False,
            "purged": False,
            "skip": False,
            "skipFact": False,
            "factvalue": "",
            "requires": [],
        },
    ]

    resource_states = {
        "test::Fact[agent1,key=key4],v=%d" % version: const.ResourceState.undefined,
        "test::Fact[agent1,key=key5],v=%d" % version: const.ResourceState.undefined,
    }

    async def get_fact(rid, result_code=200, limit=10, lower_limit=2):
        lower_limit = limit - lower_limit
        result = await client.get_param(environment, "fact", rid)

        # add minimal nr of reps or failure cases
        while (result.code != result_code and limit > 0) or limit > lower_limit:
            limit -= 1
            await asyncio.sleep(0.1)
            result = await client.get_param(environment, "fact", rid)

        assert result.code == result_code
        return result

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        resource_state=resource_states,
    )
    assert result.code == 200

    await get_fact("test::Fact[agent1,key=key1]")  # undeployable
    await get_fact("test::Fact[agent1,key=key2]")  # normal
    await get_fact("test::Fact[agent1,key=key3]", 503)  # not present
    await get_fact("test::Fact[agent1,key=key4]")  # unknown
    await get_fact("test::Fact[agent1,key=key5]", 503)  # broken
    f6 = await get_fact("test::Fact[agent1,key=key6]")  # normal
    f7 = await get_fact("test::Fact[agent1,key=key7]")  # normal

    assert f6.result["parameter"]["value"] == "None"
    assert f7.result["parameter"]["value"] == ""

    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    await get_fact("test::Fact[agent1,key=key1]")  # undeployable
    await get_fact("test::Fact[agent1,key=key2]")  # normal
    await get_fact("test::Fact[agent1,key=key3]")  # not present -> present
    await get_fact("test::Fact[agent1,key=key4]")  # unknown
    await get_fact("test::Fact[agent1,key=key5]", 503)  # broken

    await agent.stop()


@pytest.mark.asyncio
async def test_get_set_param(resource_container, client, server):
    """
        Test getting and setting params
    """
    resource_container.Provider.reset()
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    result = await client.set_param(
        tid=env_id, id="key10", value="value10", source="user"
    )
    assert result.code == 200

    result = await client.get_param(tid=env_id, id="key10")
    assert result.code == 200
    assert result.result["parameter"]["value"] == "value10"

    result = await client.delete_param(tid=env_id, id="key10")
    assert result.code == 200


@pytest.mark.asyncio
async def test_unkown_parameters(resource_container, client, server):
    """
        Test retrieving facts from the agent
    """
    resource_container.Provider.reset()
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = int(time.time())

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
        }
    ]

    unknowns = [{"resource": resource_id_wov, "parameter": "length", "source": "fact"}]
    result = await client.put_version(
        tid=env_id,
        version=version,
        resources=resources,
        unknowns=unknowns,
        version_info={},
    )
    assert result.code == 200

    result = await client.release_version(
        env_id, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    await server.get_slice("server").renew_expired_facts()

    env_id = uuid.UUID(env_id)
    params = await data.Parameter.get_list(
        environment=env_id, resource_id=resource_id_wov
    )
    while len(params) < 3:
        params = await data.Parameter.get_list(
            environment=env_id, resource_id=resource_id_wov
        )
        await asyncio.sleep(0.1)

    result = await client.get_param(env_id, "length", resource_id_wov)
    assert result.code == 200

    await agent.stop()


@pytest.mark.asyncio()
async def test_fail(resource_container, client, server):
    """
        Test results when a step fails
    """
    resource_container.Provider.reset()
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
        poolsize=10,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = int(time.time())

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": "test::Fail[agent1,key=key],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key2",
            "value": "value",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "requires": ["test::Fail[agent1,key=key],v=%d" % version],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key3",
            "value": "value",
            "id": "test::Resource[agent1,key=key3],v=%d" % version,
            "requires": ["test::Fail[agent1,key=key],v=%d" % version],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key4",
            "value": "value",
            "id": "test::Resource[agent1,key=key4],v=%d" % version,
            "requires": ["test::Resource[agent1,key=key3],v=%d" % version],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key5",
            "value": "value",
            "id": "test::Resource[agent1,key=key5],v=%d" % version,
            "requires": [
                "test::Resource[agent1,key=key4],v=%d" % version,
                "test::Fail[agent1,key=key],v=%d" % version,
            ],
            "purged": False,
            "send_event": False,
        },
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

    # deploy and wait until done
    result = await client.release_version(
        env_id, version, True, const.AgentTriggerMethod.push_full_deploy
    )
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

    await agent.stop()


@pytest.mark.asyncio(timeout=15)
async def test_wait(resource_container, client, server, no_agent_backoff):
    """
        If this test fail due to timeout,
        this is probably due to the mechanism in the agent that prevents pulling resources in very rapid succession.

        If the test server is slow, a get_resources call takes a long time,
        this makes the back-off longer

        this test deploys two models in rapid successions, if the server is slow, this may fail due to the back-off
    """
    resource_container.Provider.reset()

    # setup project
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    # setup env
    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    # setup agent
    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
        poolsize=10,
    )
    agent.add_end_point_name("agent1")
    await agent.start()

    # wait for agent
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    # set the deploy environment
    resource_container.Provider.set("agent1", "key", "value")

    def make_version(offset=0):
        version = int(time.time() + offset)

        resources = [
            {
                "key": "key",
                "value": "value",
                "id": "test::Wait[agent1,key=key],v=%d" % version,
                "requires": [],
                "purged": False,
                "send_event": False,
            },
            {
                "key": "key2",
                "value": "value",
                "id": "test::Resource[agent1,key=key2],v=%d" % version,
                "requires": ["test::Wait[agent1,key=key],v=%d" % version],
                "purged": False,
                "send_event": False,
            },
            {
                "key": "key3",
                "value": "value",
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "requires": [],
                "purged": False,
                "send_event": False,
            },
            {
                "key": "key4",
                "value": "value",
                "id": "test::Resource[agent1,key=key4],v=%d" % version,
                "requires": ["test::Resource[agent1,key=key3],v=%d" % version],
                "purged": False,
                "send_event": False,
            },
            {
                "key": "key5",
                "value": "value",
                "id": "test::Resource[agent1,key=key5],v=%d" % version,
                "requires": [
                    "test::Resource[agent1,key=key4],v=%d" % version,
                    "test::Wait[agent1,key=key],v=%d" % version,
                ],
                "purged": False,
                "send_event": False,
            },
        ]
        return version, resources

    async def wait_for_resources(version, n):
        result = await client.get_version(env_id, version)
        assert result.code == 200

        while result.result["model"]["done"] < n:
            result = await client.get_version(env_id, version)
            await asyncio.sleep(0.1)
        assert result.result["model"]["done"] == n

    logger.info("setup done")

    version1, resources = make_version()
    result = await client.put_version(
        tid=env_id, version=version1, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

    logger.info("first version pushed")

    # deploy and wait until one is ready
    result = await client.release_version(
        env_id, version1, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    logger.info("first version released")

    await wait_for_resources(version1, 2)

    logger.info("first version, 2 resources deployed")

    version2, resources = make_version(3)
    result = await client.put_version(
        tid=env_id, version=version2, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

    logger.info("second version pushed %f", time.time())

    await asyncio.sleep(1)

    logger.info("wait to expire load limiting%f", time.time())

    # deploy and wait until done
    result = await client.release_version(
        env_id, version2, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    logger.info("second version released")

    await resource_container.wait_for_done_with_waiters(client, env_id, version2)

    logger.info("second version complete")

    result = await client.get_version(env_id, version2)
    assert result.code == 200
    for x in result.result["resources"]:
        assert x["status"] == const.ResourceState.deployed.name

    result = await client.get_version(env_id, version1)
    assert result.code == 200
    states = {x["id"]: x["status"] for x in result.result["resources"]}

    assert (
        states["test::Wait[agent1,key=key],v=%d" % version1]
        == const.ResourceState.deployed.name
    )
    assert (
        states["test::Resource[agent1,key=key2],v=%d" % version1]
        == const.ResourceState.available.name
    )
    assert (
        states["test::Resource[agent1,key=key3],v=%d" % version1]
        == const.ResourceState.deployed.name
    )
    assert (
        states["test::Resource[agent1,key=key4],v=%d" % version1]
        == const.ResourceState.deployed.name
    )
    assert (
        states["test::Resource[agent1,key=key5],v=%d" % version1]
        == const.ResourceState.available.name
    )

    await agent.stop()


@pytest.mark.asyncio(timeout=15)
async def test_multi_instance(resource_container, client, server):
    """
       Test for multi threaded deploy
    """
    resource_container.Provider.reset()

    # setup project
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    # setup env
    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    # setup agent
    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost", "agent2": "localhost", "agent3": "localhost"},
        code_loader=False,
        poolsize=1,
    )
    agent.add_end_point_name("agent1")
    agent.add_end_point_name("agent2")
    agent.add_end_point_name("agent3")

    await agent.start()

    # wait for agent
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    # set the deploy environment
    resource_container.Provider.set("agent1", "key", "value")
    resource_container.Provider.set("agent2", "key", "value")
    resource_container.Provider.set("agent3", "key", "value")

    def make_version(offset=0):
        version = int(time.time() + offset)
        resources = []
        for agent in ["agent1", "agent2", "agent3"]:
            resources.extend(
                [
                    {
                        "key": "key",
                        "value": "value",
                        "id": "test::Wait[%s,key=key],v=%d" % (agent, version),
                        "requires": [
                            "test::Resource[%s,key=key3],v=%d" % (agent, version)
                        ],
                        "purged": False,
                        "send_event": False,
                    },
                    {
                        "key": "key2",
                        "value": "value",
                        "id": "test::Resource[%s,key=key2],v=%d" % (agent, version),
                        "requires": ["test::Wait[%s,key=key],v=%d" % (agent, version)],
                        "purged": False,
                        "send_event": False,
                    },
                    {
                        "key": "key3",
                        "value": "value",
                        "id": "test::Resource[%s,key=key3],v=%d" % (agent, version),
                        "requires": [],
                        "purged": False,
                        "send_event": False,
                    },
                    {
                        "key": "key4",
                        "value": "value",
                        "id": "test::Resource[%s,key=key4],v=%d" % (agent, version),
                        "requires": [
                            "test::Resource[%s,key=key3],v=%d" % (agent, version)
                        ],
                        "purged": False,
                        "send_event": False,
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

    version1, resources = make_version()
    result = await client.put_version(
        tid=env_id, version=version1, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

    logger.info("first version pushed")

    # deploy and wait until one is ready
    result = await client.release_version(
        env_id, version1, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    logger.info("first version released")
    # timeout on single thread!
    await wait_for_resources(version1, 1)

    await resource_container.wait_for_done_with_waiters(client, env_id, version1)

    logger.info("first version complete")
    await agent.stop()


@pytest.mark.asyncio
async def test_cross_agent_deps(resource_container, server, client):
    """
        deploy a configuration model with cross host dependency
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    # config for recovery mechanism
    Config.set("config", "agent-deploy-interval", "10")
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    agent2 = Agent(
        hostname="node2",
        environment=env_id,
        agent_map={"agent2": "localhost"},
        code_loader=False,
    )
    agent2.add_end_point_name("agent2")
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [
                "test::Wait[agent1,key=key2],v=%d" % version,
                "test::Resource[agent2,key=key3],v=%d" % version,
            ],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Wait[agent1,key=key2],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key3",
            "value": "value3",
            "id": "test::Resource[agent2,key=key3],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
        },
        {
            "key": "key4",
            "value": "value4",
            "id": "test::Resource[agent2,key=key4],v=%d" % version,
            "requires": [],
            "purged": False,
            "send_event": False,
        },
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        env_id, version, True, const.AgentTriggerMethod.push_full_deploy
    )
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

    result = await resource_container.wait_for_done_with_waiters(
        client, env_id, version
    )

    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["result"] == const.VersionState.success.name

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert resource_container.Provider.get("agent2", "key3") == "value3"

    await agent.stop()
    await agent2.stop()


@pytest.mark.asyncio(timeout=30)
async def test_dryrun_scale(resource_container, server, client):
    """
        test dryrun scaling
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    resources = []
    for i in range(1, 100):
        resources.append(
            {
                "key": "key%d" % i,
                "value": "value%d" % i,
                "id": "test::Resource[agent1,key=key%d],v=%d" % (i, version),
                "purged": False,
                "send_event": False,
                "requires": [],
            }
        )

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

    # request a dryrun
    result = await client.dryrun_request(env_id, version)
    assert result.code == 200
    assert result.result["dryrun"]["total"] == len(resources)
    assert result.result["dryrun"]["todo"] == len(resources)

    # get the dryrun results
    result = await client.dryrun_list(env_id, version)
    assert result.code == 200
    assert len(result.result["dryruns"]) == 1

    while result.result["dryruns"][0]["todo"] > 0:
        result = await client.dryrun_list(env_id, version)
        await asyncio.sleep(0.1)

    dry_run_id = result.result["dryruns"][0]["id"]
    result = await client.dryrun_report(env_id, dry_run_id)
    assert result.code == 200

    await agent.stop()


@pytest.mark.asyncio(timeout=30)
async def test_dryrun_failures(resource_container, server, client):
    """
        test dryrun scaling
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(
        hostname="node1",
        environment=env_id,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Noprov[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::FailFast[agent1,key=key2],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::DoesNotExist[agent1,key=key2],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        },
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

    # request a dryrun
    result = await client.dryrun_request(env_id, version)
    assert result.code == 200
    assert result.result["dryrun"]["total"] == len(resources)
    assert result.result["dryrun"]["todo"] == len(resources)

    # get the dryrun results
    result = await client.dryrun_list(env_id, version)
    assert result.code == 200
    assert len(result.result["dryruns"]) == 1

    while result.result["dryruns"][0]["todo"] > 0:
        result = await client.dryrun_list(env_id, version)
        await asyncio.sleep(0.1)

    dry_run_id = result.result["dryruns"][0]["id"]
    result = await client.dryrun_report(env_id, dry_run_id)
    assert result.code == 200

    resources = result.result["dryrun"]["resources"]

    def assert_handler_failed(resource, msg):
        changes = resources[resource]
        assert "changes" in changes
        changes = changes["changes"]
        assert "handler" in changes
        change = changes["handler"]
        assert change["current"] == "FAILED"
        assert change["desired"] == msg

    assert_handler_failed(
        "test::Noprov[agent1,key=key1],v=%d" % version, "Unable to find a handler"
    )
    assert_handler_failed(
        "test::FailFast[agent1,key=key2],v=%d" % version, "Handler failed"
    )
    assert_handler_failed(
        "test::DoesNotExist[agent1,key=key2],v=%d" % version,
        "Resource Deserialization Failed",
    )

    await agent.stop()


@pytest.mark.asyncio
async def test_send_events(resource_container, environment, server, client):
    """
        Send and receive events within one agent
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

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
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
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

    await agent.stop()


@pytest.mark.asyncio
async def test_send_events_cross_agent(resource_container, environment, server, client):
    """
        Send and receive events over agents
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    agent2 = Agent(
        hostname="node2",
        environment=environment,
        agent_map={"agent2": "localhost"},
        code_loader=False,
    )
    agent2.add_end_point_name("agent2")
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)

    version = int(time.time())

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
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
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

    await agent.stop()
    await agent2.stop()


@pytest.mark.asyncio
async def test_send_events_cross_agent_deploying(
    resource_container, environment, server, client, no_agent_backoff
):
    """
        Send and receive events over agents
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    agent2 = Agent(
        hostname="node2",
        environment=environment,
        agent_map={"agent2": "localhost"},
        code_loader=False,
    )
    agent2.add_end_point_name("agent2")
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)

    version = int(time.time())

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
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200

    await _wait_for_n_deploying(client, environment, version, 1)

    # restart deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    await resource_container.wait_for_done_with_waiters(client, environment, version)

    # incorrect CAD handling causes skip, which completes deploy without writing
    assert resource_container.Provider.get("agent1", "key1") == "value1"

    await agent.stop()
    await agent2.stop()


@pytest.mark.asyncio(timeout=15)
async def test_send_events_cross_agent_restart(
    resource_container, environment, server, client, no_agent_backoff
):
    """
        Send and receive events over agents with agents starting after deploy
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    resource_container.Provider.reset()
    agent2 = Agent(
        hostname="node2",
        environment=environment,
        agent_map={"agent2": "localhost"},
        code_loader=False,
    )
    agent2.add_end_point_name("agent2")
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

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
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200

    # wait for agent 2 to finish
    while (result.result["model"]["total"] - result.result["model"]["done"]) > 1:
        result = await client.get_version(environment, version)
        await asyncio.sleep(1)

    assert resource_container.Provider.get("agent2", "key2") == "value2"

    # start agent 1 and wait for it to finish
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
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

    await agent.stop()
    await agent2.stop()


@pytest.mark.parametrize(
    "agent_trigger_method, read_resource1, change_resource1, read_resource2, change_resource2",
    [
        (const.AgentTriggerMethod.push_incremental_deploy, 1, 1, 2, 2),
        (const.AgentTriggerMethod.push_full_deploy, 2, 1, 2, 2),
    ],
)
@pytest.mark.asyncio
async def test_auto_deploy(
    server,
    client,
    resource_container,
    environment,
    agent_trigger_method,
    read_resource1,
    change_resource1,
    read_resource2,
    change_resource2,
    no_agent_backoff,
):
    """
        dryrun and deploy a configuration model automatically
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    def get_resources(version, value_resource_two):
        return [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
            },
            {
                "key": "key2",
                "value": value_resource_two,
                "id": "test::Resource[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "requires": [],
                "purged": False,
            },
            {
                "key": "key3",
                "value": None,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "requires": [],
                "purged": True,
            },
        ]

    initial_version = int(time.time())
    for version, value_resource_two in [
        (initial_version, "value1"),
        (initial_version + 1, "value2"),
    ]:
        resources = get_resources(version, value_resource_two)

        # set auto deploy and push
        result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
        assert result.code == 200
        result = await client.set_setting(environment, data.PUSH_ON_AUTO_DEPLOY, True)
        assert result.code == 200
        result = await client.set_setting(
            environment, data.AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY, agent_trigger_method
        )
        assert result.code == 200

        result = await client.put_version(
            tid=environment,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
        )
        assert result.code == 200

        # check deploy
        result = await client.get_version(environment, version)
        assert result.code == 200
        assert result.result["model"]["released"]
        assert result.result["model"]["total"] == 3
        assert result.result["model"]["result"] == "deploying"

        await _wait_until_deployment_finishes(client, environment, version)

        result = await client.get_version(environment, version)
        assert result.result["model"]["done"] == len(resources)

        assert resource_container.Provider.isset("agent1", "key1")
        assert resource_container.Provider.get("agent1", "key1") == "value1"
        assert resource_container.Provider.get("agent1", "key2") == value_resource_two
        assert not resource_container.Provider.isset("agent1", "key3")

    assert resource_container.Provider.readcount("agent1", "key1") == read_resource1
    assert resource_container.Provider.changecount("agent1", "key1") == change_resource1
    assert resource_container.Provider.readcount("agent1", "key2") == read_resource2
    assert resource_container.Provider.changecount("agent1", "key2") == change_resource2

    await agent.stop()


@pytest.mark.asyncio(timeout=15)
async def test_auto_deploy_no_splay(server, client, resource_container, environment):
    """
        dryrun and deploy a configuration model automatically with agent autostart
    """
    resource_container.Provider.reset()
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"agent1": ""})
    await env.set(data.AUTOSTART_ON_START, True)

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        }
    ]

    # set auto deploy and push
    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200
    result = await client.set_setting(environment, data.PUSH_ON_AUTO_DEPLOY, True)
    assert result.code == 200
    result = await client.set_setting(
        environment, data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, 0
    )
    assert result.code == 200

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    # check deploy
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    # check if agent 1 is started by the server
    # deploy will fail because handler code is not uploaded to the server
    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while (
        len(result.result["agents"]) == 0
        or result.result["agents"][0]["state"] == "down"
    ):
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == "agent1"


def ps_diff(original, current_process, diff=0):
    current = current_process.children(recursive=True)

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
        pre:%s
        post:%s""" % (
        original,
        current,
    )


@pytest.mark.asyncio(timeout=15)
async def test_autostart_mapping(server, client, resource_container, environment):
    """
        Test autostart mapping and restart agents when the map is modified
    """
    current_process = psutil.Process()
    children_pre = current_process.children(recursive=True)
    resource_container.Provider.reset()
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"agent1": ""})
    await env.set(data.AUTO_DEPLOY, True)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    await env.set(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, 0)
    await env.set(data.AUTOSTART_ON_START, True)

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent2,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    # check deploy
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 2
    assert result.result["model"]["result"] == "deploying"

    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 1:
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 2
    assert len([x for x in result.result["agents"] if x["state"] == "up"]) == 1

    result = await client.set_setting(
        environment, data.AUTOSTART_AGENT_MAP, {"agent1": "", "agent2": ""}
    )
    assert result.code == 200

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 2:
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    await server.stop()

    current_process = psutil.Process()
    children = current_process.children(recursive=True)

    newchildren = set(children) - set(children_pre)

    assert len(newchildren) == 0, newchildren


@pytest.mark.asyncio(timeout=15)
async def test_autostart_clear_environment(
    server_multi, client_multi, resource_container, environment_multi
):
    """
        Test clearing an environment with autostarted agents. After clearing, autostart should still work
    """
    resource_container.Provider.reset()
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    env = await data.Environment.get_by_id(uuid.UUID(environment_multi))
    await env.set(data.AUTOSTART_AGENT_MAP, {"agent1": ""})
    await env.set(data.AUTO_DEPLOY, True)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    await env.set(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, 0)
    await env.set(data.AUTOSTART_ON_START, True)

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        }
    ]

    client = client_multi
    result = await client.put_version(
        tid=environment_multi,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    # check deploy
    result = await client.get_version(environment_multi, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    result = await client.list_agents(tid=environment_multi)
    assert result.code == 200

    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 1:
        result = await client.list_agents(tid=environment_multi)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert len([x for x in result.result["agents"] if x["state"] == "up"]) == 1
    # One autostarted agent should running as a subprocess
    ps_diff(children, current_process, 1)

    # clear environment
    await client.clear_environment(environment_multi)

    # Autostarted agent should be terminated after clearing the environment
    ps_diff(children, current_process, 0)
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
    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        }
    ]

    result = await client.put_version(
        tid=environment_multi,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    # check deploy
    result = await client.get_version(environment_multi, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    result = await client.list_agents(tid=environment_multi)
    assert result.code == 200

    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 1:
        result = await client.list_agents(tid=environment_multi)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert len([x for x in result.result["agents"] if x["state"] == "up"]) == 1

    # One autostarted agent should running as a subprocess
    ps_diff(children, current_process, 1)


async def setup_environment_with_agent(client, project_name):
    """
        1) Create a project with name project_name and create an environment.
        2) Deploy a model which requires one autostarted agent.
        3) Wait until the autostarted agent is up.
    """
    create_project_result = await client.create_project(project_name)
    assert create_project_result.code == 200
    project_id = create_project_result.result["project"]["id"]

    create_environment_result = await client.create_environment(
        project_id=project_id, name="dev"
    )
    assert create_environment_result.code == 200
    env_id = create_environment_result.result["environment"]["id"]
    env = await data.Environment.get_by_id(uuid.UUID(env_id))

    await env.set(data.AUTOSTART_AGENT_MAP, {"agent1": ""})
    await env.set(data.AUTO_DEPLOY, True)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    await env.set(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, 0)
    await env.set(data.AUTOSTART_ON_START, True)

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        }
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}
    )
    assert result.code == 200

    # check deploy
    result = await client.get_version(env_id, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    result = await client.list_agents(tid=env_id)
    assert result.code == 200

    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 1:
        result = await client.list_agents(tid=env_id)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert len([x for x in result.result["agents"] if x["state"] == "up"]) == 1

    return project_id, env_id


@pytest.mark.asyncio(timeout=15)
async def test_stop_autostarted_agents_on_environment_removal(
    server, client, resource_container
):
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    resource_container.Provider.reset()
    (project_id, env_id) = await setup_environment_with_agent(client, "proj")

    # One autostarted agent should running as a subprocess
    ps_diff(children, current_process, 1)

    result = await client.delete_environment(id=env_id)
    assert result.code == 200

    # The autostarted agent should be terminated when its environment is deleted.
    ps_diff(children, current_process, 0)


@pytest.mark.asyncio(timeout=15)
async def test_stop_autostarted_agents_on_project_removal(
    server, client, resource_container
):
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    resource_container.Provider.reset()
    (project1_id, env1_id) = await setup_environment_with_agent(client, "proj1")
    await setup_environment_with_agent(client, "proj2")

    # Two autostarted agents should be running (one in proj1 and one in proj2).
    ps_diff(children, current_process, 2)

    result = await client.delete_project(id=project1_id)
    assert result.code == 200

    # The autostarted agent of proj1 should be terminated when its project is deleted
    # The autostarted agent of proj2 keep running
    ps_diff(children, current_process, 1)


@pytest.mark.asyncio
async def test_export_duplicate(resource_container, snippetcompiler):
    """
        The exported should provide a compilation error when a resource is defined twice in a model
    """
    snippetcompiler.setup_for_snippet(
        """
        import test

        test::Resource(key="test", value="foo")
        test::Resource(key="test", value="bar")
    """
    )

    with pytest.raises(CompilerException) as exc:
        snippetcompiler.do_export()

    assert "exists more than once in the configuration model" in str(exc.value)


@pytest.mark.asyncio(timeout=90)
async def test_server_recompile(server_multi, client_multi, environment_multi):
    """
        Test a recompile on the server and verify recompile triggers
    """
    config.Config.set("server", "auto-recompile-wait", "0")
    client = client_multi
    server = server_multi
    environment = environment_multi

    async def wait_for_version(cnt):
        # Wait until the server is no longer compiling
        # wait for it to finish
        await asyncio.sleep(0.1)
        code = 200
        while code == 200:
            compiling = await client.is_compiling(environment)
            code = compiling.code
            await asyncio.sleep(0.1)
        # wait for it to appear
        versions = await client.list_versions(environment)

        while versions.result["count"] < cnt:
            logger.info(versions.result)
            versions = await client.list_versions(environment)
            await asyncio.sleep(0.1)

        reports = await client.get_reports(environment)
        for report in reports.result["reports"]:
            data = await client.get_report(report["id"])
            print(json.dumps(data.result, indent=4))

        return versions.result

    project_dir = os.path.join(
        server.get_slice("server")._server_storage["environments"], str(environment)
    )
    project_source = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data", "project"
    )

    shutil.copytree(project_source, project_dir)
    subprocess.check_output(["git", "init"], cwd=project_dir)
    subprocess.check_output(["git", "add", "*"], cwd=project_dir)
    subprocess.check_output(["git", "config", "user.name", "Unit"], cwd=project_dir)
    subprocess.check_output(
        ["git", "config", "user.email", "unit@test.example"], cwd=project_dir
    )
    subprocess.check_output(["git", "commit", "-m", "unit test"], cwd=project_dir)

    # add main.cf
    with open(os.path.join(project_dir, "main.cf"), "w") as fd:
        fd.write(
            """
        host = std::Host(name="test", os=std::linux)
        std::ConfigFile(host=host, path="/etc/motd", content="1234")
"""
        )

    logger.info("request a compile")
    await client.notify_change(environment)

    logger.info("wait for 1")
    versions = await wait_for_version(1)
    assert versions["versions"][0]["total"] == 1
    assert versions["versions"][0]["version_info"]["export_metadata"]["type"] == "api"

    # get compile reports
    reports = await client.get_reports(environment)
    assert len(reports.result["reports"]) == 1

    # set a parameter without requesting a recompile
    await client.set_param(environment, id="param1", value="test", source="plugin")
    versions = await wait_for_version(1)
    assert versions["count"] == 1

    logger.info("request second compile")
    # set a new parameter and request a recompile
    await client.set_param(
        environment, id="param2", value="test", source="plugin", recompile=True
    )
    logger.info("wait for 2")
    versions = await wait_for_version(2)
    assert versions["versions"][0]["version_info"]["export_metadata"]["type"] == "param"
    assert versions["count"] == 2

    # update the parameter to the same value -> no compile
    await client.set_param(
        environment, id="param2", value="test", source="plugin", recompile=True
    )
    versions = await wait_for_version(2)
    assert versions["count"] == 2

    # update the parameter to a new value
    await client.set_param(
        environment, id="param2", value="test2", source="plugin", recompile=True
    )
    versions = await wait_for_version(3)
    logger.info("wait for 3")
    assert versions["count"] == 3

    # clear the environment
    state_dir = server_config.state_dir.get()
    project_dir = os.path.join(state_dir, "server", "environments", environment)
    assert os.path.exists(project_dir)

    await client.clear_environment(environment)

    assert not os.path.exists(project_dir)


class ResourceProvider(object):
    def __init__(self, index, name, producer, state=None):
        self.name = name
        self.producer = producer
        self.state = state
        self.index = index

    def get_resource(
        self,
        resource_container: ResourceContainer,
        agent: str,
        key: str,
        version: str,
        requires: List[str],
    ) -> Tuple[Dict[str, str], Optional[const.ResourceState]]:
        base = {
            "key": key,
            "value": "value1",
            "id": "test::Resource[%s,key=%s],v=%d" % (agent, key, version),
            "send_event": True,
            "purged": False,
            "requires": requires,
        }

        self.producer(resource_container.Provider, agent, key)

        state = None
        if self.state is not None:
            state = ("test::Resource[%s,key=%s]" % (agent, key), self.state)

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
    ResourceProvider(
        3, "undefined", lambda p, a, k: None, const.ResourceState.undefined
    ),
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

doevents = make_matrix(
    """
        skip    fail    success    undef
skip    2    2    2    0
fail    2    2    2    0
succ    2    2    2    0
""",
    lambda x: int(x),
)


@pytest.mark.parametrize("self_state", self_states, ids=lambda x: x.name)
@pytest.mark.parametrize("dep_state", dep_states, ids=lambda x: x.name)
@pytest.mark.asyncio
async def test_deploy_and_events(
    client, server, environment, resource_container, self_state, dep_state
):

    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    (dep, dep_status) = dep_state.get_resource(
        resource_container, "agent1", "key2", version, []
    )
    (own, own_status) = self_state.get_resource(
        resource_container,
        "agent1",
        "key3",
        version,
        [
            "test::Resource[agent1,key=key2],v=%d" % version,
            "test::Resource[agent1,key=key1],v=%d" % version,
        ],
    )

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": True,
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
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
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
    assert dorun[dep_state.index][self_state.index] == (
        resource_container.Provider.readcount("agent1", "key3") > 0
    )
    assert dochange[dep_state.index][self_state.index] == (
        resource_container.Provider.changecount("agent1", "key3") > 0
    )

    events = resource_container.Provider.getevents("agent1", "key3")
    expected_events = doevents[dep_state.index][self_state.index]
    if expected_events == 0:
        assert len(events) == 0
    else:
        assert len(events) == 1
        assert len(events[0]) == expected_events

    await agent.stop()


@pytest.mark.asyncio
async def test_deploy_and_events_failed(
    client, server, environment, resource_container
):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": True,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value1",
            "id": "test::BadEvents[agent1,key=key2],v=%d" % version,
            "send_event": True,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
        },
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
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
    await agent.stop()


dep_states_reload = [
    ResourceProvider(0, "skip", lambda p, a, k: p.set_skip(a, k, 1)),
    ResourceProvider(0, "fail", lambda p, a, k: p.set_fail(a, k, 1)),
    ResourceProvider(0, "nochange", lambda p, a, k: p.set(a, k, "value1")),
    ResourceProvider(1, "changed", lambda p, a, k: None),
]


@pytest.mark.parametrize("dep_state", dep_states_reload, ids=lambda x: x.name)
@pytest.mark.asyncio(timeout=5000)
async def test_reload(client, server, environment, resource_container, dep_state):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    (dep, dep_status) = dep_state.get_resource(
        resource_container, "agent1", "key1", version, []
    )

    resources = [
        {
            "key": "key2",
            "value": "value1",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": True,
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
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
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
    await agent.stop()


@pytest.mark.asyncio(timeout=30)
async def test_s_repair_postponed_due_to_running_deploy(
    resource_container, server, client, environment, no_agent_backoff, caplog
):
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"
    myagent = agent.Agent(
        hostname="node1",
        environment=environment,
        agent_map={agent_name: "localhost"},
        code_loader=False,
    )
    myagent.add_end_point_name("agent1")
    await myagent.start()
    myagent_instance = myagent._instances[agent_name]
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key1", "value1")

    version1 = int(time.time())

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
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::Wait[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
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
        reason="Deploy", incremental_deploy=True, is_repair_run=False
    )
    # key3: Readcount=2; writecount=1
    await myagent_instance.get_latest_version_for_agent(
        reason="Repair", incremental_deploy=False, is_repair_run=True
    )

    def wait_condition():
        return not (
            resource_container.Provider.readcount(agent_name, "key3") == 2
            and resource_container.Provider.changecount(agent_name, "key3") == 1
        )

    await resource_container.wait_for_condition_with_waiters(wait_condition)

    assert resource_container.Provider.readcount(agent_name, "key3") == 2
    assert resource_container.Provider.changecount(agent_name, "key3") == 1

    assert resource_container.Provider.get("agent1", "key1") == "value2"

    await myagent.stop()

    log_contains(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.INFO,
        "Deferring run 'Repair' for 'Deploy'",
    )
    log_contains(
        caplog, "inmanta.agent.agent.agent1", logging.INFO, "Resuming run 'Repair'"
    )


debug_timeout = 10


@pytest.mark.asyncio(timeout=debug_timeout * 2)
async def test_s_repair_interrupted_by_deploy_request(
    resource_container, server, client, environment, no_agent_backoff, caplog
):
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"
    myagent = agent.Agent(
        hostname="node1",
        environment=environment,
        agent_map={agent_name: "localhost"},
        code_loader=False,
    )
    myagent.add_end_point_name("agent1")
    await myagent.start()
    myagent_instance = myagent._instances[agent_name]
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

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
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::Wait[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
            },
        ]

    version1 = int(time.time())
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(
        reason="Deploy 1", incremental_deploy=True, is_repair_run=False
    )
    await resource_container.wait_for_done_with_waiters(
        client, environment, version1, timeout=debug_timeout
    )

    # counts:  read/write
    # key1: 1/1
    # key3: 1/1

    # Interrupt repair with deploy
    # Repair
    await myagent_instance.get_latest_version_for_agent(
        reason="Repair", incremental_deploy=False, is_repair_run=True
    )

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
    version2 = version1 + 1
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, False)

    print("Interrupt")
    await myagent_instance.get_latest_version_for_agent(
        reason="Deploy 2", incremental_deploy=True, is_repair_run=False
    )
    print("Deploy")
    await resource_container.wait_for_done_with_waiters(
        client, environment, version2, timeout=debug_timeout
    )

    # counts:  read/write
    # key1: 2/1
    # key3: 2/2

    assert resource_container.Provider.readcount(agent_name, "key1") >= 2
    assert resource_container.Provider.changecount(agent_name, "key1") >= 1
    assert resource_container.Provider.readcount(agent_name, "key3") >= 2
    assert resource_container.Provider.changecount(agent_name, "key3") >= 2

    def wait_condition():
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

    await resource_container.wait_for_condition_with_waiters(
        wait_condition, timeout=debug_timeout
    )

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

    await myagent.stop()

    log_contains(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.INFO,
        "Interrupting run 'Repair' for 'Deploy 2'",
    )
    log_contains(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.INFO,
        "for reason: Restarting run 'Repair', interrupted for 'Deploy 2'",
    )
    log_contains(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.INFO,
        "Resuming run 'Restarting run 'Repair', interrupted for 'Deploy 2''",
    )


@pytest.mark.asyncio
async def test_s_repair_during_repair(
    resource_container, server, client, environment, no_agent_backoff, caplog
):
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"
    myagent = agent.Agent(
        hostname="node1",
        environment=environment,
        agent_map={agent_name: "localhost"},
        code_loader=False,
    )
    myagent.add_end_point_name("agent1")
    await myagent.start()
    myagent_instance = myagent._instances[agent_name]
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key1", "value1")
    resource_container.Provider.set("agent1", "key1", "value1")

    version = int(time.time())
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
            "id": "test::Wait[agent1,key=key2],v=%d" % version,
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
            "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
        },
    ]

    # Initial deploy
    await _deploy_resources(client, environment, resources, version, False)
    await myagent_instance.get_latest_version_for_agent(
        reason="Deploy", incremental_deploy=True, is_repair_run=False
    )
    await resource_container.wait_for_done_with_waiters(client, environment, version)

    # Interrupt repair with a repair
    await myagent_instance.get_latest_version_for_agent(
        reason="Repair 1", incremental_deploy=False, is_repair_run=True
    )
    await myagent_instance.get_latest_version_for_agent(
        reason="Repair 2", incremental_deploy=False, is_repair_run=True
    )

    def wait_condition():
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

    await myagent.stop()

    log_contains(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.INFO,
        "Terminating run 'Repair 1' for 'Repair 2'",
    )


@pytest.mark.asyncio(timeout=30)
async def test_s_deploy_during_deploy(
    resource_container, server, client, environment, no_agent_backoff, caplog
):
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"
    myagent = agent.Agent(
        hostname="node1",
        environment=environment,
        agent_map={agent_name: "localhost"},
        code_loader=False,
    )
    myagent.add_end_point_name("agent1")
    await myagent.start()
    myagent_instance = myagent._instances[agent_name]
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

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
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::Wait[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
            },
        ]

    version1 = int(time.time())
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(
        reason="Deploy 1", incremental_deploy=True, is_repair_run=False
    )

    # Make sure that resource key1 is fully deployed before triggering the interrupt
    timeout_time = time.time() + 10
    while (await client.get_version(environment, version1)).result["model"][
        "done"
    ] < 1 and time.time() < timeout_time:
        await asyncio.sleep(0.1)

    version2 = version1 + 1
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, False)
    await myagent_instance.get_latest_version_for_agent(
        reason="Deploy 2", incremental_deploy=True, is_repair_run=False
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

    await myagent.stop()
    log_contains(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.INFO,
        "Terminating run 'Deploy 1' for 'Deploy 2'",
    )


@pytest.mark.asyncio(timeout=30)
async def test_s_full_deploy_interrupts_incremental_deploy(
    resource_container, server, client, environment, no_agent_backoff, caplog
):
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"
    myagent = agent.Agent(
        hostname="node1",
        environment=environment,
        agent_map={agent_name: "localhost"},
        code_loader=False,
    )
    myagent.add_end_point_name("agent1")
    await myagent.start()
    myagent_instance = myagent._instances[agent_name]
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

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
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::Wait[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
            },
        ]

    version1 = int(time.time())
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(
        reason="Initial Deploy", incremental_deploy=True, is_repair_run=False
    )

    # Make sure that resource key1 is fully deployed before triggering the interrupt
    timeout_time = time.time() + 10
    while (await client.get_version(environment, version1)).result["model"][
        "done"
    ] < 1 and time.time() < timeout_time:
        await asyncio.sleep(0.1)

    version2 = version1 + 1
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, False)
    await myagent_instance.get_latest_version_for_agent(
        reason="Second Deploy", incremental_deploy=False, is_repair_run=False
    )

    await resource_container.wait_for_done_with_waiters(client, environment, version2)

    # Incremental deploy:
    #   * test::Resource[agent1,key=key1] is deployed successfully;
    #   * test::Resource[agent1,key=key2] and test::Resource[agent1,key=key3] are cancelled
    # Full deploy:
    #   * All resources are deployed successfully
    assert resource_container.Provider.readcount(agent_name, "key1") == 2
    assert resource_container.Provider.changecount(agent_name, "key1") == 1
    assert resource_container.Provider.readcount(agent_name, "key3") == 1
    assert resource_container.Provider.changecount(agent_name, "key3") == 1

    assert resource_container.Provider.get("agent1", "key1") == "value2"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert resource_container.Provider.get("agent1", "key3") == "value3"

    await myagent.stop()
    log_contains(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.INFO,
        "Terminating run 'Initial Deploy' for 'Second Deploy'",
    )


@pytest.mark.asyncio(timeout=30)
async def test_s_incremental_deploy_interrupts_full_deploy(
    resource_container, server, client, environment, no_agent_backoff, caplog
):
    caplog.set_level(logging.INFO)
    resource_container.Provider.reset()
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent_name = "agent1"
    myagent = agent.Agent(
        hostname="node1",
        environment=environment,
        agent_map={agent_name: "localhost"},
        code_loader=False,
    )
    myagent.add_end_point_name("agent1")
    await myagent.start()
    myagent_instance = myagent._instances[agent_name]
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

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
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": "test::Wait[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": ["test::Resource[agent1,key=key1],v=%d" % version],
            },
            {
                "key": "key3",
                "value": value_resource_three,
                "id": "test::Resource[agent1,key=key3],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": ["test::Wait[agent1,key=key2],v=%d" % version],
            },
        ]

    version1 = int(time.time())
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(
        reason="Initial Deploy", incremental_deploy=False, is_repair_run=False
    )

    # Make sure that resource key1 is fully deployed before triggering the interrupt
    timeout_time = time.time() + 10
    while (await client.get_version(environment, version1)).result["model"][
        "done"
    ] < 1 and time.time() < timeout_time:
        await asyncio.sleep(0.1)

    version2 = version1 + 1
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, False)
    await myagent_instance.get_latest_version_for_agent(
        reason="Second Deploy", incremental_deploy=True, is_repair_run=False
    )

    await resource_container.wait_for_done_with_waiters(client, environment, version2)

    # Full deploy:
    #   * test::Resource[agent1,key=key1] is deployed successfully;
    #   * test::Resource[agent1,key=key2] and test::Resource[agent1,key=key3] are cancelled
    # Incremental deploy:
    #   * test::Resource[agent1,key=key2] is not included in the increment
    #   * test::Resource[agent1,key=key2] and test::Resource[agent1,key=key3] are deployed successfully
    assert resource_container.Provider.readcount(agent_name, "key1") == 1
    assert resource_container.Provider.changecount(agent_name, "key1") == 1
    assert resource_container.Provider.readcount(agent_name, "key3") == 1
    assert resource_container.Provider.changecount(agent_name, "key3") == 1

    assert resource_container.Provider.get("agent1", "key1") == "value2"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert resource_container.Provider.get("agent1", "key3") == "value3"

    await myagent.stop()
    log_contains(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.INFO,
        "Terminating run 'Initial Deploy' for 'Second Deploy'",
    )


@pytest.mark.asyncio
async def test_bad_post_get_facts(
    resource_container, client, server, environment, caplog
):
    """
        Test retrieving facts from the agent
    """
    caplog.set_level(logging.ERROR)

    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = int(time.time())

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
        }
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    caplog.clear()

    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    assert (
        "An error occurred after deployment of test::BadPost[agent1,key=key]"
        in caplog.text
    )
    caplog.clear()

    result = await client.get_param(environment, "length", resource_id_wov)
    assert result.code == 503

    env_uuid = uuid.UUID(environment)
    params = await data.Parameter.get_list(
        environment=env_uuid, resource_id=resource_id_wov
    )
    while len(params) < 3:
        params = await data.Parameter.get_list(
            environment=env_uuid, resource_id=resource_id_wov
        )
        await asyncio.sleep(0.1)

    result = await client.get_param(environment, "key1", resource_id_wov)
    assert result.code == 200

    assert "An error occurred after getting facts about test::BadPost" in caplog.text

    await agent.stop()


@pytest.mark.asyncio
async def test_bad_post_events(resource_container, environment, server, client, caplog):
    """
        Send and receive events within one agent
    """
    caplog.set_level(logging.ERROR)

    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    res_id_1 = "test::BadPost[agent1,key=key1],v=%d" % version
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
    )
    assert result.code == 200

    caplog.clear()
    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    events = resource_container.Provider.getevents("agent1", "key1")
    assert len(events) == 1
    for res_id, res in events[0].items():
        assert res_id.agent_name == "agent1"
        assert res_id.attribute_value == "key2"
        assert res["status"] == const.ResourceState.deployed
        assert res["change"] == const.Change.created

    assert (
        "An error occurred after deployment of test::BadPost[agent1,key=key1]"
        in caplog.text
    )
    caplog.clear()

    # Nothing is reported as events don't have pre and post

    await agent.stop()


@pytest.mark.asyncio
async def test_inprogress(resource_container, client, server, environment):
    """
        Test retrieving facts from the agent
    """
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = int(time.time())

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
        }
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    async def in_progress():
        result = await client.get_version(environment, version)
        assert result.code == 200
        res = result.result["resources"][0]
        status = res["status"]
        return status == "deploying"

    await retry_limited(in_progress, 30)

    await resource_container.wait_for_done_with_waiters(client, environment, version)

    await agent.stop()


@pytest.mark.asyncio
async def test_eventprocessing(resource_container, client, server, environment):
    """
        Test retrieving facts from the agent
    """
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(server.get_slice("session")._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = int(time.time())

    resource_id_wov = "test::WaitEvent[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": resource_id,
            "purged": False,
            "send_event": False,
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
    )
    assert result.code == 200

    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    async def in_progress():
        result = await client.get_version(environment, version)
        assert result.code == 200
        status = sorted([res["status"] for res in result.result["resources"]])
        return status == ["deployed", "processing_events"]

    await retry_limited(in_progress, 1)

    await resource_container.wait_for_done_with_waiters(client, environment, version)

    await agent.stop()


@pytest.mark.asyncio
async def test_push_incremental_deploy(
    resource_container, environment, server, client, no_agent_backoff
):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    def get_resources(version, value_second_resource):
        return [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": value_second_resource,
                "id": "test::Resource[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "requires": [],
                "purged": False,
            },
        ]

    # Make sure some resources are deployed
    resources = get_resources(version, "value1")
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value1"

    # Second version deployed with incremental deploy
    version2 = version + 1
    resources_version2 = get_resources(version2, "value2")

    result = await client.put_version(
        tid=environment,
        version=version2,
        resources=resources_version2,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    result = await client.release_version(
        environment, version2, True, const.AgentTriggerMethod.push_incremental_deploy
    )
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


@pytest.mark.parametrize(
    "push, agent_trigger_method",
    [(True, None), (True, const.AgentTriggerMethod.push_full_deploy)],
)
@pytest.mark.asyncio
async def test_push_full_deploy(
    resource_container,
    environment,
    server,
    client,
    no_agent_backoff,
    push,
    agent_trigger_method,
):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    def get_resources(version, value_second_resource):
        return [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": value_second_resource,
                "id": "test::Resource[agent1,key=key2],v=%d" % version,
                "send_event": False,
                "requires": [],
                "purged": False,
            },
        ]

    # Make sure some resources are deployed
    resources = get_resources(version, "value1")
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    result = await client.release_version(
        environment, version, push, agent_trigger_method
    )
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value1"

    # Second version deployed with incremental deploy
    version2 = version + 1
    resources_version2 = get_resources(version2, "value2")

    result = await client.put_version(
        tid=environment,
        version=version2,
        resources=resources_version2,
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    result = await client.release_version(
        environment, version2, push, agent_trigger_method
    )
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


@pytest.mark.asyncio
async def test_agent_run_sync(resource_container, environment, server, client):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")
    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = int(time.time())

    def get_resources(version):
        return [
            {
                "agentname": "agent2",
                "uri": "localhost",
                "autostart": "true",
                "id": "test::AgentConfig[agent1,agentname=agent2],v=%d" % version,
                "send_event": False,
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
    )
    assert result.code == 200

    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    assert (
        "agent2"
        in (
            await client.get_setting(tid=environment, id=data.AUTOSTART_AGENT_MAP)
        ).result["value"]
    )
    await agent.stop()


@pytest.mark.asyncio
async def test_format_token_in_logline(
    server_multi,
    agent_multi,
    client_multi,
    environment_multi,
    resource_container,
    caplog,
):
    """Deploy a resource that logs a line that after formatting on the agent contains an invalid formatting character.
    """
    version = 1
    resource_container.Provider.set("agent1", "key1", "incorrect_value")

    resource = {
        "key": "key1",
        "value": "Test value %T",
        "id": "test::Resource[agent1,key=key1],v=%d" % version,
        "send_event": False,
        "purged": False,
        "requires": [],
    }

    result = await client_multi.put_version(
        tid=environment_multi,
        version=version,
        resources=[resource],
        unknowns=[],
        version_info={},
    )

    assert result.code == 200

    # do a deploy
    result = await client_multi.release_version(
        environment_multi, version, True, const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    result = await client_multi.get_version(environment_multi, version)
    assert result.code == 200
    await _wait_until_deployment_finishes(client_multi, environment_multi, version)

    result = await client_multi.get_version(environment_multi, version)
    assert result.result["model"]["done"] == 1

    log_string = "Set key '%(key)s' to value '%(value)s'" % dict(
        key=resource["key"], value=resource["value"]
    )
    assert log_string in caplog.text


@pytest.mark.asyncio
async def test_1016_cache_invalidation(
    server, agent, client, environment, resource_container, no_agent_backoff, caplog
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
            "purged": False,
            "requires": [],
        }

        result = await client.put_version(
            tid=environment,
            version=version,
            resources=[resource],
            unknowns=[],
            version_info={},
        )

        assert result.code == 200

    ai = agent._instances["agent1"]

    version = 1
    await make_version(version)

    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_incremental_deploy
    )
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    await _wait_until_deployment_finishes(client, environment, version)

    await ai.get_latest_version_for_agent(
        reason="test deploy", incremental_deploy=True, is_repair_run=False
    )

    await asyncio.gather(*(e.future for e in ai._nq.generation.values()))

    version = 2
    await make_version(version, "b")

    # do a deploy
    result = await client.release_version(
        environment, version, True, const.AgentTriggerMethod.push_incremental_deploy
    )
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    await _wait_until_deployment_finishes(client, environment, version)

    # first 1 full fetch
    idx1 = log_index(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.DEBUG,
        "Pulled 1 resources because call to trigger_update",
    )
    # then empty increment
    idx2 = log_index(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.DEBUG,
        "Pulled 0 resources because test deploy",
        idx1,
    )
    # then non-empty increment deploy
    log_index(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.DEBUG,
        "Pulled 1 resources because call to trigger_update",
        idx2,
    )


@pytest.mark.asyncio
async def test_agent_lockout(resource_container, environment, server, client):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    version = int(time.time())

    resource = {
        "key": "key1",
        "value": "Test value %T",
        "id": "test::Resource[agent1,key=key1],v=%d" % version,
        "send_event": False,
        "purged": False,
        "requires": [],
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[resource],
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    agent = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    agent2 = Agent(
        hostname="node1",
        environment=environment,
        agent_map={"agent1": "localhost"},
        code_loader=False,
    )
    agent2.add_end_point_name("agent1")
    await agent2.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 2, 10)

    assert agent._instances["agent1"].is_enabled()
    assert not agent2._instances["agent1"].is_enabled()

    result = (
        await agent2._instances["agent1"]
        .get_client()
        .get_resources_for_agent(tid=environment, agent="agent1")
    )
    assert result.code == 409

    await agent.stop()
    await agent2.stop()
