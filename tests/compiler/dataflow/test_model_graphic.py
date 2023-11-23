"""
    Copyright 2020 Inmanta

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

import re
import shutil
from functools import total_ordering
from itertools import chain
from typing import Callable, List, Optional, Tuple

import pytest

from compiler.dataflow.conftest import DataflowTestHelper
from inmanta.ast import Locatable, Namespace
from inmanta.ast.entity import Entity
from inmanta.execute.dataflow import AssignableNode, AttributeNode, InstanceNode, Node, ValueNode
from inmanta.execute.runtime import Instance

try:
    from inmanta.execute.dataflow.graphic import GraphicGraph
except Exception:
    pytest.skip(
        "skipping graphic tests because graphviz package not installed. Run `pip install graphviz` to resolve this.",
        allow_module_level=True,
    )

if shutil.which("fdp") is None:
    pytest.skip(
        "skipping graphic tests because graphviz fdp executable was not found in your $PATH."
        " Install your distribution's graphviz package to resolve this.",
        allow_module_level=True,
    )


def dot_stringify(obj: object) -> str:
    return re.sub(r"\W+", "", str(obj))


class LocationBasedGraphicGraph(GraphicGraph):
    def node_key(self, node: Node) -> str:
        if isinstance(node, InstanceNode):
            assert node.responsible is not None
            return "cluster_instance_%s_%s" % (dot_stringify(node), dot_stringify(node.responsible.location))
        elif isinstance(node, ValueNode):
            return "value_%s" % dot_stringify(node.value)
        elif isinstance(node, AttributeNode):
            assert node.instance.responsible is not None
            return "attribute_%s_on_%s_%s" % (
                dot_stringify(node.name),
                dot_stringify(node.instance),
                dot_stringify(node.instance.responsible.location),
            )
        elif isinstance(node, AssignableNode):
            assert node.result_variable is not None
            locatable: Locatable
            if node.result_variable.location is not None:
                locatable = node.result_variable
            else:
                # __self__ node
                value: object = node.result_variable.get_value()
                assert isinstance(value, Instance)
                locatable = value
            assert locatable.location is not None
            return "assignable_%s_%s" % (dot_stringify(node.name), dot_stringify(locatable.location))
        assert False


GraphicAsserter = Callable[[str, str], None]


@total_ordering
class DotSource:
    """
    Represents DOT source semi-structurally. Sorts the lines before comparing to deal with nondeterministism
    during construction.
    """

    def __init__(self, lines: List[str], subgraphs: List[Tuple[str, "DotSource"]]) -> None:
        self.lines: List[str] = sorted(lines)
        self.subgraphs: List[Tuple[str, DotSource]] = sorted(subgraphs)

    @classmethod
    def parse(cls, source: str) -> "DotSource":
        (lines, subgraphs, rest) = cls._get_lines_and_subgraphs(source.split("\n"))
        assert len(rest) == 0
        return DotSource(lines, subgraphs)

    @classmethod
    def _get_lines_and_subgraphs(cls, lines: List[str]) -> Tuple[List[str], List[Tuple[str, "DotSource"]], List[str]]:
        if len(lines) == 0:
            return ([], [], [])
        (head, tail) = (lines[0], lines[1:])
        if head.endswith("{"):
            (sublines, subsubs, rest) = cls._get_lines_and_subgraphs(tail)
            (rlines, rsubs, rrest) = cls._get_lines_and_subgraphs(rest)
            return (rlines, [(head, DotSource(sublines, subsubs)), *rsubs], rrest)
        if head.endswith("}"):
            return ([head], [], tail)
        (tail_lines, tail_subs, tail_rest) = cls._get_lines_and_subgraphs(tail)
        return ([head, *tail_lines], tail_subs, tail_rest)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DotSource):
            return NotImplemented
        return self.lines == other.lines and self.subgraphs == other.subgraphs

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, DotSource):
            return NotImplemented
        return (self.lines, self.subgraphs) < (other.lines, other.subgraphs)


@pytest.fixture(scope="function")
def graphic_asserter(dataflow_test_helper: DataflowTestHelper) -> Callable[[str, str], None]:
    def asserter(model: str, expected: str, view: Optional[bool] = False) -> None:
        dataflow_test_helper.compile(model)
        namespace: Namespace = dataflow_test_helper.get_namespace()
        entities: List[Entity] = [
            tp for tp in dataflow_test_helper.get_types().values() if isinstance(tp, Entity) if tp.namespace is namespace
        ]
        graphic: GraphicGraph = LocationBasedGraphicGraph()
        for instance in chain.from_iterable(entity.get_all_instances() for entity in entities):
            assert instance.instance_node is not None
            graphic.add_node(instance.instance_node.top_node())
        for result_variable in namespace.get_scope().slots.values():
            for node in result_variable.get_dataflow_node().nodes():
                graphic.add_node(node)
        if view:
            graphic.view()
        print(graphic.digraph.source.strip())
        assert DotSource.parse(graphic.digraph.source.strip()) == DotSource.parse(
            expected.strip().format(dir=dot_stringify(dataflow_test_helper.snippetcompiler.project_dir))
        )

    return asserter


def test_dataflow_graphic_simple_assignment(graphic_asserter: GraphicAsserter) -> None:
    graphic_asserter(
        """
