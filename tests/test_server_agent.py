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
from collections import defaultdict
import time
import json
import uuid
from threading import Condition
import logging


from tornado import gen

from inmanta import agent, data
from inmanta.agent.handler import provider, ResourceHandler
from inmanta.resources import resource, Resource
import pytest
from inmanta.agent.agent import Agent
from utils import retry_limited, assertEqualIsh, UNKWN
from inmanta.config import Config
from inmanta.server.server import Server

logger = logging.getLogger("inmanta.test.server_agent")


@resource("test::Resource", agent="agent", id_attribute="key")
class Resource(Resource):
    """
        A file on a filesystem
    """
    fields = ("key", "value", "purged", "state_id", "allow_snapshot", "allow_restore")


@resource("test::Fail", agent="agent", id_attribute="key")
class FailR(Resource):
    """
        A file on a filesystem
    """
    fields = ("key", "value", "purged", "state_id", "allow_snapshot", "allow_restore")


@resource("test::Wait", agent="agent", id_attribute="key")
class WaitR(Resource):
    """
        A file on a filesystem
    """
    fields = ("key", "value", "purged", "state_id", "allow_snapshot", "allow_restore")


@provider("test::Resource", name="test_resource")
class Provider(ResourceHandler):

    def check_resource(self, resource):
        current = resource.clone()
        current.purged = not Provider.isset(resource.id.get_agent_name(), resource.key)

        if not current.purged:
            current.value = Provider.get(resource.id.get_agent_name(), resource.key)
        else:
            current.value = None

        return current

    def list_changes(self, desired):
        current = self.check_resource(desired)
        return self._diff(current, desired)

    def do_changes(self, resource):
        changes = self.list_changes(resource)
        if "purged" in changes:
            if changes["purged"][1]:
                Provider.delete(resource.id.get_agent_name(), resource.key)
            else:
                Provider.set(resource.id.get_agent_name(), resource.key, resource.value)

        if "value" in changes:
            Provider.set(resource.id.get_agent_name(), resource.key, resource.value)

        return changes

    def snapshot(self, resource):
        return json.dumps({"value": Provider.get(resource.id.get_agent_name(), resource.key), "metadata": "1234"}).encode()

    def restore(self, resource, snapshot_id):
        content = self.get_file(snapshot_id)
        if content is None:
            return

        data = json.loads(content.decode())
        if "value" in data:
            Provider.set(resource.id.get_agent_name(), resource.key, data["value"])

    def facts(self, resource):
        return {"length": len(Provider.get(resource.id.get_agent_name(), resource.key)), "key1": "value1", "key2": "value2"}

    _STATE = defaultdict(dict)

    @classmethod
    def set(cls, agent, key, value):
        cls._STATE[agent][key] = value

    @classmethod
    def get(cls, agent, key):
        if key in cls._STATE[agent]:
            return cls._STATE[agent][key]
        return None

    @classmethod
    def isset(cls, agent, key):
        return key in cls._STATE[agent]

    @classmethod
    def delete(cls, agent, key):
        if cls.isset(agent, key):
            del cls._STATE[agent][key]

    @classmethod
    def reset(cls):
        cls._STATE = defaultdict(dict)


@provider("test::Fail", name="test_fail")
class Fail(ResourceHandler):

    def check_resource(self, resource):
        current = resource.clone()
        current.purged = not Provider.isset(resource.id.get_agent_name(), resource.key)

        if not current.purged:
            current.value = Provider.get(resource.id.get_agent_name(), resource.key)
        else:
            current.value = None

        return current

    def list_changes(self, desired):
        current = self.check_resource(desired)
        return self._diff(current, desired)

    def do_changes(self, resource):
        raise Exception()

waiter = Condition()


@gen.coroutine
def waitForDoneWithWaiters(client, env_id, version):
    # unhang waiters
    result = yield client.get_version(env_id, version)
    assert result.code == 200
    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(env_id, version)
        logger.info("waiting with waiters, %s resources done", result.result["model"]["done"])
        if result.result["model"]["done"] > 0:
            waiter.acquire()
            waiter.notifyAll()
            waiter.release()
        yield gen.sleep(0.1)
    return result


