"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io
"""

import time

from impera import protocol
from server_test import ServerTest
from nose.tools import assert_equal
from tornado.testing import gen_test


class testRestServer(ServerTest):
    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.client = None

    def setUp(self):
        ServerTest.setUp(self)
        # start the client
        self.client = protocol.Client("client", "client")

    def tearDown(self):
        ServerTest.tearDown(self)

    @gen_test
    def test_version_removal(self):
        """
            Test auto removal of older deploy model versions
        """
        result = yield self.client.create_project("env-test")
        project_id = result.result["project"]["id"]

        result = yield self.client.create_environment(project_id=project_id, name="dev")
        env_id = result.result["environment"]["id"]

        version = int(time.time())

        for _i in range(20):
            version += 1

            res = yield self.client.put_version(tid=env_id, version=version, resources=[], unknowns=[], version_info={})
            assert_equal(res.code, 200)
            result = yield self.client.get_project(id=project_id)
