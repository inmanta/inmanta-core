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
        "attribute field ({dir}/main.cf:3) is not set",
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
