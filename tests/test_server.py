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

from utils import retry_limited
import pytest
from inmanta.agent.agent import Agent
from inmanta import data, protocol
from inmanta import const
from inmanta.server import config as opt
from datetime import datetime
from uuid import UUID
from inmanta.export import upload_code
from inmanta.util import hash_file

LOGGER = logging.getLogger(__name__)


@pytest.mark.gen_test(timeout=60)
@pytest.mark.slowtest
def test_autostart(server, client, environment):
    """
        Test auto start of agent
    """
    env = yield data.Environment.get_by_id(uuid.UUID(environment))
    yield env.set(data.AUTOSTART_AGENT_MAP, {"iaas_agent": "", "iaas_agentx": ""})

    yield server.agentmanager.ensure_agent_registered(env, "iaas_agent")
    yield server.agentmanager.ensure_agent_registered(env, "iaas_agentx")

    res = yield server.agentmanager._ensure_agents(env, ["iaas_agent"])
    assert res
    yield retry_limited(lambda: len(server._sessions) == 1, 20)
    assert len(server._sessions) == 1
    res = yield server.agentmanager._ensure_agents(env, ["iaas_agent"])
    assert not res
    assert len(server._sessions) == 1

    LOGGER.warning("Killing agent")
    server.agentmanager._agent_procs[env.id].terminate()
    yield retry_limited(lambda: len(server._sessions) == 0, 20)
    res = yield server.agentmanager._ensure_agents(env, ["iaas_agent"])
    assert res
    yield retry_limited(lambda: len(server._sessions) == 1, 3)
    assert len(server._sessions) == 1

    # second agent for same env
    res = yield server.agentmanager._ensure_agents(env, ["iaas_agentx"])
    assert res
    yield retry_limited(lambda: len(server._sessions) == 1, 20)
    assert len(server._sessions) == 1

    # Test stopping all agents
    yield server.agentmanager.stop_agents(env)
    assert len(server._sessions) == 0
    assert len(server.agentmanager._agent_procs) == 0


@pytest.mark.gen_test(timeout=60)
@pytest.mark.slowtest
def test_autostart_dual_env(client, server):
    """
        Test auto start of agent
    """
    result = yield client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    result = yield client.create_environment(project_id=project_id, name="devx")
    env_id2 = result.result["environment"]["id"]

    env = yield data.Environment.get_by_id(uuid.UUID(env_id))
    yield env.set(data.AUTOSTART_AGENT_MAP, {"iaas_agent": ""})

    env2 = yield data.Environment.get_by_id(uuid.UUID(env_id2))
    yield env2.set(data.AUTOSTART_AGENT_MAP, {"iaas_agent": ""})

    yield server.agentmanager.ensure_agent_registered(env, "iaas_agent")
    yield server.agentmanager.ensure_agent_registered(env2, "iaas_agent")

    res = yield server.agentmanager._ensure_agents(env, ["iaas_agent"])
    assert res
    yield retry_limited(lambda: len(server._sessions) == 1, 20)
    assert len(server._sessions) == 1

    res = yield server.agentmanager._ensure_agents(env2, ["iaas_agent"])
    assert res
    yield retry_limited(lambda: len(server._sessions) == 2, 20)
    assert len(server._sessions) == 2


@pytest.mark.gen_test(timeout=60)
@pytest.mark.slowtest
def test_autostart_batched(client, server, environment):
    """
        Test auto start of agent
    """
    env = yield data.Environment.get_by_id(uuid.UUID(environment))
    yield env.set(data.AUTOSTART_AGENT_MAP, {"iaas_agent": "", "iaas_agentx": ""})

    yield server.agentmanager.ensure_agent_registered(env, "iaas_agent")
    yield server.agentmanager.ensure_agent_registered(env, "iaas_agentx")

    res = yield server.agentmanager._ensure_agents(env, ["iaas_agent", "iaas_agentx"])
    assert res
    yield retry_limited(lambda: len(server._sessions) == 1, 20)
    assert len(server._sessions) == 1
    res = yield server.agentmanager._ensure_agents(env, ["iaas_agent"])
    assert not res
    assert len(server._sessions) == 1

    res = yield server.agentmanager._ensure_agents(env, ["iaas_agent", "iaas_agentx"])
    assert not res
    assert len(server._sessions) == 1

    LOGGER.warning("Killing agent")
    server.agentmanager._agent_procs[env.id].terminate()
    yield retry_limited(lambda: len(server._sessions) == 0, 20)
    res = yield server.agentmanager._ensure_agents(env, ["iaas_agent", "iaas_agentx"])
    assert res
    yield retry_limited(lambda: len(server._sessions) == 1, 3)
    assert len(server._sessions) == 1


