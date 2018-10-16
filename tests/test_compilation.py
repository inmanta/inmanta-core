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

from io import StringIO
from itertools import groupby
import os
import re
import shutil
import sys
import tempfile
import unittest

import pytest

from inmanta import config
from inmanta.ast import AttributeException, IndexException
from inmanta.ast import MultiException
from inmanta.ast import NotFoundException, TypingException
from inmanta.ast import RuntimeException, DuplicateException, TypeNotFoundException, ModuleNotFoundException, \
    OptionalValueException
import inmanta.compiler as compiler
from inmanta.execute.proxy import UnsetException
from inmanta.execute.util import Unknown, NoneValue
from inmanta.export import DependencyCycleException
from inmanta.module import Project
from inmanta.parser import ParserException
from utils import assert_graph


class CompilerBaseTest(object):

    def __init__(self, name, mainfile=None):
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

    def __init__(self, methodName='runTest'):  # noqa: H803
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

    def __init__(self, methodName='runTest'):  # noqa: H803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_2")

    def test_compile(self):
        (types, _) = compiler.do_compile()
        instances = types["__config__::ManagedDevice"].get_all_instances()
        assert sorted([i.get_attribute("name").get_value() for i in instances]) == [1, 2, 3, 4, 5]


class TestIndexCompileCollision(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):  # noqa: H803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_index_collission")

    def test_compile(self):
        with pytest.raises(RuntimeException):
            compiler.do_compile()


class TestIndexCompile(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):  # noqa: H803
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

    def __init__(self, methodName='runTest'):  # noqa: H803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_test_double_assign")

    def test_compile(self):
        with pytest.raises(AttributeException):
            compiler.do_compile()


class TestCompileIssue138(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):  # noqa: H803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_138")

    def test_compile(self):
        (types, _) = compiler.do_compile()
        assert (types['std::Host'].get_all_instances()[0].get_attribute("agent").get_value().
                get_attribute("names").get_value() is not None)


class TestCompileluginTyping(CompilerBaseTest, unittest.TestCase):

    def __init__(self, methodName='runTest'):  # noqa: H803
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

    def __init__(self, methodName='runTest'):  # noqa: H803
        unittest.TestCase.__init__(self, methodName)
        CompilerBaseTest.__init__(self, "compile_plugin_typing", "invalid.cf")

    def test_compile(self):
        with pytest.raises(RuntimeException) as e:
            compiler.do_compile()
        text = e.value.format_trace(indent="  ")
        print(text)
        assert text == """Exception in plugin test::badtype (reported in test::badtype(c1.items) ({dir}/invalid.cf:16))
caused by:
  Invalid type for value 'a', should be type test::Item""".format(
            dir=self.project_dir)


def test_null(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
        entity A:
            string? a = null
        end
        implement A using std::none
        a = A()

    """)

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value().get_attribute("a").get_value()
    assert isinstance(a, NoneValue)


def test_null_unset(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
        entity A:
            string? a
        end
        implement A using std::none
        a = A()

    """)

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    with pytest.raises(OptionalValueException):
        root.lookup("a").get_value().get_attribute("a").get_value()


def test_null_unset_hang(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
            entity A:
                string? a
            end
            implement A using std::none
            a = A()
            b = a.a
        """)
    with pytest.raises(OptionalValueException):
        (_, scopes) = compiler.do_compile()


def test_null_on_list(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
        entity A:
            string[]? a = null
        end
        implement A using std::none
        a = A()
    """)

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value().get_attribute("a").get_value()
    assert isinstance(a, NoneValue)


def test_null_on_dict(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
        entity A:
            dict? a = null
        end
        implement A using std::none
        a = A()
    """)

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value().get_attribute("a").get_value()
    assert isinstance(a, NoneValue)


def test_default_remove(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
    entity A:
        bool at = true
    end
    implement A using std::none

    entity B extends A:
        bool at = undef
    end
    implement B using std::none

    a = A()
    b = B()
    """)
    with pytest.raises(UnsetException):
        compiler.do_compile()


