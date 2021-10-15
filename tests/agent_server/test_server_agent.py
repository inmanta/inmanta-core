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
import logging
import time
import uuid
from itertools import groupby
from typing import Any, Dict, List, Optional, Tuple

import psutil
import pytest
from psutil import NoSuchProcess, Process

from agent_server.conftest import ResourceContainer, _deploy_resources, get_agent, wait_for_n_deployed_resources
from inmanta import agent, config, const, data, execute
from inmanta.agent import config as agent_config
from inmanta.agent.agent import Agent
from inmanta.ast import CompilerException
from inmanta.config import Config
from inmanta.const import AgentAction, AgentStatus, ParameterSource, ResourceState
from inmanta.data import ENVIRONMENT_AGENT_TRIGGER_METHOD
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_AUTOSTARTED_AGENT_MANAGER, SLICE_PARAM, SLICE_SESSION_MANAGER
from inmanta.server.bootloader import InmantaBootloader
from inmanta.util import get_compiler_version
from utils import (
    UNKWN,
    ClientHelper,
    _wait_until_deployment_finishes,
    assert_equal_ish,
    log_contains,
    log_index,
    retry_limited,
    wait_until_logs_are_available,
)

logger = logging.getLogger("inmanta.test.server_agent")


@pytest.mark.asyncio(timeout=150)
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


@pytest.mark.asyncio(timeout=100)
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
            "requires": ["test::Resource[agent2,key=key1],v=%d" % version, "test::Resource[agent2,key=key2],v=%d" % version],
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


@pytest.mark.asyncio(timeout=30)
async def test_server_restart(
    resource_container, server, agent, environment, clienthelper, postgres_db, client, no_agent_backoff
):
    """
    Test if agent reconnects correctly after server restart
    """
    resource_container.Provider.reset()
    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    await server.stop()
    ibl = InmantaBootloader()
    server = ibl.restserver
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

    await agent.stop()
    await ibl.stop()


@pytest.mark.asyncio(timeout=30)
async def test_spontaneous_deploy(
    resource_container, server, client, environment, clienthelper, no_agent_backoff, async_finalizer
):
    """
    dryrun and deploy a configuration model
    """
    resource_container.Provider.reset()

    env_id = environment

    Config.set("config", "agent-deploy-interval", "2")
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


@pytest.mark.asyncio(timeout=30)
async def test_spontaneous_repair(
    resource_container, environment, client, clienthelper, no_agent_backoff, async_finalizer, server
):
    """
    dryrun and deploy a configuration model
    """
    resource_container.Provider.reset()

    env_id = environment

    Config.set("config", "agent-repair-interval", "2")
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
            raise Exception("Timeout occured while waiting for repair run")
        await asyncio.sleep(0.1)

    await verify_deployment_result()


@pytest.mark.asyncio(timeout=30)
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


@pytest.mark.asyncio
async def test_dual_agent(resource_container, server, client, clienthelper, environment, no_agent_backoff, async_finalizer):
    """
    dryrun and deploy a configuration model
    """
    resource_container.Provider.reset()
    myagent = agent.Agent(
        hostname="node1", environment=environment, agent_map={"agent1": "localhost", "agent2": "localhost"}, code_loader=False
    )
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_unkown_parameters(resource_container, environment, client, server, clienthelper, agent, no_agent_backoff):
    """
    Test retrieving facts from the agent
    """
    resource_container.Provider.reset()
    await client.set_setting(environment, data.SERVER_COMPILE, False)

    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{"key": "key", "value": "value", "id": resource_id, "requires": [], "purged": False, "send_event": False}]

    unknowns = [{"resource": resource_id_wov, "parameter": "length", "source": "fact"}]
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

    await server.get_slice(SLICE_PARAM).renew_expired_facts()

    env_id = uuid.UUID(environment)
    params = await data.Parameter.get_list(environment=env_id, resource_id=resource_id_wov)
    while len(params) < 3:
        params = await data.Parameter.get_list(environment=env_id, resource_id=resource_id_wov)
        await asyncio.sleep(0.1)

    result = await client.get_param(env_id, "length", resource_id_wov)
    assert result.code == 200


