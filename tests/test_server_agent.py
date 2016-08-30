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
from threading import Condition


from tornado.testing import gen_test
from tornado import gen

from inmanta import protocol, agent, data
from inmanta.agent.handler import provider, ResourceHandler
from inmanta.resources import resource, Resource
from server_test import ServerTest


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


@provider("test::Wait", name="test_wait")
class Wait(ResourceHandler):

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
        waiter.acquire()
        waiter.wait()
        waiter.release()


class testAgentServer(ServerTest):

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.client = None
        self.agent = None

    def setUp(self):
        ServerTest.setUp(self)
        self.server.start()
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

        result = yield self.client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
        assert result.code == 200

        # request a dryrun
        result = yield self.client.dryrun_request(env_id, version)
        assert result.code == 200
        assert result.result["dryrun"]["total"] == len(resources)
        assert result.result["dryrun"]["todo"] == len(resources)

        # get the dryrun results
        result = yield self.client.dryrun_list(env_id, version)
        assert result.code == 200
        assert len(result.result["dryruns"]) == 1

        while result.result["dryruns"][0]["todo"] > 0:
            result = yield self.client.dryrun_list(env_id, version)
            yield gen.sleep(0.1)

        dry_run_id = result.result["dryruns"][0]["id"]
        result = yield self.client.dryrun_report(env_id, dry_run_id)
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
        result = yield self.client.release_version(env_id, version, True)
        assert result.code == 200
        assert not result.result["model"]["deployed"]
        assert result.result["model"]["released"]
        assert result.result["model"]["total"] == 3
        assert result.result["model"]["result"] == "deploying"

        result = yield self.client.get_version(env_id, version)
        assert result.code == 200

        while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
            result = yield self.client.get_version(env_id, version)
            yield gen.sleep(0.1)

        assert result.result["model"]["done"] == len(resources)

        assert Provider.isset("agent1", "key1")
        assert Provider.get("agent1", "key1") == "value1"
        assert Provider.get("agent1", "key2") == "value2"
        assert not Provider.isset("agent1", "key3")

    @gen_test()
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

        result = yield self.client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
        assert result.code == 200

        # deploy and wait until done
        result = yield self.client.release_version(env_id, version, True)
        assert result.code == 200

        result = yield self.client.get_version(env_id, version)
        assert result.code == 200
        while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
            result = yield self.client.get_version(env_id, version)
            yield gen.sleep(0.1)

        assert result.result["model"]["done"] == len(resources)

        # create a snapshot
        result = yield self.client.create_snapshot(env_id, "snap1")
        assert result.code == 200
        snapshot_id = result.result["snapshot"]["id"]

        result = yield self.client.list_snapshots(env_id)
        assert result.code == 200
        assert len(result.result["snapshots"]) == 1
        assert result.result["snapshots"][0]["id"] == snapshot_id

        while result.result["snapshots"][0]["finished"] is None:
            result = yield self.client.list_snapshots(env_id)
            assert result.code == 200
            yield gen.sleep(0.1)

        # Change the value of the resource
        Provider.set("agent1", "key", "other")

        # try to do a restore
        result = yield self.client.restore_snapshot(env_id, snapshot_id)
        assert result.code == 200
        restore_id = result.result["restore"]["id"]

        result = yield self.client.list_restores(env_id)
        assert result.code == 200
        assert len(result.result["restores"]) == 1

        result = yield self.client.get_restore_status(env_id, restore_id)
        assert result.code == 200
        while result.result["restore"]["finished"] is None:
            result = yield self.client.get_restore_status(env_id, restore_id)
            assert result.code == 200
            yield gen.sleep(0.1)

        assert Provider.get("agent1", "key") == "value"

    @gen_test
    def test_get_facts(self):
        """
            Test retrieving facts from the agent
        """
        result = yield self.client.create_project("env-test")
        project_id = result.result["project"]["id"]

        result = yield self.client.create_environment(project_id=project_id, name="dev")
        env_id = result.result["environment"]["id"]

        self.agent = agent.Agent(self.io_loop, hostname="node1", env_id=env_id, agent_map="agent1=localhost",
                                 code_loader=False)
        self.agent.add_end_point_name("agent1")
        self.agent.start()

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

        result = yield self.client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
        assert result.code == 200
        result = yield self.client.release_version(env_id, version, True)
        assert result.code == 200

        result = yield self.client.get_param(env_id, "length", resource_id_wov)
        assert result.code == 503

        env = yield data.Environment.get_uuid(env_id)

        params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                     resource_id=resource_id_wov).find_all()  # @UndefinedVariable
        while len(params) < 3:
            params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                         resource_id=resource_id_wov).find_all()  # @UndefinedVariable
            yield gen.sleep(0.1)

        result = yield self.client.get_param(env_id, "key1", resource_id_wov)
        assert result.code == 200

    @gen_test
    def test_get_set_param(self):
        """
            Test getting and setting params
        """
        result = yield self.client.create_project("env-test")
        project_id = result.result["project"]["id"]

        result = yield self.client.create_environment(project_id=project_id, name="dev")
        env_id = result.result["environment"]["id"]

        result = yield self.client.set_param(tid=env_id, id="key10", value="value10", source="user")
        assert result.code == 200

    @gen_test
    def test_unkown_parameters(self):
        """
            Test retrieving facts from the agent
        """
        result = yield self.client.create_project("env-test")
        project_id = result.result["project"]["id"]

        result = yield self.client.create_environment(project_id=project_id, name="dev")
        env_id = result.result["environment"]["id"]

        self.agent = agent.Agent(self.io_loop, hostname="node1", env_id=env_id, agent_map="agent1=localhost",
                                 code_loader=False)
        self.agent.add_end_point_name("agent1")
        self.agent.start()

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
        result = yield self.client.put_version(tid=env_id, version=version, resources=resources, unknowns=unknowns,
                                               version_info={})
        assert result.code == 200

        result = yield self.client.release_version(env_id, version, True)
        assert result.code == 200

        yield self.server.renew_expired_facts()

        env = yield data.Environment.get_uuid(env_id)

        params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                     resource_id=resource_id_wov).find_all()  # @UndefinedVariable
        while len(params) < 3:
            params = yield data.Parameter.objects.filter(environment=env,  # @UndefinedVariable
                                                         resource_id=resource_id_wov).find_all()  # @UndefinedVariable
            yield gen.sleep(0.1)

        result = yield self.client.get_param(env_id, "length", resource_id_wov)
        assert result.code == 200

    @gen_test()
    def test_fail(self):
        """
            Test results when a step fails
        """
        result = yield self.client.create_project("env-test")
        project_id = result.result["project"]["id"]

        result = yield self.client.create_environment(project_id=project_id, name="dev")
        env_id = result.result["environment"]["id"]

        self.agent = agent.Agent(self.io_loop, hostname="node1", env_id=env_id, agent_map="agent1=localhost",
                                 code_loader=False, poolsize=10)
        self.agent.add_end_point_name("agent1")
        self.agent.start()

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

        result = yield self.client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
        assert result.code == 200

        # deploy and wait until done
        result = yield self.client.release_version(env_id, version, True)
        assert result.code == 200

        result = yield self.client.get_version(env_id, version)
        assert result.code == 200
        while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
            result = yield self.client.get_version(env_id, version)
            yield gen.sleep(0.1)

        assert result.result["model"]["done"] == len(resources)

        states = {x["id"]: x["status"] for x in result.result["resources"]}

        assert states['test::Fail[agent1,key=key],v=%d' % version] == "failed"
        assert states['test::Resource[agent1,key=key2],v=%d' % version] == "skipped"
        assert states['test::Resource[agent1,key=key3],v=%d' % version] == "skipped"
        assert states['test::Resource[agent1,key=key4],v=%d' % version] == "skipped"
        assert states['test::Resource[agent1,key=key5],v=%d' % version] == "skipped"

    @gen_test(timeout=10000)
    def test_wait(self):
        """
            Test results for a cancel
        """
        result = yield self.client.create_project("env-test")
        project_id = result.result["project"]["id"]

        result = yield self.client.create_environment(project_id=project_id, name="dev")
        env_id = result.result["environment"]["id"]

        self.agent = agent.Agent(self.io_loop, hostname="node1", env_id=env_id, agent_map="agent1=localhost",
                                 code_loader=False, poolsize=10)
        self.agent.add_end_point_name("agent1")
        self.agent.start()

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
        def waitForDone(version):
            # unhang waiters
            result = yield self.client.get_version(env_id, version)
            assert result.code == 200
            while (result.result["model"]["total"] - result.result["model"]["done"]) > 0:
                result = yield self.client.get_version(env_id, version)
                if result.result["model"]["done"] > 0:
                    waiter.acquire()
                    waiter.notifyAll()
                    waiter.release()
                yield gen.sleep(0.1)
            assert result.result["model"]["done"] == len(resources)

        @gen.coroutine
        def waitForResources(version, n):
            result = yield self.client.get_version(env_id, version)
            assert result.code == 200

            while result.result["model"]["done"] < n:
                result = yield self.client.get_version(env_id, version)
                yield gen.sleep(0.1)
            assert result.result["model"]["done"] == n

        version1, resources = makeVersion()
        result = yield self.client.put_version(tid=env_id, version=version1, resources=resources, unknowns=[], version_info={})
        assert result.code == 200

        # deploy and wait until one is ready
        result = yield self.client.release_version(env_id, version1, True)
        assert result.code == 200

        yield waitForResources(version1, 2)

        version2, resources = makeVersion(3)
        result = yield self.client.put_version(tid=env_id, version=version2, resources=resources, unknowns=[], version_info={})
        assert result.code == 200

        # deploy and wait until done
        result = yield self.client.release_version(env_id, version2, True)
        assert result.code == 200

        yield waitForDone(version2)

        result = yield self.client.get_version(env_id, version2)
        assert result.code == 200
        for x in result.result["resources"]:
            assert x["status"] == "deployed"

        result = yield self.client.get_version(env_id, version1)
        assert result.code == 200
        states = {x["id"]: x["status"] for x in result.result["resources"]}

        assert states['test::Wait[agent1,key=key],v=%d' % version1] == "deployed"
        assert states['test::Resource[agent1,key=key2],v=%d' % version1] == ""
        assert states['test::Resource[agent1,key=key3],v=%d' % version1] == "deployed"
        assert states['test::Resource[agent1,key=key4],v=%d' % version1] == "deployed"
        assert states['test::Resource[agent1,key=key5],v=%d' % version1] == ""
