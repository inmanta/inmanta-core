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

import re

import pytest

import inmanta.ast.type as inmanta_type
import inmanta.compiler as compiler
from inmanta.ast import AttributeException, Namespace, TypeDeprecationWarning, TypingException
from inmanta.ast.attribute import Attribute
from inmanta.ast.entity import Entity
from inmanta.ast.type import Bool, Float, Integer, Number, String
from inmanta.execute.util import Unknown


def test_lnr_on_double_is_defined(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string? two
end

Test.one [0:1] -- Test

implement Test using std::none when self.one.two is defined

a = Test(two="b")
a.one = a
"""
    )
    compiler.do_compile()


def test_double_define(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string test
    string? test
    bool test
end
"""
    )
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_536_number_cast(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Network:
    number segmentation_id
end
implement Network using std::none
net1 = Network(segmentation_id="10")
"""
    )
    with pytest.raises(AttributeException):
        compiler.do_compile()


def test_int_type(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    int i = 0
end

implement Test using std::none

Test(i = 42)
Test(i = -42)
Test()
        """,
    )
    compiler.do_compile()


def test_int_type_invalid(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test:
    int i = 0.0
end
        """,
        "Invalid value '0.0', expected int (reported in int i = 0.0 ({dir}/main.cf:3:9))",
    )


def test_cast_to_number(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
x = number("42")
x = 42
y = number("42.0")
y = 42.0
z = number(true)
z = 1
u = number(false)
u = 0
        """,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    x = root.lookup("x").get_value()
    y = root.lookup("y").get_value()
    z = root.lookup("z").get_value()
    u = root.lookup("u").get_value()
    assert Number().validate(x)
    assert Number().validate(y)
    assert Number().validate(z)
    assert Number().validate(u)


def test_cast_to_int(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
x = int("42")
x = 42
y = int(true)
y = 1
z = int(false)
z = 0
import tests
w = int(tests::unknown())
        """,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    x = root.lookup("x").get_value()
    y = root.lookup("y").get_value()
    z = root.lookup("z").get_value()
    w = root.lookup("w").get_value()
    assert Integer().validate(x)
    assert Integer().validate(y)
    assert Integer().validate(z)
    assert isinstance(w, Unknown)
    assert not any(isinstance(v, (bool, float)) for v in (x, y, z))


def test_cast_to_string(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
x = string(42)
x = "42"
y = string(42.0)
y = "42.0"
z = string(true)
z = "true"
        """,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    x = root.lookup("x").get_value()
    y = root.lookup("y").get_value()
    z = root.lookup("z").get_value()
    assert String().validate(x)
    assert String().validate(y)
    assert String().validate(z)


def test_cast_to_bool(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
x = bool(42)
x = true
y = bool(42.0)
y = true
z = bool(1)
z = true
u = bool(0)
u = false
v = bool("false")
v = true
w = bool("")
w = false
p = bool(null)
p = false
q = bool([])
q = false
r = bool([1])
r = true
        """,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    x = root.lookup("x").get_value()
    y = root.lookup("y").get_value()
    z = root.lookup("z").get_value()
    u = root.lookup("u").get_value()
    v = root.lookup("v").get_value()
    w = root.lookup("w").get_value()
    p = root.lookup("p").get_value()
    q = root.lookup("q").get_value()
    r = root.lookup("r").get_value()
    assert Bool().validate(x)
    assert Bool().validate(y)
    assert Bool().validate(z)
    assert Bool().validate(u)
    assert Bool().validate(v)
    assert Bool().validate(w)
    assert Bool().validate(p)
    assert Bool().validate(q)
    assert Bool().validate(r)


def test_cast_exception_kwargs(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
bool(value = 1)
        """,
        "Only positional arguments allowed in type cast (reported in bool(value=1) ({dir}/main.cf:2))",
    )


def test_cast_exception_wrapped_kwargs(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
dct = {"value" : 1}
bool(**dct)
        """,
        "Only positional arguments allowed in type cast (reported in bool(**dct) ({dir}/main.cf:3))",
    )


def test_cast_exception_too_many_args(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
bool(0, 1)
        """,
        "Illegal arguments 0,1: type cast expects exactly 1 argument (reported in bool(0,1) ({dir}/main.cf:2))",
    )


def test_cast_exception_non_primitive(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
list("[]")
        """,
        "Can not call 'list', can only call plugin or primitive type cast (reported in list('[]') ({dir}/main.cf:2))",
    )


def test_cast_exception_type_error(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
number(null)
        """,
        "Failed to cast 'null' to number (reported in number(null) ({dir}/main.cf:2))",
    )


def test_cast_exception_value_error(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
int("Hello World!")
        """,
        "Failed to cast 'Hello World!' to int (reported in int('Hello World!') ({dir}/main.cf:2))",
    )


def test_cast_exception_int_value_error(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
int("0.0")
        """,
        "Failed to cast '0.0' to int (reported in int('0.0') ({dir}/main.cf:2))",
    )


@pytest.mark.parametrize(
    "parent_modifier,child_modifier",
    [("[]", ""), ("", "[]"), ("?", ""), ("", "?")],
)
def test_2132_inheritance_type_override(snippetcompiler, parent_modifier: str, child_modifier: str) -> None:
    snippetcompiler.setup_for_error(
        f"""
entity Parent:
    number{parent_modifier} n
end

entity Child extends Parent:
    number{child_modifier} n
end
        """,
        "Incompatible attributes (original at ({dir}/main.cf:7:%d)) (duplicate at ({dir}/main.cf:3:%d))"
        % (12 + len(child_modifier), 12 + len(parent_modifier)),
    )


def test_attribute_type(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        """
entity A:
    number n
    number[] ns
    number? maybe_n
    number[]? maybe_ns
    list lst
end
        """,
    )
    types: dict[str, inmanta_type.Type]
    (types, scopes) = compiler.do_compile()
    assert "__config__::A" in types
    entity = types["__config__::A"]
    assert isinstance(entity, Entity)
    attrs: dict[str, Attribute] = entity.get_attributes()

    assert "n" in attrs
    assert isinstance(attrs["n"].type, Number)

    assert "ns" in attrs
    ns_type: inmanta_type.Type = attrs["ns"].type
    assert isinstance(ns_type, inmanta_type.TypedList)
    assert isinstance(ns_type.element_type, Number)

    assert "maybe_n" in attrs
    maybe_n_type: inmanta_type.Type = attrs["maybe_n"].type
    assert isinstance(maybe_n_type, inmanta_type.NullableType)
    assert isinstance(maybe_n_type.element_type, Number)

    assert "maybe_ns" in attrs
    maybe_ns_type: inmanta_type.Type = attrs["maybe_ns"].type
    assert isinstance(maybe_ns_type, inmanta_type.NullableType)
    maybe_ns_element_type: inmanta_type.Type = maybe_ns_type.element_type
    assert isinstance(maybe_ns_element_type, inmanta_type.TypedList)
    assert isinstance(maybe_ns_element_type.element_type, Number)

    assert "lst" in attrs
    assert isinstance(attrs["lst"].type, inmanta_type.List)


@pytest.mark.parametrize("base_type", inmanta_type.TYPES.values())
def test_types_base_type(snippetcompiler, base_type: inmanta_type.Type) -> None:
    modified_types: list[inmanta_type.Type] = [
        base_type,
        inmanta_type.TypedList(base_type),
        inmanta_type.NullableType(base_type),
        inmanta_type.NullableType(inmanta_type.TypedList(base_type)),
    ]
    for t in modified_types:
        # verify get_base_type returns the inmanta base type
        assert t.get_base_type().type_string() == base_type.type_string()
        # verify with_base_type is round-trip compatible
        assert t.with_base_type(base_type).type_string() == t.type_string()


def test_2243_override_optional(snippetcompiler) -> None:
    # make sure this compiles without errors
    snippetcompiler.setup_for_snippet(
        """
entity Parent:
    bool? val
end

implement Parent using std::none

entity Child extends Parent:
    bool? val = false
end

implement Child using std::none

Child()
        """,
    )


def test_deprecate_number(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    number val
end
        """,
    )
    with pytest.warns(
        TypeDeprecationWarning,
        match=re.escape("Type 'number' is deprecated, use 'float' or 'int' instead"),
    ):
        (_, scopes) = compiler.do_compile()


def test_same_value_float_int(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
    i = 42.0
    j = 42
    i = j
    j = i
    a = (42 == 42.0)
    a = true
    """,
    )
    (_, scopes) = compiler.do_compile()


def test_different_value_float_int(snippetcompiler, capsys):
    snippetcompiler.setup_for_error(
        """
    i = 42.1
    j = 42
    i = j
    """,
        "value set twice:\n"
        "\told value: 42.1\n"
        "\t\tset at {dir}/main.cf:2\n"
        "\tnew value: 42\n"
        "\t\tset at {dir}/main.cf:4:9\n"
        " (reported in i = j ({dir}/main.cf:4))",
    )


@pytest.mark.parametrize("float_val", ["42.0", "42.1"])
def test_float_attribute(snippetcompiler, float_val):
    snippet = f"""
    entity Float:
        float i
    end
    implement Float using std::none
    f = Float(i={float_val})
    """
    snippetcompiler.setup_for_snippet(snippet)


@pytest.mark.parametrize("float_val", ["42.0", "42.1"])
def test_int_attribute_with_float(snippetcompiler, float_val):
    snippet = f"""
    entity Int:
        int i
    end
    implement Int using std::none
    i = Int(i={float_val}) # => not an int
    """
    snippetcompiler.setup_for_error(
        snippet,
        "Could not set attribute `i` on instance `__config__::Int (instantiated at "
        "{dir}/main.cf:6)` (reported in Construct(Int) "
        "({dir}/main.cf:6))\n"
        "caused by:\n"
        f"  Invalid value '{float_val}', expected int (reported in Construct(Int) "
        "({dir}/main.cf:6))",
    )


def test_assign_float_to_int(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
    entity Test:
        int i = 0
    end
    implement Test using std::none
    Test(i = 42.1)
        """,
        "Could not set attribute `i` on instance `__config__::Test (instantiated at {dir}/main.cf:6)` "
        "(reported in Construct(Test) ({dir}/main.cf:6))\n"
        "caused by:\n"
        "  Invalid value '42.1', expected int (reported in Construct(Test) ({dir}/main.cf:6))",
    )


def test_assign_int_to_float(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
    entity Test:
        float i = 0.0
    end
    implement Test using std::none
    x = Test(i = 42.0)
    """,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    x = root.lookup("x").get_value()
    i = x.get_attribute("i").get_value()
    assert not isinstance(i, int)
    assert isinstance(i, float)


def test_float_type(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
    entity Test:
        float i = 0.0
    end
    implement Test using std::none
    Test(i = 42.0)
    Test(i = -42.0)
    Test()
    a = float(21)
    a = 21.0
    b = float(25.0)
    b = 25.0
    x = float("31")
    x = 31.0
    y = float("22.0")
    y = 22.0
    z = float(true)
    z = 1.0
    u = float(false)
    u = 0.0
    """,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    a = root.lookup("a").get_value()
    b = root.lookup("b").get_value()
    x = root.lookup("x").get_value()
    y = root.lookup("y").get_value()
    z = root.lookup("z").get_value()
    u = root.lookup("u").get_value()
    assert Number().validate(a)
    assert Number().validate(b)
    assert Number().validate(x)
    assert Number().validate(y)
    assert Number().validate(z)
    assert Number().validate(u)


def test_print_float(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """
std::print(float(1.234))
std::print(float(1.0))
        """,
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "1.234" in out
    assert "1.0" in out


def test_print_number(snippetcompiler, capsys):
    snippetcompiler.setup_for_snippet(
        """
std::print(number(1.234))
        """,
    )
    compiler.do_compile()
    out, err = capsys.readouterr()
    assert "1.234" in out


def test_float_type_argument_plugin(snippetcompiler, caplog):
    snippetcompiler.setup_for_snippet(
        """
import test_674

test = test_674::test_float_to_int(1.234)
        """
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    x = root.lookup("test").get_value()
    assert Integer().validate(x)


@pytest.mark.parametrize("val", [42, "test"])
def test_float_type_argument_plugin_error(snippetcompiler, val):
    snippet = f"""
    import test_674

    test = test_674::test_float_to_int({repr(val)})
            """
    msg = f"Invalid value '{val}', expected float (reported in test_674::test_float_to_int({repr(val)}) ({{dir}}/main.cf:4))"

    snippetcompiler.setup_for_error(
        snippet,
        msg,
    )


def test_float_type_return_type_plugin(snippetcompiler, caplog):
    snippetcompiler.setup_for_snippet(
        """
import test_674

test = test_674::test_int_to_float(1)
        """
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    x = root.lookup("test").get_value()
    assert Float().validate(x)


def test_float_type_return_type_plugin_error(snippetcompiler, caplog):
    snippetcompiler.setup_for_error(
        """
import test_674

test = test_674::test_error_float()
        """,
        (
            "Exception in plugin test_674::test_error_float (reported in "
            "test_674::test_error_float() ({dir}/main.cf:4))\n"
            "caused by:\n"
            "  Invalid value '1', expected float (reported in "
            "test_674::test_error_float() ({dir}/main.cf:4))"
        ),
    )


@pytest.mark.parametrize(
    "type, value",
    [
        ("int", "hello"),
        ("float", "hello"),
        ("number", "hello"),
        ("string", 5),
        ("bool", "hello"),
        ("list", "hello"),
        ("dict", "hello"),
    ],
)
def test_type_error_message(snippetcompiler, caplog, type, value):
    snippetcompiler.setup_for_error(
        f"""
entity Test:
    {type} test
end

implement Test using std::none

x = Test()
x.test = {repr(value)}
        """,
        (
            "Could not set attribute `test` on instance `__config__::Test (instantiated "
            f"at {{dir}}/main.cf:8)` (reported in x.test = {repr(value)} "
            "({dir}/main.cf:9))\n"
            "caused by:\n"
            f"  Invalid value '{value}', expected {type} (reported in x.test = {repr(value)} "
            "({dir}/main.cf:9))"
        ),
    )
