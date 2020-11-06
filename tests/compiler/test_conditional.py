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
from inmanta.ast import Namespace, NotFoundException


def test_if_true(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string field
end
implement Test using std::none
test = Test()
if 1 == 1:
    test.field = "substitute"
end
        """
    )
    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    assert "substitute" == root.lookup("test").get_value().lookup("field").get_value()


def test_if_false(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test:
    string field
end
implement Test using std::none
test = Test()
if 0 == 1:
    test.field = "substitute"
end
        """,
        "The object __config__::Test (instantiated at {dir}/main.cf:6) is not complete: "
        "attribute field ({dir}/main.cf:3:12) is not set",
    )


def test_if_else_true(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string field
end
implement Test using std::none
test = Test()
if 1 == 1:
    test.field = "substitute"
else:
    test.field = "alt"
end
        """
    )
    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    assert "substitute" == root.lookup("test").get_value().lookup("field").get_value()


def test_if_else_false(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string field
end
implement Test using std::none
test = Test()
if 0 == 1:
    test.field = "substitute"
else:
    test.field = "alt"
end
        """
    )
    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    assert "alt" == root.lookup("test").get_value().lookup("field").get_value()


def test_if_else_extended(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string field
    string field2
end
implement Test using std::none

entity A:
    string a = ""
end
implement A using std::none

test = Test()
a = A(a="a")

if a.a == "b":
    test.field = "substitute"
    test.field2 = "substitute2"
else:
    test.field = "alt"
    test.field2 = "alt2"
end
        """
    )
    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")
    test = root.lookup("test").get_value()
    assert "alt" == test.lookup("field").get_value()
    assert "alt2" == test.lookup("field2").get_value()


def test_if_scope_new(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
a = 1
if 1 == 1:
    a = 2
end
        """
    )
    compiler.do_compile()


