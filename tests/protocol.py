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
from impera import methods
from impera import protocol
from impera.config import Config
from impera.server import Server

from concurrent import futures
import random
import unittest
import time
import tempfile
import shutil

from nose.tools import assert_equal, assert_count_equal


class testProtocolClient(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        self._tempdir = tempfile.mkdtemp()

    def setUp(self):
        Config.load_config()
        Config.set("config", "state-dir", self._tempdir)
        executor = futures.ThreadPoolExecutor(max_workers=2)
        self.server = Server(code_loader=False)
        self.server_future = executor.submit(self.server.start)
        # give the server time to start
        time.sleep(1)

    def test_client_files(self):
        c = protocol.Client("client", "client", [protocol.RESTTransport])
        c.start()
        file_name = str(random.randint(0, 10000))
        body = "Hello world\n"

        # Check if the file exists
        result = c.call(methods.FileMethod, operation="HEAD", id="test" + file_name)
        assert_equal(result.code, 404, "The test file should not exist yet")

        # Create the file
        result = c.call(methods.FileMethod, operation="PUT", id="test" + file_name, content=body)
        assert_equal(result.code, 200, "The test file failed to upload")

        # Get the file
        result = c.call(methods.FileMethod, operation="GET", id="test" + file_name)
        assert_equal(result.code, 200, "The test file failed to retrieve")
        assert("content" in result.result)
        assert_equal(result.result["content"], body, "Retrieving the test file failed")

        file_names = []
        for _n in range(1, 10):
            file_name = "test%d" % random.randint(0, 10000)
            file_names.append(file_name)
            result = c.call(methods.FileMethod, operation="PUT", id=file_name, content="")
            assert_equal(result.code, 200)

        result = c.call(methods.StatMethod, files=file_names)
        assert_count_equal(result.result["files"], [])

        other_files = ["testtest"]
        result = c.call(methods.StatMethod, files=file_names + other_files)
        assert_count_equal(result.result["files"], other_files)

        c.stop()

    def tearDown(self):
        self.server.stop()
        self.server_future.cancel()
        shutil.rmtree(self._tempdir)
