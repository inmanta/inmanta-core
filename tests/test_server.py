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
import base64
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from functools import partial

import pytest
from dateutil import parser
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import const, data, loader, resources
from inmanta.agent import handler
from inmanta.agent.agent import Agent
from inmanta.const import ParameterSource
from inmanta.data.model import AttributeStateChange, LogLine
from inmanta.export import upload_code
from inmanta.protocol import Client
from inmanta.server import (
    SLICE_AGENT_MANAGER,
    SLICE_AUTOSTARTED_AGENT_MANAGER,
    SLICE_ORCHESTRATION,
    SLICE_RESOURCE,
    SLICE_SERVER,
    SLICE_SESSION_MANAGER,
)
from inmanta.server import config as opt
from inmanta.server.bootloader import InmantaBootloader
from inmanta.util import get_compiler_version
from utils import log_contains, log_doesnt_contain, retry_limited

LOGGER = logging.getLogger(__name__)


@pytest.mark.slowtest
async def test_autostart(server, client, environment, caplog):
    """
    Test auto start of agent
    An agent is started and then killed to simulate unexpected failure
    When the second agent is started for the same environment, the first is terminated in a controlled manner
    """
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "iaas_agent": "", "iaas_agentx": ""})

    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    autostarted_agentmanager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
    sessionendpoint = server.get_slice(SLICE_SESSION_MANAGER)

    await agentmanager.ensure_agent_registered(env, "iaas_agent")
    await agentmanager.ensure_agent_registered(env, "iaas_agentx")

    res = await autostarted_agentmanager._ensure_agents(env, ["iaas_agent"])
    assert res

    await retry_limited(lambda: len(sessionendpoint._sessions) == 1, 20)
    assert len(sessionendpoint._sessions) == 1
    res = await autostarted_agentmanager._ensure_agents(env, ["iaas_agent"])
    assert not res
    assert len(sessionendpoint._sessions) == 1

    LOGGER.warning("Killing agent")
    autostarted_agentmanager._agent_procs[env.id].terminate()
    await autostarted_agentmanager._agent_procs[env.id].wait()
    await retry_limited(lambda: len(sessionendpoint._sessions) == 0, 20)
    # Prevent race condition
    await retry_limited(lambda: len(agentmanager.tid_endpoint_to_session) == 0, 20)
    res = await autostarted_agentmanager._ensure_agents(env, ["iaas_agent"])
    assert res
    await retry_limited(lambda: len(sessionendpoint._sessions) == 1, 3)
    assert len(sessionendpoint._sessions) == 1

    # second agent for same env
    res = await autostarted_agentmanager._ensure_agents(env, ["iaas_agentx"])
    assert res
    await retry_limited(lambda: len(sessionendpoint._sessions) == 1, 20)
    assert len(sessionendpoint._sessions) == 1

    # Test stopping all agents
    await autostarted_agentmanager.stop_agents(env)
    assert len(sessionendpoint._sessions) == 0
    assert len(autostarted_agentmanager._agent_procs) == 0

    log_doesnt_contain(caplog, "inmanta.config", logging.WARNING, "rest_transport not defined")
    log_doesnt_contain(caplog, "inmanta.server.agentmanager", logging.WARNING, "Agent processes did not close in time")


@pytest.mark.slowtest
async def test_autostart_dual_env(client, server):
    """
    Test auto start of agent
    """
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
    sessionendpoint = server.get_slice(SLICE_SESSION_MANAGER)

    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    result = await client.create_environment(project_id=project_id, name="devx")
    env_id2 = result.result["environment"]["id"]

    env = await data.Environment.get_by_id(uuid.UUID(env_id))
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "iaas_agent": ""})

    env2 = await data.Environment.get_by_id(uuid.UUID(env_id2))
    await env2.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "iaas_agent": ""})

    await agentmanager.ensure_agent_registered(env, "iaas_agent")
    await agentmanager.ensure_agent_registered(env2, "iaas_agent")

    res = await autostarted_agent_manager._ensure_agents(env, ["iaas_agent"])
    assert res
    await retry_limited(lambda: len(sessionendpoint._sessions) == 1, 20)
    assert len(sessionendpoint._sessions) == 1

    res = await autostarted_agent_manager._ensure_agents(env2, ["iaas_agent"])
    assert res
    await retry_limited(lambda: len(sessionendpoint._sessions) == 2, 20)
    assert len(sessionendpoint._sessions) == 2


@pytest.mark.slowtest
async def test_autostart_batched(client, server, environment):
    """
    Test auto start of agent
    """
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "iaas_agentx": ""})

    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
    sessionendpoint = server.get_slice(SLICE_SESSION_MANAGER)

    await agentmanager.ensure_agent_registered(env, "internal")
    await agentmanager.ensure_agent_registered(env, "iaas_agentx")

    res = await autostarted_agent_manager._ensure_agents(env, ["internal", "iaas_agentx"])
    assert res
    await retry_limited(lambda: len(sessionendpoint._sessions) == 1, 20)
    assert len(sessionendpoint._sessions) == 1
    res = await autostarted_agent_manager._ensure_agents(env, ["internal"])
    assert not res
    assert len(sessionendpoint._sessions) == 1

    res = await autostarted_agent_manager._ensure_agents(env, ["internal", "iaas_agentx"])
    assert not res
    assert len(sessionendpoint._sessions) == 1

    LOGGER.warning("Killing agent")
    autostarted_agent_manager._agent_procs[env.id].terminate()
    await autostarted_agent_manager._agent_procs[env.id].wait()
    await retry_limited(lambda: len(sessionendpoint._sessions) == 0, 20)
    # Prevent race condition
    await retry_limited(lambda: len(agentmanager.tid_endpoint_to_session) == 0, 20)
    res = await autostarted_agent_manager._ensure_agents(env, ["internal", "iaas_agentx"])
    assert res
    await retry_limited(lambda: len(sessionendpoint._sessions) == 1, 3)
    assert len(sessionendpoint._sessions) == 1