x = 0
        """,
        """
digraph {{
\tassignable_x_{dir}maincf2 [label=x shape=ellipse]
\tvalue_0 [label=0 shape=diamond]
\tassignable_x_{dir}maincf2 -> value_0
}}
        """,
    )


def test_dataflow_graphic_assignment_loop(graphic_asserter: GraphicAsserter) -> None:
    graphic_asserter(
        """
x = y
y = z
z = x

y = 42
        """,
        """
digraph {{
\tassignable_x_{dir}maincf25 [label=x shape=ellipse]
\tassignable_y_{dir}maincf6 [label=y shape=ellipse]
\tassignable_z_{dir}maincf45 [label=z shape=ellipse]
\tassignable_z_{dir}maincf45 -> assignable_x_{dir}maincf25
\tassignable_y_{dir}maincf6 -> assignable_z_{dir}maincf45
\tvalue_42 [label=42 shape=diamond]
\tassignable_y_{dir}maincf6 -> value_42
\tassignable_x_{dir}maincf25 -> assignable_y_{dir}maincf6
}}

        """,
    )


def test_dataflow_graphic_instance(graphic_asserter: GraphicAsserter) -> None:
    graphic_asserter(
        """
entity A:
    number l
    number m
    number n
end

implement A using std::none


x = A(n = 42)
x.m = 0

y = x
y.l = 1


u = A(l = y.l, m = x.m, n = 2)
        """,
        """