@provider("test::Wait", name="test_wait")
class Wait(ResourceHandler):

    def __init__(self, agent, io=None):
        super().__init__(agent, io)
        self.traceid = uuid.uuid4()

    def check_resource(self, resource):
        current = resource.clone()
        current.purged = not Provider.isset(resource.id.get_agent_name(), resource.key)

        if not current.purged:
            current.value = Provider.get(resource.id.get_agent_name(), resource.key)
        else:
            current.value = None

        return current

    def list_changes(self, desired):
        current = self.check_resource(desired)
        return self._diff(current, desired)

    def do_changes(self, resource):
        logger.info("Haning waiter %s", self.traceid)
        waiter.acquire()
        waiter.wait()
        waiter.release()
        logger.info("Releasing waiter %s", self.traceid)
        changes = self.list_changes(resource)
        if "purged" in changes:
            if changes["purged"][1]:
                Provider.delete(resource.id.get_agent_name(), resource.key)
            else:
                Provider.set(resource.id.get_agent_name(), resource.key, resource.value)

        if "value" in changes:
            Provider.set(resource.id.get_agent_name(), resource.key, resource.value)

        return changes


@pytest.mark.gen_test
def test_dryrun_and_deploy(io_loop, server, client):
    """
        dryrun and deploy a configuration model
    """
    Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", env_id=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    Provider.set("agent1", "key2", "incorrect_value")
    Provider.set("agent1", "key3", "value")

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Resource[agent1,key=key2],v=%d' % version],
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key3',
                  'value': None,
                  'id': 'test::Resource[agent1,key=key3],v=%d' % version,
                  'requires': [],
                  'purged': True,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }
                 ]

    result = yield client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # request a dryrun
    result = yield client.dryrun_request(env_id, version)
    assert result.code == 200
    assert result.result["dryrun"]["total"] == len(resources)
    assert result.result["dryrun"]["todo"] == len(resources)

    # get the dryrun results
    result = yield client.dryrun_list(env_id, version)
    assert result.code == 200
    assert len(result.result["dryruns"]) == 1

    while result.result["dryruns"][0]["todo"] > 0:
        result = yield client.dryrun_list(env_id, version)
        yield gen.sleep(0.1)

    dry_run_id = result.result["dryruns"][0]["id"]
    result = yield client.dryrun_report(env_id, dry_run_id)
    assert result.code == 200

    changes = result.result["dryrun"]["resources"]
    assert changes[resources[0]["id"]]["changes"]["purged"][0]
    assert not changes[resources[0]["id"]]["changes"]["purged"][1]
    assert changes[resources[0]["id"]]["changes"]["value"][0] is None
    assert changes[resources[0]["id"]]["changes"]["value"][1] == resources[0]["value"]

    assert changes[resources[1]["id"]]["changes"]["value"][0] == "incorrect_value"
    assert changes[resources[1]["id"]]["changes"]["value"][1] == resources[1]["value"]

    assert not changes[resources[2]["id"]]["changes"]["purged"][0]
    assert changes[resources[2]["id"]]["changes"]["purged"][1]

    # do a deploy
    result = yield client.release_version(env_id, version, True)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 3
    assert result.result["model"]["result"] == "deploying"

    result = yield client.get_version(env_id, version)
    assert result.code == 200

    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(env_id, version)
        yield gen.sleep(0.1)

    assert result.result["model"]["done"] == len(resources)

    assert Provider.isset("agent1", "key1")
    assert Provider.get("agent1", "key1") == "value1"
    assert Provider.get("agent1", "key2") == "value2"
    assert not Provider.isset("agent1", "key3")

    agent.stop()


