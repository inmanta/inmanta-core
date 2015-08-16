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
from impera import protocol
from impera.config import Config
from impera.server import Server

from concurrent import futures
import unittest
import time
import tempfile
import shutil

from nose.tools import assert_equal, assert_true


class testRestServer(unittest.TestCase):
    def __init__(self, methodName='runTe    st'):
        unittest.TestCase.__init__(self, methodName)

    @classmethod
    def setUpClass(cls):
        cls._tempdir = tempfile.mkdtemp()
        Config.load_config()
        Config.set("config", "state-dir", cls._tempdir)
        Config.set("database", "name", "unittest")

        executor = futures.ThreadPoolExecutor(max_workers=2)
        cls.server = Server(code_loader=False)
        cls.server_future = executor.submit(cls.server.start)
        # give the server time to start
        time.sleep(1)

        # start the client
        cls.client = protocol.Client("client", "client")

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        shutil.rmtree(cls._tempdir)

    def setUp(self):
        # clear the mongodb database
        self.__class__.server._db.drop_database("unittest")

    def tearDown(self):
        # clear the mongodb database
        self.__class__.server._db.drop_database("unittest")

    def test_project_api(self):
        result = self.__class__.client.create_project("project-test")
        assert_equal(result.code, 200)
        assert_true("id" in result.result)

        project_id = result.result["id"]

        result = self.__class__.client.create_project("project-test")
        assert_equal(result.code, 500)

        result = self.__class__.client.list_projects()
        assert_equal(result.code, 200)
        assert_equal(len(result.result), 1)

        assert_equal(result.result[0]['id'], project_id)

        result = self.__class__.client.get_project(id=project_id)
        assert_equal(result.code, 200)
        assert_equal(result.result['id'], project_id)
        assert_equal(result.result['name'], "project-test")

        result = self.__class__.client.modify_project(id=project_id, name="project-test2")
        assert_equal(result.code, 200)
        assert_equal(result.result['id'], project_id)
        assert_equal(result.result['name'], "project-test2")

        result = self.__class__.client.get_project(id=project_id)
        assert_equal(result.code, 200)
        assert_equal(result.result['id'], project_id)
        assert_equal(result.result['name'], "project-test2")

        result = self.__class__.client.delete_project(id=project_id)
        assert_equal(result.code, 200)

        result = self.__class__.client.list_projects()
        assert_equal(result.code, 200)
        assert_equal(len(result.result), 0)

    def test_env_api(self):
        result = self.__class__.client.create_project("env-test")
        assert_equal(result.code, 200)
        assert_true("id" in result.result)
        project_id = result.result["id"]

        result = self.__class__.client.create_environment(project_id=project_id, name="dev")
        assert_equal(result.code, 200)
        assert_true("id" in result.result)
        assert_true("project" in result.result)
        assert_equal(project_id, result.result["project"])
        assert_equal("dev", result.result["name"])

        env_id = result.result["id"]

        result = self.__class__.client.modify_environment(id=env_id, name="dev2")
        assert_equal(result.code, 200)
        assert_equal(result.result['id'], env_id)
        assert_equal(result.result['name'], "dev2")

        result = self.__class__.client.get_environment(id=env_id)
        assert_equal(result.code, 200)
        assert_equal(result.result['id'], env_id)
        assert_equal(result.result['project'], project_id)
        assert_equal(result.result['name'], "dev2")

        project_result = self.__class__.client.get_project(id=project_id)
        assert_equal(project_result.code, 200)
        assert_true(env_id in project_result.result['environments'])

        result = self.__class__.client.list_environments()
        assert_equal(result.code, 200)
        assert_equal(len(result.result), 1)

        result = self.__class__.client.delete_environment(id=env_id)
        assert_equal(result.code, 200)

        result = self.__class__.client.list_environments()
        assert_equal(result.code, 200)
        assert_equal(len(result.result), 0)

    def test_project_cascade(self):
        result = self.__class__.client.create_project("env-test")
        project_id = result.result["id"]

        result = self.__class__.client.create_environment(project_id=project_id, name="dev")
        result = self.__class__.client.create_environment(project_id=project_id, name="prod")

        result = self.__class__.client.delete_project(project_id)
        assert_equal(result.code, 200)

        result = self.__class__.client.list_environments()
        assert_equal(len(result.result), 0)
