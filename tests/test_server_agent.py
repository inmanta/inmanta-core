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
from collections import defaultdict, namedtuple
import time
import json
import uuid
from threading import Condition
from itertools import groupby
import logging
import os
import shutil
import subprocess

from tornado import gen
import pytest
from _pytest.fixtures import fixture

from inmanta import agent, data, const, execute, config
from inmanta.agent.handler import provider, ResourceHandler
from inmanta.resources import resource, Resource
from inmanta.agent.agent import Agent
from utils import retry_limited, assert_equal_ish, UNKWN
from inmanta.config import Config
from inmanta.server.server import Server
from inmanta.ast import CompilerException

logger = logging.getLogger("inmanta.test.server_agent")


ResourceContainer = namedtuple('ResourceContainer', ['Provider', 'waiter', 'wait_for_done_with_waiters'])


@fixture(scope="function")
def resource_container():
    @resource("test::Resource", agent="agent", id_attribute="key")
    class MyResource(Resource):
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

        def check_resource(self, ctx, resource):
            assert resource.value != const.UNKNOWN_STRING
            current = resource.clone()
            current.purged = not self.isset(resource.id.get_agent_name(), resource.key)

            if not current.purged:
                current.value = self.get(resource.id.get_agent_name(), resource.key)
            else:
                current.value = None

            return current

        def do_changes(self, ctx, resource, changes):
            if "purged" in changes:
                if changes["purged"]["desired"]:
                    self.delete(resource.id.get_agent_name(), resource.key)
                    ctx.set_purged()
                else:
                    self.set(resource.id.get_agent_name(), resource.key, resource.value)
                    ctx.set_created()

            elif "value" in changes:
                self.set(resource.id.get_agent_name(), resource.key, resource.value)
                ctx.set_updated()

            return changes

        def snapshot(self, resource):
            return json.dumps({"value": self.get(resource.id.get_agent_name(), resource.key), "metadata": "1234"}).encode()

        def restore(self, resource, snapshot_id):
            content = self.get_file(snapshot_id)
            if content is None:
                return

            data = json.loads(content.decode())
            if "value" in data:
                self.set(resource.id.get_agent_name(), resource.key, data["value"])

        def facts(self, ctx, resource):
            return {"length": len(self.get(resource.id.get_agent_name(), resource.key)), "key1": "value1", "key2": "value2"}

        def can_process_events(self) -> bool:
            return True

        def process_events(self, ctx, resource, events):
            self.__class__._EVENTS[str(resource.id)] = events

        _STATE = defaultdict(dict)
        _EVENTS = {}

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
            cls._EVENTS = {}

    @provider("test::Fail", name="test_fail")
    class Fail(ResourceHandler):

        def check_resource(self, ctx, resource):
            current = resource.clone()
            current.purged = not Provider.isset(resource.id.get_agent_name(), resource.key)

            if not current.purged:
                current.value = Provider.get(resource.id.get_agent_name(), resource.key)
            else:
                current.value = None

            return current

        def do_changes(self, ctx, resource, changes):
            raise Exception()

    waiter = Condition()

    @gen.coroutine
    def wait_for_done_with_waiters(client, env_id, version):
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

        def check_resource(self, ctx, resource):
            current = resource.clone()
            current.purged = not Provider.isset(resource.id.get_agent_name(), resource.key)

            if not current.purged:
                current.value = Provider.get(resource.id.get_agent_name(), resource.key)
            else:
                current.value = None

            return current

        def do_changes(self, ctx, resource, changes):
            logger.info("Hanging waiter %s", self.traceid)
            waiter.acquire()
            waiter.wait()
            waiter.release()
            logger.info("Releasing waiter %s", self.traceid)
            if "purged" in changes:
                if changes["purged"]["desired"]:
                    Provider.delete(resource.id.get_agent_name(), resource.key)
                    ctx.set_purged()
                else:
                    Provider.set(resource.id.get_agent_name(), resource.key, resource.value)
                    ctx.set_created()

            if "value" in changes:
                Provider.set(resource.id.get_agent_name(), resource.key, resource.value)
                ctx.set_updated()

    return ResourceContainer(Provider=Provider, wait_for_done_with_waiters=wait_for_done_with_waiters, waiter=waiter)


