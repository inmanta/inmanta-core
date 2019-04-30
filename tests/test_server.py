"""
    Copyright 2016 Inmanta

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

import time
import logging
import uuid
import os

from utils import retry_limited
import pytest
from inmanta.agent.agent import Agent
from inmanta.agent import handler
from inmanta import data, config, const, loader, resources
from inmanta.server import config as opt, SLICE_AGENT_MANAGER, SLICE_SESSION_MANAGER, server

from datetime import datetime
from inmanta.util import hash_file
from inmanta.export import upload_code, unknown_parameters
import asyncio


LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio(timeout=60)
@pytest.mark.slowtest
async def test_autostart(server, client, environment):
    """
        Test auto start of agent
    """
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"iaas_agent": "", "iaas_agentx": ""})

    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    sessionendpoint = server.get_slice(SLICE_SESSION_MANAGER)

    await agentmanager.ensure_agent_registered(env, "iaas_agent")
    await agentmanager.ensure_agent_registered(env, "iaas_agentx")

    res = await agentmanager._ensure_agents(env, ["iaas_agent"])
    assert res

    await retry_limited(lambda: len(sessionendpoint._sessions) == 1, 20)
    assert len(sessionendpoint._sessions) == 1
    res = await agentmanager._ensure_agents(env, ["iaas_agent"])
    assert not res
    assert len(sessionendpoint._sessions) == 1

    LOGGER.warning("Killing agent")
    agentmanager._agent_procs[env.id].proc.terminate()
    await agentmanager._agent_procs[env.id].wait_for_exit(raise_error=False)
    await retry_limited(lambda: len(sessionendpoint._sessions) == 0, 20)
    res = await agentmanager._ensure_agents(env, ["iaas_agent"])
    assert res
    await retry_limited(lambda: len(sessionendpoint._sessions) == 1, 3)
    assert len(sessionendpoint._sessions) == 1

    # second agent for same env
    res = await agentmanager._ensure_agents(env, ["iaas_agentx"])
    assert res
    await retry_limited(lambda: len(sessionendpoint._sessions) == 1, 20)
    assert len(sessionendpoint._sessions) == 1

    # Test stopping all agents
    await agentmanager.stop_agents(env)
    assert len(sessionendpoint._sessions) == 0
    assert len(agentmanager._agent_procs) == 0


@pytest.mark.asyncio(timeout=60)
@pytest.mark.slowtest
async def test_autostart_dual_env(client, server):
    """
        Test auto start of agent
    """
    agentmanager = server.get_slice("server").agentmanager
    sessionendpoint = server.get_slice("session")

    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    result = await client.create_environment(project_id=project_id, name="devx")
    env_id2 = result.result["environment"]["id"]

    env = await data.Environment.get_by_id(uuid.UUID(env_id))
    await env.set(data.AUTOSTART_AGENT_MAP, {"iaas_agent": ""})

    env2 = await data.Environment.get_by_id(uuid.UUID(env_id2))
    await env2.set(data.AUTOSTART_AGENT_MAP, {"iaas_agent": ""})

    await agentmanager.ensure_agent_registered(env, "iaas_agent")
    await agentmanager.ensure_agent_registered(env2, "iaas_agent")

    res = await agentmanager._ensure_agents(env, ["iaas_agent"])
    assert res
    await retry_limited(lambda: len(sessionendpoint._sessions) == 1, 20)
    assert len(sessionendpoint._sessions) == 1

    res = await agentmanager._ensure_agents(env2, ["iaas_agent"])
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
    await env.set(data.AUTOSTART_AGENT_MAP, {"iaas_agent": "", "iaas_agentx": ""})

    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    sessionendpoint = server.get_slice(SLICE_SESSION_MANAGER)

    await agentmanager.ensure_agent_registered(env, "iaas_agent")
    await agentmanager.ensure_agent_registered(env, "iaas_agentx")

    res = await agentmanager._ensure_agents(env, ["iaas_agent", "iaas_agentx"])
    assert res
    await retry_limited(lambda: len(sessionendpoint._sessions) == 1, 20)
    assert len(sessionendpoint._sessions) == 1
    res = await agentmanager._ensure_agents(env, ["iaas_agent"])
    assert not res
    assert len(sessionendpoint._sessions) == 1

    res = await agentmanager._ensure_agents(env, ["iaas_agent", "iaas_agentx"])
    assert not res
    assert len(sessionendpoint._sessions) == 1

    LOGGER.warning("Killing agent")
    agentmanager._agent_procs[env.id].proc.terminate()
    await agentmanager._agent_procs[env.id].wait_for_exit(raise_error=False)
    await retry_limited(lambda: len(sessionendpoint._sessions) == 0, 20)
    res = await agentmanager._ensure_agents(env, ["iaas_agent", "iaas_agentx"])
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

    version = int(time.time())

    for _i in range(20):
        version += 1

        await server.get_slice("server")._purge_versions()
        res = await client.put_version(tid=env_id, version=version, resources=[], unknowns=[], version_info={})
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
    agent.add_end_point_name("vm1.dev.inmanta.com")
    agent.add_end_point_name("vm2.dev.inmanta.com")
    await agent.start()
    aclient = agent._client

    version = 1

    resources = [{'group': 'root',
                  'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
                  'id': 'std::File[vm1.dev.inmanta.com,path=/etc/sysconfig/network],v=%d' % version,
                  'owner': 'root',
                  'path': '/etc/sysconfig/network',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'version': version},
                 {'group': 'root',
                  'hash': 'b4350bef50c3ec3ee532d4a3f9d6daedec3d2aba',
                  'id': 'std::File[vm2.dev.inmanta.com,path=/etc/motd],v=%d' % version,
                  'owner': 'root',
                  'path': '/etc/motd',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'version': version},
                 {'group': 'root',
                  'hash': '3bfcdad9ab7f9d916a954f1a96b28d31d95593e4',
                  'id': 'std::File[vm1.dev.inmanta.com,path=/etc/hostname],v=%d' % version,
                  'owner': 'root',
                  'path': '/etc/hostname',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'version': version},
                 {'id': 'std::Service[vm1.dev.inmanta.com,name=network],v=%d' % version,
                  'name': 'network',
                  'onboot': True,
                  'requires': ['std::File[vm1.dev.inmanta.com,path=/etc/sysconfig/network],v=%d' % version],
                  'state': 'running',
                  'version': version}]

    res = await client_multi.put_version(tid=environment_multi, version=version, resources=resources, unknowns=[],
                                         version_info={})
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
    result = await aclient.resource_action_update(environment_multi,
                                                  ["std::File[vm1.dev.inmanta.com,path=/etc/sysconfig/network],v=%d" % version],
                                                  action_id, "deploy", now, now, "deployed", [], {})

    assert result.code == 200

    result = await client_multi.get_version(environment_multi, version)
    assert result.code == 200
    assert result.result["model"]["done"] == 1

    action_id = uuid.uuid4()
    now = datetime.now()
    result = await aclient.resource_action_update(environment_multi,
                                                  ["std::File[vm1.dev.inmanta.com,path=/etc/hostname],v=%d" % version],
                                                  action_id, "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = await client_multi.get_version(environment_multi, version)
    assert result.code == 200
    assert result.result["model"]["done"] == 2
    await agent.stop()


@pytest.mark.asyncio(timeout=10)
async def test_get_environment(client, server, environment):
    version = int(time.time())

    for i in range(10):
        version += 1

        resources = []
        for j in range(i):
            resources.append({
                'group': 'root',
                'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
                'id': 'std::File[vm1.dev.inmanta.com,path=/tmp/file%d],v=%d' % (j, version),
                'owner': 'root',
                'path': '/tmp/file%d' % j,
                'permissions': 644,
                'purged': False,
                'reload': False,
                'requires': [],
                'version': version})

        res = await client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
        assert res.code == 200

    result = await client.get_environment(environment, versions=5, resources=1)
    assert(result.code == 200)
    assert(len(result.result["environment"]["versions"]) == 5)
    assert(len(result.result["environment"]["resources"]) == 9)


@pytest.mark.asyncio
async def test_resource_update(postgresql_client, client, server, environment):
    """
        Test updating resources and logging
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
    await agent.start()
    aclient = agent._client

    version = int(time.time())

    resources = []
    for j in range(10):
        resources.append({
            'group': 'root',
            'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
            'id': 'std::File[vm1,path=/tmp/file%d],v=%d' % (j, version),
            'owner': 'root',
            'path': '/tmp/file%d' % j,
            'permissions': 644,
            'purged': False,
            'reload': False,
            'requires': [],
            'version': version})

    res = await client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert(res.code == 200)

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    resource_ids = [x["id"] for x in resources]

    # Start the deploy
    action_id = uuid.uuid4()
    now = datetime.now()
    result = await aclient.resource_action_update(environment, resource_ids, action_id, "deploy", now,
                                                  status=const.ResourceState.deploying)
    assert(result.code == 200)

    # Get the status from a resource
    result = await client.get_resource(tid=environment, id=resource_ids[0], logs=True)
    assert(result.code == 200)
    logs = {x["action"]: x for x in result.result["logs"]}

    assert("deploy" in logs)
    assert("finished" not in logs["deploy"])
    assert("messages" not in logs["deploy"])
    assert("changes" not in logs["deploy"])

    # Send some logs
    result = await aclient.resource_action_update(environment, resource_ids, action_id, "deploy",
                                                  status=const.ResourceState.deploying,
                                                  messages=[data.LogLine.log(const.LogLevel.INFO,
                                                                             "Test log %(a)s %(b)s", a="a", b="b")])
    assert(result.code == 200)

    # Get the status from a resource
    result = await client.get_resource(tid=environment, id=resource_ids[0], logs=True)
    assert(result.code == 200)
    logs = {x["action"]: x for x in result.result["logs"]}

    assert("deploy" in logs)
    assert("messages" in logs["deploy"])
    assert(len(logs["deploy"]["messages"]) == 1)
    assert(logs["deploy"]["messages"][0]["msg"] == "Test log a b")
    assert("finished" not in logs["deploy"])
    assert("changes" not in logs["deploy"])

    # Finish the deploy
    now = datetime.now()
    changes = {x: {"owner": {"old": "root", "current": "inmanta"}} for x in resource_ids}
    result = await aclient.resource_action_update(environment, resource_ids, action_id, "deploy", finished=now, changes=changes)
    assert(result.code == 400)

    result = await aclient.resource_action_update(environment, resource_ids, action_id, "deploy",
                                                  status=const.ResourceState.deployed,
                                                  finished=now, changes=changes)
    assert (result.code == 200)

    result = await client.get_version(environment, version)
    assert(result.code == 200)
    assert result.result["model"]["done"] == 10
    await agent.stop()