digraph {{
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf11 {{
\t\tlabel=A
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf11 {{
\t\tattribute_l_on___config__Ainstance_{dir}maincf11 [label=l shape=ellipse]
\t}}
\tvalue_1 [label=1 shape=diamond]
\tattribute_l_on___config__Ainstance_{dir}maincf11 -> value_1
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf11 {{
\t\tattribute_m_on___config__Ainstance_{dir}maincf11 [label=m shape=ellipse]
\t}}
\tvalue_0 [label=0 shape=diamond]
\tattribute_m_on___config__Ainstance_{dir}maincf11 -> value_0
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf11 {{
\t\tattribute_n_on___config__Ainstance_{dir}maincf11 [label=n shape=ellipse]
\t}}
\tvalue_42 [label=42 shape=diamond]
\tattribute_n_on___config__Ainstance_{dir}maincf11 -> value_42
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf11 {{
\t\tattribute_requires_on___config__Ainstance_{dir}maincf11 [label=requires shape=ellipse]
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf11 {{
\t\tattribute_provides_on___config__Ainstance_{dir}maincf11 [label=provides shape=ellipse]
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf18 {{
\t\tlabel=A
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf18 {{
\t\tattribute_l_on___config__Ainstance_{dir}maincf18 [label=l shape=ellipse]
\t}}
\tassignable_y_{dir}maincf145 [label=y shape=ellipse]
\tassignable_x_{dir}maincf11 [label=x shape=ellipse]
\tassignable_x_{dir}maincf11 -> cluster_instance___config__Ainstance_{dir}maincf11
\tassignable_y_{dir}maincf145 -> assignable_x_{dir}maincf11
\tattribute_l_on___config__Ainstance_{dir}maincf18 -> assignable_y_{dir}maincf145 [label=".l"]
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf18 {{
\t\tattribute_m_on___config__Ainstance_{dir}maincf18 [label=m shape=ellipse]
\t}}
\tattribute_m_on___config__Ainstance_{dir}maincf18 -> assignable_x_{dir}maincf11 [label=".m"]
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf18 {{
\t\tattribute_n_on___config__Ainstance_{dir}maincf18 [label=n shape=ellipse]
\t}}
\tvalue_2 [label=2 shape=diamond]
\tattribute_n_on___config__Ainstance_{dir}maincf18 -> value_2
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf18 {{
\t\tattribute_requires_on___config__Ainstance_{dir}maincf18 [label=requires shape=ellipse]
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf18 {{
\t\tattribute_provides_on___config__Ainstance_{dir}maincf18 [label=provides shape=ellipse]
\t}}
\tassignable_u_{dir}maincf18 [label=u shape=ellipse]
\tassignable_u_{dir}maincf18 -> cluster_instance___config__Ainstance_{dir}maincf18
}}
        """,
    )


def test_dataflow_graphic_relation(graphic_asserter: GraphicAsserter) -> None:
    graphic_asserter(
        """
entity A:
end

entity B:
end

implement A using std::none
implement B using std::none

A.b [0:] -- B.a [0:]

a = A()
b = B()

a.b = b
        """,
        """
digraph {{
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf13 {{
\t\tlabel=A
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf13 {{
\t\tattribute_b_on___config__Ainstance_{dir}maincf13 [label=b shape=ellipse]
\t}}
\tassignable_b_{dir}maincf14 [label=b shape=ellipse]
\tsubgraph cluster_instance___config__Binstance_{dir}maincf14 {{
\t\tlabel=B
\t}}
\tsubgraph cluster_instance___config__Binstance_{dir}maincf14 {{
\t\tattribute_a_on___config__Binstance_{dir}maincf14 [label=a shape=ellipse]
\t}}
\tattribute_a_on___config__Binstance_{dir}maincf14 -> cluster_instance___config__Ainstance_{dir}maincf13
\tsubgraph cluster_instance___config__Binstance_{dir}maincf14 {{
\t\tattribute_requires_on___config__Binstance_{dir}maincf14 [label=requires shape=ellipse]
\t}}
\tsubgraph cluster_instance___config__Binstance_{dir}maincf14 {{
\t\tattribute_provides_on___config__Binstance_{dir}maincf14 [label=provides shape=ellipse]
\t}}
\tassignable_b_{dir}maincf14 -> cluster_instance___config__Binstance_{dir}maincf14
\tattribute_b_on___config__Ainstance_{dir}maincf13 -> assignable_b_{dir}maincf14
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf13 {{
\t\tattribute_requires_on___config__Ainstance_{dir}maincf13 [label=requires shape=ellipse]
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf13 {{
\t\tattribute_provides_on___config__Ainstance_{dir}maincf13 [label=provides shape=ellipse]
\t}}
\tassignable_a_{dir}maincf13 [label=a shape=ellipse]
\tassignable_a_{dir}maincf13 -> cluster_instance___config__Ainstance_{dir}maincf13
}}
        """,
    )


def test_dataflow_graphic_implementation(graphic_asserter: GraphicAsserter) -> None:
    graphic_asserter(
        """
entity A:
    number m
    number n
end

implement A using i

implementation i for A:
    self.m = self.n
end


A(n = 42)
A(n = 42)
        """,
        """
digraph {{
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf15 {{
\t\tlabel=A
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf15 {{
\t\tattribute_m_on___config__Ainstance_{dir}maincf15 [label=m shape=ellipse]
\t}}
\tassignable___self___{dir}maincf15 [label=__self__ shape=ellipse]
\tassignable___self___{dir}maincf15 -> cluster_instance___config__Ainstance_{dir}maincf15
\tattribute_m_on___config__Ainstance_{dir}maincf15 -> assignable___self___{dir}maincf15 [label=".n"]
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf15 {{
\t\tattribute_n_on___config__Ainstance_{dir}maincf15 [label=n shape=ellipse]
\t}}
\tvalue_42 [label=42 shape=diamond]
\tattribute_n_on___config__Ainstance_{dir}maincf15 -> value_42
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf15 {{
\t\tattribute_requires_on___config__Ainstance_{dir}maincf15 [label=requires shape=ellipse]
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf15 {{
\t\tattribute_provides_on___config__Ainstance_{dir}maincf15 [label=provides shape=ellipse]
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf14 {{
\t\tlabel=A
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf14 {{
\t\tattribute_m_on___config__Ainstance_{dir}maincf14 [label=m shape=ellipse]
\t}}
\tassignable___self___{dir}maincf14 [label=__self__ shape=ellipse]
\tassignable___self___{dir}maincf14 -> cluster_instance___config__Ainstance_{dir}maincf14
\tattribute_m_on___config__Ainstance_{dir}maincf14 -> assignable___self___{dir}maincf14 [label=".n"]
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf14 {{
\t\tattribute_n_on___config__Ainstance_{dir}maincf14 [label=n shape=ellipse]
\t}}
\tattribute_n_on___config__Ainstance_{dir}maincf14 -> value_42
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf14 {{
\t\tattribute_requires_on___config__Ainstance_{dir}maincf14 [label=requires shape=ellipse]
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf14 {{
\t\tattribute_provides_on___config__Ainstance_{dir}maincf14 [label=provides shape=ellipse]
\t}}
}}
        """,
    )


def test_dataflow_graphic_index(graphic_asserter: GraphicAsserter) -> None:
    graphic_asserter(
        """
entity A:
    number m
    number n
end

index A(n)

implement A using std::none


x = A(n = 42)
y = A(n = 42)

x.m = 0
        """,
        """
digraph {{
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf12 {{
\t\tlabel=A
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf13 {{
\t\tlabel=A
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf13 {{
\t\tattribute_m_on___config__Ainstance_{dir}maincf13 [label=m shape=ellipse]
\t}}
\tvalue_0 [label=0 shape=diamond]
\tattribute_m_on___config__Ainstance_{dir}maincf13 -> value_0
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf13 {{
\t\tattribute_n_on___config__Ainstance_{dir}maincf13 [label=n shape=ellipse]
\t}}
\tvalue_42 [label=42 shape=diamond]
\tattribute_n_on___config__Ainstance_{dir}maincf13 -> value_42
\tattribute_n_on___config__Ainstance_{dir}maincf13 -> value_42
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf13 {{
\t\tattribute_requires_on___config__Ainstance_{dir}maincf13 [label=requires shape=ellipse]
\t}}
\tsubgraph cluster_instance___config__Ainstance_{dir}maincf13 {{
\t\tattribute_provides_on___config__Ainstance_{dir}maincf13 [label=provides shape=ellipse]
\t}}
\tcluster_instance___config__Ainstance_{dir}maincf12 -> cluster_instance___config__Ainstance_{dir}maincf13 [label=index]
\tassignable_x_{dir}maincf12 [label=x shape=ellipse]
\tassignable_x_{dir}maincf12 -> cluster_instance___config__Ainstance_{dir}maincf12
\tassignable_y_{dir}maincf13 [label=y shape=ellipse]
\tassignable_y_{dir}maincf13 -> cluster_instance___config__Ainstance_{dir}maincf13
}}
        """,
    )
