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
from inmanta.ast import AttributeException, MultiException, OptionalValueException
from inmanta.execute.scheduler import InvalidRelationPrecedenceRuleError
from inmanta.module import RelationPrecedenceRule


def test_issue_139_scheduler(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import std
import std::testing

typedef service_state as string matching self == "running" or self == "stopped"

entity Service:
    string name
    service_state state
    bool onboot
    bool reload=false
    bool send_event=false
end

implement Service using serviceHost

Service.host [1] -- Host.services [0:]

index Service(host, name)

implementation serviceHost for Service:
    self.requires = self.host.requires
end

implement Service using serviceHost

entity Host extends std::Host:
    string attr
end
implement Host using std::none

host = Host(name="vm1", os=std::linux)

f = std::testing::NullResource(name=host.name)
Service(host=host, name="svc", state="running", onboot=true, requires=[f])
ref = Service[host=host, name="svc"]
"""
    )
    with pytest.raises(MultiException):
        compiler.do_compile()


def test_issue_201_double_set(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:

end
implement Test1 using none

entity Test2:
end
implement Test2 using none

Test1.test2 [0:] -- Test2.test1 [1]

a=Test1()
b=Test2()

b.test1 = a
b.test1 = a

implementation none for std::Entity:
end
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
   int id
   string value = ""
end

implement Thing using none
implementation none for std::Entity:
end

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
   int id
   string value
end

implement Thing using none

index Thing(id)

a = Thing(id=5)
a.value="{{a.id}}"

implementation none for std::Entity:
end
"""
    )

    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    assert "5" == root.lookup("a").get_value().lookup("value").get_value()


def test_lazy_attibutes3(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity  Thing:
   int id
end

Thing.value [1] -- StringWrapper

entity StringWrapper:
    string value
end

implement Thing using none
implement StringWrapper using none

implementation none for std::Entity:
end

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



kafka_user = std::Entity()
kafka_volume = Volume(requires=kafka_user)
KafkaNode(requires=kafka_volume)
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
""",
        autostd=True,
    )
    compiler.do_compile()


def test_relation_precedence_policy(snippetcompiler) -> None:
    """
    End-to-end test that verifies whether the relation precedence policy set on a project
    is correctly handled.
    """
    non_deterministic_model = """
    entity A:
    end

    A.list [0:] -- A
    A.optional [0:1] -- A

    implementation a for A:
        self.optional = A()
    end

    implement A using std::none
    implement A using a when std::count(self.list) > 0

    a = A(list=A())
    test = a.optional
    """

    snippetcompiler.setup_for_snippet(
        non_deterministic_model,
        autostd=True,
        relation_precedence_rules=[
            RelationPrecedenceRule(
                first_type="__config__::A",
                first_relation_name="list",
                then_type="__config__::A",
                then_relation_name="optional",
            )
        ],
    )
    # Relation precedence rules are set correctly, compile should succeed.
    compiler.do_compile()

    snippetcompiler.setup_for_snippet(
        non_deterministic_model,
        autostd=True,
        relation_precedence_rules=[
            RelationPrecedenceRule(
                first_type="__config__::A",
                first_relation_name="optional",
                then_type="__config__::A",
                then_relation_name="list",
            )
        ],
    )
    # Relation precedence rules are set correctly, compile should fail.
    with pytest.raises(OptionalValueException, match="Optional variable accessed that has no value"):
        compiler.do_compile()


def test_validation_relation_precedence_rules(snippetcompiler, caplog) -> None:
    """
    Verify that an appropriate exception is raised when invalid relation precedence rules are defined and
    ensure that the usage a relation precedence policy results in a warning message in the compiler log.
    """
    model = """
        entity A:
            string var = ""
        end

        A.list [0:] -- A
        A.optional [0:1] -- A

        implement A using none

        implementation none for std::Entity:
        end

        typedef tcp_port as int matching self > 0 and self < 65535
    """
    snippetcompiler.setup_for_snippet(
        model,
        relation_precedence_rules=[
            RelationPrecedenceRule(
                first_type="__config__::A",
                first_relation_name="list",
                then_type="__config__::B",
                then_relation_name="test",
            )
        ],
    )
    expected_error_message = "A relation precedence rule was defined for __config__::B, but no such type was defined"
    with pytest.raises(InvalidRelationPrecedenceRuleError, match=expected_error_message):
        compiler.do_compile()

    snippetcompiler.setup_for_snippet(
        model,
        relation_precedence_rules=[
            RelationPrecedenceRule(
                first_type="__config__::A",
                first_relation_name="list",
                then_type="__config__::A",
                then_relation_name="non_existing_relationship",
            )
        ],
    )
    expected_error_message = (
        "A relation precedence rule was defined for __config__::A.non_existing_relationship, "
        "but entity __config__::A doesn't have an attribute non_existing_relationship."
    )
    with pytest.raises(InvalidRelationPrecedenceRuleError, match=expected_error_message):
        compiler.do_compile()

    snippetcompiler.setup_for_snippet(
        model,
        relation_precedence_rules=[
            RelationPrecedenceRule(
                first_type="__config__::A",
                first_relation_name="list",
                then_type="__config__::A",
                then_relation_name="var",
            )
        ],
    )
    expected_error_message = (
        "A relation precedence rule was defined for __config__::A.var, " "but attribute var is not a relationship attribute."
    )
    with pytest.raises(InvalidRelationPrecedenceRuleError, match=expected_error_message):
        compiler.do_compile()

    snippetcompiler.setup_for_snippet(
        model,
        relation_precedence_rules=[
            RelationPrecedenceRule(
                first_type="__config__::tcp_port",
                first_relation_name="test",
                then_type="__config__::A",
                then_relation_name="optional",
            )
        ],
    )
    expected_error_message = "A relation precedence rule was defined for non-entity type __config__::tcp_port"
    with pytest.raises(InvalidRelationPrecedenceRuleError, match=expected_error_message):
        compiler.do_compile()

    # Only valid relation precedence rules are specified. Ensure log message regarding use of experimental feature.
    snippetcompiler.setup_for_snippet(
        model,
        relation_precedence_rules=[
            RelationPrecedenceRule(
                first_type="__config__::A",
                first_relation_name="list",
                then_type="__config__::A",
                then_relation_name="optional",
            )
        ],
    )
    caplog.clear()
    compiler.do_compile()
    assert "[EXPERIMENTAL FEATURE] Using the relation precedence policy" in caplog.text

    # No relation precedence policy defined. No warning usage experimental feature
    snippetcompiler.setup_for_snippet(model)
    caplog.clear()
    compiler.do_compile()
    assert "[EXPERIMENTAL FEATURE] Using the relation precedence policy" not in caplog.text