@pytest.mark.gen_test(timeout=15)
def test_dryrun_and_deploy(io_loop, server_multi, client_multi, resource_container):
    """
        dryrun and deploy a configuration model

        There is a second agent with an undefined resource. The server will shortcut the dryrun and deploy for this resource
        without an agent being present.
    """
    resource_container.Provider.reset()
    result = yield client_multi.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client_multi.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", environment=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()

    yield retry_limited(lambda: len(server_multi.agentmanager.sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'send_event': False,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Resource[agent1,key=key2],v=%d' % version],
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'send_event': False,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key3',
                  'value': None,
                  'id': 'test::Resource[agent1,key=key3],v=%d' % version,
                  'send_event': False,
                  'requires': [],
                  'purged': True,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key4',
                  'value': execute.util.Unknown(source=None),
                  'id': 'test::Resource[agent2,key=key4],v=%d' % version,
                  'send_event': False,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key5',
                  'value': "val",
                  'id': 'test::Resource[agent2,key=key5],v=%d' % version,
                  'send_event': False,
                  'requires': ['test::Resource[agent2,key=key4],v=%d' % version],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }
                 ]

    status = {'test::Resource[agent2,key=key4]': const.ResourceState.undefined}
    result = yield client_multi.put_version(tid=env_id, version=version, resources=resources, resource_state=status,
                                            unknowns=[], version_info={})
    assert result.code == 200

    # request a dryrun
    result = yield client_multi.dryrun_request(env_id, version)
    assert result.code == 200
    assert result.result["dryrun"]["total"] == len(resources)
    assert result.result["dryrun"]["todo"] == len(resources)

    # get the dryrun results
    result = yield client_multi.dryrun_list(env_id, version)
    assert result.code == 200
    assert len(result.result["dryruns"]) == 1

    while result.result["dryruns"][0]["todo"] > 0:
        result = yield client_multi.dryrun_list(env_id, version)
        yield gen.sleep(0.1)

    dry_run_id = result.result["dryruns"][0]["id"]
    result = yield client_multi.dryrun_report(env_id, dry_run_id)
    assert result.code == 200

    changes = result.result["dryrun"]["resources"]
    assert changes[resources[0]["id"]]["changes"]["purged"]["current"]
    assert not changes[resources[0]["id"]]["changes"]["purged"]["desired"]
    assert changes[resources[0]["id"]]["changes"]["value"]["current"] is None
    assert changes[resources[0]["id"]]["changes"]["value"]["desired"] == resources[0]["value"]

    assert changes[resources[1]["id"]]["changes"]["value"]["current"] == "incorrect_value"
    assert changes[resources[1]["id"]]["changes"]["value"]["desired"] == resources[1]["value"]

    assert not changes[resources[2]["id"]]["changes"]["purged"]["current"]
    assert changes[resources[2]["id"]]["changes"]["purged"]["desired"]

    # do a deploy
    result = yield client_multi.release_version(env_id, version, True)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 5
    assert result.result["model"]["result"] == "deploying"

    result = yield client_multi.get_version(env_id, version)
    assert result.code == 200

    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client_multi.get_version(env_id, version)
        yield gen.sleep(0.1)

    assert result.result["model"]["done"] == len(resources)

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert not resource_container.Provider.isset("agent1", "key3")

    actions = yield data.ResourceAction.get_list()
    assert len([x for x in actions if x.status == const.ResourceState.undefined]) == 1
    assert len([x for x in actions if x.status == const.ResourceState.skipped]) == 1

    agent.stop()


@pytest.mark.gen_test(timeout=30)
def test_server_restart(resource_container, io_loop, server, mongo_db, client):
    """
        dryrun and deploy a configuration model
    """
    resource_container.Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", environment=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    server.stop()

    server = Server(database_host="localhost", database_port=int(mongo_db.port), io_loop=io_loop)
    server.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'purged': False,
                  'send_event': False,
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
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key3',
                  'value': None,
                  'id': 'test::Resource[agent1,key=key3],v=%d' % version,
                  'requires': [],
                  'purged': True,
                  'send_event': False,
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
    assert changes[resources[0]["id"]]["changes"]["purged"]["current"]
    assert not changes[resources[0]["id"]]["changes"]["purged"]["desired"]
    assert changes[resources[0]["id"]]["changes"]["value"]["current"] is None
    assert changes[resources[0]["id"]]["changes"]["value"]["desired"] == resources[0]["value"]

    assert changes[resources[1]["id"]]["changes"]["value"]["current"] == "incorrect_value"
    assert changes[resources[1]["id"]]["changes"]["value"]["desired"] == resources[1]["value"]

    assert not changes[resources[2]["id"]]["changes"]["purged"]["current"]
    assert changes[resources[2]["id"]]["changes"]["purged"]["desired"]

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

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert not resource_container.Provider.isset("agent1", "key3")

    agent.stop()
    server.stop()


@pytest.mark.gen_test(timeout=30)
def test_spontaneous_deploy(resource_container, io_loop, server, client):
    """
        dryrun and deploy a configuration model
    """
    resource_container.Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    Config.set("config", "agent-interval", "2")
    Config.set("config", "agent-splay", "2")

    agent = Agent(io_loop, hostname="node1", environment=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'purged': False,
                  'send_event': False,
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
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key3',
                  'value': None,
                  'id': 'test::Resource[agent1,key=key3],v=%d' % version,
                  'requires': [],
                  'purged': True,
                  'send_event': False,
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

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert not resource_container.Provider.isset("agent1", "key3")

    agent.stop()


@pytest.mark.gen_test
def test_dual_agent(resource_container, io_loop, server, client, environment):
    """
        dryrun and deploy a configuration model
    """
    resource_container.Provider.reset()
    myagent = agent.Agent(io_loop, hostname="node1", environment=environment,
                          agent_map={"agent1": "localhost", "agent2": "localhost"},
                          code_loader=False)
    myagent.add_end_point_name("agent1")
    myagent.add_end_point_name("agent2")
    myagent.start()
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key1", "incorrect_value")
    resource_container.Provider.set("agent2", "key1", "incorrect_value")

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Wait[agent1,key=key1],v=%d' % version,
                  'purged': False,
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': []
                  },
                 {'key': 'key2',
                  'value': 'value1',
                  'id': 'test::Wait[agent1,key=key2],v=%d' % version,
                  'purged': False,
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Wait[agent1,key=key1],v=%d' % version]
                  },
                 {'key': 'key1',
                  'value': 'value2',
                  'id': 'test::Wait[agent2,key=key1],v=%d' % version,
                  'purged': False,
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': []
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Wait[agent2,key=key2],v=%d' % version,
                  'purged': False,
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Wait[agent2,key=key1],v=%d' % version]
                  }]

    result = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # expire rate limiting
    yield gen.sleep(0.5)
    # do a deploy
    result = yield client.release_version(environment, version, True)
    assert result.code == 200

    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 4

    result = yield client.get_version(environment, version)
    assert result.code == 200

    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(environment, version)
        resource_container.waiter.acquire()
        resource_container.waiter.notifyAll()
        resource_container.waiter.release()
        yield gen.sleep(0.1)

    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["result"] == const.VersionState.success.name

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent2", "key1") == "value2"
    assert resource_container.Provider.get("agent1", "key2") == "value1"
    assert resource_container.Provider.get("agent2", "key2") == "value2"

    myagent.stop()