@pytest.mark.asyncio
async def test_environment_settings(client, server, environment):
    """
        Test environment settings
    """
    result = await client.list_settings(tid=environment)
    assert result.code == 200
    assert "settings" in result.result
    assert "metadata" in result.result
    assert "auto_deploy" in result.result["metadata"]
    assert len(result.result["settings"]) == 0

    result = await client.set_setting(tid=environment, id="auto_deploy", value="test")
    assert result.code == 500

    result = await client.set_setting(tid=environment, id="auto_deploy", value=False)
    assert result.code == 200

    result = await client.list_settings(tid=environment)
    assert result.code == 200
    assert len(result.result["settings"]) == 1

    result = await client.get_setting(tid=environment, id="auto_deploy")
    assert result.code == 200
    assert not result.result["value"]

    result = await client.get_setting(tid=environment, id="test2")
    assert result.code == 404

    result = await client.set_setting(tid=environment, id="auto_deploy", value=True)
    assert result.code == 200

    result = await client.get_setting(tid=environment, id="auto_deploy")
    assert result.code == 200
    assert result.result["value"]

    result = await client.delete_setting(tid=environment, id="test2")
    assert result.code == 404

    result = await client.delete_setting(tid=environment, id="auto_deploy")
    assert result.code == 200

    result = await client.list_settings(tid=environment)
    assert result.code == 200
    assert "settings" in result.result
    assert len(result.result["settings"]) == 1

    result = await client.set_setting(tid=environment, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, value=20)
    assert result.code == 200

    result = await client.set_setting(tid=environment, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, value="30")
    assert result.code == 200

    result = await client.get_setting(tid=environment, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME)
    assert result.code == 200
    assert result.result["value"] == 30

    result = await client.delete_setting(tid=environment, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME)
    assert result.code == 200

    result = await client.set_setting(tid=environment, id=data.AUTOSTART_AGENT_MAP, value={"agent1": "", "agent2": "localhost",
                                                                                           "agent3": "user@agent3"})
    assert result.code == 200

    result = await client.set_setting(tid=environment, id=data.AUTOSTART_AGENT_MAP, value="")
    assert result.code == 500


