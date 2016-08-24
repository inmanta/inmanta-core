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

from nose.tools import assert_equal, assert_regexp_matches, assert_is_not_none, assert_list_equal
from inmanta.module import Project
import inmanta.compiler as compiler
from inmanta import config
from inmanta.ast import RuntimeException, DoubleSetException, DuplicateException, TypeNotFoundException, ModuleNotFoundException
from inmanta.ast import MultiException
from inmanta.ast import NotFoundException, TypingException
from nose.tools.nontrivial import raises
from inmanta.parser import ParserException
from unittest.case import skip


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

    def testIssue121_non_matching_index(self):
        self.setUpForSnippet("""
        a=std::Host[name="test"]
        """)

        try:
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except NotFoundException as e:
            assert_equal(e.location.lnr, 2)

    def testIssue122IndexInheritance(self):
        self.setUpForSnippet("""
entity Repository extends std::File:
    string name
    bool gpgcheck=false
    bool enabled=true
    string baseurl
    string gpgkey=""
    number metadata_expire=7200
end

implementation redhatRepo for Repository:
    self.mode = 644
    self.owner = "root"
    self.group = "root"

    self.path = "/etc/yum.repos.d/{{ name }}.repo"
    self.content = "{{name}}"
end

implement Repository using redhatRepo

import redhat

h1 = std::Host(name="test", os=redhat::fedora23)

Repository(host=h1, name="flens-demo",
                           baseurl="http://people.cs.kuleuven.be/~wouter.deborger/repo/")

Repository(host=h1, name="flens-demo",
                           baseurl="http://people.cs.kuleuven.be/~wouter.deborger/repo/")
        """)

        try:
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except TypingException as e:
            assert_equal(e.location.lnr, 26)

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

    def testIssue127DefaultOverrides(self):
        self.setUpForSnippet("""
f1=std::ConfigFile(host=std::Host(name="jos",os=std::linux), path="/tmp/test", owner="wouter", content="blabla")
        """)
        (types, scopes) = compiler.do_compile()
        instances = types["std::File"].get_all_instances()
        assert_equal(instances[0].get_attribute("owner").get_value(), "wouter")

    @raises(DuplicateException)
    def testIssue135DuploRelations(self):
        self.setUpForSnippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2
Test1 test1 [0:1] -- [0:] Test2 test2
""")
        compiler.do_compile()

    @raises(DuplicateException)
    def testIssue135DuploRelations2(self):
        self.setUpForSnippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2
Test1 test1 [1] -- [0:] Test2 floem
""")
        compiler.do_compile()

    @raises(DuplicateException)
    def testIssue135DuploRelations3(self):
        self.setUpForSnippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2
Test1 test1 [1] -- [0:] Test1 test2
""")
        compiler.do_compile()

    @raises(DuplicateException)
    def testIssue135DuploRelations4(self):
        self.setUpForSnippet("""
entity Stdhost:

end

entity Tussen extends Stdhost:
end

entity Oshost extends Tussen:

end

entity Agent:
end

Agent inmanta_agent   [1] -- [1] Oshost os_host
Stdhost deploy_host [1] -- [0:1] Agent inmanta_agent
""")
        compiler.do_compile()

    @raises(DuplicateException)
    def testIssue135DuploRelations5(self):
        self.setUpForSnippet("""
entity Stdhost:

end

entity Tussen extends Stdhost:
end

entity Oshost extends Tussen:

end

entity Agent:
end

Oshost os_host [1] -- [1] Agent inmanta_agent

Stdhost deploy_host [1] -- [0:1] Agent inmanta_agent
""")
        compiler.do_compile()

    @raises(TypingException)
    def testIssue132RelationOnDefault(self):
        self.setUpForSnippet("""
std::ConfigFile cfg [1] -- [1] std::File stuff
""")
        compiler.do_compile()

    @raises(DuplicateException)
    def testIssue141(self):
        self.setUpForSnippet("""
h = std::Host(name="test", os=std::linux)

entity SpecialService extends std::Service:

end

std::Host host [1] -- [0:] SpecialService services_list""")
        compiler.do_compile()

    def testIssue140IndexError(self):
        try:
            self.setUpForSnippet("""
        h = std::Host(name="test", os=std::linux)
        test = std::Service[host=h, path="test"]""")
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except NotFoundException as e:
            assert_regexp_matches(str(e), 'No index defined on std::Service for this lookup:.*')

    @raises(DuplicateException)
    def testIssue134CollidingUmplementations(self):

        self.setUpForSnippet("""
implementation test for std::Entity:
end
implementation test for std::Entity:
end""")
        compiler.do_compile()
        raise AssertionError("Should get exception")

    @raises(RuntimeException)
    def testIssue126HangingStatements(self):
        self.setUpForSnippet("""entity LogFile:
string name
end

implement LogFile using std::none

entity LogCollector:
string name
end

implement LogCollector using std::none