@pytest.mark.gen_test(timeout=60)
def test_snapshot_restore(resource_container, client, server, io_loop):
    """
        create a snapshot and restore it again
    """
    resource_container.Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", environment=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = int(time.time())

    resources = [{'key': 'key',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key2',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'send_event': False,
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
    resource_container.Provider.set("agent1", "key", "other")

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

    assert resource_container.Provider.get("agent1", "key") == "value"

    # get a snapshot
    result = yield client.get_snapshot(env_id, snapshot_id)
    assert result.code == 200
    assert result.result["snapshot"]["id"] == snapshot_id

    # delete the restore
    result = yield client.delete_restore(env_id, restore_id)
    assert result.code == 200

    # delete the snapshot
    result = yield client.delete_snapshot(env_id, snapshot_id)
    assert result.code == 200


@pytest.mark.gen_test
def test_server_agent_api(resource_container, client, server, io_loop):
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]
    agent = Agent(io_loop, environment=env_id, hostname="agent1", agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.start()

    agent = Agent(io_loop, environment=env_id, hostname="agent2", agent_map={"agent2": "localhost"},
                  code_loader=False)
    agent.start()

    yield retry_limited(lambda: len(server.agentmanager.sessions) == 2, 10)
    assert len(server.agentmanager.sessions) == 2

    result = yield client.list_agent_processes(env_id)
    assert result.code == 200

    while len(result.result["processes"]) != 2:
        result = yield client.list_agent_processes(env_id)
        assert result.code == 200
        yield gen.sleep(0.1)

    assert len(result.result["processes"]) == 2
    agents = ["agent1", "agent2"]
    for proc in result.result["processes"]:
        assert proc["environment"] == env_id
        assert len(proc["endpoints"]) == 1
        assert proc["endpoints"][0]["name"] in agents
        agents.remove(proc["endpoints"][0]["name"])

    assert_equal_ish({'processes': [{'expired': None, 'environment': env_id,
                                     'endpoints': [{'name': UNKWN, 'process': UNKWN, 'id': UNKWN}], 'id': UNKWN,
                                     'hostname': UNKWN, 'first_seen': UNKWN, 'last_seen': UNKWN},
                                    {'expired': None, 'environment': env_id,
                                     'endpoints': [{'name': UNKWN, 'process': UNKWN, 'id': UNKWN}],
                                     'id': UNKWN, 'hostname': UNKWN, 'first_seen': UNKWN, 'last_seen': UNKWN}
                                    ]},
                     result.result, ['name', 'first_seen'])

    agentid = result.result["processes"][0]["id"]
    endpointid = [x["endpoints"][0]["id"] for x in result.result["processes"] if x["endpoints"][0]["name"] == "agent1"][0]

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
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key2',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'send_event': False,
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

    assert_equal_ish(shouldbe, result.result)

    result = yield client.list_agents(tid=uuid.uuid4())
    assert result.code == 404


@pytest.mark.gen_test
def test_get_facts(resource_container, client, server, io_loop):
    """
        Test retrieving facts from the agent
    """
    resource_container.Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", environment=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = int(time.time())

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{'key': 'key',
                  'value': 'value',
                  'id': resource_id,
                  'requires': [],
                  'purged': False,
                  'send_event': False,
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

    env_uuid = uuid.UUID(env_id)
    params = yield data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
    while len(params) < 3:
        params = yield data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
        yield gen.sleep(0.1)

    result = yield client.get_param(env_id, "key1", resource_id_wov)
    assert result.code == 200


@pytest.mark.gen_test
def test_purged_facts(resource_container, client, server, io_loop, environment):
    """
        Test if facts are purged when the resource is purged.
    """
    resource_container.Provider.reset()
    agent = Agent(io_loop, hostname="node1", environment=environment, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = 1
    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{'key': 'key',
                  'value': 'value',
                  'id': resource_id,
                  'requires': [],
                  'purged': False,
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }]

    result = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200
    result = yield client.release_version(environment, version, True)
    assert result.code == 200

    result = yield client.get_param(environment, "length", resource_id_wov)
    assert result.code == 503

    env_uuid = uuid.UUID(environment)
    params = yield data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
    while len(params) < 3:
        params = yield data.Parameter.get_list(environment=env_uuid, resource_id=resource_id_wov)
        yield gen.sleep(0.1)

    result = yield client.get_param(environment, "key1", resource_id_wov)
    assert result.code == 200

    # Purge the resource
    version = 2
    resources[0]["id"] = "%s,v=%d" % (resource_id_wov, version)
    resources[0]["purged"] = True
    result = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200
    result = yield client.release_version(environment, version, True)
    assert result.code == 200

    result = yield client.get_version(environment, version)
    assert result.code == 200
    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(environment, version)
        yield gen.sleep(0.1)

    assert result.result["model"]["done"] == len(resources)

    # The resource facts should be purged
    result = yield client.get_param(environment, "length", resource_id_wov)
    assert result.code == 503


@pytest.mark.gen_test
def test_get_set_param(resource_container, client, server, io_loop):
    """
        Test getting and setting params
    """
    resource_container.Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    result = yield client.set_param(tid=env_id, id="key10", value="value10", source="user")
    assert result.code == 200

    result = yield client.get_param(tid=env_id, id="key10")
    assert result.code == 200
    assert result.result["parameter"]["value"] == "value10"

    result = yield client.delete_param(tid=env_id, id="key10")
    assert result.code == 200


@pytest.mark.gen_test
def test_unkown_parameters(resource_container, client, server, io_loop):
    """
        Test retrieving facts from the agent
    """
    resource_container.Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", environment=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = int(time.time())

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [{'key': 'key',
                  'value': 'value',
                  'id': resource_id,
                  'requires': [],
                  'purged': False,
                  'send_event': False,
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

    env_id = uuid.UUID(env_id)
    params = yield data.Parameter.get_list(environment=env_id, resource_id=resource_id_wov)
    while len(params) < 3:
        params = yield data.Parameter.get_list(environment=env_id, resource_id=resource_id_wov)
        yield gen.sleep(0.1)

    result = yield client.get_param(env_id, "length", resource_id_wov)
    assert result.code == 200


@pytest.mark.gen_test()
def test_fail(resource_container, client, server, io_loop):
    """
        Test results when a step fails
    """
    resource_container.Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", environment=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False, poolsize=10)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key", "value")

    version = int(time.time())

    resources = [{'key': 'key',
                  'value': 'value',
                  'id': 'test::Fail[agent1,key=key],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key2',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'requires': ['test::Fail[agent1,key=key],v=%d' % version],
                  'purged': False,
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key3',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key3],v=%d' % version,
                  'requires': ['test::Fail[agent1,key=key],v=%d' % version],
                  'purged': False,
                  'send_event': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key4',
                  'value': 'value',
                  'id': 'test::Resource[agent1,key=key4],v=%d' % version,
                  'requires': ['test::Resource[agent1,key=key3],v=%d' % version],
                  'purged': False,
                  'send_event': False,
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
                  'send_event': False,
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


@pytest.mark.gen_test(timeout=15)
def test_wait(resource_container, client, server, io_loop):
    """
        If this test fail due to timeout,
        this is probably due to the mechanism in the agent that prevents pulling resources in very rapid succession.

        If the test server is slow, a get_resources call takes a long time,
        this makes the back-off longer

        this test deploys two models in rapid successions, if the server is slow, this may fail due to the back-off
    """
    resource_container.Provider.reset()

    # setup project
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    # setup env
    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    # setup agent
    agent = Agent(io_loop, hostname="node1", environment=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False, poolsize=10)
    agent.add_end_point_name("agent1")
    agent.start()

    # wait for agent
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    # set the deploy environment
    resource_container.Provider.set("agent1", "key", "value")

    def make_version(offset=0):
        version = int(time.time() + offset)

        resources = [{'key': 'key',
                      'value': 'value',
                      'id': 'test::Wait[agent1,key=key],v=%d' % version,
                      'requires': [],
                      'purged': False,
                      'send_event': False,
                      'state_id': '',
                      'allow_restore': True,
                      'allow_snapshot': True,
                      },
                     {'key': 'key2',
                      'value': 'value',
                      'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                      'requires': ['test::Wait[agent1,key=key],v=%d' % version],
                      'purged': False,
                      'send_event': False,
                      'state_id': '',
                      'allow_restore': True,
                      'allow_snapshot': True,
                      },
                     {'key': 'key3',
                      'value': 'value',
                      'id': 'test::Resource[agent1,key=key3],v=%d' % version,
                      'requires': [],
                      'purged': False,
                      'send_event': False,
                      'state_id': '',
                      'allow_restore': True,
                      'allow_snapshot': True,
                      },
                     {'key': 'key4',
                      'value': 'value',
                      'id': 'test::Resource[agent1,key=key4],v=%d' % version,
                      'requires': ['test::Resource[agent1,key=key3],v=%d' % version],
                      'purged': False,
                      'send_event': False,
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
                      'send_event': False,
                      'state_id': '',
                      'allow_restore': True,
                      'allow_snapshot': True,
                      }]
        return version, resources

    @gen.coroutine
    def wait_for_resources(version, n):
        result = yield client.get_version(env_id, version)
        assert result.code == 200

        while result.result["model"]["done"] < n:
            result = yield client.get_version(env_id, version)
            yield gen.sleep(0.1)
        assert result.result["model"]["done"] == n

    logger.info("setup done")

    version1, resources = make_version()
    result = yield client.put_version(tid=env_id, version=version1, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    logger.info("first version pushed")

    # deploy and wait until one is ready
    result = yield client.release_version(env_id, version1, True)
    assert result.code == 200

    logger.info("first version released")

    yield wait_for_resources(version1, 2)

    logger.info("first version, 2 resources deployed")

    version2, resources = make_version(3)
    result = yield client.put_version(tid=env_id, version=version2, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    logger.info("second version pushed %f", time.time())

    yield gen.sleep(1)

    logger.info("wait to expire load limiting%f", time.time())

    # deploy and wait until done
    result = yield client.release_version(env_id, version2, True)
    assert result.code == 200

    logger.info("second version released")

    yield resource_container.wait_for_done_with_waiters(client, env_id, version2)

    logger.info("second version complete")

    result = yield client.get_version(env_id, version2)
    assert result.code == 200
    for x in result.result["resources"]:
        assert x["status"] == const.ResourceState.deployed.name

    result = yield client.get_version(env_id, version1)
    assert result.code == 200
    states = {x["id"]: x["status"] for x in result.result["resources"]}

    assert states['test::Wait[agent1,key=key],v=%d' % version1] == const.ResourceState.deployed.name
    assert states['test::Resource[agent1,key=key2],v=%d' % version1] == const.ResourceState.available.name
    assert states['test::Resource[agent1,key=key3],v=%d' % version1] == const.ResourceState.deployed.name
    assert states['test::Resource[agent1,key=key4],v=%d' % version1] == const.ResourceState.deployed.name
    assert states['test::Resource[agent1,key=key5],v=%d' % version1] == const.ResourceState.available.name


@pytest.mark.gen_test(timeout=15)
def test_multi_instance(resource_container, client, server, io_loop):
    """
       Test for multi threaded deploy
    """
    resource_container.Provider.reset()

    # setup project
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    # setup env
    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    # setup agent
    agent = Agent(io_loop, hostname="node1", environment=env_id,
                  agent_map={"agent1": "localhost", "agent2": "localhost", "agent3": "localhost"},
                  code_loader=False, poolsize=1)
    agent.add_end_point_name("agent1")
    agent.add_end_point_name("agent2")
    agent.add_end_point_name("agent3")

    agent.start()

    # wait for agent
    yield retry_limited(lambda: len(server._sessions) == 1, 10)

    # set the deploy environment
    resource_container.Provider.set("agent1", "key", "value")
    resource_container.Provider.set("agent2", "key", "value")
    resource_container.Provider.set("agent3", "key", "value")

    def make_version(offset=0):
        version = int(time.time() + offset)
        resources = []
        for agent in ["agent1", "agent2", "agent3"]:
            resources.extend([{'key': 'key',
                               'value': 'value',
                               'id': 'test::Wait[%s,key=key],v=%d' % (agent, version),
                               'requires': ['test::Resource[%s,key=key3],v=%d' % (agent, version)],
                               'purged': False,
                               'send_event': False,
                               'state_id': '',
                               'allow_restore': True,
                               'allow_snapshot': True,
                               },
                              {'key': 'key2',
                               'value': 'value',
                               'id': 'test::Resource[%s,key=key2],v=%d' % (agent, version),
                               'requires': ['test::Wait[%s,key=key],v=%d' % (agent, version)],
                               'purged': False,
                               'send_event': False,
                               'state_id': '',
                               'allow_restore': True,
                               'allow_snapshot': True,
                               },
                              {'key': 'key3',
                               'value': 'value',
                               'id': 'test::Resource[%s,key=key3],v=%d' % (agent, version),
                               'requires': [],
                               'purged': False,
                               'send_event': False,
                               'state_id': '',
                               'allow_restore': True,
                               'allow_snapshot': True,
                               },
                              {'key': 'key4',
                               'value': 'value',
                               'id': 'test::Resource[%s,key=key4],v=%d' % (agent, version),
                               'requires': ['test::Resource[%s,key=key3],v=%d' % (agent, version)],
                               'purged': False,
                               'send_event': False,
                               'state_id': '',
                               'allow_restore': True,
                               'allow_snapshot': True,
                               },
                              {'key': 'key5',
                               'value': 'value',
                               'id': 'test::Resource[%s,key=key5],v=%d' % (agent, version),
                               'requires': ['test::Resource[%s,key=key4],v=%d' % (agent, version),
                                            'test::Wait[%s,key=key],v=%d' % (agent, version)],
                               'purged': False,
                               'send_event': False,
                               'state_id': '',
                               'allow_restore': True,
                               'allow_snapshot': True,
                               }])
        return version, resources

    @gen.coroutine
    def wait_for_resources(version, n):
        result = yield client.get_version(env_id, version)
        assert result.code == 200

        def done_per_agent(result):
            done = [x for x in result.result["resources"] if x["status"] == "deployed"]
            peragent = groupby(done, lambda x: x["agent"])
            return {agent: len([x for x in grp]) for agent, grp in peragent}

        def mindone(result):
            alllist = done_per_agent(result).values()
            if(len(alllist) == 0):
                return 0
            return min(alllist)

        while mindone(result) < n:
            yield gen.sleep(0.1)
            result = yield client.get_version(env_id, version)
        assert mindone(result) >= n

    logger.info("setup done")

    version1, resources = make_version()
    result = yield client.put_version(tid=env_id, version=version1, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    logger.info("first version pushed")

    # deploy and wait until one is ready
    result = yield client.release_version(env_id, version1, True)
    assert result.code == 200

    logger.info("first version released")
    # timeout on single thread!
    yield wait_for_resources(version1, 1)

    yield resource_container.wait_for_done_with_waiters(client, env_id, version1)

    logger.info("first version complete")


@pytest.mark.gen_test
def test_cross_agent_deps(resource_container, io_loop, server, client):
    """
        deploy a configuration model with cross host dependency
    """
    resource_container.Provider.reset()
    # config for recovery mechanism
    Config.set("config", "agent-interval", "10")
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", environment=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    agent2 = Agent(io_loop, hostname="node2", environment=env_id, agent_map={"agent2": "localhost"},
                   code_loader=False)
    agent2.add_end_point_name("agent2")
    agent2.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 2, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'purged': False,
                  'state_id': '',
                  'send_event': False,
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
                  'send_event': False,
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key3',
                  'value': 'value3',
                  'id': 'test::Resource[agent2,key=key3],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'send_event': False,
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key4',
                  'value': 'value4',
                  'id': 'test::Resource[agent2,key=key4],v=%d' % version,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'send_event': False,
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
    assert result.result["model"]["result"] == const.VersionState.deploying.name

    result = yield client.get_version(env_id, version)
    assert result.code == 200

    while result.result["model"]["done"] == 0:
        result = yield client.get_version(env_id, version)
        yield gen.sleep(0.1)

    result = yield resource_container.wait_for_done_with_waiters(client, env_id, version)

    assert result.result["model"]["done"] == len(resources)
    assert result.result["model"]["result"] == const.VersionState.success.name

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert resource_container.Provider.get("agent2", "key3") == "value3"

    agent.stop()
    agent2.stop()


@pytest.mark.gen_test(timeout=30)
def test_dryrun_scale(resource_container, io_loop, server, client):
    """
        test dryrun scaling
    """
    resource_container.Provider.reset()
    result = yield client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    agent = Agent(io_loop, hostname="node1", environment=env_id, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    version = int(time.time())

    resources = []
    for i in range(1, 100):
        resources.append({'key': 'key%d' % i,
                          'value': 'value%d' % i,
                          'id': 'test::Resource[agent1,key=key%d],v=%d' % (i, version),
                          'purged': False,
                          'state_id': '',
                          'send_event': False,
                          'allow_restore': True,
                          'allow_snapshot': True,
                          'requires': [],
                          })

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

    agent.stop()


@pytest.mark.gen_test
def test_send_events(resource_container, io_loop, environment, server, client):
    """
        Send and receive events within one agent
    """
    resource_container.Provider.reset()
    agent = Agent(io_loop, hostname="node1", environment=environment, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    version = int(time.time())

    res_id_1 = 'test::Resource[agent1,key=key1],v=%d' % version
    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': res_id_1,
                  'send_event': False,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Resource[agent1,key=key2],v=%d' % version],
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'send_event': True,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }
                 ]

    result = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # do a deploy
    result = yield client.release_version(environment, version, True)
    assert result.code == 200

    result = yield client.get_version(environment, version)
    assert result.code == 200

    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(environment, version)
        yield gen.sleep(0.1)

    assert res_id_1 in resource_container.Provider._EVENTS
    event = resource_container.Provider._EVENTS[res_id_1]
    assert len(event) == 1
    for res_id, res in event.items():
        assert res_id.agent_name == "agent1"
        assert res_id.attribute_value == "key2"
        assert res["status"] == const.ResourceState.deployed
        assert res["change"] == const.Change.created

    agent.stop()


@pytest.mark.gen_test
def test_send_events_cross_agent(resource_container, io_loop, environment, server, client):
    """
        Send and receive events over agents
    """
    resource_container.Provider.reset()
    agent = Agent(io_loop, hostname="node1", environment=environment, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    agent2 = Agent(io_loop, hostname="node2", environment=environment, agent_map={"agent2": "localhost"},
                   code_loader=False)
    agent2.add_end_point_name("agent2")
    agent2.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 2, 10)

    version = int(time.time())

    res_id_1 = 'test::Resource[agent1,key=key1],v=%d' % version
    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': res_id_1,
                  'send_event': False,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Resource[agent2,key=key2],v=%d' % version],
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Resource[agent2,key=key2],v=%d' % version,
                  'send_event': True,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }
                 ]

    result = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # do a deploy
    result = yield client.release_version(environment, version, True)
    assert result.code == 200

    result = yield client.get_version(environment, version)
    assert result.code == 200

    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(environment, version)
        yield gen.sleep(0.1)

    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent2", "key2") == "value2"

    assert res_id_1 in resource_container.Provider._EVENTS
    event = resource_container.Provider._EVENTS[res_id_1]
    assert len(event) == 1
    for res_id, res in event.items():
        assert res_id.agent_name == "agent2"
        assert res_id.attribute_value == "key2"
        assert res["status"] == const.ResourceState.deployed
        assert res["change"] == const.Change.created

    agent.stop()
    agent2.stop()


@pytest.mark.gen_test(timeout=15)
def test_send_events_cross_agent_restart(resource_container, io_loop, environment, server, client):
    """
        Send and receive events over agents with agents starting after deploy
    """
    resource_container.Provider.reset()
    agent2 = Agent(io_loop, hostname="node2", environment=environment, agent_map={"agent2": "localhost"},
                   code_loader=False)
    agent2.add_end_point_name("agent2")
    agent2.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    version = int(time.time())

    res_id_1 = 'test::Resource[agent1,key=key1],v=%d' % version
    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': res_id_1,
                  'send_event': False,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Resource[agent2,key=key2],v=%d' % version],
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Resource[agent2,key=key2],v=%d' % version,
                  'send_event': True,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }
                 ]

    result = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # do a deploy
    result = yield client.release_version(environment, version, True)
    assert result.code == 200

    result = yield client.get_version(environment, version)
    assert result.code == 200

    # wait for agent 2 to finish
    while (result.result["model"]["total"] - result.result["model"]["done"]) > 1:
        result = yield client.get_version(environment, version)
        yield gen.sleep(1)

    assert resource_container.Provider.get("agent2", "key2") == "value2"

    # start agent 1 and wait for it to finish
    Config.set("config", "agent-splay", "0")
    agent = Agent(io_loop, hostname="node1", environment=environment, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 2, 10)

    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(environment, version)
        yield gen.sleep(1)

    assert resource_container.Provider.get("agent1", "key1") == "value1"

    assert res_id_1 in resource_container.Provider._EVENTS
    event = resource_container.Provider._EVENTS[res_id_1]
    assert len(event) == 1
    for res_id, res in event.items():
        assert res_id.agent_name == "agent2"
        assert res_id.attribute_value == "key2"
        assert res["status"] == const.ResourceState.deployed
        assert res["change"] == const.Change.created

    agent.stop()
    agent2.stop()


@pytest.mark.gen_test
def test_auto_deploy(io_loop, server, client, resource_container, environment):
    """
        dryrun and deploy a configuration model automatically
    """
    resource_container.Provider.reset()
    agent = Agent(io_loop, hostname="node1", environment=environment, agent_map={"agent1": "localhost"},
                  code_loader=False)
    agent.add_end_point_name("agent1")
    agent.start()
    yield retry_limited(lambda: len(server.agentmanager.sessions) == 1, 10)

    resource_container.Provider.set("agent1", "key2", "incorrect_value")
    resource_container.Provider.set("agent1", "key3", "value")

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'send_event': False,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Resource[agent1,key=key2],v=%d' % version],
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Resource[agent1,key=key2],v=%d' % version,
                  'send_event': False,
                  'requires': [],
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  },
                 {'key': 'key3',
                  'value': None,
                  'id': 'test::Resource[agent1,key=key3],v=%d' % version,
                  'send_event': False,
                  'requires': [],
                  'purged': True,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  }
                 ]

    # set auto deploy and push
    result = yield client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200
    result = yield client.set_setting(environment, data.PUSH_ON_AUTO_DEPLOY, True)
    assert result.code == 200

    result = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # check deploy
    result = yield client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 3
    assert result.result["model"]["result"] == "deploying"

    while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
        result = yield client.get_version(environment, version)
        yield gen.sleep(0.1)

    assert result.result["model"]["done"] == len(resources)

    assert resource_container.Provider.isset("agent1", "key1")
    assert resource_container.Provider.get("agent1", "key1") == "value1"
    assert resource_container.Provider.get("agent1", "key2") == "value2"
    assert not resource_container.Provider.isset("agent1", "key3")

    agent.stop()


@pytest.mark.gen_test(timeout=15)
def test_auto_deploy_no_splay(io_loop, server, client, resource_container, environment):
    """
        dryrun and deploy a configuration model automatically with agent autostart
    """
    resource_container.Provider.reset()
    env = yield data.Environment.get_by_id(uuid.UUID(environment))
    yield env.set(data.AUTOSTART_AGENT_MAP, {"agent1": ""})
    yield env.set(data.AUTOSTART_ON_START, True)

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'send_event': False,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': ['test::Resource[agent1,key=key2],v=%d' % version],
                  },
                 ]

    # set auto deploy and push
    result = yield client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200
    result = yield client.set_setting(environment, data.PUSH_ON_AUTO_DEPLOY, True)
    assert result.code == 200
    result = yield client.set_setting(environment, data.AUTOSTART_SPLAY, 0)
    assert result.code == 200

    result = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # check deploy
    result = yield client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    # check if agent 1 is started by the server
    # deploy will fail because handler code is not uploaded to the server
    result = yield client.list_agents(tid=environment)
    assert result.code == 200

    while len(result.result["agents"]) == 0 or result.result["agents"][0]["state"] == "down":
        result = yield client.list_agents(tid=environment)
        yield gen.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == "agent1"


