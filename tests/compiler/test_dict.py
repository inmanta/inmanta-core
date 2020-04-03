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
from inmanta.ast import DuplicateException, RuntimeException, TypingException
from inmanta.execute.runtime import Instance


def test_dict(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
a = "a"
b = { "a" : a, "b" : "b", "c" : 3}
"""
    )

    (_, root) = compiler.do_compile()

    scope = root.get_child("__config__").scope
    b = scope.lookup("b").get_value()
    assert b["a"] == "a"
    assert b["b"] == "b"
    assert b["c"] == 3


def test_dict_collide(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
a = "a"
b = { "a" : a, "a" : "b", "c" : 3}
"""
    )

    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_dict_attr(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
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
"""
    )

    (_, root) = compiler.do_compile()

    scope = root.get_child("__config__").scope

    def map_assert(in_dict, expected):
        for (ek, ev), (k, v) in zip(expected.items(), in_dict.items()):
            assert ek == k
            assert ev == v

    def validate(var, bar, foo, blah):
        e = scope.lookup(var).get_value()
        map_assert(e.get_attribute("bar").get_value(), bar)
        map_assert(e.get_attribute("foo").get_value(), foo)
        map_assert(e.get_attribute("blah").get_value(), blah)

    validate("a", {}, {}, {"a": "a"})
    validate("b", {"a": 5}, {}, {"a": "a"})

    validate("c", {}, {}, {"z": "y"})


def test_dict_attr_type_error(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Foo:
  dict bar
  dict foo = {}
  dict blah = {"a":"a"}
end

implement Foo using std::none

a=Foo(bar=b)
b=Foo(bar={"a":"A"})
"""
    )
    with pytest.raises(RuntimeException):
        compiler.do_compile()


def test_611_dict_access(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
a = "a"
b = { "a" : a, "b" : "b", "c" : 3}
c=b[a]
d=b["c"]
"""
    )

    (_, root) = compiler.do_compile()

    scope = root.get_child("__config__").scope
    assert scope.lookup("c").get_value() == "a"
    assert scope.lookup("d").get_value() == 3


def test_632_dict_access_2(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
b = { "a" : {"b":"c"}}
c=b["a"]["b"]
"""
    )

    (_, root) = compiler.do_compile()

    scope = root.get_child("__config__").scope
    assert scope.lookup("c").get_value() == "c"


def test_632_dict_access_3(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
b = { "a" : "b"}
c=b["a"]["b"]
"""
    )

    with pytest.raises(TypingException):
        compiler.do_compile()


def test_673_in_dict(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    dict attributes
end

implementation test for Test:

end

implement Test using test when "foo" in self.attributes

Test(attributes={"foo": 42})
"""
    )
    compiler.do_compile()


def test_bad_map_lookup(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        b = {"c" : 3}
        c=b["a"]
        """,
        "key a not found in dict, options are [c] (reported in c = b['a'] ({dir}/main.cf:3))",
    )


def test_1168_const_dict(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """typedef test as string matching std::contains({"1234":"xxx"}, self)

entity X:
    test x
end

X(x="1234")

implement X using std::none
"""
    )

    compiler.do_compile()


def test_1168_const_dict_failure(snippetcompiler):
    snippetcompiler.setup_for_error(
        """typedef test as string matching std::contains({"1234":z}, self)
z = "1234"

entity X:
    test x
end

X(x="1234")

implement X using std::none
""",
        """Could not set attribute `x` on instance `__config__::X (instantiated at {dir}/main.cf:8)` (reported in Construct(X) ({dir}/main.cf:8))
caused by:
  Unable to resolve `z`: a type constraint can not reference variables. (reported in z ({dir}/main.cf:1:55))""",  # noqa: E501,
    )


def test_constructor_kwargs(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    number n
    number m
    string str
end

implement Test using std::none

dct = { "config": {"n": 42, "m": 0 } }

x = Test(**dct["config"], str = "Hello World!")
"""
    )
    (_, root) = compiler.do_compile()
    scope = root.get_child("__config__").scope

    instance: Instance = scope.lookup("x").get_value()
    assert instance.get_attribute("n").get_value() == 42
    assert instance.get_attribute("m").get_value() == 0
    assert instance.get_attribute("str").get_value() == "Hello World!"


@pytest.mark.parametrize("override", [True, False])
def test_2003_constructor_kwargs_default(snippetcompiler, override: bool):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    number v = 0
end

implement Test using std::none

values = {%s}
t = Test(
    **values
)
        """
        % ("'v': 10" if override else ""),
    )
    (_, root) = compiler.do_compile()
    scope = root.get_child("__config__").scope

    instance: Instance = scope.lookup("t").get_value()
    assert instance.get_attribute("v").get_value() == (10 if override else 0)


def test_constructor_kwargs_double_set(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity A:
    int a
end

v = {"a": 4}
A(a = 3, **v)
        """,
        "The attribute a is set twice in the constructor call of A. (reported in Construct(A) ({dir}/main.cf:7))",
    )


def test_constructor_kwargs_index_match(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    number n
    number m
    string str
end

index Test(n, m)

implement Test using std::none

dct = { "config": {"n": 42, "m": 0 } }

x = Test(n = 42, m = 0, str = "Hello World!")
y = Test(**dct["config"], str = "Hello World!")
"""
    )
    (_, root) = compiler.do_compile()
    scope = root.get_child("__config__").scope

    x: Instance = scope.lookup("x").get_value()
    y: Instance = scope.lookup("y").get_value()
    assert x is y


def test_indexlookup_kwargs(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    number n
    number m
    string str
end

index Test(n, m)

implement Test using std::none

dct = {"m": 0}
x = Test(n = 42, m = 0, str = "Hello World!")

y = Test[n = 42, **dct]
    """
    )
    (_, root) = compiler.do_compile()
    scope = root.get_child("__config__").scope

    x: Instance = scope.lookup("x").get_value()
    y: Instance = scope.lookup("y").get_value()
    assert x is y


def test_short_indexlookup_kwargs(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Collection:
end

implement Collection using std::none

entity Test:
    number n
    number m
    string str
end

Collection.tests [0:] -- Test.collection [1]
index Test(collection, n, m)

implement Test using std::none

dct = {"m": 0}
c = Collection()

x = Test(collection = c, n = 42, m = 0, str = "Hello World!")
y = Test(collection = c, n = 0, m = 0, str = "Hello World!")

z = c.tests[n = 42, **dct]
    """
    )
    (_, root) = compiler.do_compile()
    scope = root.get_child("__config__").scope

    x: Instance = scope.lookup("x").get_value()
    z: Instance = scope.lookup("z").get_value()
    assert x is z
