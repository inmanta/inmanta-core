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


def test_issue_92(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
    entity Host extends std::NotThere:
    end
""")
    try:
        compiler.do_compile()
        raise AssertionError("Should get exception")
    except TypeNotFoundException as e:
        assert e.location.lnr == 2


def test_issue_73(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
vm1 = std::floob()
""")
    with pytest.raises(TypeNotFoundException):
        compiler.do_compile()


def test_issue_110_resolution(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:

end
implement Test1 using test1i


implementation test1i for Test1:
    test = host
end

t = Test1()
""")
    with pytest.raises(NotFoundException):
        compiler.do_compile()


def test_issue_134_colliding_umplementations(snippetcompiler):

    snippetcompiler.setup_for_snippet("""
implementation test for std::Entity:
end
implementation test for std::Entity:
end""")
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_issue_164_fqn_in_when(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
implementation linux for std::HostConfig:
end

implement std::HostConfig using linux when host.os == std::linux

std::Host(name="vm1", os=std::linux)
""")
    compiler.do_compile()