def test_emptylists(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
    implement std::Entity using std::none

    a=std::Entity()
    b=std::Entity()
    c=std::Entity()

    a.provides = b.provides
    b.provides = c.provides
    """)
    compiler.do_compile()


def test_doc_string_on_new_relation(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity File:
end

entity Host:
end

File.host [1] -- Host
\"""
Each file needs to be associated with a host
\"""
""")
    (types, _) = compiler.do_compile()
    assert types["__config__::File"].get_attribute("host").comment.strip() == "Each file needs to be associated with a host"


def test_doc_string_on_relation(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity File:
end

entity Host:
end

File file [1] -- [0:] Host host
\"""
Each file needs to be associated with a host
\"""
""")
    (types, _) = compiler.do_compile()
    assert types["__config__::File"].get_attribute("host").comment.strip() == "Each file needs to be associated with a host"
    assert types["__config__::Host"].get_attribute("file").comment.strip() == "Each file needs to be associated with a host"


def test_function_in_typedef(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
import tests
typedef notempty as string matching tests::length(self) > 0
typedef uniquechars as string matching tests::empty(self)

entity A:
    notempty ne
    uniquechars uc
end

A(ne="aa", uc="")

implement A using std::none
""")
    (types, _) = compiler.do_compile()


def test_doc_string_on_typedef(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
typedef foo as string matching /^a+$/
\"""
    Foo is a stringtype that only allows "a"
\"""
""")
    (types, _) = compiler.do_compile()
    assert types["__config__::foo"].comment.strip() == "Foo is a stringtype that only allows \"a\""


def test_doc_string_on_typedefault(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity File:
    number x
end

typedef Foo as File(x=5)
\"""
    Foo is a stringtype that only allows "a"
\"""
""")
    (types, _) = compiler.do_compile()
    assert types["__config__::Foo"].comment.strip() == "Foo is a stringtype that only allows \"a\""


def test_doc_string_on_impl(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Host:
end

implementation test for Host:
    \"""
        Bla bla
    \"""
end
""")

    (types, _) = compiler.do_compile()
    assert types["__config__::Host"].implementations[0].comment.strip() == "Bla bla"


def test_doc_string_on_implements(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Host:
end

implementation test for Host:
end

implement Host using test
\"""
    Always use test!
\"""
""")
    (types, _) = compiler.do_compile()

    assert types["__config__::Host"].implements[0].comment.strip() == "Always use test!"


def test_400_typeloops(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
    entity Test extends Test:

    end
    """)
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_400_typeloops_2(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
    entity Test extends Test2:

    end

    entity Test2 extends Test:

    end
    """)
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_394_short_index(snippetcompiler):
    snippetcompiler.setup_for_snippet("""implementation none for std::Entity:

end

entity Host:
    string name
    string blurp
end

entity File:
    string name
end

implement Host using none
implement File using none

Host host [1] -- [0:] File files

index Host(name)
index File(host, name)

h1 = Host(name="h1", blurp="blurp1")
f1h1=File(host=h1,name="f1")
f2h1=File(host=h1,name="f2")

z = h1.files[name="f1"]
""")
    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    z = root.lookup("z").get_value()
    f1h1 = root.lookup("f1h1").get_value()
    assert z is f1h1


def test_438_parent_scopes_accessible(snippetcompiler):

    snippetcompiler.setup_for_snippet("""
entity Host:
    string name
end

entity HostConfig:
    string result
end

HostConfig.host [1] -- Host

implementation hostDefaults for Host:
    test="foo"
    HostConfig(host=self)
end

implement Host using hostDefaults

implementation test for HostConfig:
    # fails correctly
    # std::print(test)
    # works and should fail
    self.result = name
end

implement HostConfig using test

Host(name="bar")
""", autostd=False)
    with pytest.raises(NotFoundException):
        compiler.do_compile()


