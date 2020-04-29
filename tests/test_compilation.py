"""
    Copyright 2018 Inmanta

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

import os
import re
import shutil
import tempfile
import unittest
from itertools import groupby

import pytest

import inmanta.compiler as compiler
from inmanta import config
from inmanta.ast import AttributeException, RuntimeException
from inmanta.module import Project


class CompilerBaseTest(object):
    def __init__(self, name, mainfile=None):
        config.Config.load_config()
        self.project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", name)
        if not os.path.isdir(self.project_dir):
            raise Exception("A compile test should set a valid project directory: %s does not exist" % self.project_dir)
        self.mainfile = mainfile

    def setUp(self):
        project = Project(self.project_dir, autostd=False)
        if self.mainfile is not None:
            project.main_file = self.mainfile
        Project.set(project)
        self.state_dir = tempfile.mkdtemp()
        config.Config.set("config", "state-dir", self.state_dir)

    def tearDown(self):
        shutil.rmtree(self.state_dir)


class TestBaseCompile(CompilerBaseTest, unittest.TestCase):
    def __init__(self, methodName="runTest"):  # noqa: N803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_1")

    def test_compile(self):
        (types, _) = compiler.do_compile()
        instances = types["__config__::Host"].get_all_instances()
        assert len(instances) == 1
        i = instances[0]
        assert i.get_attribute("name").get_value() == "test1"
        assert i.get_attribute("os").get_value().get_attribute("name").get_value() == "linux"


class TestForCompile(CompilerBaseTest, unittest.TestCase):
    def __init__(self, methodName="runTest"):  # noqa: N803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_2")

    def test_compile(self):
        (types, _) = compiler.do_compile()
        instances = types["__config__::ManagedDevice"].get_all_instances()
        assert sorted([i.get_attribute("name").get_value() for i in instances]) == [1, 2, 3, 4, 5]


class TestIndexCompileCollision(CompilerBaseTest, unittest.TestCase):
    def __init__(self, methodName="runTest"):  # noqa: N803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_index_collission")

    def test_compile(self):
        with pytest.raises(RuntimeException):
            compiler.do_compile()


class TestIndexCompile(CompilerBaseTest, unittest.TestCase):
    def __init__(self, methodName="runTest"):  # noqa: N803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_index")

    def test_compile(self):
        (_, scopes) = compiler.do_compile()
        variables = {k: x.get_value() for k, x in scopes.get_child("__config__").scope.slots.items()}

        p = re.compile(r"(f\d+h\d+)(a\d+)?")

        items = [
            (m.groups()[0], m.groups()[1], v) for m, v in [(re.search(p, k), v) for k, v in variables.items()] if m is not None
        ]
        groups = groupby(sorted(items, key=lambda x: x[0]), lambda x: x[0])
        firsts = []
        for k, v in groups:
            v = list(v)
            first = v[0]
            firsts.append(first)
            for other in v[1:]:
                assert first[2] == other[2]

        for i in range(len(firsts)):
            for j in range(len(firsts)):
                if not i == j:
                    self.assertNotEqual(
                        firsts[i][2],
                        firsts[j][2],
                        "Variable %s%s should not be equal to %s%s" % (firsts[i][0], firsts[i][1], firsts[j][0], firsts[j][1]),
                    )


class TestDoubleSet(CompilerBaseTest, unittest.TestCase):
    def __init__(self, methodName="runTest"):  # noqa: N803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_double_assign")

    def test_compile(self):
        with pytest.raises(AttributeException):
            compiler.do_compile()


class TestCompileIssue138(CompilerBaseTest, unittest.TestCase):
    def __init__(self, methodName="runTest"):  # noqa: N803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_138")

    def test_compile(self):
        (types, _) = compiler.do_compile()
        assert (
            types["std::Host"].get_all_instances()[0].get_attribute("agent").get_value().get_attribute("names").get_value()
            is not None
        )

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(os.path.join(self.project_dir, "libs", "std"))


class TestCompileluginTyping(CompilerBaseTest, unittest.TestCase):
    def __init__(self, methodName="runTest"):  # noqa: N803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_plugin_typing")

    def test_compile(self):
        (_, scopes) = compiler.do_compile()
        root = scopes.get_child("__config__")

        def verify(name):
            c1a1 = root.lookup(name).get_value()
            name = sorted([item.get_attribute("name").get_value() for item in c1a1])
            assert name == ["t1", "t2", "t3"]

        verify("c1a1")
        verify("c1a2")

        s1 = root.lookup("s1").get_value()
        s2 = root.lookup("s2").get_value()

        assert s2[0] == s1
        assert isinstance(s2, list)
        assert isinstance(s2[0], str)


class TestCompileluginTypingErr(CompilerBaseTest, unittest.TestCase):
    def __init__(self, methodName="runTest"):  # noqa: N803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_plugin_typing", "invalid.cf")

    def test_compile(self):
        with pytest.raises(RuntimeException) as e:
            compiler.do_compile()
        text = e.value.format_trace(indent="  ")
        print(text)
        assert (
            text
            == """Exception in plugin test::badtype (reported in test::badtype(c1.items) ({dir}/invalid.cf:16))
caused by:
  Invalid type for value 'a', should be type test::Item (reported in test::badtype(c1.items) ({dir}/invalid.cf:16))""".format(
                dir=self.project_dir
            )
        )
