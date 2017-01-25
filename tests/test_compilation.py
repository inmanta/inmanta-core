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
import re
from itertools import groupby
import sys
from io import StringIO


from inmanta.module import Project
import inmanta.compiler as compiler
from inmanta import config
from inmanta.ast import RuntimeException, DuplicateException, TypeNotFoundException, ModuleNotFoundException
from inmanta.ast import AttributeException
from inmanta.ast import MultiException
from inmanta.ast import NotFoundException, TypingException
from inmanta.parser import ParserException
import pytest
from inmanta.execute.util import Unknown
from inmanta.export import DependencyCycleException


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


class AbstractSnippetTest(object):
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
            modulepath: [%s, %s]
            downloadpath: %s
            version: 1.0
            repo: ['https://github.com/inmanta/']"""
                % (self.__class__.libs,
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules"),
                    self.__class__.libs))

        with open(os.path.join(self.project_dir, "main.cf"), "w") as x:
            x.write(snippet)

        Project.set(Project(self.project_dir))

    def do_export(self):
        config.Config.load_config()
        from inmanta.export import Exporter

        (types, scopes) = compiler.do_compile()

        class Options(object):
            pass
        options = Options()
        options.json = True
        options.depgraph = False
        options.deploy = False
        options.ssl = False

        export = Exporter(options=options)
        return export.run(types, scopes)

    def xtearDown(self):
        shutil.rmtree(self.project_dir)


class SnippetTests(AbstractSnippetTest, unittest.TestCase):

    def testIssue92(self):
        self.setUpForSnippet("""
        entity Host extends std::NotThere:
        end
""")
        try:
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except TypeNotFoundException as e:
            assert e.location.lnr == 2

    def testIssue73(self):
        self.setUpForSnippet("""
