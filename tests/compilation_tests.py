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
import sys
from io import StringIO

from nose.tools import assert_equal
from inmanta.module import Project
import inmanta.compiler as compiler
from inmanta import config
from inmanta.ast import RuntimeException, DoubleSetException, DuplicateException, TypeNotFoundException, ModuleNotFoundException
from inmanta.ast import NotFoundException
from nose.tools.nontrivial import raises


class CompilerBaseTest(object):

    def __init__(self, name):
        self.project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", name)
        if not os.path.isdir(self.project_dir):
            raise Exception("A compile test should set a valid project directory: %s does not exist" % self.project_dir)

    def setUp(self):
        Project.set(Project(self.project_dir, autostd=False))
        self.state_dir = tempfile.mkdtemp()
        config.Config.load_config()
        config.Config.set("config", "state-dir", self.state_dir)

    def tearDown(self):
        shutil.rmtree(self.state_dir)


class SnippetTests(unittest.TestCase):
    libs = None
    env = None

    @classmethod
    def setUpClass(cls):
        cls.libs = tempfile.mkdtemp()
        cls.env = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.libs)
        shutil.rmtree(cls.env)

    def setUpForSnippet(self, snippet):
        # init project
        self.project_dir = tempfile.mkdtemp()
        os.symlink(self.__class__.env, os.path.join(self.project_dir, ".env"))

        with open(os.path.join(self.project_dir, "project.yml"), "w") as cfg:
            cfg.write(
                """
            name: snippet test
            modulepath: %s
            downloadpath: %s
            version: 1.0
            repo: ['git@git.inmanta.com:modules/', 'git@git.inmanta.com:config/']"""
                % (self.__class__.libs, self.__class__.libs))

        with open(os.path.join(self.project_dir, "main.cf"), "w") as x:
            x.write(snippet)

        Project.set(Project(self.project_dir))

    def xtearDown(self):
        shutil.rmtree(self.project_dir)

    @raises(DuplicateException)
    def testIssue90Compile(self):
        self.setUpForSnippet(""" import ip
import std
import redhat

ctrl1 = ip::Host(name="os-ctrl-1", os=redhat::centos7, ip="172.20.20.10")
odl1  = ip::Host(name="os-odl-1", os=redhat::centos7, ip="172.20.20.15")
comp1 = ip::Host(name="os-comp-1", os=redhat::centos7, ip="172.20.20.20")
comp2 = ip::Host(name="os-comp-1", os=redhat::centos7, ip="172.20.20.21")
""")
        compiler.do_compile()

    def testIssue92(self):
        self.setUpForSnippet("""
        entity Host extends std::NotThere:
        end
""")
        try:
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except TypeNotFoundException as e:
            assert_equal(e.location.lnr, 2)

    @raises(TypeNotFoundException)
    def testIssue73(self):
        self.setUpForSnippet("""
vm1 = std::floob()
""")

        compiler.do_compile()

    @raises(RuntimeException)
    def testOptionValues(self):
        self.setUpForSnippet("""
entity Test1:

end

entity Test2:
    bool flag=false
end

implement Test2 using std::none

Test1 test1 [1] -- [0:1] Test2 other

implementation tt for Test1:

end

implement Test1 using tt when self.other.flag == false

Test1()
""")
        compiler.do_compile()

    def testIsset(self):
        self.setUpForSnippet("""
entity Test1:

end

entity Test2:
    bool flag=false
end

implement Test2 using std::none

Test1 test1 [1] -- [0:1] Test2 other

implementation tt for Test1:

end

implement Test1 using tt when self.other is defined and self.other.flag == false

Test1(other=Test2())
""")
        compiler.do_compile()

    def testIssue93(self):
        self.setUpForSnippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
    string attribute="1234"
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2

t = Test1()
t2a = Test2(test1=t)
t2b = Test2(test1=t)

std::print(t.test2.attribute)
        """)

        try:
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except RuntimeException as e:
            assert_equal(e.location.lnr, 18)

    @raises(NotFoundException)
    def testIssue110Resolution(self):
        self.setUpForSnippet("""
entity Test1:

end
implement Test1 using test1i


implementation test1i for Test1:
    test = host
end

t = Test1()
""")

        compiler.do_compile()

    def testIssue120BadImport(self):
        self.setUpForSnippet("""import ip::ip""")
        try:
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except ModuleNotFoundException as e:
            assert_equal(e.location.lnr, 1)

    def testIssue120BadImport_extra(self):
        self.setUpForSnippet("""import slorpf""")
        try:
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except ModuleNotFoundException as e:
            assert_equal(e.location.lnr, 1)

    def testOrderOfExecution(self):
        self.setUpForSnippet("""
for i in std::sequence(10):
    std::print(i)
end
        """)

        saved_stdout = sys.stdout
        try:
            out = StringIO()
            sys.stdout = out
            compiler.do_compile()
            output = out.getvalue().strip()
            assert_equal(output, '\n'.join([str(x) for x in range(10)]))
        finally:
            sys.stdout = saved_stdout


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
        variables = {k: x.get_value() for k, x in scopes.get_child("__config__").scope.slots.items()}

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


class TestDoubleSet(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_double_assign")

    @raises(DoubleSetException)
    def test_compile(self):
        compiler.do_compile()