@pytest.mark.asyncio()
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
            "requires": ["test::Resource[agent1,key=key4],v=%d" % version, "test::Fail[agent1,key=key],v=%d" % version],
            "purged": False,
            "send_event": False,
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


@pytest.mark.asyncio(timeout=15)
async def test_wait(resource_container, client, clienthelper, environment, server, no_agent_backoff, async_finalizer):
    """
    If this test fail due to timeout,
    this is probably due to the mechanism in the agent that prevents pulling resources in very rapid succession.

    If the test server is slow, a get_resources call takes a long time,
    this makes the back-off longer

    this test deploys two models in rapid successions, if the server is slow, this may fail due to the back-off
    """
    resource_container.Provider.reset()

    env_id = environment

    # setup agent
    agent = Agent(hostname="node1", environment=env_id, agent_map={"agent1": "localhost"}, code_loader=False, poolsize=10)
    await agent.add_end_point_name("agent1")
    await agent.start()
    async_finalizer(agent.stop)

    # wait for agent
    await retry_limited(lambda: len(server.get_slice(SLICE_SESSION_MANAGER)._sessions) == 1, 10)

    # set the deploy environment
    resource_container.Provider.set("agent1", "key", "value")

    async def make_version():
        version = await clienthelper.get_version()

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
                "requires": ["test::Resource[agent1,key=key4],v=%d" % version, "test::Wait[agent1,key=key],v=%d" % version],
                "purged": False,
                "send_event": False,
            },
        ]
        return version, resources

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

    await wait_for_n_deployed_resources(client, env_id, version1, n=2)

    result = await client.get_version(environment, version1)
    assert result.code == 200
    assert result.result["model"]["done"] == 2

    logger.info("first version, 2 resources deployed")

    version2, resources = await make_version()
    result = await client.put_version(
        tid=env_id, version=version2, resources=resources, unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    logger.info("second version pushed %f", time.time())

    # deploy and wait until done
    result = await client.release_version(env_id, version2, True, const.AgentTriggerMethod.push_full_deploy)
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

    assert states["test::Wait[agent1,key=key],v=%d" % version1] == const.ResourceState.deployed.name
    assert states["test::Resource[agent1,key=key2],v=%d" % version1] == const.ResourceState.available.name
    assert states["test::Resource[agent1,key=key3],v=%d" % version1] == const.ResourceState.deployed.name
    assert states["test::Resource[agent1,key=key4],v=%d" % version1] == const.ResourceState.deployed.name
    assert states["test::Resource[agent1,key=key5],v=%d" % version1] == const.ResourceState.available.name


@pytest.mark.asyncio(timeout=15)
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
        poolsize=1,
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
                        "requires": ["test::Resource[%s,key=key3],v=%d" % (agent, version)],
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


@pytest.mark.asyncio
async def test_cross_agent_deps(resource_container, server, client, environment, clienthelper, no_agent_backoff):
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
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    agent2 = Agent(hostname="node2", environment=env_id, agent_map={"agent2": "localhost"}, code_loader=False)
    await agent2.add_end_point_name("agent2")
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
            "requires": ["test::Wait[agent 1,key=key2],v=%d" % version, "test::Resource[agent2,key=key3],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Wait[agent 1,key=key2],v=%d" % version,
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

    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["result"] == const.VersionState.success.name

    assert resource_container.Provider.isset("agent 1", "key1")
    assert resource_container.Provider.get("agent 1", "key1") == "value1"
    assert resource_container.Provider.get("agent 1", "key2") == "value2"
    assert resource_container.Provider.get("agent2", "key3") == "value3"

    await agent.stop()
    await agent2.stop()


@pytest.mark.parametrize(
    "agent_trigger_method, read_resource1, change_resource1, read_resource2, change_resource2",
    [(const.AgentTriggerMethod.push_incremental_deploy, 1, 1, 2, 2), (const.AgentTriggerMethod.push_full_deploy, 2, 1, 2, 2)],
)
@pytest.mark.asyncio
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

        await clienthelper.put_version_simple(resources, version)

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


@pytest.mark.asyncio(timeout=15)
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
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        }
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
    assert result.result["model"]["total"] == 1
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


def ps_diff_inmanta_agent_processes(original: List[psutil.Process], current_process: psutil.Process, diff: int = 0) -> None:
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
        pre:%s
        post:%s""" % (
        original,
        current,
    )


@pytest.mark.asyncio(timeout=15)
async def test_autostart_mapping(server, client, clienthelper, resource_container, environment, no_agent_backoff):
    """
    Test whether an autostarted agent updates its agent-map correctly when the autostart_agent_map is updated on the server.

    The handler code in the resource_container is not available to the autostarted agent. When the agent loads these
    resources it will mark them as unavailable. There is only one agent started when deploying is checked.
    """
    env_uuid = uuid.UUID(environment)
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)
    current_process = psutil.Process()
    children_pre = current_process.children(recursive=True)
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

    await clienthelper.put_version_simple(resources, version)

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

    async def assert_session_state(expected_agent_states: Dict[str, AgentStatus], expected_agent_instances: List[str]) -> None:
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
    await server.stop()

    current_process = psutil.Process()
    children = current_process.children(recursive=True)

    newchildren = set(children) - set(children_pre)

    assert len(newchildren) == 0, newchildren


@pytest.mark.asyncio
async def test_autostart_mapping_update_uri(server, client, environment, async_finalizer, caplog):
    caplog.set_level(logging.INFO)
    agent_config.use_autostart_agent_map.set("true")
    env_uuid = uuid.UUID(environment)
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)
    agent_name = "internal"
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_MAP, {agent_name: ""})
    assert result.code == 200

    # Start agent
    a = agent.Agent(hostname=agent_name, environment=env_uuid, code_loader=False)
    await a.start()
    async_finalizer(a.stop)

    # Wait until agent is up
    await retry_limited(lambda: (env_uuid, agent_name) in agent_manager.tid_endpoint_to_session, 10)
    instances = await data.AgentInstance.get_list()
    assert len(instances) == 1

    # Update agentmap
    caplog.clear()
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_MAP, {agent_name: "localhost"})
    assert result.code == 200

    await retry_limited(lambda: f"Updating the URI of the endpoint {agent_name} from  to localhost" in caplog.text, 10)

    # Pause agent
    result = await client.agent_action(tid=env_uuid, name="internal", action=const.AgentAction.pause.value)
    assert result.code == 200

    # Update agentmap when internal agent is paused
    caplog.clear()
    result = await client.set_setting(environment, data.AUTOSTART_AGENT_MAP, {agent_name: ""})
    assert result.code == 200

    await retry_limited(lambda: f"Updating the URI of the endpoint {agent_name} from localhost to " in caplog.text, 10)


@pytest.mark.asyncio(timeout=15)
async def test_autostart_clear_environment(server, client, resource_container, environment, no_agent_backoff):
    """
    Test clearing an environment with autostarted agents. After clearing, autostart should still work

    The handler code in the resource_container is not available to the autostarted agent. When the agent loads these
    resources it will mark them as unavailable. This will make the deploy fail.
    """
    resource_container.Provider.reset()
    current_process = psutil.Process()
    inmanta_agent_child_processes: List[psutil.Process] = _get_inmanta_agent_child_processes(current_process)
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

    # clear environment
    await client.clear_environment(environment)

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


def _get_inmanta_agent_child_processes(parent_process: psutil.Process) -> List[psutil.Process]:
    return [p for p in parent_process.children(recursive=True) if "inmanta.app" in p.cmdline() and "agent" in p.cmdline()]


@pytest.mark.asyncio(timeout=15)
async def test_stop_autostarted_agents_on_environment_removal(server, client, resource_container, no_agent_backoff):
    current_process = psutil.Process()
    inmanta_agent_child_processes: List[psutil.Process] = _get_inmanta_agent_child_processes(current_process)
    resource_container.Provider.reset()
    (project_id, env_id) = await setup_environment_with_agent(client, "proj")

    # One autostarted agent should running as a subprocess
    ps_diff_inmanta_agent_processes(original=inmanta_agent_child_processes, current_process=current_process, diff=1)

    result = await client.delete_environment(id=env_id)
    assert result.code == 200

    # The autostarted agent should be terminated when its environment is deleted.
    ps_diff_inmanta_agent_processes(original=inmanta_agent_child_processes, current_process=current_process, diff=0)


@pytest.mark.asyncio(timeout=15)
async def test_stop_autostarted_agents_on_project_removal(server, client, resource_container, no_agent_backoff):
    current_process = psutil.Process()
    inmanta_agent_child_processes: List[psutil.Process] = _get_inmanta_agent_child_processes(current_process)
    resource_container.Provider.reset()
    (project1_id, env1_id) = await setup_environment_with_agent(client, "proj1")
    await setup_environment_with_agent(client, "proj2")

    # Two autostarted agents should be running (one in proj1 and one in proj2).
    ps_diff_inmanta_agent_processes(original=inmanta_agent_child_processes, current_process=current_process, diff=2)

    result = await client.delete_project(id=project1_id)
    assert result.code == 200

    # The autostarted agent of proj1 should be terminated when its project is deleted
    # The autostarted agent of proj2 keep running
    ps_diff_inmanta_agent_processes(original=inmanta_agent_child_processes, current_process=current_process, diff=1)


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


class ResourceProvider(object):
    def __init__(self, index, name, producer, state=None):
        self.name = name
        self.producer = producer
        self.state = state
        self.index = index

    def get_resource(
        self, resource_container: ResourceContainer, agent: str, key: str, version: str, requires: List[str]
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

    events = resource_container.Provider.getevents("agent1", "key3")
    expected_events = doevents[dep_state.index][self_state.index]
    if expected_events == 0:
        assert len(events) == 0
    else:
        assert len(events) == 1
        assert len(events[0]) == expected_events


@pytest.mark.asyncio
async def test_deploy_and_events_failed(server, client, clienthelper, environment, resource_container, no_agent_backoff):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = await clienthelper.get_version()

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
    await agent.stop()


dep_states_reload = [
    ResourceProvider(0, "skip", lambda p, a, k: p.set_skip(a, k, 1)),
    ResourceProvider(0, "fail", lambda p, a, k: p.set_fail(a, k, 1)),
    ResourceProvider(0, "nochange", lambda p, a, k: p.set(a, k, "value1")),
    ResourceProvider(1, "changed", lambda p, a, k: None),
]


@pytest.mark.parametrize("dep_state", dep_states_reload, ids=lambda x: x.name)
@pytest.mark.asyncio(timeout=5000)
async def test_reload(server, client, clienthelper, environment, resource_container, dep_state, no_agent_backoff):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    resource_container.Provider.reset()
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await agent.add_end_point_name("agent1")
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
    await agent.stop()


@pytest.mark.asyncio(timeout=30)
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
    await myagent_instance.get_latest_version_for_agent(reason="Deploy", incremental_deploy=True, is_repair_run=False)
    # key3: Readcount=2; writecount=1
    await myagent_instance.get_latest_version_for_agent(reason="Repair", incremental_deploy=False, is_repair_run=True)

    def wait_condition():
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


@pytest.mark.asyncio(timeout=debug_timeout * 2)
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

    version1 = await clienthelper.get_version()
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(reason="Deploy 1", incremental_deploy=True, is_repair_run=False)
    await resource_container.wait_for_done_with_waiters(client, environment, version1, timeout=debug_timeout)

    # counts:  read/write
    # key1: 1/1
    # key3: 1/1

    # Interrupt repair with deploy
    # Repair
    await myagent_instance.get_latest_version_for_agent(reason="Repair", incremental_deploy=False, is_repair_run=True)

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
    await myagent_instance.get_latest_version_for_agent(reason="Deploy 2", incremental_deploy=True, is_repair_run=False)
    print("Deploy")
    await resource_container.wait_for_done_with_waiters(client, environment, version2, timeout=debug_timeout)

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

    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Interrupting run 'Repair' for 'Deploy 2'")
    log_contains(
        caplog, "inmanta.agent.agent.agent1", logging.INFO, "for reason: Restarting run 'Repair', interrupted for 'Deploy 2'"
    )
    log_contains(
        caplog, "inmanta.agent.agent.agent1", logging.INFO, "Resuming run 'Restarting run 'Repair', interrupted for 'Deploy 2''"
    )


@pytest.mark.asyncio
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
    await myagent_instance.get_latest_version_for_agent(reason="Deploy", incremental_deploy=True, is_repair_run=False)
    await resource_container.wait_for_done_with_waiters(client, environment, version)

    # Interrupt repair with a repair
    await myagent_instance.get_latest_version_for_agent(reason="Repair 1", incremental_deploy=False, is_repair_run=True)
    await myagent_instance.get_latest_version_for_agent(reason="Repair 2", incremental_deploy=False, is_repair_run=True)

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

    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Terminating run 'Repair 1' for 'Repair 2'")


@pytest.mark.asyncio(timeout=30)
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

    version1 = await clienthelper.get_version()
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(reason="Deploy 1", incremental_deploy=True, is_repair_run=False)

    # Make sure that resource key1 is fully deployed before triggering the interrupt
    timeout_time = time.time() + 10
    while (await client.get_version(environment, version1)).result["model"]["done"] < 1 and time.time() < timeout_time:
        await asyncio.sleep(0.1)

    version2 = await clienthelper.get_version()
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, False)
    await myagent_instance.get_latest_version_for_agent(reason="Deploy 2", incremental_deploy=True, is_repair_run=False)

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


@pytest.mark.asyncio(timeout=30)
async def test_s_full_deploy_interrupts_incremental_deploy(
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

    version1 = await clienthelper.get_version()
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(reason="Initial Deploy", incremental_deploy=True, is_repair_run=False)

    # Make sure that resource key1 is fully deployed before triggering the interrupt
    timeout_time = time.time() + 10
    while (await client.get_version(environment, version1)).result["model"]["done"] < 1 and time.time() < timeout_time:
        await asyncio.sleep(0.1)

    # cache has 1 version in flight
    assert len(myagent_instance._cache.counterforVersion) == 1

    version2 = await clienthelper.get_version()
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, False)
    await myagent_instance.get_latest_version_for_agent(reason="Second Deploy", incremental_deploy=False, is_repair_run=False)

    await resource_container.wait_for_done_with_waiters(client, environment, version2)

    # cache has no versions in flight
    # for issue #1883
    assert not myagent_instance._cache.counterforVersion

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

    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Terminating run 'Initial Deploy' for 'Second Deploy'")


@pytest.mark.asyncio(timeout=30)
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

    version1 = await clienthelper.get_version()
    resources_version_1 = get_resources(version1, "value2")

    # Initial deploy
    await _deploy_resources(client, environment, resources_version_1, version1, False)
    await myagent_instance.get_latest_version_for_agent(reason="Initial Deploy", incremental_deploy=False, is_repair_run=False)

    # Make sure that resource key1 is fully deployed before triggering the interrupt
    timeout_time = time.time() + 10
    while (await client.get_version(environment, version1)).result["model"]["done"] < 1 and time.time() < timeout_time:
        await asyncio.sleep(0.1)

    version2 = await clienthelper.get_version()
    resources_version_2 = get_resources(version2, "value3")
    await _deploy_resources(client, environment, resources_version_2, version2, False)
    await myagent_instance.get_latest_version_for_agent(reason="Second Deploy", incremental_deploy=True, is_repair_run=False)

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

    log_contains(caplog, "inmanta.agent.agent.agent1", logging.INFO, "Terminating run 'Initial Deploy' for 'Second Deploy'")


@pytest.mark.asyncio
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

    resources = [{"key": "key", "value": "value", "id": resource_id, "requires": [], "purged": False, "send_event": False}]

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


@pytest.mark.asyncio
async def test_bad_post_events(resource_container, environment, server, agent, client, clienthelper, caplog, no_agent_backoff):
    """
    Send and receive events within one agent
    """
    caplog.set_level(logging.ERROR)

    version = await clienthelper.get_version()

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

    await clienthelper.put_version_simple(resources, version)

    caplog.clear()
    # do a deploy
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version)

    events = resource_container.Provider.getevents("agent1", "key1")
    assert len(events) == 1
    for res_id, res in events[0].items():
        assert res_id.agent_name == "agent1"
        assert res_id.attribute_value == "key2"
        assert res["status"] == const.ResourceState.deployed
        assert res["change"] == const.Change.created

    assert "An error occurred after deployment of test::BadPost[agent1,key=key1]" in caplog.text
    caplog.clear()

    # Nothing is reported as events don't have pre and post


@pytest.mark.asyncio
async def test_inprogress(resource_container, server, client, clienthelper, environment, no_agent_backoff):
    """
    Test retrieving facts from the agent
    """
    agent = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await agent.add_end_point_name("agent1")
    await agent.start()
    await retry_limited(lambda: len(server.get_slice(SLICE_SESSION_MANAGER)._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::Wait[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{"key": "key", "value": "value", "id": resource_id, "requires": [], "purged": False, "send_event": False}]

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

    await agent.stop()


@pytest.mark.asyncio
async def test_eventprocessing(resource_container, server, client, clienthelper, environment, agent, no_agent_backoff):
    """
    Test retrieving facts from the agent
    """
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

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

    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    async def in_progress():
        result = await client.get_version(environment, version)
        assert result.code == 200
        status = sorted([res["status"] for res in result.result["resources"]])
        return status == ["deployed", "processing_events"]

    await retry_limited(in_progress, 1)

    await resource_container.wait_for_done_with_waiters(client, environment, version)


@pytest.mark.parametrize("use_agent_trigger_method_setting", [(True,), (False)])
@pytest.mark.asyncio
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


@pytest.mark.parametrize("push, agent_trigger_method", [(True, None), (True, const.AgentTriggerMethod.push_full_deploy)])
@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_format_token_in_logline(server, agent, client, environment, resource_container, caplog, no_agent_backoff):
    """Deploy a resource that logs a line that after formatting on the agent contains an invalid formatting character."""
    version = (await client.reserve_version(environment)).result["data"]
    resource_container.Provider.set("agent1", "key1", "incorrect_value")

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


@pytest.mark.asyncio
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

    await ai.get_latest_version_for_agent(reason="test deploy", incremental_deploy=True, is_repair_run=False)

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


@pytest.mark.asyncio
async def test_agent_lockout(resource_container, environment, server, client, clienthelper, async_finalizer, no_agent_backoff):
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    version = await clienthelper.get_version()

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


@pytest.mark.asyncio
async def test_deploy_no_code(resource_container, client, clienthelper, environment, autostarted_agent):
    """
    Test retrieving facts from the agent when there is no handler code available. We use an autostarted agent, these
    do not have access to the handler code for the resource_container.

    Expected logs:
        * Deploy action: Start run/End run
        * Deploy action: Failed to load handler code or install handler code
        * Pull action
        * Store action
    """
    resource_container.Provider.reset()
    resource_container.Provider.set("agent1", "key", "value")

    version = await clienthelper.get_version()

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{"key": "key", "value": "value", "id": resource_id, "requires": [], "purged": False, "send_event": False}]

    await clienthelper.put_version_simple(resources, version)

    await _wait_until_deployment_finishes(client, environment, version)
    # The resource state and its logs are not set atomically. This call prevents a race condition.
    await wait_until_logs_are_available(client, environment, resource_id, expect_nr_of_logs=4)

    response = await client.get_resource(environment, resource_id, logs=True)
    assert response.code == 200
    result = response.result

    assert result["resource"]["status"] == "unavailable"

    assert result["logs"][0]["action"] == "deploy"
    assert result["logs"][0]["status"] == "unavailable"
    assert "Start run for " in result["logs"][0]["messages"][0]["msg"]

    assert result["logs"][1]["action"] == "deploy"
    assert result["logs"][1]["status"] == "unavailable"
    assert "Failed to load handler code " in result["logs"][1]["messages"][0]["msg"]


@pytest.mark.asyncio
async def test_issue_1662(resource_container, server, client, clienthelper, environment, monkeypatch, request):
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)
    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)

    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    a = Agent(hostname="node1", environment=environment, agent_map={"agent1": "localhost"}, code_loader=False)
    await a.add_end_point_name("agent1")
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
            "purged": False,
            "requires": [],
            "purge_on_delete": False,
        },
    ]

    await clienthelper.put_version_simple(resources, version)
    result = await client.release_version(environment, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200

    await _wait_until_deployment_finishes(client, environment, version, timeout=10)


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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

    def _get_resources(agent_name: str) -> List[Dict]:
        return [
            {
                "key": "key1",
                "value": "value1",
                "id": f"test::Resource[{agent_name},key=key1],v={version}",
                "send_event": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "value2",
                "id": f"test::Wait[{agent_name},key=key2],v={version}",
                "send_event": False,
                "purged": False,
                "requires": [f"test::Resource[{agent_name},key=key1],v={version}"],
            },
            {
                "key": "key3",
                "value": "value3",
                "id": f"test::Resource[{agent_name},key=key3],v={version}",
                "send_event": False,
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


@pytest.mark.asyncio
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
            "purged": False,
            "requires": [],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": f"test::Wait[agent1,key=key2],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key1],v={version}"],
        },
        {
            "key": "key3",
            "value": "value3",
            "id": f"test::Wait[agent1,key=key3],v={version}",
            "send_event": False,
            "purged": False,
            "requires": [f"test::Resource[agent1,key=key2],v={version}"],
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


@pytest.mark.asyncio
async def test_set_fact_in_handler(server, client, environment, agent, clienthelper, resource_container, no_agent_backoff):
    """
    Test whether facts set in the handler via the ctx.set_fact() method arrive on the server.
    """

    def get_resources(version: str, params: List[data.Parameter]) -> List[Dict[str, Any]]:
        return [
            {
                "key": param.name,
                "value": param.value,
                "metadata": param.metadata,
                "id": f"{param.resource_id},v={version}",
                "send_event": False,
                "purged": False,
                "purge_on_delete": False,
                "requires": [],
            }
            for param in params
        ]

    def compare_params(actual_params: List[data.Parameter], expected_params: List[data.Parameter]) -> None:
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
    )
    param2 = data.Parameter(
        name="key2",
        value="value2",
        environment=uuid.UUID(environment),
        resource_id="test::SetFact[agent1,key=key2]",
        source=ParameterSource.fact.value,
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
    )
    param4 = data.Parameter(
        name="returned_fact_key2",
        value="test",
        environment=uuid.UUID(environment),
        resource_id="test::SetFact[agent1,key=key2]",
        source=ParameterSource.fact.value,
    )

    params = await data.Parameter.get_list()
    compare_params(params, [param1, param2, param3, param4])
