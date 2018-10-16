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


def test_issue_121_non_matching_index(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
        a=std::Host[name="test"]
        """)

    try:
        compiler.do_compile()
        raise AssertionError("Should get exception")
    except NotFoundException as e:
        assert e.location.lnr == 2


def test_issue_122_index_inheritance(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Repository extends std::File:
    string name
    bool gpgcheck=false
    bool enabled=true
    string baseurl
    string gpgkey=""
    number metadata_expire=7200
    bool send_event=true
end

implementation redhatRepo for Repository:
    self.mode = 644
    self.owner = "root"
    self.group = "root"

    self.path = "/etc/yum.repos.d/{{ name }}.repo"
    self.content = "{{name}}"
end

implement Repository using redhatRepo

h1 = std::Host(name="test", os=std::linux)

Repository(host=h1, name="flens-demo",
                           baseurl="http://people.cs.kuleuven.be/~wouter.deborger/repo/")

Repository(host=h1, name="flens-demo",
                           baseurl="http://people.cs.kuleuven.be/~wouter.deborger/repo/")
        """)

    try:
        compiler.do_compile()
        raise AssertionError("Should get exception")
    except TypingException as e:
        assert e.location.lnr == 25

def test_issue_140_index_error(snippetcompiler):
    try:
        snippetcompiler.setup_for_snippet("""
        h = std::Host(name="test", os=std::linux)
        test = std::Service[host=h, path="test"]""")
        compiler.do_compile()
        raise AssertionError("Should get exception")
    except NotFoundException as e:
        assert re.match('.*No index defined on std::Service for this lookup:.*', str(e))


def test_issue_745_index_on_nullable(snippetcompiler):
    with pytest.raises(IndexException):
        snippetcompiler.setup_for_snippet("""
entity A:
    string name
    string? opt
end

index A(name,opt)
""")
        compiler.do_compile()


def test_issue_745_index_on_optional(snippetcompiler):
    with pytest.raises(IndexException):
        snippetcompiler.setup_for_snippet("""
entity A:
    string name
end

A.opt [0:1] -- A

index A(name,opt)
""")
        compiler.do_compile()


def test_issue_745_index_on_multi(snippetcompiler):
    with pytest.raises(IndexException):
        snippetcompiler.setup_for_snippet("""
entity A:
    string name
end

A.opt [1:] -- A

index A(name,opt)
""")
        compiler.do_compile()


def test_issue_index_on_not_existing(snippetcompiler):
    with pytest.raises(TypeNotFoundException):
        snippetcompiler.setup_for_snippet("""
index A(name)
""")
        compiler.do_compile()


def test_issue_212_bad_index_defintion(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:
    string x
end
index Test1(x,y)
""")
    with pytest.raises(RuntimeException):
        compiler.do_compile()