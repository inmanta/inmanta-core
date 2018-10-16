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

def test_issue_139_scheduler(snippetcompiler):
    snippetcompiler.setup_for_snippet("""import std

entity Host extends std::Host:
    string attr
end
implement Host using std::none

host = Host(name="vm1", os=std::linux)

f = std::ConfigFile(host=host, path="", content="{{ host.attr }}")
std::Service(host=host, name="svc", state="running", onboot=true, requires=[f])
ref = std::Service[host=host, name="svc"]

""")
    with pytest.raises(MultiException):
        compiler.do_compile()


def test_issue_201_double_set(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2

a=Test1()
b=Test2()

b.test1 = a
b.test1 = a

std::print(b.test1)
""")

    (types, _) = compiler.do_compile()
    a = types["__config__::Test1"].get_all_instances()[0]
    assert len(a.get_attribute("test2").value)


def test_issue_170_attribute_exception(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:
    string a
end

Test1(a=3)
""")
    with pytest.raises(AttributeException):
        compiler.do_compile()


def test_execute_twice(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
import mod4::other
import mod4
    """)

    (_, scopes) = compiler.do_compile()
    assert scopes.get_child("mod4").lookup("main").get_value() == 0
    assert scopes.get_child("mod4").get_child("other").lookup("other").get_value() == 0

