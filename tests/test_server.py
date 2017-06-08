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
from inmanta import data
from inmanta import const
from datetime import datetime

LOGGER = logging.getLogger(__name__)


@pytest.mark.gen_test(timeout=60)
@pytest.mark.slowtest
def test_autostart(server, client, environment):
    """
        Test auto start of agent
    """
    env = yield data.Environment.get_by_id(uuid.UUID(environment))

    yield server.agentmanager.ensure_agent_registered(env, "iaas_jos")
    yield server.agentmanager.ensure_agent_registered(env, "iaas_josx")

    res = yield server.agentmanager._ensure_agent(environment, "iaas_jos")
    assert res
    yield retry_limited(lambda: len(server._sessions) == 1, 20)
    assert len(server._sessions) == 1
    res = yield server.agentmanager._ensure_agent(environment, "iaas_jos")
    assert not res
    assert len(server._sessions) == 1

    LOGGER.warning("Killing agent")
    server.agentmanager._requires_agents[environment]["process"].terminate()
    yield retry_limited(lambda: len(server._sessions) == 0, 20)
    res = yield server.agentmanager._ensure_agent(environment, "iaas_jos")
    assert res
    yield retry_limited(lambda: len(server._sessions) == 1, 3)
    assert len(server._sessions) == 1

    # second agent for same env
    res = yield server.agentmanager._ensure_agent(environment, "iaas_josx")
    assert res
    yield retry_limited(lambda: len(server._sessions) == 1, 20)
    assert len(server._sessions) == 1


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
    env2 = yield data.Environment.get_by_id(uuid.UUID(env_id2))

    yield server.agentmanager.ensure_agent_registered(env, "iaas_jos")
    yield server.agentmanager.ensure_agent_registered(env2, "iaas_jos")

    res = yield server.agentmanager._ensure_agent(env_id, "iaas_jos")
    assert res
    yield retry_limited(lambda: len(server._sessions) == 1, 20)
    assert len(server._sessions) == 1

    res = yield server.agentmanager._ensure_agent(env_id2, "iaas_jos")
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

    yield server.agentmanager.ensure_agent_registered(env, "iaas_jos")
    yield server.agentmanager.ensure_agent_registered(env, "iaas_josx")

    res = yield server.agentmanager._ensure_agents(environment, ["iaas_jos", "iaas_josx"])
    assert res
    yield retry_limited(lambda: len(server._sessions) == 1, 20)
    assert len(server._sessions) == 1
    res = yield server.agentmanager._ensure_agent(environment, "iaas_jos")
    assert not res
    assert len(server._sessions) == 1

    res = yield server.agentmanager._ensure_agents(environment, ["iaas_jos", "iaas_josx"])
    assert not res
    assert len(server._sessions) == 1

    LOGGER.warning("Killing agent")
    server.agentmanager._requires_agents[environment]["process"].terminate()
    yield retry_limited(lambda: len(server._sessions) == 0, 20)
    res = yield server.agentmanager._ensure_agents(environment, ["iaas_jos", "iaas_josx"])
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
        assert res.code, 200
        result = yield client.get_project(id=project_id)

        versions = yield client.list_versions(tid=env_id)
        assert versions.result["count"] <= 3


@pytest.mark.gen_test(timeout=30)
@pytest.mark.slowtest
def test_get_resource_for_agent(io_loop, motor, server_multi, client, environment):
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

    res = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert res.code == 200

    result = yield client.list_versions(environment)
    assert result.code == 200
    assert result.result["count"] == 1

    result = yield client.release_version(environment, version, push=False)
    assert result.code == 200

    result = yield client.get_version(environment, version)
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

    result = yield client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["done"] == 1

    action_id = uuid.uuid4()
    now = datetime.now()
    result = yield aclient.resource_action_update(environment,
                                                  ["std::File[vm1.dev.inmanta.com,path=/etc/hostname],v=%d" % version],
                                                  action_id, "deploy", now, now, "deployed", [], {})
    print(result.result)
    assert result.code == 200

    result = yield client.get_version(environment, version)
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