vm1 = std::floob()
""")
        with pytest.raises(TypeNotFoundException):
            compiler.do_compile()

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
        with pytest.raises(RuntimeException):
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
            assert e.location.lnr == 18

    def testIssue121_non_matching_index(self):
        self.setUpForSnippet("""
        a=std::Host[name="test"]
        """)

        try:
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except NotFoundException as e:
            assert e.location.lnr == 2

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

h1 = std::Host(name="test", os=std::linux)

Repository(host=h1, name="flens-demo",
                           baseurl="http://people.cs.kuleuven.be/~wouter.deborger/repo/")

Repository(host=h1, name="flens-demo",
                           baseurl="http://people.cs.kuleuven.be/~wouter.deborger/repo/")
        """)

        try:
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except TypingException as e:
            assert e.location.lnr == 24

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
        with pytest.raises(NotFoundException):
            compiler.do_compile()

    def testIssue120BadImport(self):
        self.setUpForSnippet("""import ip::ip""")
        try:
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except ModuleNotFoundException as e:
            assert e.location.lnr == 1

    def testIssue120BadImport_extra(self):
        self.setUpForSnippet("""import slorpf""")
        try:
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except ModuleNotFoundException as e:
            assert e.location.lnr == 1

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
            assert output == '\n'.join([str(x) for x in range(10)])
        finally:
            sys.stdout = saved_stdout

    def testIssue127DefaultOverrides(self):
        self.setUpForSnippet("""
f1=std::ConfigFile(host=std::Host(name="jos",os=std::linux), path="/tmp/test", owner="wouter", content="blabla")
        """)
        (types, _) = compiler.do_compile()
        instances = types["std::File"].get_all_instances()
        assert instances[0].get_attribute("owner").get_value() == "wouter"

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
        with pytest.raises(DuplicateException):
            compiler.do_compile()

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
        with pytest.raises(DuplicateException):
            compiler.do_compile()

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
        with pytest.raises(DuplicateException):
            compiler.do_compile()

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
        with pytest.raises(DuplicateException):
            compiler.do_compile()

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
        with pytest.raises(DuplicateException):
            compiler.do_compile()

    def testIssue132RelationOnDefault(self):
        self.setUpForSnippet("""
std::ConfigFile cfg [1] -- [1] std::File stuff
""")
        with pytest.raises(TypingException):
            compiler.do_compile()

    def testIssue141(self):
        self.setUpForSnippet("""
h = std::Host(name="test", os=std::linux)

entity SpecialService extends std::Service:

end

std::Host host [1] -- [0:] SpecialService services_list""")
        with pytest.raises(DuplicateException):
            compiler.do_compile()

    def testIssue140IndexError(self):
        try:
            self.setUpForSnippet("""
        h = std::Host(name="test", os=std::linux)
        test = std::Service[host=h, path="test"]""")
            compiler.do_compile()
            raise AssertionError("Should get exception")
        except NotFoundException as e:
            assert re.match('.*No index defined on std::Service for this lookup:.*', str(e))

    def testIssue134CollidingUmplementations(self):

        self.setUpForSnippet("""
implementation test for std::Entity:
end
implementation test for std::Entity:
end""")
        with pytest.raises(DuplicateException):
            compiler.do_compile()

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
        with pytest.raises(RuntimeException):
            compiler.do_compile()

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
        with pytest.raises(MultiException):
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
            assert lf.get_attribute("members").get_value() == len(lf.get_attribute("collectors").get_value())

    def testDict(self):
        self.setUpForSnippet("""
a = "a"
b = { "a" : a, "b" : "b", "c" : 3}
""")

        (_, root) = compiler.do_compile()

        scope = root.get_child("__config__").scope
        b = scope.lookup("b").get_value()
        assert b["a"] == "a"
        assert b["b"] == "b"
        assert b["c"] == 3

    def testDictCollide(self):
        self.setUpForSnippet("""
a = "a"
b = { "a" : a, "a" : "b", "c" : 3}
""")

        with pytest.raises(DuplicateException):
            compiler.do_compile()

    def testDictAttr(self):
        self.setUpForSnippet("""
entity Foo:
  dict bar
  dict foo = {}
  dict blah = {"a":"a"}
end

implement Foo using std::none

a=Foo(bar={})
b=Foo(bar={"a":z})
c=Foo(bar={}, blah={"z":"y"})
z=5
""")

        (_, root) = compiler.do_compile()

        scope = root.get_child("__config__").scope

        def mapAssert(in_dict, expected):
            for (ek, ev), (k, v) in zip(expected.items(), in_dict.items()):
                assert ek == k
                assert ev == v

        def validate(var, bar, foo, blah):
            e = scope.lookup(var).get_value()
            mapAssert(e.get_attribute("bar").get_value(), bar)
            mapAssert(e.get_attribute("foo").get_value(), foo)
            mapAssert(e.get_attribute("blah").get_value(), blah)

        validate("a", {}, {}, {"a": "a"})
        validate("b", {"a": 5}, {}, {"a": "a"})

        validate("c", {}, {}, {"z": "y"})

    def testDictAttrTypeError(self):
        self.setUpForSnippet("""
entity Foo:
  dict bar
  dict foo = {}
  dict blah = {"a":"a"}
end

implement Foo using std::none

a=Foo(bar=b)
b=Foo(bar={"a":"A"})
""")
        with pytest.raises(RuntimeException):
            compiler.do_compile()

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
        (_, root) = compiler.do_compile()

        def check_jos(jos, bar, ips=["installed"], floom=[], floomx=["a", "b"], box="a"):
            jos = jos.get_value()
            assert jos.get_attribute("bar").get_value() == bar
            assert jos.get_attribute("ips").get_value(), ips
            assert jos.get_attribute("floom").get_value() == floom
            assert jos.get_attribute("floomx").get_value() == floomx
            assert jos.get_attribute("box").get_value() == box

        scope = root.get_child("__config__").scope

        check_jos(scope.lookup("a"), [True])
        check_jos(scope.lookup("b"), [True, False])
        check_jos(scope.lookup("c"), [])
        check_jos(scope.lookup("d"), [], floom=["test", "test2"])

    def testListAtributeTypeViolation1(self):
        self.setUpForSnippet("""
entity Jos:
  bool[] bar = true
end
implement Jos using std::none
c = Jos()
""")
        with pytest.raises(ParserException):
            compiler.do_compile()

    def testListAtributeTypeViolation2(self):
        self.setUpForSnippet("""
entity Jos:
  bool[] bar = ["x"]
end
implement Jos using std::none
c = Jos()
""")
        with pytest.raises(RuntimeException):
            compiler.do_compile()

    def testListAtributeTypeViolation3(self):
        self.setUpForSnippet("""
entity Jos:
  bool[] bar
end
implement Jos using std::none
c = Jos(bar = ["X"])
""")
        with pytest.raises(RuntimeException):
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

        assert len(scope.lookup("a").get_value().get_attribute("tests").get_value()) == 2
        assert len(scope.lookup("b").get_value().get_attribute("tests").get_value()) == 1

    def testNewRelationWithAnnotationSyntax(self):
        self.setUpForSnippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