@pytest.mark.asyncio
async def test_clear_environment(client, server, environment):
    """
        Test clearing out an environment
    """
    version = int(time.time())
    result = await client.put_version(tid=environment, version=version, resources=[], unknowns=[], version_info={})
    assert result.code == 200

    result = await client.get_environment(id=environment, versions=10)
    assert result.code == 200
    assert len(result.result["environment"]["versions"]) == 1

    result = await client.clear_environment(id=environment)
    assert result.code == 200

    result = await client.get_environment(id=environment, versions=10)
    assert result.code == 200
    assert len(result.result["environment"]["versions"]) == 0


@pytest.mark.asyncio
async def test_purge_on_delete_requires(client, server, environment):
    """
        Test purge on delete of resources and inversion of requires
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
    await agent.start()
    aclient = agent._client

    version = 1

    resources = [{'group': 'root',
                  'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
                  'id': 'std::File[vm1,path=/tmp/file1],v=%d' % version,
                  'owner': 'root',
                  'path': '/tmp/file1',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'purge_on_delete': True,
                  'version': version},
                 {'group': 'root',
                  'hash': 'b4350bef50c3ec3ee532d4a3f9d6daedec3d2aba',
                  'id': 'std::File[vm2,path=/tmp/file2],v=%d' % version,
                  'owner': 'root',
                  'path': '/tmp/file2',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'purge_on_delete': True,
                  'requires': ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                  'version': version}]

    res = await client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    now = datetime.now()
    result = await aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = await aclient.resource_action_update(environment,
                                                  ['std::File[vm2,path=/tmp/file2],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == const.VersionState.success.name

    # validate requires and provides
    file1 = [x for x in result.result["resources"] if "file1" in x["id"]][0]
    file2 = [x for x in result.result["resources"] if "file2" in x["id"]][0]

    assert file2["id"] in file1["provides"]
    assert len(file1["attributes"]["requires"]) == 0

    assert len(file2["provides"]) == 0
    assert file1["id"] in file2["attributes"]["requires"]

    result = await client.decomission_environment(id=environment)
    assert result.code == 200

    version = result.result["version"]
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == len(resources)

    # validate requires and provides
    file1 = [x for x in result.result["resources"] if "file1" in x["id"]][0]
    file2 = [x for x in result.result["resources"] if "file2" in x["id"]][0]

    assert file2["id"] in file1["attributes"]["requires"]
    assert type(file1["attributes"]["requires"]) == list
    assert len(file1["provides"]) == 0

    assert len(file2["attributes"]["requires"]) == 0
    assert file1["id"] in file2["provides"]
    await agent.stop()


@pytest.mark.asyncio(timeout=20)
async def test_purge_on_delete_compile_failed_with_compile(event_loop, client, server, environment, snippetcompiler):
    config.Config.set("compiler_rest_transport", "request_timeout", "1")

    snippetcompiler.setup_for_snippet("""
    h = std::Host(name="test", os=std::linux)
    f = std::ConfigFile(host=h, path="/etc/motd", content="test", purge_on_delete=true)
    """)
    version, _ = await snippetcompiler.do_export_and_deploy(do_raise=False)

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == 1

    snippetcompiler.setup_for_snippet("""
    h = std::Host(name="test")
    """)

    # force deploy by having unknown
    unknown_parameters.append({"parameter": "a", "source": "b"})

    # ensure new version, wait for other second
    await asyncio.sleep(1)

    version, _ = await snippetcompiler.do_export_and_deploy(do_raise=False)
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == 0


@pytest.mark.asyncio
async def test_purge_on_delete_compile_failed(client, server, environment):
    """
        Test purge on delete of resources
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
    await agent.start()
    aclient = agent._client

    version = 1

    resources = [{'group': 'root',
                  'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
                  'id': 'std::File[vm1,path=/tmp/file1],v=%d' % version,
                  'owner': 'root',
                  'path': '/tmp/file1',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'purge_on_delete': True,
                  'version': version},
                 {'group': 'root',
                  'hash': 'b4350bef50c3ec3ee532d4a3f9d6daedec3d2aba',
                  'id': 'std::File[vm1,path=/tmp/file2],v=%d' % version,
                  'owner': 'root',
                  'path': '/tmp/file2',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'purge_on_delete': True,
                  'requires': ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                  'version': version},
                 {'group': 'root',
                  'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
                  'id': 'std::File[vm1,path=/tmp/file3],v=%d' % version,
                  'owner': 'root',
                  'path': '/tmp/file3',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'purge_on_delete': True,
                  'version': version}]

    result = await client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # Release the model and set all resources as deployed
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    now = datetime.now()
    result = await aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = await aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file2],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = await aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file3],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == const.VersionState.success.name

    # New version with only file3
    version = 2
    result = await client.put_version(tid=environment, version=version, resources=[],
                                      unknowns=[{"parameter": "a", "source": "b"}], version_info={const.EXPORT_META_DATA:
                                      {const.META_DATA_COMPILE_STATE: const.Compilestate.failed}})
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == 0
    await agent.stop()
    assert len(result.result["unknowns"]) == 1


