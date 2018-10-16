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

from io import StringIO
from itertools import groupby
import os
import re
import shutil
import sys
import tempfile
import unittest

import pytest

from inmanta import config
from inmanta.ast import AttributeException, IndexException
from inmanta.ast import MultiException
from inmanta.ast import NotFoundException, TypingException
from inmanta.ast import RuntimeException, DuplicateException, TypeNotFoundException, ModuleNotFoundException, \
    OptionalValueException
import inmanta.compiler as compiler
from inmanta.execute.proxy import UnsetException
from inmanta.execute.util import Unknown, NoneValue
from inmanta.export import DependencyCycleException
from inmanta.module import Project
from inmanta.parser import ParserException
from utils import assert_graph

def test_list_atributes(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Jos:
  bool[] bar
  std::package_state[] ips = ["installed"]
  string[] floom = []
  string[] floomx = ["a", "b"]
  string box = "a"
end

implement Jos using std::none

a = Jos(bar = [true])
b = Jos(bar = [true, false])
c = Jos(bar = [])
d = Jos(bar = [], floom=["test","test2"])

""")
    (_, root) = compiler.do_compile()

    def check_jos(jos, bar, ips=["installed"], floom=[], floomx=["a", "b"], box="a"):
        jos = jos.get_value()
        assert jos.get_attribute("bar").get_value() == bar
        assert jos.get_attribute("ips").get_value(), ips
        assert jos.get_attribute("floom").get_value() == floom
        assert jos.get_attribute("floomx").get_value() == floomx
        assert jos.get_attribute("box").get_value() == box

    scope = root.get_child("__config__").scope

    check_jos(scope.lookup("a"), [True])
    check_jos(scope.lookup("b"), [True, False])
    check_jos(scope.lookup("c"), [])
    check_jos(scope.lookup("d"), [], floom=["test", "test2"])


def test_list_atribute_type_violation_1(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Jos:
  bool[] bar = true
end
implement Jos using std::none
c = Jos()
""")
    with pytest.raises(ParserException):
        compiler.do_compile()


def test_list_atribute_type_violation_2(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Jos:
  bool[] bar = ["x"]
end
implement Jos using std::none
c = Jos()
""")
    with pytest.raises(RuntimeException):
        compiler.do_compile()


def test_list_atribute_type_violation_3(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Jos:
  bool[] bar
end
implement Jos using std::none
c = Jos(bar = ["X"])
""")
    with pytest.raises(RuntimeException):
        compiler.do_compile()


def test_issue_235_empty_lists(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 tests [0:] -- [0:] Test2 tests

t1 = Test1(tests=[])
std::print(t1.tests)
""")
    (_, root) = compiler.do_compile()
    scope = root.get_child("__config__").scope

    assert scope.lookup("t1").get_value().get_attribute("tests").get_value() == []