annotation = 5

Test1.tests [0:] annotation Test2.test1 [1]

a = Test1(tests=[Test2(),Test2()])
b = Test1()
Test2(test1 = b)
""")
        types, root = compiler.do_compile()

        scope = root.get_child("__config__").scope

        assert len(scope.lookup("a").get_value().get_attribute("tests").get_value()) == 2
        assert len(scope.lookup("b").get_value().get_attribute("tests").get_value()) == 1

    def testNewRelationUniDir(self):
        self.setUpForSnippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1.tests [0:] -- Test2

a = Test1(tests=[Test2(),Test2()])

""")
        types, root = compiler.do_compile()

        scope = root.get_child("__config__").scope

        assert len(scope.lookup("a").get_value().get_attribute("tests").get_value()) == 2

    def testNewRelationUniDirDoubleDefine(self):
        self.setUpForSnippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1.tests [0:] -- Test2

Test2.xx [1] -- Test1.tests [0:]
""")
        with pytest.raises(DuplicateException):
            compiler.do_compile()

    def testIssue164FQNInWhen(self):
        self.setUpForSnippet("""
import ubuntu
implementation linux for std::HostConfig:
end

implement std::HostConfig using linux when host.os == ubuntu::ubuntu1404

std::Host(name="vm1", os=ubuntu::ubuntu1404)
""")
        compiler.do_compile()

    def testIssue201DoubleSet(self):
        self.setUpForSnippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2

a=Test1()
b=Test2()

b.test1 = a
b.test1 = a

std::print(b.test1)
""")

        (types, _) = compiler.do_compile()
        a = types["__config__::Test1"].get_all_instances()[0]
        assert len(a.get_attribute("test2").value)

    def testIssue212BadIndexDefintion(self):
        self.setUpForSnippet("""
entity Test1:
    string x
end
index Test1(x,y)
""")
        with pytest.raises(RuntimeException):
            compiler.do_compile()

    def testIssue224DefaultOverInheritance(self):
        self.setUpForSnippet("""
entity Test1:
    string a = "a"
end
entity Test2 extends Test1:
end
entity Test3 extends Test2:
end
implement Test3 using std::none

Test3()
""")
        (types, _) = compiler.do_compile()
        instances = types["__config__::Test3"].get_all_instances()
        assert len(instances) == 1
        i = instances[0]
        assert i.get_attribute("a").get_value() == "a"

    def testIssue219UnknowsInTemplate(self):
        self.setUpForSnippet("""
import tests

a = tests::unknown()
b = "abc{{a}}"
""")
        (_, root) = compiler.do_compile()
        scope = root.get_child("__config__").scope

        assert isinstance(scope.lookup("a").get_value(), Unknown)
        assert isinstance(scope.lookup("b").get_value(), Unknown)

    def testIssue235EmptyLists(self):
        self.setUpForSnippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 tests [0:] -- [0:] Test2 tests