@pytest.mark.gen_test(timeout=15)
def test_autostart_mapping(io_loop, server, client, resource_container, environment):
    """
        Test autostart mapping and restart agents when the map is modified
    """
    resource_container.Provider.reset()
    env = yield data.Environment.get_by_id(uuid.UUID(environment))
    yield env.set(data.AUTOSTART_AGENT_MAP, {"agent1": ""})
    yield env.set(data.AUTO_DEPLOY, True)
    yield env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    yield env.set(data.AUTOSTART_SPLAY, 0)
    yield env.set(data.AUTOSTART_ON_START, True)

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'send_event': False,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': [],
                  },
                 {'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent2,key=key1],v=%d' % version,
                  'send_event': False,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': [],
                  },
                 ]

    result = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # check deploy
    result = yield client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 2
    assert result.result["model"]["result"] == "deploying"

    result = yield client.list_agents(tid=environment)
    assert result.code == 200

    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 1:
        result = yield client.list_agents(tid=environment)
        yield gen.sleep(0.1)

    assert len(result.result["agents"]) == 2
    assert len([x for x in result.result["agents"] if x["state"] == "up"]) == 1

    result = yield client.set_setting(environment, data.AUTOSTART_AGENT_MAP, {"agent1": "", "agent2": ""})
    assert result.code == 200

    result = yield client.list_agents(tid=environment)
    assert result.code == 200
    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 2:
        result = yield client.list_agents(tid=environment)
        yield gen.sleep(0.1)


