"""
    Copyright 2016 Inmanta

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
from inmanta.ast import NotFoundException, OptionalValueException, RuntimeException
from inmanta.execute.proxy import DynamicProxy
from inmanta.execute.util import NoneValue


def proxy_object(snippetcompiler, snippet, var):
    snippetcompiler.setup_for_snippet(snippet)
    (_, root) = compiler.do_compile()

    scope = root.get_child("__config__").scope

    value = scope.lookup(var).get_value()
    return DynamicProxy.return_value(value)


def test_basic_object(snippetcompiler):
    px = proxy_object(
        snippetcompiler,
        """
entity Test1:
string x
end
implement Test1 using std::none

a = Test1(x="a")
""",
        "a",
    )

    assert px.x == "a"
    with pytest.raises(Exception):
        px.x = "b"


def test_dict_attr(snippetcompiler):
    px = proxy_object(
        snippetcompiler,
        """
entity Test1:
dict x = {}
end
implement Test1 using std::none

a = Test1(x={"a":"A"})
""",
        "a",
    )

    dic = px.x
    assert dic["a"] == "A"
    with pytest.raises(Exception):
        dic["a"] = "Z"

    with pytest.raises(Exception):
        dic["b"]

    with pytest.raises(Exception):
        dic["b"] = "a"


def test_unwrap_none():
    assert DynamicProxy.unwrap(None) == NoneValue()


def test_unwrap_list_dict_recurse():
    assert DynamicProxy.unwrap([{"null": None, "nulls": [None]}]) == [{"null": NoneValue(), "nulls": [NoneValue()]}]


def test_unwrap_dict_key_validation():
    with pytest.raises(RuntimeException):
        DynamicProxy.unwrap({1: 2})


def test_dynamic_proxy_attribute_error(snippetcompiler):
    proxy: object = proxy_object(
        snippetcompiler,
        """
entity A:
end
implement A using std::none

x = A()
        """,
        "x",
    )

    assert isinstance(proxy, DynamicProxy)
    with pytest.raises(AttributeError):
        proxy.x
    with pytest.raises(NotFoundException):
        proxy.x


def test_dynamic_proxy_optional_value_error(snippetcompiler):
    """
    Verify that accessing an unset optional value through a dynamic proxy results in an OptionalValueException.
    """
    proxy: object = proxy_object(
        snippetcompiler,
        """
entity A:
end
A.other [0:1] -- A
implement A using std::none

x = A(other=null)
        """,
        "x",
    )
    assert isinstance(proxy, DynamicProxy)
    with pytest.raises(OptionalValueException):
        proxy.other