@pytest.mark.parametrize(
    "n_versions_to_keep, n_versions_to_create",
    [
        (2, 4),
        (4, 2),
        (2, 2),
    ],
)
async def test_create_too_many_versions(client, server, n_versions_to_keep, n_versions_to_create):
    """
    - set AVAILABLE_VERSIONS_TO_KEEP environment setting to <n_versions_to_keep>
    - create <n_versions_to_create> versions
    - check the actual number of versions before and after cleanup
    """

    # Create project
    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    # Create environment
    result = await client.create_environment(project_id=project_id, name="env_1")
    env_1_id = result.result["environment"]["id"]
    result = await client.set_setting(tid=env_1_id, id=data.AVAILABLE_VERSIONS_TO_KEEP, value=n_versions_to_keep)
    assert result.code == 200

    # Check value was set
    result = await client.get_setting(tid=env_1_id, id=data.AVAILABLE_VERSIONS_TO_KEEP)
    assert result.code == 200
    assert result.result["value"] == n_versions_to_keep

    for _ in range(n_versions_to_create):
        version = (await client.reserve_version(env_1_id)).result["data"]

        res = await client.put_version(
            tid=env_1_id, version=version, resources=[], unknowns=[], version_info={}, compiler_version=get_compiler_version()
        )
        assert res.code == 200

    versions = await client.list_versions(tid=env_1_id)
    assert versions.result["count"] == n_versions_to_create

    await server.get_slice(SLICE_ORCHESTRATION)._purge_versions()

    versions = await client.list_versions(tid=env_1_id)
    assert versions.result["count"] == min(n_versions_to_keep, n_versions_to_create)