def test_438_parent_scopes_accessible_2(snippetcompiler):

    snippetcompiler.setup_for_snippet("""
entity Host:
    string name
end

entity HostConfig:
    string result
end

HostConfig.host [1] -- Host

implementation hostDefaults for Host:
    test="foo"
    HostConfig(host=self)
end

implement Host using hostDefaults

implementation test for HostConfig:
    self.result = test
end

implement HostConfig using test

Host(name="bar")
""", autostd=False)
    with pytest.raises(NotFoundException):
        compiler.do_compile()


def test_veryhardsequencing(snippetcompiler):

    snippetcompiler.setup_for_snippet("""
implementation none for std::Entity:

end

implement std::Entity using none

#Volumes
entity Volume:
end

implementation create for Volume:
    backing = std::Entity(requires=self.requires)
    backing.provides = self.provides
end

implement Volume using create

entity KafkaNode:

end


implementation fromtarball for KafkaNode:
    install = std::Entity()
    install.requires = self.requires
end

implement KafkaNode using fromtarball



kafka-user = std::Entity()
kafka-volume = Volume(requires=kafka-user)
KafkaNode(requires=kafka-volume)
""", autostd=False)

    compiler.do_compile()


def test_lazy_constructor(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity One:
end

entity Two:
end

One.two [1] -- Two.one [1]

one = One(two=two)
two = Two(one=one)

implementation none for std::Entity:

end

implement One using none
implement Two using none
""", autostd=False)

    compiler.do_compile()


def test_484_attr_redef(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
typedef type as string matching self == "component" or self == "package" or self == "frame"

entity Node:
    type viz_type
end

entity Group extends Node:
end

entity Service extends Group:
    string viz_type="package"
end
""", autostd=False)
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_index_on_subtype(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
        host = std::Host(name="a",os=std::linux)
        a=std::DefaultDirectory(host=host,path="/etc")
        b=std::DefaultDirectory(host=host,path="/etc")
    """)

    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a")
    b = root.lookup("b")

    assert a.get_value() == b.get_value()


def test_index_on_subtype2(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
        host = std::Host(name="a",os=std::linux)
        a=std::DefaultDirectory(host=host,path="/etc")
        b=std::Directory(host=host,path="/etc",mode=755 ,group="root",owner="root" )
    """)
    with pytest.raises(DuplicateException):
        compiler.do_compile()


diamond = """
entity A:
    string at = "a"
end
implement A using std::none

entity B:
    string at = "a"
end
implement B using std::none


entity C extends A,B:
end
implement C using std::none
"""


def test_index_on_subtype_diamond(snippetcompiler):
    snippetcompiler.setup_for_snippet(diamond + """
    index A(at)
    index B(at)

    a = A(at="a")
    b = C(at="a")
    """)

    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_index_on_subtype_diamond_2(snippetcompiler):
    snippetcompiler.setup_for_snippet(diamond + """
    index A(at)
    index B(at)

    a = A(at="a")
    b = B(at="a")
    """)
    compiler.do_compile()


def test_index_on_subtype_diamond_3(snippetcompiler):
    snippetcompiler.setup_for_snippet(diamond + """
    index A(at)
    index B(at)

    a = A(at="a")
    b = B(at="ab")
    """)
    compiler.do_compile()


def test_index_on_subtype_diamond_4(snippetcompiler):
    snippetcompiler.setup_for_snippet(diamond + """
    index A(at)
    index B(at)

    a = C(at="a")
    b = C(at="a")
    a=b
    """)
    (types, _) = compiler.do_compile()
    c = types["__config__::C"]
    assert len(c.get_indices()) == 1


def test_relation_attributes(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test:
end

entity Foo:
end

foo = "a"
bar = Test()
bar.bar = Foo()

implement Test using std::none
implement Foo using std::none


Test.bar [1] foo,bar Foo
""")
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    bar = root.lookup("bar")
    annotations = bar.value.get_attribute("bar").attribute.source_annotations
    assert len(annotations) == 2
    assert annotations[0].get_value() == "a"
    assert annotations[1].get_value() == bar.value


def test_relation_attributes_unresolved(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test:
end

entity Foo:
end

foo = "a"

implement Test using std::none
implement Foo using std::none


Test.bar [1] foo,bar Foo
""")
    with pytest.raises(NotFoundException):
        compiler.do_compile()


