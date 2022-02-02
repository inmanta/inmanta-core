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

import os
import re
from itertools import groupby

import pytest

import inmanta.compiler as compiler
from inmanta.ast import AttributeException, RuntimeException


@pytest.fixture
def setup_project_for(snippetcompiler):
    def do_setup(name: str, main_file: str = "main.cf"):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", name)
        return snippetcompiler.setup_for_existing_project(path, main_file=main_file)

    return do_setup


def test_compile_test_1(setup_project_for):
    setup_project_for("compile_test_1")
    (types, _) = compiler.do_compile()
    instances = types["__config__::Host"].get_all_instances()
    assert len(instances) == 1
    i = instances[0]
    assert i.get_attribute("name").get_value() == "test1"
    assert i.get_attribute("os").get_value().get_attribute("name").get_value() == "linux"


def test_compile_test_2(setup_project_for):
    setup_project_for("compile_test_2")
    (types, _) = compiler.do_compile()
    instances = types["__config__::ManagedDevice"].get_all_instances()
    assert sorted([i.get_attribute("name").get_value() for i in instances]) == [1, 2, 3, 4, 5]


def test_compile_test_index_collission(setup_project_for):
    setup_project_for("compile_test_index_collission")
    with pytest.raises(RuntimeException):
        compiler.do_compile()


def test_compile_test_index(setup_project_for):
    setup_project_for("compile_test_index")
    (_, scopes) = compiler.do_compile()
    variables = {k: x.get_value() for k, x in scopes.get_child("__config__").scope.slots.items()}

    p = re.compile(r"(f\d+h\d+)(a\d+)?")

    items = [
        (m.groups()[0], m.groups()[1], v) for m, v in [(re.search(p, k), v) for k, v in variables.items()] if m is not None
    ]
    groups = groupby(sorted(items, key=lambda x: x[0]), lambda x: x[0])
    firsts = []
    for k, v in groups:
        v = list(v)
        first = v[0]
        firsts.append(first)
        for other in v[1:]:
            assert first[2] == other[2]

    for i in range(len(firsts)):
        for j in range(len(firsts)):
            if not i == j:
                assert firsts[i][2] != firsts[j][2], "Variable %s%s should not be equal to %s%s" % (
                    firsts[i][0],
                    firsts[i][1],
                    firsts[j][0],
                    firsts[j][1],
                )


def test_compile_test_double_assign(setup_project_for):
    setup_project_for("compile_test_double_assign")
    with pytest.raises(AttributeException):
        compiler.do_compile()


def test_compile_138(setup_project_for):
    setup_project_for("compile_138")
    (types, _) = compiler.do_compile()
    assert (
        types["std::Host"].get_all_instances()[0].get_attribute("agent").get_value().get_attribute("names").get_value()
        is not None
    )


def test_compile_plugin_typing(setup_project_for):
    setup_project_for("compile_plugin_typing")
    (_, scopes) = compiler.do_compile()
    root = scopes.get_child("__config__")

    def verify(name):
        c1a1 = root.lookup(name).get_value()
        name = sorted([item.get_attribute("name").get_value() for item in c1a1])
        assert name == ["t1", "t2", "t3"]

    verify("c1a1")
    verify("c1a2")

    s1 = root.lookup("s1").get_value()
    s2 = root.lookup("s2").get_value()

    assert s2[0] == s1
    assert isinstance(s2, list)
    assert isinstance(s2[0], str)


def test_compile_plugin_typing_invalid(setup_project_for):
    project = setup_project_for("compile_plugin_typing", "invalid.cf")
    with pytest.raises(RuntimeException) as e:
        compiler.do_compile()
    text = e.value.format_trace(indent="  ")
    print(text)
    assert (
        text
        == """Exception in plugin test::badtype (reported in test::badtype(c1.items) ({dir}/invalid.cf:16))
caused by:
  Invalid type for value 'a', should be type test::Item (reported in test::badtype(c1.items) ({dir}/invalid.cf:16))""".format(
            dir=project.project_path
        )
    )