@pytest.mark.gen_test(timeout=30)
def test_server_restart(io_loop, server, mongo_db, client):
    """
        dryrun and deploy a configuration model
    """
    Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", env_id=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    Provider.set("agent1", "key2", "incorrect_value")
    Provider.set("agent1", "key3", "value")

    server.stop()

    server = Server(database_host="localhost", database_port=int(mongo_db.port), io_loop=io_loop)
    server.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Resource[agent1,key=key2],v=%d' % version],
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key3',
                  'value': None,
                  'id': 'test::Resource[agent1,key=key3],v=%d' % version,
                  'requires': [],
                  'purged': True,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }
                 ]

    result = yield client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # request a dryrun
    result = yield client.dryrun_request(env_id, version)
    assert result.code == 200
    assert result.result["dryrun"]["total"] == len(resources)
    assert result.result["dryrun"]["todo"] == len(resources)

    # get the dryrun results
    result = yield client.dryrun_list(env_id, version)
    assert result.code == 200
    assert len(result.result["dryruns"]) == 1

    while result.result["dryruns"][0]["todo"] > 0:
        result = yield client.dryrun_list(env_id, version)
        yield gen.sleep(0.1)

    dry_run_id = result.result["dryruns"][0]["id"]
    result = yield client.dryrun_report(env_id, dry_run_id)
    assert result.code == 200

    changes = result.result["dryrun"]["resources"]
    assert changes[resources[0]["id"]]["changes"]["purged"][0]
    assert not changes[resources[0]["id"]]["changes"]["purged"][1]
    assert changes[resources[0]["id"]]["changes"]["value"][0] is None
    assert changes[resources[0]["id"]]["changes"]["value"][1] == resources[0]["value"]

    assert changes[resources[1]["id"]]["changes"]["value"][0] == "incorrect_value"
    assert changes[resources[1]["id"]]["changes"]["value"][1] == resources[1]["value"]

    assert not changes[resources[2]["id"]]["changes"]["purged"][0]
    assert changes[resources[2]["id"]]["changes"]["purged"][1]

    # do a deploy
    result = yield client.release_version(env_id, version, True)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 3
    assert result.result["model"]["result"] == "deploying"

    result = yield client.get_version(env_id, version)
    assert result.code == 200

    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(env_id, version)
        yield gen.sleep(0.1)

    assert result.result["model"]["done"] == len(resources)

    assert Provider.isset("agent1", "key1")
    assert Provider.get("agent1", "key1") == "value1"
    assert Provider.get("agent1", "key2") == "value2"
    assert not Provider.isset("agent1", "key3")

    agent.stop()
    server.stop()


@pytest.mark.gen_test(timeout=30)
def test_spontaneous_deploy(io_loop, server, client):
    """
        dryrun and deploy a configuration model
    """
    Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    Config.set("config", "agent-interval", "2")
    Config.set("config", "agent-splay", "2")

    agent = Agent(io_loop, hostname="node1", env_id=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    Provider.set("agent1", "key2", "incorrect_value")
    Provider.set("agent1", "key3", "value")

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Resource[agent1,key=key2],v=%d' % version],
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key3',
                  'value': None,
                  'id': 'test::Resource[agent1,key=key3],v=%d' % version,
                  'requires': [],
                  'purged': True,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }
                 ]

    result = yield client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # do a deploy
    result = yield client.release_version(env_id, version, False)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 3
    assert result.result["model"]["result"] == "deploying"

    result = yield client.get_version(env_id, version)
    assert result.code == 200

    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(env_id, version)
        yield gen.sleep(0.1)

    assert result.result["model"]["done"] == len(resources)

    assert Provider.isset("agent1", "key1")
    assert Provider.get("agent1", "key1") == "value1"
    assert Provider.get("agent1", "key2") == "value2"
    assert not Provider.isset("agent1", "key3")

    agent.stop()


@pytest.mark.gen_test
def test_dual_agent(io_loop, server, client):
    """
        dryrun and deploy a configuration model
    """
    Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    myagent = agent.Agent(io_loop, hostname="node1", env_id=env_id,
                          agent_map={"agent1": "localhost", "agent2": "localhost"},
                          code_loader=False)
    myagent.add_end_point_name("agent1")
    myagent.add_end_point_name("agent2")
    myagent.start()
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    Provider.set("agent1", "key1", "incorrect_value")
    Provider.set("agent2", "key1", "incorrect_value")

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Wait[agent1,key=key1],v=%d' % version,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': []
                  },
                 {'key': 'key2',
                  'value': 'value1',
                  'id': 'test::Wait[agent1,key=key2],v=%d' % version,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Wait[agent1,key=key1],v=%d' % version]
                  },
                 {'key': 'key1',
                  'value': 'value2',
                  'id': 'test::Wait[agent2,key=key1],v=%d' % version,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': []
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Wait[agent2,key=key2],v=%d' % version,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Wait[agent2,key=key1],v=%d' % version]
                  }]

    result = yield client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # do a deploy
    result = yield client.release_version(env_id, version, True)
    assert result.code == 200

    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 4

    result = yield client.get_version(env_id, version)
    assert result.code == 200

    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(env_id, version)
        waiter.acquire()
        waiter.notifyAll()
        waiter.release()
        yield gen.sleep(0.1)

    assert result.result["model"]["done"] == len(resources)

    assert Provider.isset("agent1", "key1")
    assert Provider.get("agent1", "key1") == "value1"
    assert Provider.get("agent2", "key1") == "value2"
    assert Provider.get("agent1", "key2") == "value1"
    assert Provider.get("agent2", "key2") == "value2"

    myagent.stop()