@pytest.mark.gen_test(timeout=10)
def test_version_removal(client, server):
    """
        Test auto removal of older deploy model versions
    """
    result = yield client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    version = int(time.time())

    for _i in range(20):
        version += 1

        yield server._purge_versions()
        res = yield client.put_version(tid=env_id, version=version, resources=[], unknowns=[], version_info={})
        assert res.code == 200
        result = yield client.get_project(id=project_id)

        versions = yield client.list_versions(tid=env_id)
        assert versions.result["count"] <= opt.server_version_to_keep.get() + 1


@pytest.mark.gen_test(timeout=30)
@pytest.mark.slowtest
def test_get_resource_for_agent(io_loop, motor, server_multi, client_multi, environment):
    """
        Test the server to manage the updates on a model during agent deploy
    """
    agent = Agent(io_loop, "localhost", {"nvblah": "localhost"}, environment=environment)
    agent.start()
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

    res = yield client_multi.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    result = yield client_multi.list_versions(environment)
    assert result.code == 200
    assert result.result["count"] == 1

    result = yield client_multi.release_version(environment, version, push=False)
    assert result.code == 200

    result = yield client_multi.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == "deploying"

    result = yield aclient.get_resources_for_agent(environment, "vm1.dev.inmanta.com")
    assert result.code == 200
    assert len(result.result["resources"]) == 3

    action_id = uuid.uuid4()
    now = datetime.now()
    result = yield aclient.resource_action_update(environment,
                                                  ["std::File[vm1.dev.inmanta.com,path=/etc/sysconfig/network],v=%d" % version],
                                                  action_id, "deploy", now, now, "deployed", [], {})

    assert result.code == 200

    result = yield client_multi.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["done"] == 1

    action_id = uuid.uuid4()
    now = datetime.now()
    result = yield aclient.resource_action_update(environment,
                                                  ["std::File[vm1.dev.inmanta.com,path=/etc/hostname],v=%d" % version],
                                                  action_id, "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = yield client_multi.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["done"] == 2


@pytest.mark.gen_test(timeout=10)
def test_get_environment(client, server, environment):
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

        res = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
        assert res.code == 200

    result = yield client.get_environment(environment, versions=5, resources=1)
    assert(result.code == 200)
    assert(len(result.result["environment"]["versions"]) == 5)
    assert(len(result.result["environment"]["resources"]) == 9)


@pytest.mark.gen_test
def test_resource_update(io_loop, client, server, environment):
    """
        Test updating resources and logging
    """
    agent = Agent(io_loop, "localhost", {"blah": "localhost"}, environment=environment)
    agent.start()
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

    res = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert(res.code == 200)

    result = yield client.release_version(environment, version, push=False)
    assert result.code == 200

    resource_ids = [x["id"] for x in resources]

    # Start the deploy
    action_id = uuid.uuid4()
    now = datetime.now()
    result = yield aclient.resource_action_update(environment, resource_ids, action_id, "deploy", now)
    assert(result.code == 200)

    # Get the status from a resource
    result = yield client.get_resource(tid=environment, id=resource_ids[0], logs=True)
    assert(result.code == 200)
    logs = {x["action"]: x for x in result.result["logs"]}

    assert("deploy" in logs)
    assert("finished" not in logs["deploy"])
    assert("messages" not in logs["deploy"])
    assert("changes" not in logs["deploy"])

    # Send some logs
    result = yield aclient.resource_action_update(environment, resource_ids, action_id, "deploy",
                                                  messages=[data.LogLine.log(const.LogLevel.INFO,
                                                                             "Test log %(a)s %(b)s", a="a", b="b")])
    assert(result.code == 200)

    # Get the status from a resource
    result = yield client.get_resource(tid=environment, id=resource_ids[0], logs=True)
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
    result = yield aclient.resource_action_update(environment, resource_ids, action_id, "deploy", finished=now, changes=changes)
    assert(result.code == 500)

    result = yield aclient.resource_action_update(environment, resource_ids, action_id, "deploy", status="deployed",
                                                  finished=now, changes=changes)
    assert(result.code == 200)

    result = yield client.get_version(environment, version)
    assert(result.code == 200)
    assert result.result["model"]["done"] == 10


@pytest.mark.gen_test
def test_environment_settings(io_loop, client, server, environment):
    """
        Test environment settings
    """
    result = yield client.list_settings(tid=environment)
    assert result.code == 200
    assert "settings" in result.result
    assert "metadata" in result.result
    assert "auto_deploy" in result.result["metadata"]
    assert len(result.result["settings"]) == 0

    result = yield client.set_setting(tid=environment, id="auto_deploy", value="test")
    assert result.code == 500

    result = yield client.set_setting(tid=environment, id="auto_deploy", value=False)
    assert result.code == 200

    result = yield client.list_settings(tid=environment)
    assert result.code == 200
    assert len(result.result["settings"]) == 1

    result = yield client.get_setting(tid=environment, id="auto_deploy")
    assert result.code == 200
    assert not result.result["value"]

    result = yield client.get_setting(tid=environment, id="test2")
    assert result.code == 404

    result = yield client.set_setting(tid=environment, id="auto_deploy", value=True)
    assert result.code == 200

    result = yield client.get_setting(tid=environment, id="auto_deploy")
    assert result.code == 200
    assert result.result["value"]

    result = yield client.delete_setting(tid=environment, id="test2")
    assert result.code == 404

    result = yield client.delete_setting(tid=environment, id="auto_deploy")
    assert result.code == 200

    result = yield client.list_settings(tid=environment)
    assert result.code == 200
    assert "settings" in result.result
    assert len(result.result["settings"]) == 1

    result = yield client.set_setting(tid=environment, id=data.AUTOSTART_SPLAY, value=20)
    assert result.code == 200

    result = yield client.set_setting(tid=environment, id=data.AUTOSTART_SPLAY, value="30")
    assert result.code == 200

    result = yield client.get_setting(tid=environment, id=data.AUTOSTART_SPLAY)
    assert result.code == 200
    assert result.result["value"] == 30

    result = yield client.delete_setting(tid=environment, id=data.AUTOSTART_SPLAY)
    assert result.code == 200

    result = yield client.set_setting(tid=environment, id=data.AUTOSTART_AGENT_MAP, value={"agent1": "", "agent2": "localhost",
                                                                                           "agent3": "user@agent3"})
    assert result.code == 200

    result = yield client.set_setting(tid=environment, id=data.AUTOSTART_AGENT_MAP, value="")
    assert result.code == 500


@pytest.mark.gen_test
def test_clear_environment(client, server, environment):
    """
        Test clearing out an environment
    """
    version = int(time.time())
    result = yield client.put_version(tid=environment, version=version, resources=[], unknowns=[], version_info={})
    assert result.code == 200

    result = yield client.get_environment(id=environment, versions=10)
    assert result.code == 200
    assert len(result.result["environment"]["versions"]) == 1

    result = yield client.clear_environment(id=environment)
    assert result.code == 200

    result = yield client.get_environment(id=environment, versions=10)
    assert result.code == 200
    assert len(result.result["environment"]["versions"]) == 0


@pytest.mark.gen_test
def test_purge_on_delete_requires(io_loop, client, server, environment):
    """
        Test purge on delete of resources and inversion of requires
    """
    agent = Agent(io_loop, "localhost", {"blah": "localhost"}, environment=environment)
    agent.start()
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

    res = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = yield client.release_version(environment, version, push=False)
    assert result.code == 200

    now = datetime.now()
    result = yield aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = yield aclient.resource_action_update(environment,
                                                  ['std::File[vm2,path=/tmp/file2],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = yield client.get_version(environment, version)
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

    result = yield client.decomission_environment(id=environment)
    assert result.code == 200

    version = result.result["version"]
    result = yield client.get_version(environment, version)
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


@pytest.mark.gen_test
def test_purge_on_delete(io_loop, client, server, environment):
    """
        Test purge on delete of resources
    """
    agent = Agent(io_loop, "localhost", {"blah": "localhost"}, environment=environment)
    agent.start()
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

    res = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = yield client.release_version(environment, version, push=False)
    assert result.code == 200

    now = datetime.now()
    result = yield aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = yield aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file2],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = yield aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file3],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = yield client.get_version(environment, version)
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
    res = yield client.put_version(tid=environment, version=version, resources=[res3], unknowns=[], version_info={})
    assert result.code == 200

    result = yield client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["total"] == 3

    # validate requires and provides
    file1 = [x for x in result.result["resources"] if "file1" in x["id"]][0]
    file2 = [x for x in result.result["resources"] if "file2" in x["id"]][0]
    file3 = [x for x in result.result["resources"] if "file3" in x["id"]][0]

    assert file1["attributes"]["purged"]
    assert file2["attributes"]["purged"]
    assert not file3["attributes"]["purged"]


@pytest.mark.gen_test
def test_purge_on_delete_ignore(io_loop, client, server, environment):
    """
        Test purge on delete behavior for resources that have not longer purged_on_delete set
    """
    agent = Agent(io_loop, "localhost", {"blah": "localhost"}, environment=environment)
    agent.start()
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

    res = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = yield client.release_version(environment, version, push=False)
    assert result.code == 200

    now = datetime.now()
    result = yield aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = yield client.get_version(environment, version)
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

    res = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    # Release the model and set all resources as deployed
    result = yield client.release_version(environment, version, push=False)
    assert result.code == 200

    now = datetime.now()
    result = yield aclient.resource_action_update(environment,
                                                  ['std::File[vm1,path=/tmp/file1],v=%d' % version],
                                                  uuid.uuid4(), "deploy", now, now, "deployed", [], {})
    assert result.code == 200

    result = yield client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["released"]
    assert result.result["model"]["result"] == const.VersionState.success.name

    # Version 3 with no resources
    version = 3
    resources = []
    res = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    result = yield client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)