@pytest.mark.gen_test(timeout=15)
def test_autostart_clear_environment(io_loop, server_multi, client_multi, resource_container, environment):
    """
        Test clearing an environment with autostarted agents. After clearing, autostart should still work
    """
    resource_container.Provider.reset()
    env = yield data.Environment.get_by_id(uuid.UUID(environment))
    yield env.set(data.AUTOSTART_AGENT_MAP, {"agent1": ""})
    yield env.set(data.AUTO_DEPLOY, True)
    yield env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    yield env.set(data.AUTOSTART_SPLAY, 0)
    yield env.set(data.AUTOSTART_ON_START, True)

    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'send_event': False,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': [],
                  }
                 ]

    client = client_multi
    result = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # check deploy
    result = yield client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    result = yield client.list_agents(tid=environment)
    assert result.code == 200

    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 1:
        result = yield client.list_agents(tid=environment)
        yield gen.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert len([x for x in result.result["agents"] if x["state"] == "up"]) == 1

    # clear environment
    yield client.clear_environment(environment)

    items = yield data.ConfigurationModel.get_list()
    assert len(items) == 0
    items = yield data.Resource.get_list()
    assert len(items) == 0
    items = yield data.ResourceAction.get_list()
    assert len(items) == 0
    items = yield data.Code.get_list()
    assert len(items) == 0
    items = yield data.Agent.get_list()
    assert len(items) == 0
    items = yield data.AgentInstance.get_list()
    assert len(items) == 0
    items = yield data.AgentProcess.get_list()
    assert len(items) == 0

    # Do a deploy again
    version = int(time.time())

    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                  'send_event': False,
                  'purged': False,
                  'state_id': '',
                  'allow_restore': True,
                  'allow_snapshot': True,
                  'requires': [],
                  }
                 ]

    result = yield client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
    assert result.code == 200

    # check deploy
    result = yield client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    result = yield client.list_agents(tid=environment)
    assert result.code == 200

    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 1:
        result = yield client.list_agents(tid=environment)
        yield gen.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert len([x for x in result.result["agents"] if x["state"] == "up"]) == 1


