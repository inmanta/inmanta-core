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
import random
import string
import os

from inmanta import protocol, config
from server_test import ServerTest
from tornado.testing import gen_test
from utils import retry_limited
from tornado.gen import sleep
import pytest


class testRestServer(ServerTest):

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.client = None

    def setUp(self):
        ServerTest.setUp(self)
        # start the client
        self.client = protocol.Client("client")

    def tearDown(self):
        ServerTest.tearDown(self)

    @gen_test(timeout=20)
    @pytest.mark.slowtest
    def test_autostart(self):
        """
            Test auto start of agent
        """
        self.server.start()
        result = yield self.client.create_project("env-test")
        assert result.code == 200
        project_id = result.result["project"]["id"]

        result = yield self.client.create_environment(project_id=project_id, name="dev")
        env_id = result.result["environment"]["id"]

        res = yield self.server.agentmanager._ensure_agent(env_id, "iaas_jos")
        assert res
        yield retry_limited(lambda: len(self.server._sessions) == 1, 10)
        assert len(self.server._sessions) == 1
        res = yield self.server.agentmanager._ensure_agent(env_id, "iaas_jos")
        assert not res
        assert len(self.server._sessions) == 1

        self.server.agentmanager._requires_agents[env_id]["process"].terminate()
        yield sleep(1)
        res = yield self.server.agentmanager._ensure_agent(env_id, "iaas_jos")
        assert res
        yield retry_limited(lambda: len(self.server._sessions) == 1, 3)
        assert len(self.server._sessions) == 1

        # second agent for same env
        res = yield self.server.agentmanager._ensure_agent(env_id, "iaas_josx")
        assert res
        yield sleep(3)
        assert len(self.server._sessions) == 1

    @gen_test
    def test_version_removal(self):
        """
            Test auto removal of older deploy model versions
        """
        self.server.start()
        result = yield self.client.create_project("env-test")
        assert result.code == 200
        project_id = result.result["project"]["id"]

        result = yield self.client.create_environment(project_id=project_id, name="dev")
        env_id = result.result["environment"]["id"]

        version = int(time.time())

        for _i in range(20):
            version += 1

            yield self.server._purge_versions()
            res = yield self.client.put_version(tid=env_id, version=version, resources=[], unknowns=[], version_info={})
            assert res.code, 200
            result = yield self.client.get_project(id=project_id)

            versions = yield self.client.list_versions(tid=env_id)
            assert versions.result["count"] <= 3

    @gen_test
    def test_get_resource_for_agent(self):
        return self.get_resource_for_agent()

    @gen_test
    def test_get_resource_for_agent_with_auth(self):
        testuser = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        testpass = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))

        for x in ["server",
                  "server_rest_transport",
                  "agent_rest_transport",
                  "compiler_rest_transport",
                  "client_rest_transport",
                  "cmdline_rest_transport"]:
            config.Config.set(x, "username", testuser)
            config.Config.set(x, "password", testpass)

        return self.get_resource_for_agent()

    @gen_test
    def test_get_resource_for_agent_with_SSL(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        for x in ["server",
                  "server_rest_transport",
                  "agent_rest_transport",
                  "compiler_rest_transport",
                  "client_rest_transport",
                  "cmdline_rest_transport"]:
            config.Config.set(x, "ssl_cert_file", os.path.join(path, "server.crt"))
            config.Config.set(x, "ssl_ca_cert_file", os.path.join(path, "server.crt"))
            config.Config.set(x, "ssl_key_file", os.path.join(path, "server.open.key"))
            config.Config.set(x, "ssl", "True")

        return self.get_resource_for_agent()

    @gen_test
    def test_get_resource_for_agent_with_SSLAndAuth(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        testuser = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        testpass = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))

        for x in ["server",
                  "server_rest_transport",
                  "agent_rest_transport",
                  "compiler_rest_transport",
                  "client_rest_transport",
                  "cmdline_rest_transport"]:
            config.Config.set(x, "ssl_cert_file", os.path.join(path, "server.crt"))
            config.Config.set(x, "ssl_key_file", os.path.join(path, "server.open.key"))
            config.Config.set(x, "ssl_ca_cert_file", os.path.join(path, "server.crt"))
            config.Config.set(x, "ssl", "True")
            config.Config.set(x, "username", testuser)
            config.Config.set(x, "password", testpass)

        return self.get_resource_for_agent()

    def get_resource_for_agent(self):
        """
            Test the server to manage the updates on a model during agent deploy
        """
        self.server.start()
        result = yield self.client.create_project("env-test")
        assert result.code == 200
        project_id = result.result["project"]["id"]

        result = yield self.client.create_environment(project_id=project_id, name="dev")
        env_id = result.result["environment"]["id"]

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

        res = yield self.client.put_version(tid=env_id, version=version, resources=resources, unknowns=[], version_info={})
        assert res.code == 200

        result = yield self.client.list_versions(env_id)
        assert result.code == 200
        assert result.result["count"] == 1

        result = yield self.client.release_version(env_id, version, push=False)
        assert result.code == 200

        result = yield self.client.get_version(env_id, version)
        assert result.code == 200
        assert result.result["model"]["version"] == version
        assert result.result["model"]["total"] == len(resources)
        assert result.result["model"]["released"]
        assert result.result["model"]["result"] == "deploying"

        result = yield self.client.get_resources_for_agent(env_id, "vm1.dev.inmanta.com")
        assert result.code == 200
        assert len(result.result["resources"]) == 3

        result = yield self.client.resource_updated(env_id,
                                                    "std::File[vm1.dev.inmanta.com,path=/etc/sysconfig/network],v=%d" % version,
                                                    "INFO", "deploy", "", "deployed", {})
        assert result.code == 200

        result = yield self.client.get_version(env_id, version)
        assert result.code == 200
        assert result.result["model"]["done"] == 1

        result = yield self.client.resource_updated(env_id,
                                                    "std::File[vm1.dev.inmanta.com,path=/etc/hostname],v=%d" % version,
                                                    "INFO", "deploy", "", "deployed", {})
        assert result.code == 200

        result = yield self.client.get_version(env_id, version)
        assert result.code == 200
        assert result.result["model"]["done"] == 2
