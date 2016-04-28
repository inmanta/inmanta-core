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
import os
from itertools import groupby

from nose.tools import assert_equal
from impera.module import Project
import impera.compiler as compiler
from impera import config
from impera.ast import RuntimeException
from nose.tools.nontrivial import raises


class CompilerBaseTest(object):

    def __init__(self, name):
        self.project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", name)
        if not os.path.isdir(self.project_dir):
            raise Exception("A compile test should set a valid project directory: %s does not exist" % self.project_dir)

    def setUp(self):
        Project.set(Project(self.project_dir))
        self.state_dir = tempfile.mkdtemp()
        config.Config.load_config()
        config.Config.set("config", "state-dir", self.state_dir)

    def tearDown(self):
        shutil.rmtree(self.state_dir)


class TestBaseCompile(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_1")

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
        CompilerBaseTest.__init__(self, "compile_test_2")

    def test_compile(self):
        (types, scopes) = compiler.do_compile()
        instances = types["__config__::ManagedDevice"].get_all_instances()
        assert_equal(sorted([i.get_attribute("name").get_value() for i in instances]), [1, 2, 3, 4, 5])


class TestIndexCompileCollision(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_index_collission")

    @raises(RuntimeException)
    def test_compile(self):
        compiler.do_compile()


class TestIndexCompile(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_index")

    def test_compile(self):
        (types, scopes) = compiler.do_compile()
        variables = {k: x.get_value() for k, x in scopes["__config__"].slots.items()}

        import re
        p = re.compile(r'(f\d+h\d+)(a\d+)?')

        items = [(m.groups()[0], m.groups()[1], v)
                 for m, v in [(re.search(p, k), v)for k, v in variables.items()] if m is not None]
        groups = groupby(sorted(items, key=lambda x: x[0]), lambda x: x[0])
        firsts = []
        for k, v in groups:
            v = list(v)
            first = v[0]
            firsts.append(first)
            for other in v[1:]:
                assert_equal(first[2], other[2], "Variable %s%s should be equal to %s%s" %
                             (first[0], first[1], other[0], other[1]))

        for i in range(len(firsts)):
            for j in range(len(firsts)):
                if not i == j:
                    self.assertNotEqual(firsts[i][2], firsts[j][2], "Variable %s%s should not be equal to %s%s" % (
                        firsts[i][0], firsts[i][1], firsts[j][0], firsts[j][1]))
