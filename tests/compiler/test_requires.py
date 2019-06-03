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
from utils import assert_graph


def test_abstract_requires(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
host = std::Host(name="host", os=std::unix)

entity A:
    string name
end

implementation a for A:
    one = std::ConfigFile(path="{{self.name}}1", host=host, content="")
    two = std::ConfigFile(path="{{self.name}}2", host=host, content="")
    two.requires = one
end

implement A using a

pre = std::ConfigFile(path="host0", host=host, content="")
post = std::ConfigFile(path="hosts4", host=host, content="")

inter = A(name = "inter")
"""
    )

    v, resources = snippetcompiler.do_export()
    assert_graph(resources, """inter2: inter1""")


def test_abstract_requires_3(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
host = std::Host(name="host", os=std::unix)

entity A:
    string name
end

implementation a for A:
    one = std::ConfigFile(path="{{self.name}}1", host=host, content="")
    two = std::ConfigFile(path="{{self.name}}2", host=host, content="")
    two.requires = one
    one.requires = self.requires
    two.provides = self.provides
end

implement A using a

pre = std::ConfigFile(path="pre", host=host, content="")
post = std::ConfigFile(path="post", host=host, content="")

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
host = std::Host(name="host", os=std::unix)

entity A:
string name
end

implementation a for A:
one = std::ConfigFile(path="{{self.name}}1", host=host, content="")
two = std::ConfigFile(path="{{self.name}}2", host=host, content="")
two.requires = one
end

implement A using a

pre = std::ConfigFile(path="host0", host=host, content="")
post = std::ConfigFile(path="hosts4", host=host, content="")

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
import std

host = std::Host(name="Test", os=std::unix)
f1 = std::ConfigFile(host=host, path="/f1", content="")
f2 = std::ConfigFile(host=host, path="/f2", content="")
f3 = std::ConfigFile(host=host, path="/f3", content="")
f4 = std::ConfigFile(host=host, path="/f4", content="")
f1.requires = f2
f2.requires = f3
f3.requires = f1
f4.requires = f1
"""
    )
    with pytest.raises(DependencyCycleException) as e:
        snippetcompiler.do_export()

    cyclenames = [r.id.resource_str() for r in e.value.cycle]
    assert set(cyclenames) == set(["std::File[Test,path=/f3]", "std::File[Test,path=/f2]", "std::File[Test,path=/f1]"])
