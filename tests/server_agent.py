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

from nose.tools import assert_equal, assert_true
from tornado.testing import gen_test
from tornado import gen

from impera import protocol, agent
from impera.agent.handler import provider, ResourceHandler
from impera.resources import resource, Resource
from server_test import ServerTest


@resource("test::Resource", agent="agent", id_attribute="key")
class Resource(Resource):
    """
        A file on a filesystem
    """
    fields = ("key", "value", "purged", "state_id", "allow_snapshot", "allow_restore")


@provider("test::Resource", name="test_resource")
class TestProvider(ResourceHandler):
    def check_resource(self, resource):
        current = resource.clone()
        current.purged = not TestProvider.isset(resource.id.get_agent_name(), resource.key)

        if not current.purged:
            current.value = TestProvider.get(resource.id.get_agent_name(), resource.key)
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
                TestProvider.delete(resource.id.get_agent_name(), resource.key)
            else:
                TestProvider.set(resource.id.get_agent_name(), resource.key, resource.value)

        if "value" in changes:
            TestProvider.set(resource.id.get_agent_name(), resource.key, resource.value)

        return changes

    def snapshot(self, resource):
        return json.dumps({"value": TestProvider.get(resource.id.get_agent_name(), resource.key), "metadata": "1234"}).encode()

    def restore(self, resource, snapshot_id):
        content = self.get_file(snapshot_id)
        if content is None:
            return

        data = json.loads(content.decode())
        if "value" in data:
            TestProvider.set(resource.id.get_agent_name(), resource.key, data["value"])

    def facts(self, resource):
        return {"length": len(TestProvider.get(resource.id.get_agent_name(), resource.key))}

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