def test_relation_attributes_unknown(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test:
end

entity Foo:
end

import tests

foo = tests::unknown()
bar = "a"

implement Test using std::none
implement Foo using std::none


Test.bar [1] foo,bar Foo
""")
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_implements_inheritance(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test:
    string a
end

entity TestC extends Test:
end

implementation test for Test:
    self.a = "xx"
end



implement Test using test
implement TestC using parents

a = TestC()
""")
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    assert "xx" == root.lookup("a").get_value().lookup("a").get_value()


def test_double_define(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test:
    string test
    string? test
    bool test
end
""")
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_511_index_on_default(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test:
    string a="a"
    string b
end

index Test(a, b)

implement Test using std::none

Test(b="b")
""")
    compiler.do_compile()


def test_536_number_cast(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Network:
    number segmentation_id
end
implement Network using std::none
net1 = Network(segmentation_id="10")
""")
    with pytest.raises(AttributeException):
        compiler.do_compile()


def test_587_assign_extend_correct(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
    entity A:
    end
    implement A using std::none

    entity B:
        string name
    end
    implement B using std::none

    A.b [0:] -- B

    a = A()
    a.b += B(name = "a")
    a.b += B(name = "b")

    """)

    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a")
    ab = a.get_value().get_attribute("b").get_value()
    assert ["a", "b"] == [v.get_attribute("name").get_value() for v in ab]


def test_587_assign_extend_incorrect(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
    entity A:
    end
    implement A using std::none

    entity B:
        string name
    end
    implement B using std::none

    A.b [1:1] -- B

    a = A()
    a.b += B(name = "a")

    """)

    with pytest.raises(TypingException):
        (_, scopes) = compiler.do_compile()


def test_611_dict_access(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
a = "a"
b = { "a" : a, "b" : "b", "c" : 3}
c=b[a]
d=b["c"]
""")

    (_, root) = compiler.do_compile()

    scope = root.get_child("__config__").scope
    assert scope.lookup("c").get_value() == "a"
    assert scope.lookup("d").get_value() == 3


def test_632_dict_access_2(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
b = { "a" : {"b":"c"}}
c=b["a"]["b"]
""")

    (_, root) = compiler.do_compile()

    scope = root.get_child("__config__").scope
    assert scope.lookup("c").get_value() == "c"


def test_632_dict_access_3(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
b = { "a" : "b"}
c=b["a"]["b"]
""")

    with pytest.raises(TypingException):
        compiler.do_compile()


def test_552_string_rendering_for_lists(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Network:
    string[] tags=[]
end

implement Network using std::none

net1 = Network(tags=["vlan"])
a="Net has tags {{ net1.tags }}"
""")

    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value()

    assert a == """Net has tags ['vlan']"""


def test_608_opt_to_list(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
implementation none for std::Entity:
end

entity A:
    string name
end

entity B:
    string name
end

B.a [1:] -- A

entity C:
    string name
end

C.a [0:1] -- A

implement A using none
implement B using none
implement C using none

a1 = A(name="a1")
a2 = A(name="a2")

b1 = B(name="b1")

c1 = C(name="c1")

b1.a = a1
b1.a = c1.a
""")
    with pytest.raises(OptionalValueException):
        (_, scopes) = compiler.do_compile()


def test_608_opt_to_single(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
implementation none for std::Entity:
end

entity A:
    string name
end

entity B:
    string name
end

B.a [1] -- A

entity C:
    string name
end

C.a [0:1] -- A

implement A using none
implement B using none
implement C using none

a1 = A(name="a1")

b1 = B(name="b1")

c1 = C(name="c1")

b1.a = a1
b1.a = c1.a
""")
    with pytest.raises(OptionalValueException):
        (_, scopes) = compiler.do_compile()


def test_608_opt_to_single_2(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
implementation none for std::Entity:
end

entity A:
    string name
end

entity B:
    string name
end

B.a [1] -- A

entity C:
    string name
end

C.a [0:1] -- A

implement A using none
implement B using none
implement C using none

a1 = A(name="a1")

b1 = B(name="b1")

c1 = C(name="c1")

b1.a = a1
b1.a = c1.a

c1.a = a1
""")
    (_, scopes) = compiler.do_compile()