LogCollector collectors [0:] -- [0:] LogFile logfiles

    lf1 = LogFile(name="lf1", collectors = c2)

c2 = LogCollector(name="c2", logfiles=lf1)
""")

        compiler.do_compile()

    @raises(MultiException)
    def testIssue139Scheduler(self):
        self.setUpForSnippet("""import std

entity Host extends std::Host:
    string attr
end
implement Host using std::none

host = Host(name="vm1", os=std::linux)

f = std::ConfigFile(host=host, path="", content="{{ host.attr }}")
std::Service(host=host, name="svc", state="running", onboot=true, requires=[f])
ref = std::Service[host=host, name="svc"]

""")

        compiler.do_compile()

    def testMtoN(self):
        self.setUpForSnippet("""
entity LogFile:
  string name
  number members
end

implement LogFile using std::none

entity LogCollector:
  string name
end

implement LogCollector using std::none

LogCollector collectors [0:] -- [0:] LogFile logfiles

lf1 = LogFile(name="lf1", collectors = [c1, c2], members=3)
lf2 = LogFile(name="lf2", collectors = [c1, c2], members=2)
lf3 = LogFile(name="lf3", collectors = lf2.collectors, members=2)
lf6 = LogFile(name="lf6", collectors = c1, members=1)

lf4 = LogFile(name="lf4", members=2)
lf5 = LogFile(name="lf5", members=0)

lf7 = LogFile(name="lf7", members=2)
lf8 = LogFile(name="lf8", collectors = lf7.collectors, members=2)

c1 = LogCollector(name="c1")
c2 = LogCollector(name="c2", logfiles=[lf4, lf7])
c3 = LogCollector(name="c3", logfiles=[lf4, lf7, lf1])

std::print([c1,c2,lf1,lf2,lf3,lf4,lf5,lf6,lf7,lf8])
        """)

        (types, _) = compiler.do_compile()
        for lf in types["__config__::LogFile"].get_all_instances():
            assert_equal(lf.get_attribute("members").get_value(), len(lf.get_attribute("collectors").get_value()),
                         "content of collectors attribute is not correct on %s" % lf.get_attribute("name").get_value())

    def testListAtributes(self):
        self.setUpForSnippet("""
entity Jos:
  bool[] bar
  std::package_state[] ips = ["installed"]
  string[] floom = []
  string[] floomx = ["a", "b"]
  string box = "a"
end

implement Jos using std::none

a = Jos(bar = [true])
b = Jos(bar = [true, false])
c = Jos(bar = [])
d = Jos(bar = [], floom=["test","test2"])

""")
        (types, root) = compiler.do_compile()

        def check_jos(jos, bar, ips=["installed"], floom=[], floomx=["a", "b"], box="a"):
            jos = jos.get_value()
            assert_list_equal(jos.get_attribute("bar").get_value(), bar)
            assert_list_equal(jos.get_attribute("ips").get_value(), ips)
            assert_list_equal(jos.get_attribute("floom").get_value(), floom)
            assert_list_equal(jos.get_attribute("floomx").get_value(), floomx)
            assert_equal(jos.get_attribute("box").get_value(), box)

        scope = root.get_child("__config__").scope

        check_jos(scope.lookup("a"), [True])
        check_jos(scope.lookup("b"), [True, False])
        check_jos(scope.lookup("c"), [])
        check_jos(scope.lookup("d"), [], floom=["test", "test2"])

    @raises(ParserException)
    def testListAtributeTypeViolation1(self):
        self.setUpForSnippet("""
entity Jos:
  bool[] bar = true
end
implement Jos using std::none
c = Jos()
""")
        compiler.do_compile()

    @raises(RuntimeException)
    def testListAtributeTypeViolation2(self):
        self.setUpForSnippet("""
entity Jos:
  bool[] bar = ["x"]
end
implement Jos using std::none
c = Jos()
""")
        compiler.do_compile()

    @raises(RuntimeException)
    def testListAtributeTypeViolation3(self):
        self.setUpForSnippet("""
entity Jos:
  bool[] bar
end
implement Jos using std::none
c = Jos(bar = ["X"])
""")
        compiler.do_compile()

    def testNewRelationSyntax(self):
        self.setUpForSnippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1.tests [0:] -- Test2.test1 [1]

a = Test1(tests=[Test2(),Test2()])
b = Test1()
Test2(test1 = b)
""")
        types, root = compiler.do_compile()

        scope = root.get_child("__config__").scope

        assert_equal(len(scope.lookup("a").get_value().get_attribute("tests").get_value()), 2)
        assert_equal(len(scope.lookup("b").get_value().get_attribute("tests").get_value()), 1)


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


class TestCompileIssue138(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_138")

    def test_compile(self):
        (types, _) = compiler.do_compile()
        assert_is_not_none(types['std::Host'].get_all_instances()[0]
                           .get_attribute("agent").get_value()
                           .get_attribute("names").get_value())