@pytest.mark.gen_test
def test_snapshot_restore(client, server, io_loop):
    """
        create a snapshot and restore it again
    """
    Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", env_id=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    Provider.set("agent1", "key", "value")

    version = int(time.time())

    resources = [{'key': 'key',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key2',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }]

    result = yield client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # deploy and wait until done
    result = yield client.release_version(env_id, version, True)
    assert result.code == 200

    result = yield client.get_version(env_id, version)
    assert result.code == 200
    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(env_id, version)
        yield gen.sleep(0.1)

    assert result.result["model"]["done"] == len(resources)

    # create a snapshot
    result = yield client.create_snapshot(env_id, "snap1")
    assert result.code == 200
    snapshot_id = result.result["snapshot"]["id"]

    result = yield client.list_snapshots(env_id)
    assert result.code == 200
    assert len(result.result["snapshots"]) == 1
    assert result.result["snapshots"][0]["id"] == snapshot_id

    while result.result["snapshots"][0]["finished"] is None:
        result = yield client.list_snapshots(env_id)
        assert result.code == 200
        yield gen.sleep(0.1)

    # Change the value of the resource
    Provider.set("agent1", "key", "other")

    # try to do a restore
    result = yield client.restore_snapshot(env_id, snapshot_id)
    assert result.code == 200
    restore_id = result.result["restore"]["id"]

    result = yield client.list_restores(env_id)
    assert result.code == 200
    assert len(result.result["restores"]) == 1

    result = yield client.get_restore_status(env_id, restore_id)
    assert result.code == 200
    while result.result["restore"]["finished"] is None:
        result = yield client.get_restore_status(env_id, restore_id)
        assert result.code == 200
        yield gen.sleep(0.1)

    assert Provider.get("agent1", "key") == "value"


@pytest.mark.gen_test
def test_server_agent_api(client, server, io_loop):
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]
    agent = Agent(io_loop, env_id=env_id, hostname="agent1", agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.start()
    yield gen.sleep(0.1)
    agent = Agent(io_loop, env_id=env_id, hostname="agent2", agent_map={"agent2": "localhost"},
                  code_loader=False)
    agent.start()

    yield retry_limited(lambda: len(server.agentmanager.sessions) == 2, 10)
    assert len(server.agentmanager.sessions) == 2

    result = yield client.list_agent_processes(env_id)
    assert result.code == 200
    assertEqualIsh({'processes': [{'expired': None, 'environment': env_id, 'endpoints':
                                   [{'name': 'agent1', 'process': UNKWN, 'id': UNKWN}], 'id': UNKWN,
                                   'hostname': UNKWN, 'first_seen': UNKWN, 'last_seen': UNKWN},
                                  {'expired': None, 'environment': env_id, 'endpoints':
                                   [{'name': 'agent2', 'process': UNKWN, 'id': UNKWN}], 'id': UNKWN,
                                   'hostname': UNKWN, 'first_seen': UNKWN, 'last_seen': UNKWN}]},
                   result.result, ['name', 'first_seen'])

    agentid = result.result["processes"][0]["id"]
    endpointid = result.result["processes"][0]["endpoints"][0]["id"]

    result = yield client.get_agent_process(id=agentid)
    assert result.code == 200

    result = yield client.get_agent_process(id=uuid.uuid4())
    assert result.code == 404

    version = int(time.time())

    resources = [{'key': 'key',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key2',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }]

    result = yield client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    result = yield client.list_agents(tid=env_id)
    assert result.code == 200

    shouldbe = {'agents': [
        {'last_failover': UNKWN, 'environment': env_id, 'paused': False,
         'primary': endpointid, 'name': 'agent1', 'state': 'up'}]}

    assertEqualIsh(shouldbe, result.result)

    result = yield client.list_agents(tid=uuid.uuid4())
    assert result.code == 404


@pytest.mark.gen_test
def test_get_facts(client, server, io_loop):
    """
        Test retrieving facts from the agent
    """
    Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", env_id=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    Provider.set("agent1", "key", "value")

    version = int(time.time())

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{'key': 'key',
                  'value': 'value',
                  'id': resource_id,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }]

    result = yield client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200
    result = yield client.release_version(env_id, version, True)
    assert result.code == 200

    result = yield client.get_param(env_id, "length", resource_id_wov)
    assert result.code == 503

    env = yield data.Environment.get_uuid(env_id)

    params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                 resource_id=resource_id_wov).find_all()  # @UndefinedVariable
    while len(params) < 3:
        params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                     resource_id=resource_id_wov).find_all()  # @UndefinedVariable
        yield gen.sleep(0.1)

    result = yield client.get_param(env_id, "key1", resource_id_wov)
    assert result.code == 200


@pytest.mark.gen_test
def test_get_set_param(client, server, io_loop):
    """
        Test getting and setting params
    """
    Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    result = yield client.set_param(tid=env_id, id="key10", value="value10", source="user")
    assert result.code == 200


@pytest.mark.gen_test
def test_unkown_parameters(client, server, io_loop):
    """
        Test retrieving facts from the agent
    """
    Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", env_id=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    Provider.set("agent1", "key", "value")

    version = int(time.time())

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{'key': 'key',
                  'value': 'value',
                  'id': resource_id,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }]

    unknowns = [{"resource": resource_id_wov, "parameter": "length", "source": "fact"}]
    result = yield client.put_version(tid=env_id, version=version, resources=resources, unknowns=unknowns,
                                      version_info={})
    assert result.code == 200

    result = yield client.release_version(env_id, version, True)
    assert result.code == 200

    yield server.renew_expired_facts()

    env = yield data.Environment.get_uuid(env_id)

    params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                 resource_id=resource_id_wov).find_all()  # @UndefinedVariable
    while len(params) < 3:
        params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                     resource_id=resource_id_wov).find_all()  # @UndefinedVariable
        yield gen.sleep(0.1)

    result = yield client.get_param(env_id, "length", resource_id_wov)
    assert result.code == 200