@pytest.mark.gen_test
def test_export_duplicate(resource_container, snippetcompiler):
    """
        The exported should provide a compilation error when a resource is defined twice in a model
    """
    snippetcompiler.setup_for_snippet("""
        import test

        test::Resource(key="test", value="foo")
        test::Resource(key="test", value="bar")
    """)

    with pytest.raises(CompilerException) as exc:
        snippetcompiler.do_export()

    assert "exists more than once in the configuration model" in str(exc.value)


@pytest.mark.gen_test(timeout=90)
def test_server_recompile(server_multi, client_multi, environment_multi):
    """
        Test a recompile on the server and verify recompile triggers
    """
    config.Config.set("server", "auto-recompile-wait", "0")
    client = client_multi
    server = server_multi
    environment = environment_multi

    @gen.coroutine
    def wait_for_version(cnt):
        # Wait until the server is no longer compiling
        # wait for it to finish
        code = 200
        while code == 200:
            compiling = yield client.is_compiling(environment)
            code = compiling.code
            yield gen.sleep(1)

        # wait for it to appear
        versions = yield client.list_versions(environment)

        while versions.result["count"] < cnt:
            versions = yield client.list_versions(environment)

        return versions.result

    project_dir = os.path.join(server._server_storage["environments"], str(environment))
    project_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "project")

    shutil.copytree(project_source, project_dir)
    subprocess.check_output(["git", "init"], cwd=project_dir)
    subprocess.check_output(["git", "add", "*"], cwd=project_dir)
    subprocess.check_output(["git", "config", "user.name", "Unit"], cwd=project_dir)
    subprocess.check_output(["git", "config", "user.email", "unit@test.example"], cwd=project_dir)
    subprocess.check_output(["git", "commit", "-m", "unit test"], cwd=project_dir)

    # add main.cf
    with open(os.path.join(project_dir, "main.cf"), "w") as fd:
        fd.write("""
        host = std::Host(name="test", os=std::linux)
        std::ConfigFile(host=host, path="/etc/motd", content="1234")
""")

    # request a compile
    yield client.notify_change(environment)

    versions = yield wait_for_version(1)
    assert versions["versions"][0]["total"] == 1
    assert versions["versions"][0]["version_info"]["export_metadata"]["type"] == "api"

    # get compile reports
    reports = yield client.get_reports(environment)
    assert len(reports.result["reports"]) == 1

    # set a parameter without requesting a recompile
    yield client.set_param(environment, id="param1", value="test", source="plugin")
    versions = yield wait_for_version(1)
    assert versions["count"] == 1

    # set a new parameter and request a recompile
    yield client.set_param(environment, id="param2", value="test", source="plugin", recompile=True)
    versions = yield wait_for_version(2)
    assert versions["versions"][0]["version_info"]["export_metadata"]["type"] == "param"
    assert versions["count"] == 2

    # update the parameter to the same value -> no compile
    yield client.set_param(environment, id="param2", value="test", source="plugin", recompile=True)
    versions = yield wait_for_version(2)
    assert versions["count"] == 2

    # update the parameter to a new value
    yield client.set_param(environment, id="param2", value="test2", source="plugin", recompile=True)
    versions = yield wait_for_version(3)
    assert versions["count"] == 3
