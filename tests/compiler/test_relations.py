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
from typing import Optional, Tuple, Union

import pytest

import inmanta.ast.type as ast_type
import inmanta.compiler as compiler
from inmanta.ast import CompilerException, DuplicateException, Namespace, NotFoundException, RuntimeException, TypingException
from inmanta.execute.runtime import Instance, ResultVariable


def test_issue_93(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
        """
    )

    try:
        compiler.do_compile()
        raise AssertionError("Should get exception")
    except RuntimeException as e:
        assert e.location.lnr == 18


def test_issue_135_duplo_relations_2(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2
Test1 test1 [1] -- [0:] Test2 floem
"""
    )
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_issue_135_duplo_relations_3(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2
Test1 test1 [1] -- [0:] Test1 test2
"""
    )
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_issue_135_duplo_relations_4(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
"""
    )
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_issue_135_duplo_relations_5(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
"""
    )
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_issue_132_relation_on_default(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
typedef CFG as std::File(mode=755)
CFG cfg [1] -- [1] std::File stuff
"""
    )
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_issue_141(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
h = std::Host(name="test", os=std::linux)

entity SpecialService extends std::Service:

end

std::Host host [1] -- [0:] SpecialService services_list"""
    )
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_m_to_n(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
        """
    )

    (types, _) = compiler.do_compile()
    for lf in types["__config__::LogFile"].get_all_instances():
        assert lf.get_attribute("members").get_value() == len(lf.get_attribute("collectors").get_value())


def test_new_relation_syntax(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
"""
    )
    types, root = compiler.do_compile()

    scope = root.get_child("__config__").scope

    assert len(scope.lookup("a").get_value().get_attribute("tests").get_value()) == 2
    assert len(scope.lookup("b").get_value().get_attribute("tests").get_value()) == 1


def test_new_relation_with_annotation_syntax(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
"""
    )
    types, root = compiler.do_compile()

    scope = root.get_child("__config__").scope

    assert len(scope.lookup("a").get_value().get_attribute("tests").get_value()) == 2
    assert len(scope.lookup("b").get_value().get_attribute("tests").get_value()) == 1


def test_new_relation_uni_dir(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1.tests [0:] -- Test2

a = Test1(tests=[Test2(),Test2()])

"""
    )
    types, root = compiler.do_compile()

    scope = root.get_child("__config__").scope

    assert len(scope.lookup("a").get_value().get_attribute("tests").get_value()) == 2


def test_new_relation_uni_dir_double_define(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1.tests [0:] -- Test2

Test2.xx [1] -- Test1.tests [0:]
"""
    )
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_relation_attributes(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
"""
    )
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    bar = root.lookup("bar")
    annotations = bar.value.get_attribute("bar").attribute.source_annotations
    assert len(annotations) == 2
    assert annotations[0].get_value() == "a"
    assert annotations[1].get_value() == bar.value


def test_relation_attributes_unresolved(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
end

entity Foo:
end

foo = "a"

implement Test using std::none
implement Foo using std::none


Test.bar [1] foo,bar Foo
"""
    )
    with pytest.raises(NotFoundException):
        compiler.do_compile()


def test_relation_attributes_unknown(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
"""
    )
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_671_bounds_check(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """ entity Test:

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
""",
        autostd=False,
    )
    compiler.do_compile()


def test_587_assign_extend_correct(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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

    """
    )

    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a")
    ab = a.get_value().get_attribute("b").get_value()
    assert ["a", "b"] == [v.get_attribute("name").get_value() for v in ab]


def test_587_assign_extend_incorrect(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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

    """
    )

    with pytest.raises(TypingException):
        (_, scopes) = compiler.do_compile()


def test_set_wrong_relation_type(snippetcompiler):
    """
    Test the error message when setting the wrong type on a relation in the two cases:
    1) on an instance
    2) in the constructor
    """
    # noqa: E501
    snippetcompiler.setup_for_error(
        """
        entity Credentials:
        end

        Credentials.file [1] -- std::File

        implement Credentials using std::none

        creds = Credentials(file=creds)
        """,
        """Could not set attribute `file` on instance `__config__::Credentials (instantiated at {dir}/main.cf:9)`"""
        """ (reported in Construct(Credentials) ({dir}/main.cf:9))
caused by:
  Invalid class type for __config__::Credentials (instantiated at {dir}/main.cf:9), should be std::File """
        """(reported in Construct(Credentials) ({dir}/main.cf:9))""",
    )

    snippetcompiler.setup_for_error(
        """
        entity Credentials:
        end

        Credentials.file [1] -- std::File

        implement Credentials using std::none

        creds = Credentials()
        creds.file = creds
        """,
        r"""Could not set attribute `file` on instance `__config__::Credentials (instantiated at {dir}/main.cf:9)` (reported in creds.file = creds ({dir}/main.cf:10))
