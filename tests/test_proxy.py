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

import unittest

import pytest
from test_compilation import SnippetCompilationTest
import inmanta.compiler as compiler
from inmanta.execute.proxy import DynamicProxy


class TestDynamicProxy(SnippetCompilationTest, unittest.TestCase):

    def proxy_object(self, snippet, var):
        self.setup_for_snippet(snippet)
        (_, root) = compiler.do_compile()

        scope = root.get_child("__config__").scope

        value = scope.lookup(var).get_value()
        return DynamicProxy.return_value(value)

    def test_basic_object(self):
        px = self.proxy_object("""
entity Test1:
    string x
end
implement Test1 using std::none

a = Test1(x="a")
""", "a")

        assert px.x == "a"
        with pytest.raises(Exception):
            px.x = "b"

    def test_dict_attr(self):
        px = self.proxy_object("""
entity Test1:
    dict x = {}
end
implement Test1 using std::none

a = Test1(x={"a":"A"})
""", "a")

        dic = px.x
        assert dic["a"] == "A"
        with pytest.raises(Exception):
            dic["a"] = "Z"

        with pytest.raises(Exception):
            dic["b"]

        with pytest.raises(Exception):
            dic["b"] = "a"