async def test_n_versions_env_setting_scope(client, server):
    """
    The AVAILABLE_VERSIONS_TO_KEEP environment setting used to be a global config option.
    This test checks that a specific environment setting can be set for each environment
    """

    n_versions_to_keep_env1 = 5
    n_versions_to_keep_env2 = 2

    n_many_versions = n_versions_to_keep_env1 + n_versions_to_keep_env2

    # Create project
    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    # Create environments
    result = await client.create_environment(project_id=project_id, name="env_1")
    env_1_id = result.result["environment"]["id"]
    result = await client.set_setting(tid=env_1_id, id=data.AVAILABLE_VERSIONS_TO_KEEP, value=n_versions_to_keep_env1)
    assert result.code == 200

    result = await client.create_environment(project_id=project_id, name="env_2")
    env_2_id = result.result["environment"]["id"]
    result = await client.set_setting(tid=env_2_id, id=data.AVAILABLE_VERSIONS_TO_KEEP, value=n_versions_to_keep_env2)
    assert result.code == 200

    # Create a lot of versions in both environments
    for _ in range(n_many_versions):
        env1_version = (await client.reserve_version(env_1_id)).result["data"]
        env2_version = (await client.reserve_version(env_2_id)).result["data"]

        res = await client.put_version(
            tid=env_1_id,
            version=env1_version,
            resources=[],
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert res.code == 200

        res = await client.put_version(
            tid=env_2_id,
            version=env2_version,
            resources=[],
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert res.code == 200

    # Before cleanup we have too many versions in both envs
    versions = await client.list_versions(tid=env_1_id)
    assert versions.result["count"] == n_many_versions

    versions = await client.list_versions(tid=env_2_id)
    assert versions.result["count"] == n_many_versions

    # Cleanup
    await server.get_slice(SLICE_ORCHESTRATION)._purge_versions()

    # After cleanup each env should have its specific number of version
    versions = await client.list_versions(tid=env_1_id)
    assert versions.result["count"] == n_versions_to_keep_env1

    versions = await client.list_versions(tid=env_2_id)
    assert versions.result["count"] == n_versions_to_keep_env2


@pytest.mark.slowtest
async def test_get_resource_for_agent(server_multi, client_multi, environment_multi, async_finalizer):
    """
    Test the server to manage the updates on a model during agent deploy
    """
    agent = Agent("localhost", {"nvblah": "localhost"}, environment=environment_multi, code_loader=False)
    await agent.add_end_point_name("vm1.dev.inmanta.com")
    await agent.add_end_point_name("vm2.dev.inmanta.com")
    async_finalizer(agent.stop)
    await agent.start()
    aclient = agent._client

    version = (await client_multi.reserve_version(environment_multi)).result["data"]

    resources = [
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": "std::File[vm1.dev.inmanta.com,path=/etc/sysconfig/network],v=%d" % version,
            "owner": "root",
            "path": "/etc/sysconfig/network",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "version": version,
        },
        {
            "group": "root",
            "hash": "b4350bef50c3ec3ee532d4a3f9d6daedec3d2aba",
            "id": "std::File[vm2.dev.inmanta.com,path=/etc/motd],v=%d" % version,
            "owner": "root",
            "path": "/etc/motd",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "version": version,
        },
        {
            "group": "root",
            "hash": "3bfcdad9ab7f9d916a954f1a96b28d31d95593e4",
            "id": "std::File[vm1.dev.inmanta.com,path=/etc/hostname],v=%d" % version,
            "owner": "root",
            "path": "/etc/hostname",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "version": version,
        },
        {
            "id": "std::Service[vm1.dev.inmanta.com,name=network],v=%d" % version,
            "name": "network",
            "onboot": True,
            "requires": ["std::File[vm1.dev.inmanta.com,path=/etc/sysconfig/network],v=%d" % version],
            "state": "running",
            "version": version,
        },
    ]

    res = await client_multi.put_version(
        tid=environment_multi,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    result = await client_multi.list_versions(environment_multi)
    assert result.code == 200
    assert result.result["count"] == 1

    result = await client_multi.release_version(environment_multi, version, False)
    assert result.code == 200

    result = await client_multi.get_version(environment_multi, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == "deploying"

    async def wait_for_session() -> bool:
        result = await aclient.get_resources_for_agent(environment_multi, "vm1.dev.inmanta.com")
        return result.code == 200 and len(result.result["resources"]) == 3

    """
    This retry_limited is required to prevent 409 errors in case the agent didn't obtain
    a session yet by the time the get_resources_for_agent API call is made.
    """
    await retry_limited(wait_for_session, 10)

    action_id = uuid.uuid4()
    now = datetime.now()
    result = await aclient.resource_action_update(
        environment_multi,
        ["std::File[vm1.dev.inmanta.com,path=/etc/sysconfig/network],v=%d" % version],
        action_id,
        "deploy",
        now,
        now,
        "deployed",
        [],
        {},
    )

    assert result.code == 200

    result = await client_multi.get_version(environment_multi, version)
    assert result.code == 200
    assert result.result["model"]["done"] == 1

    action_id = uuid.uuid4()
    now = datetime.now()
    result = await aclient.resource_action_update(
        environment_multi,
        ["std::File[vm1.dev.inmanta.com,path=/etc/hostname],v=%d" % version],
        action_id,
        "deploy",
        now,
        now,
        "deployed",
        [],
        {},
    )
    assert result.code == 200

    result = await client_multi.get_version(environment_multi, version)
    assert result.code == 200
    assert result.result["model"]["done"] == 2


async def test_get_environment(client, clienthelper, server, environment):
    for i in range(10):
        version = await clienthelper.get_version()

        resources = []
        for j in range(i):
            resources.append(
                {
                    "group": "root",
                    "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
                    "id": "std::File[vm1.dev.inmanta.com,path=/tmp/file%d],v=%d" % (j, version),
                    "owner": "root",
                    "path": "/tmp/file%d" % j,
                    "permissions": 644,
                    "purged": False,
                    "reload": False,
                    "requires": [],
                    "version": version,
                }
            )

        res = await client.put_version(
            tid=environment,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert res.code == 200

    result = await client.get_environment(environment, versions=5, resources=1)
    assert result.code == 200
    assert len(result.result["environment"]["versions"]) == 5
    assert len(result.result["environment"]["resources"]) == 9


async def test_resource_update(postgresql_client, client, clienthelper, server, environment, async_finalizer):
    """
    Test updating resources and logging
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
    async_finalizer(agent.stop)
    await agent.start()
    aclient = agent._client

    version = await clienthelper.get_version()

    resources = []
    for j in range(10):
        resources.append(
            {
                "group": "root",
                "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
                "id": "std::File[vm1,path=/tmp/file%d],v=%d" % (j, version),
                "owner": "root",
                "path": "/tmp/file%d" % j,
                "permissions": 644,
                "purged": False,
                "reload": False,
                "requires": [],
                "version": version,
            }
        )

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    resource_ids = [x["id"] for x in resources]

    # Start the deploy
    action_id = uuid.uuid4()
    now = datetime.now()
    result = await aclient.resource_action_update(
        environment, resource_ids, action_id, "deploy", now, status=const.ResourceState.deploying
    )
    assert result.code == 200

    # Get the status from a resource
    result = await client.get_resource(tid=environment, id=resource_ids[0], logs=True)
    assert result.code == 200
    logs = {x["action"]: x for x in result.result["logs"]}

    assert "deploy" in logs
    assert logs["deploy"]["finished"] is None
    assert logs["deploy"]["messages"] is None
    assert logs["deploy"]["changes"] is None

    # Send some logs
    result = await aclient.resource_action_update(
        environment,
        resource_ids,
        action_id,
        "deploy",
        status=const.ResourceState.deploying,
        messages=[data.LogLine.log(const.LogLevel.INFO, "Test log %(a)s %(b)s", a="a", b="b")],
    )
    assert result.code == 200

    # Get the status from a resource
    result = await client.get_resource(tid=environment, id=resource_ids[0], logs=True)
    assert result.code == 200
    logs = {x["action"]: x for x in result.result["logs"]}

    assert "deploy" in logs
    assert "messages" in logs["deploy"]
    assert len(logs["deploy"]["messages"]) == 1
    assert logs["deploy"]["messages"][0]["msg"] == "Test log a b"
    assert logs["deploy"]["finished"] is None
    assert logs["deploy"]["changes"] is None

    # Finish the deploy
    now = datetime.now()
    changes = {x: {"owner": {"old": "root", "current": "inmanta"}} for x in resource_ids}
    result = await aclient.resource_action_update(environment, resource_ids, action_id, "deploy", finished=now, changes=changes)
    assert result.code == 400

    result = await aclient.resource_action_update(
        environment, resource_ids, action_id, "deploy", status=const.ResourceState.deployed, finished=now, changes=changes
    )
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["done"] == 10


async def test_clear_environment(client, server, clienthelper, environment):
    """
    Test clearing out an environment
    """
    version = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment, version=version, resources=[], unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    result = await client.get_environment(id=environment, versions=10)
    assert result.code == 200
    assert len(result.result["environment"]["versions"]) == 1

    # trigger multiple compiles and wait for them to complete in order to test cascade deletion of collapsed compiles (#2350)
    result = await client.notify_change_get(id=environment)
    assert result.code == 200
    result = await client.notify_change_get(id=environment)
    assert result.code == 200
    result = await client.notify_change_get(id=environment)
    assert result.code == 200

    async def compile_done():
        return (await client.is_compiling(environment)).code == 204

    await retry_limited(compile_done, 10)

    # Wait for env directory to appear
    slice = server.get_slice(SLICE_SERVER)
    env_dir = os.path.join(slice._server_storage["environments"], environment)

    while not os.path.exists(env_dir):
        await asyncio.sleep(0.1)

    result = await client.clear_environment(id=environment)
    assert result.code == 200

    assert not os.path.exists(env_dir)

    result = await client.get_environment(id=environment, versions=10)
    assert result.code == 200
    assert len(result.result["environment"]["versions"]) == 0


async def test_tokens(server_multi, client_multi, environment_multi, request):
    # Test using API tokens

    # Check the parameters of the 'server_multi' fixture
    if request.node.callspec.id in ["SSL", "Normal"]:
        # Generating tokens is not allowed if auth is not enabled
        return

    test_token = client_multi._transport_instance.token
    token = await client_multi.create_token(environment_multi, ["api"], idempotent=True)
    jot = token.result["token"]

    assert jot != test_token

    client_multi._transport_instance.token = jot

    # try to access a non environment call (global)
    result = await client_multi.list_environments()
    assert result.code == 401

    result = await client_multi.list_versions(environment_multi)
    assert result.code == 200

    token = await client_multi.create_token(environment_multi, ["agent"], idempotent=True)
    agent_jot = token.result["token"]

    client_multi._transport_instance.token = agent_jot
    result = await client_multi.list_versions(environment_multi)
    assert result.code == 401


async def test_token_without_auth(server, client, environment):
    """Generating a token when auth is not enabled is not allowed"""
    token = await client.create_token(environment, ["api"], idempotent=True)
    assert token.code == 400


async def test_batched_code_upload(
    server_multi, client_multi, sync_client_multi, environment_multi, agent_multi, snippetcompiler
):
    """Test uploading all code definitions at once"""
    snippetcompiler.setup_for_snippet(
        """
    h = std::Host(name="test", os=std::linux)
    f = std::ConfigFile(host=h, path="/etc/motd", content="test", purge_on_delete=true)
    """
    )
    version, _ = await snippetcompiler.do_export_and_deploy(do_raise=False)

    code_manager = loader.CodeManager()

    for type_name, resource_definition in resources.resource.get_resources():
        code_manager.register_code(type_name, resource_definition)

    for type_name, handler_definition in handler.Commander.get_providers():
        code_manager.register_code(type_name, handler_definition)

    await asyncio.get_event_loop().run_in_executor(
        None, lambda: upload_code(sync_client_multi, environment_multi, version, code_manager)
    )

    for name, source_info in code_manager.get_types():
        res = await agent_multi._client.get_code(tid=environment_multi, id=version, resource=name)
        assert res.code == 200
        assert len(source_info) == 2
        for info in source_info:
            assert info.hash in res.result["sources"]
            code = res.result["sources"][info.hash]

            # fetch the code from the server
            response = await agent_multi._client.get_file(info.hash)
            assert response.code == 200

            source_code = base64.b64decode(response.result["content"])
            assert info.content == source_code
            assert info.requires == code[3]


async def test_resource_action_log(server, client, environment):
    version = (await client.reserve_version(environment)).result["data"]
    resources = [
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": "std::File[vm1.dev.inmanta.com,path=/etc/sysconfig/network],v=%d" % version,
            "owner": "root",
            "path": "/etc/sysconfig/network",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "version": version,
        }
    ]
    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    resource_action_log = server.get_slice(SLICE_RESOURCE).get_resource_action_log_file(environment)
    assert os.path.isfile(resource_action_log)
    assert os.stat(resource_action_log).st_size != 0
    with open(resource_action_log, "r") as f:
        contents = f.read()
        parts = contents.split(" ")
        # Date and time
        parser.parse(f"{parts[0]} {parts[1]}")


async def test_invalid_sid(server, client, environment):
    """
    Test the server to manage the updates on a model during agent deploy
    """
    # request get_code with a compiler client that does not have a sid
    res = await client.get_code(tid=environment, id=1, resource="std::File")
    assert res.code == 400
    assert res.result["message"] == "Invalid request: this is an agent to server call, it should contain an agent session id"


async def test_get_param(server, client, environment):
    metadata = {"key1": "val1", "key2": "val2"}
    await client.set_param(environment, "param", ParameterSource.user, "val", "", metadata, False)
    await client.set_param(environment, "param2", ParameterSource.user, "val2", "", {"a": "b"}, False)

    res = await client.list_params(tid=environment, query={"key1": "val1"})
    assert res.code == 200
    parameters = res.result["parameters"]
    assert len(parameters) == 1
    metadata_received = parameters[0]["metadata"]
    assert len(metadata_received) == 2
    for k, v in metadata.items():
        assert k in metadata_received
        assert metadata_received[k] == v

    res = await client.list_params(tid=environment, query={})
    assert res.code == 200
    parameters = res.result["parameters"]
    assert len(parameters) == 2


async def test_server_logs_address(server_config, caplog, async_finalizer):
    with caplog.at_level(logging.INFO):
        ibl = InmantaBootloader()
        async_finalizer.add(partial(ibl.stop, timeout=15))
        await ibl.start()

        client = Client("client")
        result = await client.create_project("env-test")
        assert result.code == 200
        address = "127.0.0.1"

        log_contains(caplog, "protocol.rest", logging.INFO, f"Server listening on {address}:")


async def test_get_resource_actions(postgresql_client, client, clienthelper, server, environment, agent):
    """
    Test querying resource actions via the API
    """
    aclient = agent._client

    version = await clienthelper.get_version()

    resources = []
    for j in range(10):
        resources.append(
            {
                "group": "root",
                "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
                "id": "std::File[vm1,path=/tmp/file%d],v=%d" % (j, version),
                "owner": "root",
                "path": "/tmp/file%d" % j,
                "permissions": 644,
                "purged": False,
                "reload": False,
                "requires": [],
                "version": version,
            }
        )

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    resource_ids = [x["id"] for x in resources]

    # Start the deploy
    action_id = uuid.uuid4()
    now = datetime.now().astimezone()
    result = await aclient.resource_action_update(
        environment, resource_ids, action_id, "deploy", now, status=const.ResourceState.deploying
    )
    assert result.code == 200

    # Get the status from a resource
    result = await client.get_resource_actions(tid=environment)
    assert result.code == 200

    result = await client.get_resource_actions(tid=environment, attribute="path")
    assert result.code == 400
    result = await client.get_resource_actions(tid=environment, attribute_value="/tmp/file")
    assert result.code == 400
    result = await client.get_resource_actions(tid=environment, attribute="path", attribute_value="/tmp/file1")
    assert result.code == 200
    assert len(result.result["data"]) == 2
    # Query actions happening earlier than the deploy
    result = await client.get_resource_actions(tid=environment, last_timestamp=now)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["action"] == "store"
    # Query actions happening later than the start of the test case
    result = await client.get_resource_actions(tid=environment, first_timestamp=now - timedelta(minutes=1))
    assert result.code == 200
    assert len(result.result["data"]) == 2
    result = await client.get_resource_actions(tid=environment, first_timestamp=now - timedelta(minutes=1), last_timestamp=now)
    assert result.code == 400
    result = await client.get_resource_actions(tid=environment, action_id=action_id)
    assert result.code == 400
    result = await client.get_resource_actions(tid=environment, first_timestamp=now - timedelta(minutes=1), action_id=action_id)
    assert result.code == 200
    assert len(result.result["data"]) == 2


async def test_resource_action_pagination(postgresql_client, client, clienthelper, server, agent):
    """Test querying resource actions via the API, including the pagination links."""
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # Add multiple versions of model
    for i in range(1, 12):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=datetime.now(),
            total=1,
            version_info={},
        )
        await cm.insert()
        res1 = data.Resource.new(
            environment=env.id,
            resource_version_id="std::File[agent1,path=/etc/motd],v=%s" % str(i),
            status=const.ResourceState.deployed,
            last_deploy=datetime.now() + timedelta(minutes=i),
            attributes={"attr": [{"a": 1, "b": "c"}], "path": "/etc/motd"},
        )
        await res1.insert()

    # Add resource actions for motd
    motd_first_start_time = datetime.now()
    earliest_action_id = uuid.uuid4()
    resource_action = data.ResourceAction(
        environment=env.id,
        version=1,
        resource_version_ids=[f"std::File[agent1,path=/etc/motd],v={1}"],
        action_id=earliest_action_id,
        action=const.ResourceAction.deploy,
        started=motd_first_start_time - timedelta(minutes=1),
    )
    await resource_action.insert()
    resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=1)])
    await resource_action.save()

    action_ids_with_the_same_timestamp = []
    for i in range(2, 7):
        action_id = uuid.uuid4()
        action_ids_with_the_same_timestamp.append(action_id)
        resource_action = data.ResourceAction(
            environment=env.id,
            version=i,
            resource_version_ids=[f"std::File[agent1,path=/etc/motd],v={i}"],
            action_id=action_id,
            action=const.ResourceAction.deploy,
            started=motd_first_start_time,
        )
        await resource_action.insert()
        resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=i)])
        await resource_action.save()
    action_ids_with_the_same_timestamp = sorted(action_ids_with_the_same_timestamp, reverse=True)
    later_action_id = uuid.uuid4()
    resource_action = data.ResourceAction(
        environment=env.id,
        version=6,
        resource_version_ids=[f"std::File[agent1,path=/etc/motd],v={6}"],
        action_id=later_action_id,
        action=const.ResourceAction.deploy,
        started=motd_first_start_time + timedelta(minutes=6),
    )
    await resource_action.insert()
    resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=6)])
    await resource_action.save()

    result = await client.get_resource_actions(
        tid=env.id,
        resource_type="std::File",
        attribute="path",
        attribute_value="/etc/motd",
        last_timestamp=motd_first_start_time + timedelta(minutes=7),
        limit=2,
    )
    assert result.code == 200
    resource_actions = result.result["data"]
    expected_action_ids = [later_action_id] + action_ids_with_the_same_timestamp[:1]
    assert [uuid.UUID(resource_action["action_id"]) for resource_action in resource_actions] == expected_action_ids

    # Use the next link for pagination
    next_page = result.result["links"]["next"]
    port = opt.get_bind_port()
    base_url = "http://localhost:%s" % (port,)
    url = f"{base_url}{next_page}"
    client = AsyncHTTPClient()
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(env.id)},
    )
    response = await client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    second_page_action_ids = [uuid.UUID(resource_action["action_id"]) for resource_action in response["data"]]
    assert second_page_action_ids == action_ids_with_the_same_timestamp[1:3]
    next_page = response["links"]["next"]
    url = f"{base_url}{next_page}"
    request.url = url
    response = await client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    third_page_action_ids = [uuid.UUID(resource_action["action_id"]) for resource_action in response["data"]]
    assert third_page_action_ids == action_ids_with_the_same_timestamp[3:5]
    # Go back to the previous page
    prev_page = response["links"]["prev"]
    url = f"{base_url}{prev_page}"
    request.url = url
    response = await client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    action_ids = [uuid.UUID(resource_action["action_id"]) for resource_action in response["data"]]
    assert action_ids == second_page_action_ids
    # And back to the third
    prev_page = response["links"]["next"]
    url = f"{base_url}{prev_page}"
    request.url = url
    response = await client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    action_ids = [uuid.UUID(resource_action["action_id"]) for resource_action in response["data"]]
    assert action_ids == third_page_action_ids


@pytest.mark.parametrize("endpoint_to_use", ["resource_deploy_start", "resource_action_update"])
async def test_resource_deploy_start(server, client, environment, agent, endpoint_to_use: str):
    """
    Ensure that API endpoint `resource_deploy_start()` does the same as the `resource_action_update()`
    API endpoint when a new deployment is reported.
    """
    env_id = uuid.UUID(environment)

    model_version = 1
    cm = data.ConfigurationModel(
        environment=env_id,
        version=model_version,
        date=datetime.now().astimezone(),
        total=1,
        version_info={},
    )
    await cm.insert()

    model_version = 1
    rvid_r1 = "std::File[agent1,path=/etc/file1]"
    rvid_r2 = "std::File[agent1,path=/etc/file2]"
    rvid_r3 = "std::File[agent1,path=/etc/file3]"
    rvid_r1_v1 = f"{rvid_r1},v={model_version}"
    rvid_r2_v1 = f"{rvid_r2},v={model_version}"
    rvid_r3_v1 = f"{rvid_r3},v={model_version}"

    await data.Resource.new(
        environment=env_id,
        status=const.ResourceState.skipped,
        last_non_deploying_status=const.NonDeployingResourceState.skipped,
        resource_version_id=rvid_r1_v1,
        attributes={"purge_on_delete": False, "requires": [rvid_r2, rvid_r3]},
    ).insert()
    await data.Resource.new(
        environment=env_id,
        status=const.ResourceState.deployed,
        last_non_deploying_status=const.NonDeployingResourceState.deployed,
        resource_version_id=rvid_r2_v1,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()
    await data.Resource.new(
        environment=env_id,
        status=const.ResourceState.failed,
        last_non_deploying_status=const.NonDeployingResourceState.failed,
        resource_version_id=rvid_r3_v1,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()

    action_id = uuid.uuid4()

    if endpoint_to_use == "resource_deploy_start":
        result = await agent._client.resource_deploy_start(tid=env_id, rvid=rvid_r1_v1, action_id=action_id)
        assert result.code == 200
        resource_states_dependencies = result.result["data"]
        assert len(resource_states_dependencies) == 2
        assert resource_states_dependencies[rvid_r2_v1] == const.ResourceState.deployed
        assert resource_states_dependencies[rvid_r3_v1] == const.ResourceState.failed
    else:
        await agent._client.resource_action_update(
            tid=env_id,
            resource_ids=[rvid_r1_v1],
            action_id=action_id,
            action=const.ResourceAction.deploy,
            started=datetime.now().astimezone(),
            status=const.ResourceState.deploying,
        )

    # Ensure that both API calls result in the same behavior
    result = await client.get_resource_actions(tid=env_id)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    resource_action = result.result["data"][0]
    assert resource_action["environment"] == str(env_id)
    assert resource_action["version"] == model_version
    assert resource_action["resource_version_ids"] == [rvid_r1_v1]
    assert resource_action["action_id"] == str(action_id)
    assert resource_action["action"] == const.ResourceAction.deploy
    assert resource_action["started"] is not None
    assert resource_action["finished"] is None
    assert resource_action["status"] == const.ResourceState.deploying
    assert resource_action["changes"] is None
    assert resource_action["change"] is None


async def test_resource_deploy_start_error_handling(server, client, environment, agent):
    """
    Test the error handling of the `resource_deploy_start` API endpoint.
    """
    env_id = uuid.UUID(environment)

    # Version part missing from resource_version_id
    result = await agent._client.resource_deploy_start(
        tid=env_id, rvid="std::File[agent1,path=/etc/file1]", action_id=uuid.uuid4()
    )
    assert result.code == 400
    assert "Invalid resource version id" in result.result["message"]

    # Execute resource_deploy_start call for resource that doesn't exist
    resource_id = "std::File[agent1,path=/etc/file1],v=1"
    result = await agent._client.resource_deploy_start(tid=env_id, rvid=resource_id, action_id=uuid.uuid4())
    assert result.code == 404
    assert f"Environment {environment} doesn't contain a resource with id {resource_id}" in result.result["message"]


async def test_resource_deploy_start_action_id_conflict(server, client, environment, agent):
    """
    Ensure proper error handling when the same action_id is provided twice to the `resource_deploy_start` API endpoint.
    """
    env_id = uuid.UUID(environment)

    model_version = 1
    cm = data.ConfigurationModel(
        environment=env_id,
        version=model_version,
        date=datetime.now().astimezone(),
        total=1,
        version_info={},
    )
    await cm.insert()

    model_version = 1
    rvid_r1_v1 = f"std::File[agent1,path=/etc/file1],v={model_version}"

    await data.Resource.new(
        environment=env_id,
        status=const.ResourceState.skipped,
        resource_version_id=rvid_r1_v1,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()

    action_id = uuid.uuid4()

    async def execute_resource_deploy_start(expected_return_code: int, resulting_nr_resource_actions: int) -> None:
        result = await agent._client.resource_deploy_start(tid=env_id, rvid=rvid_r1_v1, action_id=action_id)
        assert result.code == expected_return_code

        result = await client.get_resource_actions(tid=env_id)
        assert result.code == 200
        assert len(result.result["data"]) == resulting_nr_resource_actions

    await execute_resource_deploy_start(expected_return_code=200, resulting_nr_resource_actions=1)
    await execute_resource_deploy_start(expected_return_code=409, resulting_nr_resource_actions=1)


@pytest.mark.parametrize("endpoint_to_use", ["resource_deploy_done", "resource_action_update"])
async def test_resource_deploy_done(server, client, environment, agent, caplog, endpoint_to_use):
    """
    Ensure that the `resource_deploy_done` endpoint behaves in the same way as the `resource_action_update` endpoint
    when the finished field is not None.
    """
    env_id = uuid.UUID(environment)

    model_version = 1
    cm = data.ConfigurationModel(
        environment=env_id,
        version=model_version,
        date=datetime.now().astimezone(),
        total=1,
        version_info={},
    )
    await cm.insert()

    rvid_r1_v1 = f"std::File[agent1,path=/etc/file1],v={model_version}"
    await data.Resource.new(
        environment=env_id,
        status=const.ResourceState.available,
        resource_version_id=rvid_r1_v1,
        attributes={"purge_on_delete": False, "purged": True, "requires": []},
    ).insert()

    # Add parameter for resource
    parameter_id = "test_param"
    result = await client.set_param(
        tid=env_id,
        id=parameter_id,
        source=const.ParameterSource.user,
        value="val",
        resource_id="std::File[agent1,path=/etc/file1]",
    )
    assert result.code == 200

    action_id = uuid.uuid4()
    result = await agent._client.resource_deploy_start(tid=env_id, rvid=rvid_r1_v1, action_id=action_id)
    assert result.code == 200, result.result

    # Assert initial state
    result = await client.get_resource_actions(tid=env_id)
    assert result.code == 200, result.result
    assert len(result.result["data"]) == 1
    resource_action = result.result["data"][0]
    assert resource_action["environment"] == str(env_id)
    assert resource_action["version"] == model_version
    assert resource_action["resource_version_ids"] == [rvid_r1_v1]
    assert resource_action["action_id"] == str(action_id)
    assert resource_action["action"] == const.ResourceAction.deploy
    assert resource_action["started"] is not None
    assert resource_action["finished"] is None
    assert resource_action["status"] == const.ResourceState.deploying
    assert resource_action["changes"] is None
    assert resource_action["change"] is None

    result = await client.get_resource(tid=env_id, id=rvid_r1_v1)
    assert result.code == 200, result.result
    assert result.result["resource"]["last_deploy"] is None
    assert result.result["resource"]["status"] == const.ResourceState.deploying

    result = await client.get_version(tid=env_id, id=1)
    assert result.code == 200, result.result
    assert not result.result["model"]["deployed"]

    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        # Mark deployment as done
        now = datetime.now()
        if endpoint_to_use == "resource_deploy_done":
            result = await agent._client.resource_deploy_done(
                tid=env_id,
                rvid=rvid_r1_v1,
                action_id=action_id,
                status=const.ResourceState.deployed,
                messages=[
                    LogLine(level=const.LogLevel.DEBUG, msg="message", kwargs={"keyword": 123, "none": None}, timestamp=now),
                    LogLine(level=const.LogLevel.INFO, msg="test", kwargs={}, timestamp=now),
                ],
                changes={"attr1": AttributeStateChange(current=None, desired="test")},
                change=const.Change.purged,
            )
            assert result.code == 200, result.result
        else:
            result = await agent._client.resource_action_update(
                tid=env_id,
                resource_ids=[rvid_r1_v1],
                action_id=action_id,
                action=const.ResourceAction.deploy,
                started=None,
                finished=now,
                status=const.ResourceState.deployed,
                messages=[
                    data.LogLine.log(level=const.LogLevel.DEBUG, msg="message", timestamp=now, keyword=123, none=None),
                    data.LogLine.log(level=const.LogLevel.INFO, msg="test", timestamp=now),
                ],
                changes={rvid_r1_v1: {"attr1": AttributeStateChange(current=None, desired="test")}},
                change=const.Change.purged,
                send_events=True,
            )
            assert result.code == 200, result.result

    # Assert effect of resource_deploy_done call
    assert f"{rvid_r1_v1}: message" in caplog.messages
    assert f"{rvid_r1_v1}: test" in caplog.messages

    result = await client.get_resource_actions(tid=env_id)
    assert result.code == 200, result.result
    assert len(result.result["data"]) == 1
    resource_action = result.result["data"][0]
    assert resource_action["environment"] == str(env_id)
    assert resource_action["version"] == model_version
    assert resource_action["resource_version_ids"] == [rvid_r1_v1]
    assert resource_action["action_id"] == str(action_id)
    assert resource_action["action"] == const.ResourceAction.deploy
    assert resource_action["started"] is not None
    assert resource_action["finished"] is not None
    assert resource_action["messages"] == [
        {
            "level": const.LogLevel.DEBUG.name,
            "msg": "message",
            "args": [],
            "kwargs": {"keyword": 123, "none": None},
            "timestamp": now.isoformat(timespec="microseconds"),
        },
        {
            "level": const.LogLevel.INFO.name,
            "msg": "test",
            "args": [],
            "kwargs": {},
            "timestamp": now.isoformat(timespec="microseconds"),
        },
    ]
    assert resource_action["status"] == const.ResourceState.deployed
    assert resource_action["changes"] == {rvid_r1_v1: {"attr1": AttributeStateChange(current=None, desired="test").dict()}}
    assert resource_action["change"] == const.Change.purged.value

    result = await client.get_resource(tid=env_id, id=rvid_r1_v1)
    assert result.code == 200, result.result
    assert result.result["resource"]["last_deploy"] is not None
    assert result.result["resource"]["status"] == const.ResourceState.deployed

    result = await client.get_version(tid=env_id, id=1)
    assert result.code == 200, result.result
    assert result.result["model"]["deployed"]

    # parameter was deleted due to purge operation
    result = await client.list_params(tid=env_id)
    assert result.code == 200
    assert len(result.result["parameters"]) == 0

    # A new resource_deploy_done call for the same action_id should result in a Conflict
    result = await agent._client.resource_deploy_done(
        tid=env_id,
        rvid=rvid_r1_v1,
        action_id=action_id,
        status=const.ResourceState.deployed,
        messages=[],
        changes={"attr1": AttributeStateChange(current="test", desired="test2")},
        change=const.Change.created,
    )
    assert result.code == 409, result.result


async def test_resource_deploy_done_invalid_state(server, client, environment, agent, caplog):
    """
    Ensure proper error handling when a transient state is passed to the `resource_deploy_done` endpoint.
    """
    env_id = uuid.UUID(environment)

    model_version = 1
    cm = data.ConfigurationModel(
        environment=env_id,
        version=model_version,
        date=datetime.now().astimezone(),
        total=1,
        version_info={},
    )
    await cm.insert()

    rvid_r1_v1 = f"std::File[agent1,path=/etc/file1],v={model_version}"
    await data.Resource.new(
        environment=env_id,
        status=const.ResourceState.available,
        resource_version_id=rvid_r1_v1,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()

    action_id = uuid.uuid4()
    result = await agent._client.resource_deploy_start(tid=env_id, rvid=rvid_r1_v1, action_id=action_id)
    assert result.code == 200, result.result

    result = await agent._client.resource_deploy_done(
        tid=env_id,
        rvid=rvid_r1_v1,
        action_id=action_id,
        status=const.ResourceState.deploying,
        messages=[],
        changes={"attr1": AttributeStateChange(current=None, desired="test")},
        change=const.Change.created,
    )
    assert result.code == 400, result.result
    assert "No transient state can be used to mark a deployment as done" in result.result["message"]


async def test_resource_deploy_done_error_handling(server, client, environment, agent):
    env_id = uuid.UUID(environment)

    model_version = 1
    cm = data.ConfigurationModel(
        environment=env_id,
        version=model_version,
        date=datetime.now().astimezone(),
        total=1,
        version_info={},
    )
    await cm.insert()

    rvid_r1_v1 = f"std::File[agent1,path=/etc/file1],v={model_version}"

    # Resource doesn't exist
    result = await agent._client.resource_deploy_done(
        tid=env_id,
        rvid=rvid_r1_v1,
        action_id=uuid.uuid4(),
        status=const.ResourceState.deployed,
        messages=[],
        changes={},
        change=const.Change.nochange,
    )
    assert result.code == 404, result.result

    # Create resource
    await data.Resource.new(
        environment=env_id,
        status=const.ResourceState.available,
        resource_version_id=rvid_r1_v1,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()

    # Resource action doesn't exist
    result = await agent._client.resource_deploy_done(
        tid=env_id,
        rvid=rvid_r1_v1,
        action_id=uuid.uuid4(),
        status=const.ResourceState.deployed,
        messages=[],
        changes={},
        change=const.Change.nochange,
    )
    assert result.code == 404, result.result


async def test_start_location_no_redirect(server):
    """
    Ensure that there is no redirection for the "start" location. (issue #3497)
    """
    port = opt.get_bind_port()
    base_url = "http://localhost:%s/" % (port,)
    http_client = AsyncHTTPClient()
    request = HTTPRequest(
        url=base_url,
    )
    response = await http_client.fetch(request, raise_error=False)
    assert base_url == response.effective_url


@pytest.mark.parametrize("path", ["", "/", "/test"])
async def test_redirect_dashboard_to_console(server, path):
    """
    Ensure that there is a redirection from the dashboard to the webconsole
    """
    port = opt.get_bind_port()
    base_url = "http://localhost:%s/dashboard%s" % (port, path)
    result_url = "http://localhost:%s/console%s" % (port, path)
    http_client = AsyncHTTPClient()
    request = HTTPRequest(
        url=base_url,
    )
    response = await http_client.fetch(request, raise_error=False)
    assert result_url == response.effective_url
