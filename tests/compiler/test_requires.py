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

from inmanta.export import DependencyCycleException


def assert_graph(graph, expected):
    lines = [f"{f.id.get_attribute_value()}: {t.id.get_attribute_value()}" for f in graph.values() for t in f.resource_requires]
    lines = sorted(lines)

    elines = [x.strip() for x in expected.split("\n")]
    elines = sorted(elines)

    assert elines == lines, (lines, elines)


def test_abstract_requires(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import std::testing

host = std::Host(name="host", os=std::unix)

entity A:
    string name
end

implementation a for A:
    one = std::testing::NullResource(name="{{self.name}}1")
    two = std::testing::NullResource(name="{{self.name}}2")

    two.requires = one
end

implement A using a

pre = std::testing::NullResource(name="host0")
post = std::testing::NullResource(name="hosts4")

inter = A(name = "inter")
"""
    )

    v, resources = snippetcompiler.do_export()
    assert_graph(resources, """inter2: inter1""")


def test_abstract_requires_3(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import std::testing

entity A:
    string name
end

implementation a for A:
    one = std::testing::NullResource(name="{{self.name}}1")
    two = std::testing::NullResource(name="{{self.name}}2")
    two.requires = one
    one.requires = self.requires
    two.provides = self.provides
end

implement A using a

pre = std::testing::NullResource(name="pre")
post = std::testing::NullResource(name="post")

inter = A(name = "inter")
inter.requires = pre
post.requires = inter
"""
    )

    v, resources = snippetcompiler.do_export()
    assert_graph(
        resources,
        """post: inter2
        inter2: inter1
        inter1: pre""",
    )


def test_abstract_requires_2(snippetcompiler, caplog):
    snippetcompiler.setup_for_snippet(
        """
import std::testing

entity A:
    string name
end

implementation a for A:
    one = std::testing::NullResource(name="{{self.name}}1")
    two = std::testing::NullResource(name="{{self.name}}2")
    two.requires = one
end

implement A using a

pre = std::testing::NullResource(name="host0")
post = std::testing::NullResource(name="host4")

inter = A(name = "inter")
inter.requires = pre
post.requires = inter
"""
    )

    snippetcompiler.do_export()
    warning = [
        x
        for x in caplog.records
        if x.msg == "The resource %s had requirements before flattening, but not after flattening."
        " Initial set was %s. Perhaps provides relation is not wired through correctly?"
    ]
    assert len(warning) == 1


def test_issue_220_dep_loops(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import std::testing

f1 = std::testing::NullResource(name="f1")
f2 = std::testing::NullResource(name="f2")
f3 = std::testing::NullResource(name="f3")
f4 = std::testing::NullResource(name="f4")
f1.requires = f2
f2.requires = f3
f3.requires = f1
f4.requires = f1
"""
    )
    with pytest.raises(DependencyCycleException) as e:
        snippetcompiler.do_export()

    cyclenames = [r.id.resource_str() for r in e.value.cycle]
    assert set(cyclenames) == {
        "std::testing::NullResource[internal,name=f1]",
        "std::testing::NullResource[internal,name=f2]",
        "std::testing::NullResource[internal,name=f3]",
    }
