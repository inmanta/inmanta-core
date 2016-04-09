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

    Contact: bart@inmanta.com
"""
import os
import uuid

from mongobox.unittest import MongoTestCase
from motorengine.connection import connect, disconnect
from impera import data
from tornado.testing import AsyncTestCase, gen_test
from nose.tools import assert_equal, assert_not_equal


class MotorEngineTestCase(MongoTestCase, AsyncTestCase):
    def setUp(self):
        MongoTestCase.setUp(self)
        AsyncTestCase.setUp(self)

        mongo_port = os.getenv('MONGOBOX_PORT')
        if mongo_port is None:
            raise Exception("MONGOBOX_PORT env variable not available. Make sure test are executed with --with-mongobox")

        connect(db="inmanta", host="localhost", port=int(mongo_port), io_loop=self.io_loop)

    def tearDown(self):
        MongoTestCase.tearDown(self)
        AsyncTestCase.tearDown(self)

        self.purge_database()
        disconnect()


class testProjectTestCase(MotorEngineTestCase):
    @gen_test
    def testProject(self):
        project = data.Project(name="test", uuid=uuid.uuid4())
        project = yield project.save()

        projects = yield data.Project.objects.filter(name="test").find_all()  # @UndefinedVariable
        assert_equal(len(projects), 1)
        assert_equal(projects[0].uuid, project.uuid)

        other = yield data.Project.get_uuid(project.uuid)
        assert_not_equal(project, other)
        assert_equal(project.uuid, other.uuid)

    @gen_test
    def testEnvironment(self):
        project = data.Project(name="test", uuid=uuid.uuid4())
        project = yield project.save()

        env = yield data.Environment.objects.create(uuid=uuid.uuid4(),  # @UndefinedVariable
                                                    name="dev", project_id=project.uuid, repo_url="", repo_branch="")
        assert_equal(env.project_id, project.uuid)

        yield project.delete_cascade()

        f1 = data.Project.objects.find_all()  # @UndefinedVariable
        f2 = data.Environment.objects.find_all()  # @UndefinedVariable
        projects, envs = yield [f1, f2]
        assert_equal(len(projects), 0)
        assert_equal(len(envs), 0)