t1 = Test1(tests=[])
std::print(t1.tests)
""")
        (_, root) = compiler.do_compile()
        scope = root.get_child("__config__").scope

        assert scope.lookup("t1").get_value().get_attribute("tests").get_value() == []

    def testIssue170AttributeException(self):
        self.setUpForSnippet("""
entity Test1:
    string a
end

Test1(a=3)
""")
        with pytest.raises(AttributeException):
            compiler.do_compile()

    def testIssue220DepLoops(self):
        self.setUpForSnippet("""
import std

host = std::Host(name="Test", os=std::unix)
f1 = std::ConfigFile(host=host, path="/f1", content="")
f2 = std::ConfigFile(host=host, path="/f2", content="")
f3 = std::ConfigFile(host=host, path="/f3", content="")
f4 = std::ConfigFile(host=host, path="/f4", content="")
f1.requires = f2
f2.requires = f3
f3.requires = f1
f4.requires = f1
""")
        with pytest.raises(DependencyCycleException) as e:
            self.do_export()

        cyclenames = [r.id.resource_str() for r in e.value.cycle]
        assert set(cyclenames) == set(['std::File[Test,path=/f3]', 'std::File[Test,path=/f2]', 'std::File[Test,path=/f1]'])

    def test_str_on_instance_pos(self):
        self.setUpForSnippet("""
import std

entity Hg:
end

Hg.hosts [0:] -- std::Host

implement Hg using std::none

hg = Hg()

for i in [1,2,3]:
 hg.hosts = std::Host(name="Test{{i}}", os=std::unix)
end


for i in hg.hosts:
    std::ConfigFile(host=i, path="/fx", content="")
end
""")
        (types, _) = compiler.do_compile()
        files = types["std::File"].get_all_instances()
        assert len(files) == 3

    def test_str_on_instance_neg(self):
        self.setUpForSnippet("""
import std

entity Hg:
end

Hg.hosts [0:] -- std::Host

implement Hg using std::none

hg = Hg()

for i in [1,2,3]:
 hg.hosts = std::Host(name="Test", os=std::unix)
end


for i in hg.hosts:
    std::ConfigFile(host=i, path="/fx", content="")
end
""")
        (types, _) = compiler.do_compile()
        files = types["std::File"].get_all_instances()
        assert len(files) == 1


class TestBaseCompile(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
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

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_2")

    def test_compile(self):
        (types, _) = compiler.do_compile()
        instances = types["__config__::ManagedDevice"].get_all_instances()
        assert sorted([i.get_attribute("name").get_value() for i in instances]) == [1, 2, 3, 4, 5]


class TestIndexCompileCollision(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_index_collission")

    def test_compile(self):
        with pytest.raises(RuntimeException):
            compiler.do_compile()


class TestIndexCompile(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_index")

    def test_compile(self):
        (_, scopes) = compiler.do_compile()
        variables = {k: x.get_value() for k, x in scopes.get_child("__config__").scope.slots.items()}

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
                assert first[2] == other[2]

        for i in range(len(firsts)):
            for j in range(len(firsts)):
                if not i == j:
                    self.assertNotEqual(firsts[i][2], firsts[j][2], "Variable %s%s should not be equal to %s%s" % (
                        firsts[i][0], firsts[i][1], firsts[j][0], firsts[j][1]))


class TestDoubleSet(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_double_assign")

    def test_compile(self):
        with pytest.raises(AttributeException):
            compiler.do_compile()


class TestCompileIssue138(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_138")

    def test_compile(self):
        (types, _) = compiler.do_compile()
        assert (types['std::Host'].get_all_instances()[0].get_attribute("agent").get_value().
                get_attribute("names").get_value() is not None)