@pytest.mark.gen_test
def test_tokens(server_multi, client_multi, environment):
    # Test using API tokens
    test_token = client_multi._transport_instance.token
    token = yield client_multi.create_token(environment, ["api"], idempotent=True)
    jot = token.result["token"]

    assert jot != test_token

    client_multi._transport_instance.token = jot

    # try to access a non environment call (global)
    result = yield client_multi.list_environments()
    assert result.code == 403

    result = yield client_multi.list_versions(environment)
    assert result.code == 200

    token = yield client_multi.create_token(environment, ["agent"], idempotent=True)
    agent_jot = token.result["token"]

    client_multi._transport_instance.token = agent_jot
    result = yield client_multi.list_versions(environment)
    assert result.code == 403


def make_source(collector, filename, module, source, req):
    myhash = hash_file(source.encode())
    collector[myhash] = [filename, module, source, req]
    return collector


@pytest.mark.gen_test(timeout=30)
def test_code_upload(io_loop, motor, server_multi, client_multi, environment):
    """
        Test the server to manage the updates on a model during agent deploy
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

    res = yield client_multi.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    sources = make_source({}, "a.py", "std.test", "wlkvsdbhewvsbk vbLKBVWE wevbhbwhBH", [])
    sources = make_source(sources, "b.py", "std.xxx", "rvvWBVWHUvejIVJE UWEBVKW", ["pytest"])

    res = yield client_multi.upload_code(tid=environment, id=version, resource="std::File", sources=sources)
    assert res.code == 200

    agent = protocol.Client("agent")

    res = yield agent.get_code(tid=environment, id=version, resource="std::File")
    assert res.code == 200
    assert res.result["sources"] == sources


@pytest.mark.gen_test(timeout=30)
def test_batched_code_upload(io_loop, motor, server_multi, client_multi, environment):
    """
        Test the server to manage the updates on a model during agent deploy
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

    res = yield client_multi.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    asources = make_source({}, "a.py", "std.test", "wlkvsdbhewvsbk vbLKBVWE wevbhbwhBH", [])
    asources = make_source(asources, "b.py", "std.xxx", "rvvWBVWHUvejIVJE UWEBVKW", ["pytest"])

    bsources = make_source({}, "a.py", "std.test", "wlkvsdbhewvsbk vbLKBVWE wevbhbwhBH", [])
    bsources = make_source(bsources, "c.py", "std.xxx", "enhkahEUWLGBVFEHJ UWEBVKW", ["pytest"])

    csources = make_source({}, "a.py", "sss", "ujekncedsiekvsd", [])

    sources = {"std::File": asources,
               "std::Other": bsources,
               "std:xxx": csources
               }

    yield upload_code(client_multi, environment, version, sources)

    agent = protocol.Client("agent")

    for name, sourcemap in sources.items():
        res = yield agent.get_code(tid=environment, id=version, resource=name)
        assert res.code == 200
        assert res.result["sources"] == sourcemap


@pytest.mark.gen_test(timeout=30)
def test_legacy_code(io_loop, motor, server_multi, client_multi, environment):
    """
        Test the server to manage the updates on a model during agent deploy
    """
    version = 2

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

    res = yield client_multi.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    sources = {"a.py": "ujeknceds", "b.py": "weknewbevbvebedsvb"}

    code = data.Code(environment=UUID(environment), version=version, resource="std::File", sources=sources)
    yield code.insert()

    agent = protocol.Client("agent")

    res = yield agent.get_code(tid=environment, id=version, resource="std::File")
    assert res.code == 200
    assert res.result["sources"] == sources