@pytest.mark.gen_test()
def test_fail(client, server, io_loop):
    """
        Test results when a step fails
    """
    Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", env_id=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False, poolsize=10)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    Provider.set("agent1", "key", "value")

    version = int(time.time())

    resources = [{'key': 'key',
                  'value': 'value',
                  'id': 'test::Fail[agent1,key=key],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key2',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'requires': ['test::Fail[agent1,key=key],v=%d' % version],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key3',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key3],v=%d' % version,
                  'requires': ['test::Fail[agent1,key=key],v=%d' % version],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key4',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key4],v=%d' % version,
                  'requires': ['test::Resource[agent1,key=key3],v=%d' % version],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key5',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key5],v=%d' % version,
                  'requires': ['test::Resource[agent1,key=key4],v=%d' % version,
                               'test::Fail[agent1,key=key],v=%d' % version],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }]

    result = yield client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # deploy and wait until done
    result = yield client.release_version(env_id, version, True)
    assert result.code == 200

    result = yield client.get_version(env_id, version)
    assert result.code == 200
    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(env_id, version)
        yield gen.sleep(0.1)

    assert result.result["model"]["done"] == len(resources)

    states = {x["id"]: x["status"] for x in result.result["resources"]}

    assert states['test::Fail[agent1,key=key],v=%d' % version] == "failed"
    assert states['test::Resource[agent1,key=key2],v=%d' % version] == "skipped"
    assert states['test::Resource[agent1,key=key3],v=%d' % version] == "skipped"
    assert states['test::Resource[agent1,key=key4],v=%d' % version] == "skipped"
    assert states['test::Resource[agent1,key=key5],v=%d' % version] == "skipped"