class testAgentServer(ServerTest):
    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.client = None
        self.agent = None

    def setUp(self):
        ServerTest.setUp(self)
        self.client = protocol.Client("client")

    def tearDown(self):
        if self.agent is not None:
            self.agent.stop()
        ServerTest.tearDown(self)

    # TODO: add test to validate missing handler or other failure in the agent -> result in failure instead of nothing
    # TOOD: handler requires that is missing
    @gen_test
    def test_dryrun_and_deploy(self):
        """
            dryrun and deploy a configuration model
        """
        result = yield self.client.create_project("env-test")
        project_id = result.result["project"]["id"]

        result = yield self.client.create_environment(project_id=project_id, name="dev")
        env_id = result.result["environment"]["id"]

        self.agent = agent.Agent(self.io_loop, hostname="node1", env_id=env_id, agent_map="agent1=localhost",
                                 code_loader=False)
        self.agent.add_end_point_name("agent1")
        self.agent.start()

        TestProvider.set("agent1", "key2", "incorrect_value")
        TestProvider.set("agent1", "key3", "value")

        version = int(time.time())

        resources = [{'key': 'key1',
                      'value': 'value1',
                      'id': 'test::Resource[agent1,key=key1],v=%d' % version,
                      'requires': [],
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

        result = yield self.client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
        assert_equal(result.code, 200)

        # request a dryrun
        result = yield self.client.dryrun_request(env_id, version)
        assert_equal(result.code, 200)
        assert_equal(result.result["dryrun"]["total"], len(resources))
        assert_equal(result.result["dryrun"]["todo"], len(resources))

        # get the dryrun results
        result = yield self.client.dryrun_list(env_id, version)
        assert_equal(result.code, 200)
        assert_equal(len(result.result["dryruns"]), 1)

        while result.result["dryruns"][0]["todo"] > 0:
            result = yield self.client.dryrun_list(env_id, version)
            yield gen.sleep(0.1)

        dry_run_id = result.result["dryruns"][0]["id"]
        result = yield self.client.dryrun_report(env_id, dry_run_id)
        assert_equal(result.code, 200)

        changes = result.result["dryrun"]["resources"]
        assert_equal(changes[resources[0]["id"]]["changes"]["purged"][0], True)
        assert_equal(changes[resources[0]["id"]]["changes"]["purged"][1], False)
        assert_equal(changes[resources[0]["id"]]["changes"]["value"][0], None)
        assert_equal(changes[resources[0]["id"]]["changes"]["value"][1], resources[0]["value"])

        assert_equal(changes[resources[1]["id"]]["changes"]["value"][0], "incorrect_value")
        assert_equal(changes[resources[1]["id"]]["changes"]["value"][1], resources[1]["value"])

        assert_equal(changes[resources[2]["id"]]["changes"]["purged"][0], False)
        assert_equal(changes[resources[2]["id"]]["changes"]["purged"][1], True)

        # do a deploy
        result = yield self.client.release_version(env_id, version, True)
        assert_equal(result.code, 200)
        assert_equal(result.result["model"]["deployed"], False)
        assert_equal(result.result["model"]["released"], True)
        assert_equal(result.result["model"]["total"], 3)
        assert_equal(result.result["model"]["result"], "deploying")

        result = yield self.client.get_version(env_id, version)
        assert_equal(result.code, 200)

        while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
            result = yield self.client.get_version(env_id, version)
            yield gen.sleep(0.1)

        assert_equal(result.result["model"]["done"], len(resources))

        assert_true(TestProvider.isset("agent1", "key1"))
        assert_equal(TestProvider.get("agent1", "key1"), "value1")
        assert_equal(TestProvider.get("agent1", "key2"), "value2")
        assert_true(not TestProvider.isset("agent1", "key3"))

    @gen_test
    def test_snapshot_restore(self):
        """
            create a snapshot and restore it again
        """
        result = yield self.client.create_project("env-test")
        project_id = result.result["project"]["id"]

        result = yield self.client.create_environment(project_id=project_id, name="dev")
        env_id = result.result["environment"]["id"]

        self.agent = agent.Agent(self.io_loop, hostname="node1", env_id=env_id, agent_map="agent1=localhost",
                                 code_loader=False)
        self.agent.add_end_point_name("agent1")
        self.agent.start()

        TestProvider.set("agent1", "key", "value")

        version = int(time.time())

        resources = [{'key': 'key',
                      'value': 'value',
                      'id': 'test::Resource[agent1,key=key],v=%d' % version,
                      'requires': [],
                      'purged': False,
                      'state_id': '',
                      'allow_restore': True,
                      'allow_snapshot': True,
                      }]

        result = yield self.client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
        assert_equal(result.code, 200)

        # deploy and wait until done
        result = yield self.client.release_version(env_id, version, True)
        assert_equal(result.code, 200)

        result = yield self.client.get_version(env_id, version)
        assert_equal(result.code, 200)
        while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
            result = yield self.client.get_version(env_id, version)
            yield gen.sleep(0.1)

        assert_equal(result.result["model"]["done"], len(resources))

        # create a snapshot
        result = yield self.client.create_snapshot(env_id, "snap1")
        assert_equal(result.code, 200)
        snapshot_id = result.result["snapshot"]["id"]

        result = yield self.client.list_snapshots(env_id)
        assert_equal(result.code, 200)
        assert_equal(len(result.result["snapshots"]), 1)
        assert_equal(result.result["snapshots"][0]["id"], snapshot_id)

        while result.result["snapshots"][0]["finished"] is None:
            result = yield self.client.list_snapshots(env_id)
            assert_equal(result.code, 200)
            yield gen.sleep(0.1)

        # Change the value of the resource
        TestProvider.set("agent1", "key", "other")

        # try to do a restore
        result = yield self.client.restore_snapshot(env_id, snapshot_id)
        assert_equal(result.code, 200)
        restore_id = result.result["restore"]["id"]

        result = yield self.client.list_restores(env_id)
        assert_equal(result.code, 200)
        assert_equal(len(result.result["restores"]), 1)

        result = yield self.client.get_restore_status(env_id, restore_id)
        assert_equal(result.code, 200)
        while result.result["restore"]["finished"] is None:
            result = yield self.client.get_restore_status(env_id, restore_id)
            assert_equal(result.code, 200)
            yield gen.sleep(0.1)

        assert_equal(TestProvider.get("agent1", "key"), "value")