def test_608_list_to_list(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
implementation none for std::Entity:
end

entity A:
    string name
end

entity B:
    string name
end

B.a [1:] -- A

entity C:
    string name
end

C.a [0:] -- A

implement A using none
implement B using none
implement C using none

a1 = A(name="a1")
a2 = A(name="a2")

b1 = B(name="b1")

c1 = C(name="c1")

b1.a = a1
b1.a = c1.a
""")
    (_, scopes) = compiler.do_compile()


def test_608_list_to_single(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
implementation none for std::Entity:
end

entity A:
    string name
end

entity B:
    string name
end

B.a [1] -- A

entity C:
    string name
end

C.a [0:] -- A

implement A using none
implement B using none
implement C using none

a1 = A(name="a1")
a2 = A(name="a2")

b1 = B(name="b1")

c1 = C(name="c1")

b1.a = c1.a
""")
    with pytest.raises(AttributeException):
        (_, scopes) = compiler.do_compile()


def test_633_default_on_list(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Foo:
   list first=[]
   list second=["a", "b"]
   string[] third=["a", "b"]
end

implementation none for std::Entity:
end

implement Foo using none

foo = Foo()
""")
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    foo = root.lookup("foo").get_value()

    ab = foo.get_attribute("first").get_value()
    assert ab == []

    second = foo.get_attribute("second").get_value()
    assert second == ["a", "b"]

    third = foo.get_attribute("third").get_value()
    assert third == ["a", "b"]


def test_lnr_on_double_is_defined(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test:
    string? two
end

Test.one [0:1] -- Test

implement Test using std::none when self.one.two is defined

a = Test(two="b")
a.one = a
""")
    compiler.do_compile()


def test_671_bounds_check(snippetcompiler):
    snippetcompiler.setup_for_snippet(""" entity Test:

end

entity Foo:

end

Test.foos [2] -- Foo

t = Test()
t.foos += Foo()
t.foos += Foo()

a = t.foos

implementation none for std::Entity:
end

implement Test using none
implement Foo using none
""", autostd=False)
    compiler.do_compile()


def test_673_in_dict(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test:
    dict attributes
end

implementation test for Test:

end

implement Test using test when "foo" in self.attributes

Test(attributes={"foo": 42})
""")
    compiler.do_compile()


def test_673_in_list(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test:
    string[] attributes
end

implementation test for Test:

end

implement Test using test when "foo" in self.attributes

Test(attributes=["blah", "foo"])
""")
    compiler.do_compile()


def test_643_cycle_empty(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Alpha:
end

implementation none for std::Entity:
end

implement Alpha using none

a = Alpha()

a.requires = a.provides
""")
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value()

    ab = a.get_attribute("requires").get_value()
    assert ab == []


def test_643_cycle(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Alpha:
    string name
end

implementation none for std::Entity:
end

implement Alpha using none

a = Alpha(name="a")
b = Alpha(name="b")

a.requires = b
a.requires = b.provides
""")
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value()
    b = root.lookup("b").get_value()

    # a.requires = b  ==> b.provides = a
    # a.requires = b.provides => a.requires = a ==> a.provides = a

    ab = [alpha.get_attribute("name").get_value() for alpha in a.get_attribute("requires").get_value()]
    assert sorted(ab) == ["a", "b"]

    ab = [alpha.get_attribute("name").get_value() for alpha in a.get_attribute("provides").get_value()]
    assert sorted(ab) == ["a"]

    ab = [alpha.get_attribute("name").get_value() for alpha in b.get_attribute("provides").get_value()]
    assert sorted(ab) == ["a"]