caused by:
  Invalid class type for __config__::Credentials (instantiated at {dir}/main.cf:9), should be std::File (reported in creds.file = creds ({dir}/main.cf:10))""",  # noqa: E501
    )


def test_610_multi_add(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        entity A:
        end
        implement A using std::none

        entity B:
            string name
        end
        implement B using std::none

        A.b [2:] -- B

        a = A()
        a.b = B(name = "a")

        """,
        "The object __config__::A (instantiated at {dir}/main.cf:13) is not complete:"
        " attribute b ({dir}/main.cf:11:11) requires 2 values but only 1 are set",
    )


def test_670_assign_on_relation(snippetcompiler):
    snippetcompiler.setup_for_error_re(
        """
        h = std::Host(name="test", os=std::linux)
        f = std::ConfigFile(host=h, path="a", content="")

        h.files.path = "1"

        """,
        r"The object at h.files is not an Entity but a <class 'list'> with value \[std::ConfigFile [0-9a-fA-F]+\]"
        r" \(reported in h.files.path = '1' \({dir}/main.cf:5\)\)",
    )


def test_reflexive(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:

end
implement Test1 using std::none

Test1.peer [1] -- Test1.peer [1]
"""
    )
    compiler.do_compile()


def test_1600_relation_arity_exceeded_error_message(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity A:
end
implement A using std::none
entity AContainer:
end
implement AContainer using std::none

AContainer.aa [0:2] -- A


container = AContainer(aa = [A(), A()])
container.aa = A()
        """,
        "Could not set attribute `aa` on instance `__config__::AContainer (instantiated at {dir}/main.cf:12)`"
        " (reported in container.aa = Construct(A) ({dir}/main.cf:13))"
        "\n"
        "caused by:"
        "\n"
        "  Exceeded relation arity on attribute 'aa' of instance '__config__::AContainer (instantiated at {dir}/main.cf:12)'"
        " (reported in container.aa = Construct(A) ({dir}/main.cf:13))",
    )


@pytest.mark.parametrize("multi", (True, False))
def test_relation_null(snippetcompiler, multi: bool) -> None:
    snippetcompiler.setup_for_snippet(
        """
entity A:
end

A.other [0:%s] -- A

implement A using std::none


a = A()
a.other = null
        """
        % ("" if multi else "1")
    )
    root_ns: Namespace
    (_, root_ns) = compiler.do_compile()
    config_ns: Optional[Namespace] = root_ns.get_child("__config__")
    assert config_ns is not None
    a_var: Union[ast_type.Type, ResultVariable] = config_ns.lookup("a")
    assert isinstance(a_var, ResultVariable)
    a: object = a_var.get_value()
    assert isinstance(a, Instance)
    other_var: ResultVariable = a.get_attribute("other")
    if multi:
        assert other_var.value == []
    else:
        assert other_var.value is None


def test_optional_variable_relation(snippetcompiler):
    """
    Make sure DeprecatedOptionVariables do not allow `null`.
    """
    snippetcompiler.setup_for_error(
        """
entity A:
    number[] ns
end

implement A using std::none


a = A()
a.ns = null
        """,
        "Could not set attribute `ns` on instance `__config__::A (instantiated at {dir}/main.cf:9)`"
        " (reported in a.ns = null ({dir}/main.cf:10))"
        "\ncaused by:"
        "\n  Invalid value 'null', expected number[] (reported in a.ns = null ({dir}/main.cf:10))",
    )


@pytest.mark.parametrize(
    "statements,valid",
    [
        (("a.other = null", "a.other = null"), True),
        (("a.other = A()", "a.other = null"), False),
        (("a.other = null", "a.other = A()"), False),
        (("a.others = null", "a.others = null"), True),
        (("a.others = [A(), A()]", "a.others = null"), False),
        (("a.others = null", "a.others = [A(), A()]"), False),
    ],
)
def test_relation_null_multiple_assignments(snippetcompiler, statements: Tuple[str, str], valid: bool) -> None:
    snippetcompiler.setup_for_snippet(
        f"""
entity A:
end

A.other [0:1] -- A
A.others [0:] -- A

implement A using std::none


a = A()
{statements[0]}
{statements[1]}
        """
    )
    if valid:
        compiler.do_compile()
    else:
        with pytest.raises(CompilerException):
            compiler.do_compile()


def test_2689_relation_unset_lower(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        """
entity A:
end

entity B:
end
B.a [:1] -- A
B(a=A())

implement A using std::none
implement B using std::none
        """
    )
    compiler.do_compile()
