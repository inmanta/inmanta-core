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


def test_issue_93(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
    string attribute="1234"
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2

t = Test1()
t2a = Test2(test1=t)
t2b = Test2(test1=t)

std::print(t.test2.attribute)
        """)

    try:
        compiler.do_compile()
        raise AssertionError("Should get exception")
    except RuntimeException as e:
        assert e.location.lnr == 18
        
def test_issue_135_duplo_relations_2(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2
Test1 test1 [1] -- [0:] Test2 floem
""")
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_issue_135_duplo_relations_3(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 test1 [1] -- [0:] Test2 test2
Test1 test1 [1] -- [0:] Test1 test2
""")
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_issue_135_duplo_relations_4(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Stdhost:

end

entity Tussen extends Stdhost:
end

entity Oshost extends Tussen:

end

entity Agent:
end

Agent inmanta_agent   [1] -- [1] Oshost os_host
Stdhost deploy_host [1] -- [0:1] Agent inmanta_agent
""")
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_issue_135_duplo_relations_5(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Stdhost:

end

entity Tussen extends Stdhost:
end

entity Oshost extends Tussen:

end

entity Agent:
end

Oshost os_host [1] -- [1] Agent inmanta_agent

Stdhost deploy_host [1] -- [0:1] Agent inmanta_agent
""")
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_issue_132_relation_on_default(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
typedef CFG as std::File(mode=755)
CFG cfg [1] -- [1] std::File stuff
""")
    with pytest.raises(TypingException):
        compiler.do_compile()


def test_issue_141(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
h = std::Host(name="test", os=std::linux)

entity SpecialService extends std::Service:

end

std::Host host [1] -- [0:] SpecialService services_list""")
    with pytest.raises(DuplicateException):
        compiler.do_compile()


def test_m_to_n(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity LogFile:
  string name
  number members
end

implement LogFile using std::none

entity LogCollector:
  string name
end

implement LogCollector using std::none

LogCollector collectors [0:] -- [0:] LogFile logfiles

lf1 = LogFile(name="lf1", collectors = [c1, c2], members=3)
lf2 = LogFile(name="lf2", collectors = [c1, c2], members=2)
lf3 = LogFile(name="lf3", collectors = lf2.collectors, members=2)
lf6 = LogFile(name="lf6", collectors = c1, members=1)

lf4 = LogFile(name="lf4", members=2)
lf5 = LogFile(name="lf5", members=0)

lf7 = LogFile(name="lf7", members=2)
lf8 = LogFile(name="lf8", collectors = lf7.collectors, members=2)

c1 = LogCollector(name="c1")
c2 = LogCollector(name="c2", logfiles=[lf4, lf7])
c3 = LogCollector(name="c3", logfiles=[lf4, lf7, lf1])

std::print([c1,c2,lf1,lf2,lf3,lf4,lf5,lf6,lf7,lf8])
        """)

    (types, _) = compiler.do_compile()
    for lf in types["__config__::LogFile"].get_all_instances():
        assert lf.get_attribute("members").get_value() == len(lf.get_attribute("collectors").get_value())

def test_new_relation_syntax(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1.tests [0:] -- Test2.test1 [1]

a = Test1(tests=[Test2(),Test2()])
b = Test1()
Test2(test1 = b)
""")
    types, root = compiler.do_compile()

    scope = root.get_child("__config__").scope

    assert len(scope.lookup("a").get_value().get_attribute("tests").get_value()) == 2
    assert len(scope.lookup("b").get_value().get_attribute("tests").get_value()) == 1


def test_new_relation_with_annotation_syntax(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

annotation = 5

Test1.tests [0:] annotation Test2.test1 [1]

a = Test1(tests=[Test2(),Test2()])
b = Test1()
Test2(test1 = b)
""")
    types, root = compiler.do_compile()

    scope = root.get_child("__config__").scope

    assert len(scope.lookup("a").get_value().get_attribute("tests").get_value()) == 2
    assert len(scope.lookup("b").get_value().get_attribute("tests").get_value()) == 1


def test_new_relation_uni_dir(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1.tests [0:] -- Test2

a = Test1(tests=[Test2(),Test2()])

""")
    types, root = compiler.do_compile()

    scope = root.get_child("__config__").scope

    assert len(scope.lookup("a").get_value().get_attribute("tests").get_value()) == 2


def test_new_relation_uni_dir_double_define(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1.tests [0:] -- Test2

Test2.xx [1] -- Test1.tests [0:]
""")
    with pytest.raises(DuplicateException):
        compiler.do_compile()