def test_643_forcycle_complex(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Alpha:
    string name
end

Alpha.alink [0:] -- Alpha

implementation links for std::Entity:
    for x in alink:
        x.alink = self.alink
    end
end

implement Alpha using links

a = Alpha(name="a")
b = Alpha(name="b")
c = Alpha(name="c")
d = Alpha(name="d")

a.alink = b
a.alink = c
a.alink = d

b.alink = c

b.alink = a

""", autostd=False)
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value()
    b = root.lookup("b").get_value()
    c = root.lookup("c").get_value()
    d = root.lookup("d").get_value()

    def get_names(a):
        return sorted([alpha.get_attribute("name").get_value() for alpha in a.get_attribute("alink").get_value()])

    assert get_names(a) == ["a", "b", "c", "d"]
    assert get_names(b) == ["a", "b", "c", "d"]
    assert get_names(c) == ["a", "b", "c", "d"]
    assert get_names(d) == ["a", "b", "c", "d"]


def test_643_forcycle_complex_reverse(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Alpha:
    string name
end

Alpha.alink [0:] -- Alpha.blink [0:]

implementation links for std::Entity:
    for x in alink:
        x.alink = self.alink
    end
end

implement Alpha using links

a = Alpha(name="a")
b = Alpha(name="b")
c = Alpha(name="c")
d = Alpha(name="d")

a.alink = b
a.alink = c
a.alink = d

b.alink = c

b.alink = a

""", autostd=False)
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value()
    b = root.lookup("b").get_value()
    c = root.lookup("c").get_value()
    d = root.lookup("d").get_value()

    def get_names(a, name="alink"):
        return sorted([alpha.get_attribute("name").get_value() for alpha in a.get_attribute(name).get_value()])

    assert get_names(a) == ["a", "b", "c", "d"]
    assert get_names(b) == ["a", "b", "c", "d"]
    assert get_names(c) == ["a", "b", "c", "d"]
    assert get_names(d) == ["a", "b", "c", "d"]

    assert get_names(a, "blink") == ["a", "b", "c", "d"]
    assert get_names(b, "blink") == ["a", "b", "c", "d"]
    assert get_names(c, "blink") == ["a", "b", "c", "d"]
    assert get_names(d, "blink") == ["a", "b", "c", "d"]


def test_lazy_attibutes(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity  Thing:
   number id
   string value
end

implement Thing using std::none

index Thing(id)

a = Thing(id=5, value="{{a.id}}")

""")

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")

    assert "5" == root.lookup("a").get_value().lookup("value").get_value()


def test_lazy_attibutes2(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity  Thing:
   number id
   string value
end

implement Thing using std::none

index Thing(id)

a = Thing(id=5)
a.value="{{a.id}}"

""")

    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    assert "5" == root.lookup("a").get_value().lookup("value").get_value()


def test_lazy_attibutes3(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity  Thing:
   number id
end

Thing.value [1] -- StringWrapper

entity StringWrapper:
    string value
end

implement Thing using std::none
implement StringWrapper using std::none


index Thing(id)

a = Thing(id=5, value=StringWrapper(value="{{a.id}}"))

""")
    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")

    assert "5" == root.lookup("a").get_value().lookup("value").get_value().lookup("value").get_value()


def test_747_entity_multi_location(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Alpha:
    string name
end

implementation none for Alpha:
end
implement Alpha using none

index Alpha(name)

a= Alpha(name="A")
b= Alpha(name="A")
c= Alpha(name="A")
""", autostd=False)
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value()
    assert len(a.get_locations()) == 3
    assert sorted([l.lnr for l in a.get_locations()]) == [12, 13, 14]


def test_749_is_unknown(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
        import tests

        a="a"
        b=tests::unknown()

        au = tests::is_uknown(a)
        bu = tests::is_uknown(b)

        ax = tests::do_uknown(a)
        bx = tests::do_uknown(b)
    """)

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")

    assert not root.lookup("au").get_value()
    assert root.lookup("bu").get_value()

    assert root.lookup("ax").get_value() == "XX"
    assert root.lookup("bx").get_value() == "XX"
