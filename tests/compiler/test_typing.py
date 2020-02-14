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
from inmanta.ast import AttributeException, Namespace, TypingException
from inmanta.ast.type import Bool, Integer, Number, String


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
        "Invalid value '0.0', expected int (reported in int i = 0.0 ({dir}/main.cf:3))",
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
        """,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    x = root.lookup("x").get_value()
    y = root.lookup("y").get_value()
    z = root.lookup("z").get_value()
    assert Integer().validate(x)
    assert Integer().validate(y)
    assert Integer().validate(z)


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
    assert Bool().validate(x)
    assert Bool().validate(y)
    assert Bool().validate(z)
    assert Bool().validate(u)
    assert Bool().validate(v)
    assert Bool().validate(w)


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
number("Hello World!")
        """,
        "Failed to cast 'Hello World!' to number (reported in number('Hello World!') ({dir}/main.cf:2))",
    )


def test_cast_exception_int_value_error(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
int("0.0")
        """,
        "Failed to cast '0.0' to int (reported in int('0.0') ({dir}/main.cf:2))",
    )
