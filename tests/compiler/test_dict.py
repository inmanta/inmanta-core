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

from inmanta.ast import TypingException
from inmanta.ast import RuntimeException, DuplicateException
import inmanta.compiler as compiler


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
        "key a not found in dict, options are [c] (reported in b['a'] ({dir}/main.cf:3))",
    )
