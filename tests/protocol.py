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
from inmanta import protocol

import random
import base64

from server_test import ServerTest

from nose.tools import assert_equal, assert_count_equal, assert_in
from tornado.testing import gen_test


class testProtocolClient(ServerTest):
    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.client = None

    def setUp(self):
        ServerTest.setUp(self)
        self.server.start()
        # start the client
        self.client = protocol.Client("client")

    def tearDown(self):
        ServerTest.tearDown(self)

    @gen_test
    def test_client_files(self):
        file_name = str(random.randint(0, 10000))
        body = base64.b64encode(b"Hello world\n").decode("ascii")

        # Check if the file exists
        result = yield self.client.stat_file(id="test" + file_name)
        assert_equal(result.code, 404, "The test file should not exist yet")

        # Create the file
        result = yield self.client.upload_file(id="test" + file_name, content=body)
        assert_equal(result.code, 200, "The test file failed to upload")

        # Get the file
        result = yield self.client.get_file(id="test" + file_name)
        assert_equal(result.code, 200, "The test file failed to retrieve")
        assert_in("content", result.result)
        assert_equal(result.result["content"], body, "Retrieving the test file failed")

        file_names = []
        for _n in range(1, 10):
            file_name = "test%d" % random.randint(0, 10000)
            file_names.append(file_name)
            result = yield self.client.upload_file(id=file_name, content="")
            assert_equal(result.code, 200)

        result = yield self.client.stat_files(files=file_names)
        assert_count_equal(result.result["files"], [])

        other_files = ["testtest"]
        result = yield self.client.stat_files(files=file_names + other_files)
        assert_count_equal(result.result["files"], other_files)
