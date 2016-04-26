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

import unittest
import tempfile
import shutil

from nose.tools import assert_equal
from impera.module import Project
import impera.compiler as compiler
from impera import config


class CompilerBaseTest(object):

    def __init__(self, file):
        self.file = file

    def setUp(self):
        Project.set(Project(self.file))
        self.state_dir = tempfile.mkdtemp()
        config.Config.load_config()
        config.Config.set("config", "state-dir", self.state_dir)

    def tearDown(self):
        shutil.rmtree(self.state_dir)


class TestBaseCompile(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "tests/data/compile_test_1")

    def test_compile(self):
        (types, scopes) = compiler.do_compile()
        instances = types["__config__::Host"].get_all_instances()
        assert_equal(len(instances), 1)
        i = instances[0]
        assert_equal(i.get_attribute("name").get_value(), "test1")
        assert_equal(i.get_attribute("os").get_value().get_attribute("name").get_value(), "linux")


class TestForCompile(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "tests/data/compile_test_2")

    def test_compile(self):
        (types, scopes) = compiler.do_compile()
        instances = types["__config__::ManagedDevice"].get_all_instances()
        assert_equal(sorted([i.get_attribute("name").get_value() for i in instances]), [1, 2, 3, 4, 5])
