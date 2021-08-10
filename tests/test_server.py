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
import json
import logging
import os
import uuid
from datetime import datetime, timedelta

import pytest
from dateutil import parser
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import const, data, loader, resources
from inmanta.agent import handler
from inmanta.agent.agent import Agent
from inmanta.const import ParameterSource
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
from inmanta.util import get_compiler_version, hash_file
from utils import log_contains, log_doesnt_contain, retry_limited

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio(timeout=60)
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


@pytest.mark.asyncio(timeout=60)
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


@pytest.mark.asyncio(timeout=60)
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


@pytest.mark.asyncio(timeout=10)
async def test_version_removal(client, server):
    """
    Test auto removal of older deploy model versions
    """
    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    for _i in range(20):
        version = (await client.reserve_version(env_id)).result["data"]

        await server.get_slice(SLICE_ORCHESTRATION)._purge_versions()
        res = await client.put_version(
            tid=env_id, version=version, resources=[], unknowns=[], version_info={}, compiler_version=get_compiler_version()
        )
        assert res.code == 200
        result = await client.get_project(id=project_id)

        versions = await client.list_versions(tid=env_id)
        assert versions.result["count"] <= opt.server_version_to_keep.get() + 1


@pytest.mark.asyncio(timeout=30)
@pytest.mark.slowtest
async def test_get_resource_for_agent(server_multi, client_multi, environment_multi):
    """
    Test the server to manage the updates on a model during agent deploy
    """
    agent = Agent("localhost", {"nvblah": "localhost"}, environment=environment_multi, code_loader=False)
    await agent.add_end_point_name("vm1.dev.inmanta.com")
    await agent.add_end_point_name("vm2.dev.inmanta.com")
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

    result = await aclient.get_resources_for_agent(environment_multi, "vm1.dev.inmanta.com")
    assert result.code == 200
    assert len(result.result["resources"]) == 3

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
    await agent.stop()


@pytest.mark.asyncio(timeout=10)
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


@pytest.mark.asyncio
async def test_resource_update(postgresql_client, client, clienthelper, server, environment):
    """
    Test updating resources and logging
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
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
    assert "finished" not in logs["deploy"]
    assert "messages" not in logs["deploy"]
    assert "changes" not in logs["deploy"]

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
    assert "finished" not in logs["deploy"]
    assert "changes" not in logs["deploy"]

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
    await agent.stop()


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_tokens(server_multi, client_multi, environment_multi):
    # Test using API tokens
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


def make_source(collector, filename, module, source, req):
    myhash = hash_file(source.encode())
    collector[myhash] = [filename, module, source, req]
    return collector


@pytest.mark.asyncio(timeout=30)
async def test_code_upload(server, client, agent, environment):
    """Test upload of a single code definition"""
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

    sources = make_source({}, "a.py", "std.test", "wlkvsdbhewvsbk vbLKBVWE wevbhbwhBH", [])
    sources = make_source(sources, "b.py", "std.xxx", "rvvWBVWHUvejIVJE UWEBVKW", ["pytest"])

    res = await client.upload_code(tid=environment, id=version, resource="std::File", sources=sources)
    assert res.code == 200

    res = await agent._client.get_code(tid=environment, id=version, resource="std::File")
    assert res.code == 200
    assert res.result["sources"] == sources


@pytest.mark.asyncio(timeout=30)
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

            assert info.content == code[2]
            assert info.requires == code[3]


@pytest.mark.asyncio(timeout=30)
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


@pytest.mark.asyncio(timeout=30)
async def test_invalid_sid(server, client, environment):
    """
    Test the server to manage the updates on a model during agent deploy
    """
    # request get_code with a compiler client that does not have a sid
    res = await client.get_code(tid=environment, id=1, resource="std::File")
    assert res.code == 400
    assert res.result["message"] == "Invalid request: this is an agent to server call, it should contain an agent session id"


@pytest.mark.asyncio(timeout=30)
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


@pytest.mark.asyncio(timeout=30)
async def test_server_logs_address(server_config, caplog):
    with caplog.at_level(logging.INFO):
        ibl = InmantaBootloader()
        await ibl.start()

        client = Client("client")
        result = await client.create_project("env-test")
        assert result.code == 200
        address = "127.0.0.1"

        await ibl.stop()
        log_contains(caplog, "protocol.rest", logging.INFO, f"Server listening on {address}:")


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_resource_action_pagination(postgresql_client, client, clienthelper, server, agent):
    """ Test querying resource actions via the API, including the pagination links."""
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # Add multiple versions of model
    for i in range(0, 11):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=datetime.now(),
            total=1,
            version_info={},
        )
        await cm.insert()

    # Add resource actions for motd
    motd_first_start_time = datetime.now()
    earliest_action_id = uuid.uuid4()
    resource_action = data.ResourceAction(
        environment=env.id,
        version=0,
        resource_version_ids=[f"std::File[agent1,path=/etc/motd],v={0}"],
        action_id=earliest_action_id,
        action=const.ResourceAction.deploy,
        started=motd_first_start_time - timedelta(minutes=1),
    )
    await resource_action.insert()
    resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=0)])
    await resource_action.save()

    action_ids_with_the_same_timestamp = []
    for i in range(1, 6):
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
    for i in range(0, 11):
        res1 = data.Resource.new(
            environment=env.id,
            resource_version_id="std::File[agent1,path=/etc/motd],v=%s" % str(i),
            status=const.ResourceState.deployed,
            last_deploy=datetime.now() + timedelta(minutes=i),
            attributes={"attr": [{"a": 1, "b": "c"}], "path": "/etc/motd"},
        )
        await res1.insert()

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