@pytest.mark.asyncio
async def test_purge_on_delete(client, server, environment):
    """
        Test purge on delete of resources
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
    await agent.start()
    aclient = agent._client

    version = 1

    resources = [{'group': 'root',
                  'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
                  'id': 'std::File[vm1,path=/tmp/file1],v=%d' % version,
                  'owner': 'root',
                  'path': '/tmp/file1',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'purge_on_delete': True,
                  'version': version},
                 {'group': 'root',
                  'hash': 'b4350bef50c3ec3ee532d4a3f9d6daedec3d2aba',
                  'id': 'std::File[vm1,path=/tmp/file2],v=%d' % version,
                  'owner': 'root',
                  'path': '/tmp/file2',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'purge_on_delete': True,
                  'requires': ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                  'version': version},
                 {'group': 'root',
                  'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
                  'id': 'std::File[vm1,path=/tmp/file3],v=%d' % version,
                  'owner': 'root',
                  'path': '/tmp/file3',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'purge_on_delete': True,
                  'version': version}]

    res = await client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    now = datetime.now()
    result = await aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = await aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file2],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = await aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file3],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == const.VersionState.success.name

    # New version with only file3
    version = 2
    res3 = {'group': 'root',
            'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
            'id': 'std::File[vm1,path=/tmp/file3],v=%d' % version,
            'owner': 'root',
            'path': '/tmp/file3',
            'permissions': 644,
            'purged': False,
            'reload': False,
            'requires': [],
            'purge_on_delete': True,
            'version': version}
    result = await client.put_version(tid=environment, version=version, resources=[res3], unknowns=[], version_info={})
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == 3

    # validate requires and provides
    file1 = [x for x in result.result["resources"] if "file1" in x["id"]][0]
    file2 = [x for x in result.result["resources"] if "file2" in x["id"]][0]
    file3 = [x for x in result.result["resources"] if "file3" in x["id"]][0]

    assert file1["attributes"]["purged"]
    assert file2["attributes"]["purged"]
    assert not file3["attributes"]["purged"]
    await agent.stop()


@pytest.mark.asyncio
async def test_purge_on_delete_ignore(client, server, environment):
    """
        Test purge on delete behavior for resources that have not longer purged_on_delete set
    """
    agent = Agent("localhost", {"blah": "localhost"}, environment=environment, code_loader=False)
    await agent.start()
    aclient = agent._client

    # Version 1 with purge_on_delete true
    version = 1

    resources = [{'group': 'root',
                  'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
                  'id': 'std::File[vm1,path=/tmp/file1],v=%d' % version,
                  'owner': 'root',
                  'path': '/tmp/file1',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'purge_on_delete': True,
                  'version': version}]

    res = await client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    now = datetime.now()
    result = await aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == const.VersionState.success.name

    # Version 2 with purge_on_delete false
    version = 2

    resources = [{'group': 'root',
                  'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
                  'id': 'std::File[vm1,path=/tmp/file1],v=%d' % version,
                  'owner': 'root',
                  'path': '/tmp/file1',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'purge_on_delete': False,
                  'version': version}]

    res = await client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = await client.release_version(environment, version, False)
    assert result.code == 200

    now = datetime.now()
    result = await aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == const.VersionState.success.name

    # Version 3 with no resources
    version = 3
    resources = []
    res = await client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    await agent.stop()


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
async def test_code_upload(server_multi, client_multi, agent_multi, environment_multi):
    """ Test upload of a single code definition
    """
    version = 1

    resources = [{'group': 'root',
                  'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
                  'id': 'std::File[vm1.dev.inmanta.com,path=/etc/sysconfig/network],v=%d' % version,
                  'owner': 'root',
                  'path': '/etc/sysconfig/network',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'version': version}]

    res = await client_multi.put_version(
        tid=environment_multi, version=version, resources=resources, unknowns=[], version_info={}
    )
    assert res.code == 200

    sources = make_source({}, "a.py", "std.test", "wlkvsdbhewvsbk vbLKBVWE wevbhbwhBH", [])
    sources = make_source(sources, "b.py", "std.xxx", "rvvWBVWHUvejIVJE UWEBVKW", ["pytest"])

    res = await client_multi.upload_code(tid=environment_multi, id=version, resource="std::File", sources=sources)
    assert res.code == 200

    res = await agent_multi._client.get_code(tid=environment_multi, id=version, resource="std::File")
    assert res.code == 200
    assert res.result["sources"] == sources


@pytest.mark.asyncio(timeout=30)
async def test_batched_code_upload(
    server_multi, client_multi, sync_client_multi, environment_multi, agent_multi, snippetcompiler
):
    """ Test uploading all code definitions at once
    """
    config.Config.set("compiler_rest_transport", "request_timeout", "1")

    snippetcompiler.setup_for_snippet("""
    h = std::Host(name="test", os=std::linux)
    f = std::ConfigFile(host=h, path="/etc/motd", content="test", purge_on_delete=true)
    """)
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
        assert len(source_info) == 1
        info = source_info[0]
        assert info.hash in res.result["sources"]
        code = res.result["sources"][info.hash]

        assert info.content == code[2]
        assert info.requires == code[3]


@pytest.mark.asyncio(timeout=30)
async def test_resource_action_log(server_multi, client_multi, environment_multi):
    version = 1
    resources = [{'group': 'root',
                  'hash': '89bf880a0dc5ffc1156c8d958b4960971370ee6a',
                  'id': 'std::File[vm1.dev.inmanta.com,path=/etc/sysconfig/network],v=%d' % version,
                  'owner': 'root',
                  'path': '/etc/sysconfig/network',
                  'permissions': 644,
                  'purged': False,
                  'reload': False,
                  'requires': [],
                  'version': version}]
    res = await client_multi.put_version(tid=environment_multi, version=version, resources=resources, unknowns=[],
                                         version_info={})
    assert res.code == 200

    resource_action_log = server.Server.get_resource_action_log_file(environment_multi)
    assert os.path.isfile(resource_action_log)
    assert os.stat(resource_action_log).st_size != 0


@pytest.mark.asyncio(timeout=30)
async def test_invalid_sid(server_multi, client_multi, environment_multi):
    """
        Test the server to manage the updates on a model during agent deploy
    """
    # request get_code with a compiler client that does not have a sid
    res = await client_multi.get_code(tid=environment_multi, id=1, resource="std::File")
    assert res.code == 400
    assert res.result["message"] == "Invalid request: this is an agent to server call, it should contain an agent session id"


@pytest.mark.asyncio(timeout=30)
async def test_get_param(server, client, environment):
    metadata = {"key1": "val1", "key2": "val2"}
    await client.set_param(environment, "param", "source", "val", "", metadata, False)
    await client.set_param(environment, "param2", "source2", "val2", "", {"a": "b"}, False)

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
