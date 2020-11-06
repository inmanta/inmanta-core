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

import pytest

import inmanta.compiler as compiler
from inmanta.ast import AttributeException, MultiException


def test_issue_139_scheduler(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """import std

entity Host extends std::Host:
    string attr
end
implement Host using std::none

host = Host(name="vm1", os=std::linux)

f = std::ConfigFile(host=host, path="", content="{{ host.attr }}")
std::Service(host=host, name="svc", state="running", onboot=true, requires=[f])
ref = std::Service[host=host, name="svc"]

"""
    )
    with pytest.raises(MultiException):
        compiler.do_compile()


def test_issue_201_double_set(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
"""
    )

    (types, _) = compiler.do_compile()
    a = types["__config__::Test1"].get_all_instances()[0]
    assert len(a.get_attribute("test2").value)


def test_issue_170_attribute_exception(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:
    string a
end

Test1(a=3)
"""
    )
    with pytest.raises(AttributeException):
        compiler.do_compile()


def test_execute_twice(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import mod4::other
import mod4
    """
    )

    (_, scopes) = compiler.do_compile()
    assert scopes.get_child("mod4").lookup("main").get_value() == 0
    assert scopes.get_child("mod4").get_child("other").lookup("other").get_value() == 0


def test_643_cycle_empty(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Alpha:
end

implementation none for std::Entity:
end

implement Alpha using none

a = Alpha()

a.requires = a.provides
"""
    )
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value()

    ab = a.get_attribute("requires").get_value()
    assert ab == []


def test_643_cycle(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
"""
    )
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
    snippetcompiler.setup_for_snippet(
        """
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

""",
        autostd=False,
    )
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
    snippetcompiler.setup_for_snippet(
        """
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

""",
        autostd=False,
    )
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
    snippetcompiler.setup_for_snippet(
        """
entity  Thing:
   number id
   string value = ""
end

implement Thing using std::none

index Thing(id)

a = Thing(id=5, value="{{a.id}}")

"""
    )

    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")

    assert "5" == root.lookup("a").get_value().lookup("value").get_value()


def test_lazy_attibutes2(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity  Thing:
   number id
   string value
end

implement Thing using std::none

index Thing(id)

a = Thing(id=5)
a.value="{{a.id}}"

"""
    )

    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    assert "5" == root.lookup("a").get_value().lookup("value").get_value()


def test_lazy_attibutes3(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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

"""
    )
    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")

    assert "5" == root.lookup("a").get_value().lookup("value").get_value().lookup("value").get_value()


def test_veryhardsequencing(snippetcompiler):

    snippetcompiler.setup_for_snippet(
        """
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
""",
        autostd=False,
    )

    compiler.do_compile()


def test_lazy_constructor(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
""",
        autostd=False,
    )

    compiler.do_compile()


def test_incomplete(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
import std

entity Test1:
    string a
end

implement Test1 using std::none

t1 = Test1()
""",
        "The object __config__::Test1 (instantiated at {dir}/main.cf:10) is not complete: "
        "attribute a ({dir}/main.cf:5:12) is not set",
    )


def test_issue_2378_scheduler(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity A:
    string name
end

A.b [0:] -- B

entity B:
    string name
end


b = B(name="b")

a3 = A(name="a3")

a1 = A(name="a1")
a2 = A(name="a2")

implement A using std::none
implement B using std::none

a3.b = std::key_sort(a1.b, "name")
a1.b = a2.b
a2.b += b
"""
    )
    compiler.do_compile()