@pytest.mark.gen_test
def test_wait(client, server, io_loop):
    """
        If this test fail due to timeout,
        this is probably due to the mechanism in the agent that prevents pulling resources in very rapp\id succession.

        If the test server is slow, a get_resources call takes a long time,
        this makes the back-off longer

        this test deploys two models in rapid successions, if the server is slow, this may fail due to the back-off
    """
    Provider.reset()

    # setup project
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    # setup env
    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    # setup agent
    agent = Agent(io_loop, hostname="node1", env_id=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False, poolsize=10)
    agent.add_end_point_name("agent1")
    agent.start()

    # wait for agent
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    # set the deploy environment
    Provider.set("agent1", "key", "value")

    def makeVersion(offset=0):
        version = int(time.time() + offset)

        resources = [{'key': 'key',
                      'value': 'value',
                      'id': 'test::Wait[agent1,key=key],v=%d' % version,
                      'requires': [],
                      'purged': False,
                      'state_id': '',
                      'allow_restore': True,
                      'allow_snapshot': True,
                      },
                     {'key': 'key2',
                      'value': 'value',
                      'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                      'requires': ['test::Wait[agent1,key=key],v=%d' % version],
                      'purged': False,
                      'state_id': '',
                      'allow_restore': True,
                      'allow_snapshot': True,
                      },
                     {'key': 'key3',
                      'value': 'value',
                      'id': 'test::Resource[agent1,key=key3],v=%d' % version,
                      'requires': [],
                      'purged': False,
                      'state_id': '',
                      'allow_restore': True,
                      'allow_snapshot': True,
                      },
                     {'key': 'key4',
                      'value': 'value',
                      'id': 'test::Resource[agent1,key=key4],v=%d' % version,
                      'requires': ['test::Resource[agent1,key=key3],v=%d' % version],
                      'purged': False,
                      'state_id': '',
                      'allow_restore': True,
                      'allow_snapshot': True,
                      },
                     {'key': 'key5',
                      'value': 'value',
                      'id': 'test::Resource[agent1,key=key5],v=%d' % version,
                      'requires': ['test::Resource[agent1,key=key4],v=%d' % version,
                                   'test::Wait[agent1,key=key],v=%d' % version],
                      'purged': False,
                      'state_id': '',
                      'allow_restore': True,
                      'allow_snapshot': True,
                      }]
        return version, resources

    @gen.coroutine
    def waitForResources(version, n):
        result = yield client.get_version(env_id, version)
        assert result.code == 200

        while result.result["model"]["done"] < n:
            result = yield client.get_version(env_id, version)
            yield gen.sleep(0.1)
        assert result.result["model"]["done"] == n

    logger.info("setup done")

    version1, resources = makeVersion()
    result = yield client.put_version(tid=env_id, version=version1, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    logger.info("first version pushed")

    # deploy and wait until one is ready
    result = yield client.release_version(env_id, version1, True)
    assert result.code == 200

    logger.info("first version released")

    yield waitForResources(version1, 2)

    logger.info("first version, 2 resources deployed")

    version2, resources = makeVersion(3)
    result = yield client.put_version(tid=env_id, version=version2, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    logger.info("second version pushed %f", time.time())

    yield gen.sleep(1)

    logger.info("wait to expire load limiting%f", time.time())

    # deploy and wait until done
    result = yield client.release_version(env_id, version2, True)
    assert result.code == 200

    logger.info("second version released")

    yield waitForDoneWithWaiters(client, env_id, version2)

    logger.info("second version complete")

    result = yield client.get_version(env_id, version2)
    assert result.code == 200
    for x in result.result["resources"]:
        assert x["status"] == "deployed"

    result = yield client.get_version(env_id, version1)
    assert result.code == 200
    states = {x["id"]: x["status"] for x in result.result["resources"]}

    assert states['test::Wait[agent1,key=key],v=%d' % version1] == "deployed"
    assert states['test::Resource[agent1,key=key2],v=%d' % version1] == ""
    assert states['test::Resource[agent1,key=key3],v=%d' % version1] == "deployed"
    assert states['test::Resource[agent1,key=key4],v=%d' % version1] == "deployed"
    assert states['test::Resource[agent1,key=key5],v=%d' % version1] == ""


@pytest.mark.gen_test
def test_cross_agent_deps(io_loop, server, client):
    """
        deploy a configuration model with cross host dependency
    """
    Provider.reset()
    # config for recovery mechanism
    Config.set("config", "agent-interval", "10")
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", env_id=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    agent2 = Agent(io_loop, hostname="node2", env_id=env_id, agent_map={"agent2": "localhost"},
                   code_loader=False)
    agent2.add_end_point_name("agent2")
    agent2.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 2, 10)

    Provider.set("agent1", "key2", "incorrect_value")
    Provider.set("agent1", "key3", "value")

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Wait[agent1,key=key2],v=%d' % version, 'test::Resource[agent2,key=key3],v=%d' % version],
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Wait[agent1,key=key2],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key3',
                  'value': 'value3',
                  'id': 'test::Resource[agent2,key=key3],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key4',
                  'value': 'value4',
                  'id': 'test::Resource[agent2,key=key4],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }
                 ]

    result = yield client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # do a deploy
    result = yield client.release_version(env_id, version, True)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 4
    assert result.result["model"]["result"] == "deploying"

    result = yield client.get_version(env_id, version)
    assert result.code == 200

    while result.result["model"]["done"] == 0:
        result = yield client.get_version(env_id, version)
        yield gen.sleep(0.1)

    result = yield waitForDoneWithWaiters(client, env_id, version)

    assert result.result["model"]["done"] == len(resources)

    assert Provider.isset("agent1", "key1")
    assert Provider.get("agent1", "key1") == "value1"
    assert Provider.get("agent1", "key2") == "value2"
    assert Provider.get("agent2", "key3") == "value3"

    agent.stop()
    agent2.stop()