def test_if_scope_double_assignment(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Test:
    string field
end
implement Test using std::none
a = Test()
if 1 == 1:
    a.field = "val"
    a = 3
end
        """,
        "The object at a is not an Entity but a <class 'int'> with value 3 (reported in a.field = 'val' ({dir}/main.cf:8))",
    )


def test_if_scope_capture(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string field
end
implement Test using std::none

b = 1
if 1 == 1:
    b = 2
    if 1 == 1:
        b = 3
        a.field = "val"
    end
    a = Test()
end
        """
    )
    (types, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    assert 1 == root.lookup("b").get_value()
    with pytest.raises(NotFoundException):
        root.lookup("a")
    test_instances = types["__config__::Test"].get_all_instances()
    assert 1 == len(test_instances)


def test_if_relation_count(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    bool multiple
end
entity Ref:
end

implement Test using std::none
implement Ref using std::none

Ref.test [1] -- Test.refs [0:]

r1 = Ref()
r2 = Ref()
t = Test()
if std::count(t.refs) > 1:
    t.multiple = true
else:
    t.multiple = false
end
r1.test = t
r2.test = t
        """
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    assert root.lookup("t").get_value().lookup("multiple").get_value()


def test_if_relation_count_false(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    bool multiple
end
entity Ref:
end

implement Test using std::none
implement Ref using std::none

Ref.test [1] -- Test.refs [0:]

r1 = Ref()
r1.test = t
if std::count(t.refs) > 1:
    t.multiple = true
else:
    t.multiple = false
end
t = Test()
        """
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    assert not root.lookup("t").get_value().lookup("multiple").get_value()


def test_1573_if_dict_lookup(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    bool t_success
    bool f_success
end

implement Test using std::none

dct = {"t": true, "f": false}

x = Test()
if dct["t"]:
    x.t_success = true
else:
    x.t_success = false
end

if dct["f"]:
    x.f_success = false
else:
    x.f_success = true
end
        """,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    assert root.lookup("x").get_value().lookup("t_success").get_value() is True
    assert root.lookup("x").get_value().lookup("f_success").get_value() is True


def test_1573_implementation_condition_dict_lookup(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    bool success
end

implementation i_t for Test:
    self.success = true
end

implementation i_f for Test:
    self.success = false
end

dct = {"t": true, "f": false}

implement Test using i_t when dct["t"]
implement Test using i_f when dct["f"]

x = Test()
        """,
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    assert root.lookup("x").get_value().lookup("success").get_value() is True


def test_1804_false_and_condition(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity A:
    number n
end
implement A using std::none

x = A(n = 42)
if false and true == true:
    x.n = 0
else:
    x.n = 42
end
        """,
    )
    compiler.do_compile()


def test_1804_implementation_condition_false(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity A:
    bool b
end

implement A using t when true
implement A using f when false

implementation t for A:
    self.b = true
end

implementation f for A:
    self.b = false
end

A()
        """,
    )
    compiler.do_compile()


def test_1808_non_boolean_condition(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
str = "some_string"
if str and true:
end
        """,
        "Invalid left hand value `some_string`: `and` expects a boolean (reported in (str and true) ({dir}/main.cf:3))",
    )


def test_1808_non_boolean_condition_direct_exec(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
typedef mytype as string matching self in ["a", "b"] or null
entity A:
    mytype myvalue = "x"
end
implement A using std::none
        """,
        "Invalid right hand value `null`: `or` expects a boolean (reported in ((self in ['a','b']) or null) ({dir}/main.cf:2))",
    )


def test_1808_non_boolean_not(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
str = "some_string"
if not str:
end
        """,
        "Invalid value `some_string`: `not` expects a boolean (reported in If ({dir}/main.cf:3))",
    )


def test_1808_non_boolean_if(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
str = "some_string"
if str:
end
        """,
        "Invalid value `some_string`: the condition for an if statement can only be a boolean expression"
        " (reported in If ({dir}/main.cf:3))",
    )


def test_1808_non_boolean_when(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity A:
end
implement A using std::none

str = "some_string"

implementation i for A:
end
implement A using i when str

A()
        """,
        "Invalid value `some_string`: the condition for a conditional implementation can only be a boolean expression"
        " (reported in implement __config__::A using i when str ({dir}/main.cf:10:11))",
    )


def test_conditional_expression(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity A:
    int n
    int sign
end

implement A using a

implementation a for A:
    self.sign = self.n > 0 ? 1 : self.n < 0 ? -1 : 0
    std::print(self.n)
    std::print(self.n > 0)
end


x = A(n = 42)
y = A(n = -42)
z = A(n = 0)
        """
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    assert root.lookup("x").get_value().lookup("sign").get_value() == 1
    assert root.lookup("y").get_value().lookup("sign").get_value() == -1
    assert root.lookup("z").get_value().lookup("sign").get_value() == 0


def test_conditional_expression_when(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity A:
    int? primary = null
    int secondary
end

A.others [0:] -- A

implement A using std::none
implement A using a when self.primary is defined ? self.primary > 0 : self.secondary > 0

implementation a for A:
    self.others = A(secondary = 0)
end

x = A(primary = 1, secondary = -1)
y = A(primary = -1, secondary = 1)
z = A(primary = null, secondary = 1)
u = A(primary = null, secondary = -1)
        """
    )
    (_, scopes) = compiler.do_compile()
    root: Namespace = scopes.get_child("__config__")
    assert len(root.lookup("x").get_value().lookup("others").get_value()) == 1
    assert len(root.lookup("y").get_value().lookup("others").get_value()) == 0
    assert len(root.lookup("z").get_value().lookup("others").get_value()) == 1
    assert len(root.lookup("u").get_value().lookup("others").get_value()) == 0


def test_conditional_expression_prevents_modify_after_freeze(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Base:
end

Base.x [0:] -- std::Entity

implement Base using base


entity A extends Base:
end

A.y [0:] -- std::Entity

implement A using parents, a


implementation base for Base:
    n = std::count(self.x)
end

implementation a for A:
    # using an if statement here causes a list modified after freeze error (sometimes) because the scheduler has
    # no reason to prefer `y` over `x` when freezing:
    #if std::count(self.y) > 0:
    #    self.x += Base()
    #end
    # The use of the conditional expression allows the scheduler to infer that self.x must not be frozen yet
    # because it is waiting for at least one other value.
    self.x += std::count(self.y) > 0 ? [Base()] : []
end


A(y = A())
        """
    )
    compiler.do_compile()
