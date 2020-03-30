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
from compiler.dataflow.conftest import DataflowTestHelper
from itertools import chain
from typing import Callable, List

import pytest

from inmanta.ast import Namespace
from inmanta.ast.entity import Entity
from inmanta.execute.dataflow import AssignableNode, AttributeNode, DataflowGraph, InstanceNode, Node, ValueNode
from inmanta.execute.dataflow.graphic import GraphicGraph


def fdp_stringify(obj: object) -> str:
    return re.sub(r"\W+", "", str(obj))


class LocationBasedGraphicGraph(GraphicGraph):
    def node_key(self, node: Node) -> str:
        if isinstance(node, InstanceNode):
            assert node.responsible is not None
            return "cluster_instance_%s_%s" % (fdp_stringify(node), fdp_stringify(node.responsible.location))
        elif isinstance(node, ValueNode):
            return "value_%s" % fdp_stringify(node.value)
        elif isinstance(node, AttributeNode):
            assert node.instance.responsible is not None
            return "attribute_%s_on_%s_%s" % (
                fdp_stringify(node.name),
                fdp_stringify(node.instance),
                fdp_stringify(node.instance.responsible.location),
            )
        elif isinstance(node, AssignableNode):
            assert node.result_variable is not None
            assert node.result_variable.location is not None
            return "assignable_%s_%s" % (fdp_stringify(node.name), fdp_stringify(node.result_variable.location))
        assert False


@pytest.fixture(scope="function")
def graphic_asserter(dataflow_test_helper: DataflowTestHelper) -> Callable[[str, str], None]:
    def asserter(model: str, expected: str) -> None:
        dataflow_test_helper.compile(model)
        graph: DataflowGraph = dataflow_test_helper.get_graph()
        namespace: Namespace = dataflow_test_helper.get_namespace()
        entities: List[Entity] = [
            tp for tp in dataflow_test_helper.get_types().values() if isinstance(tp, Entity) if tp.namespace is namespace
        ]
        graphic: GraphicGraph = LocationBasedGraphicGraph()
        for instance in chain.from_iterable(entity.get_all_instances() for entity in entities):
            assert instance.instance_node is not None
            graphic.add_node(instance.instance_node.top_node())
        for named_node in graph.named_nodes.values():
            graphic.add_node(named_node)
        assert graphic.digraph.source.strip() == expected.strip().format(
            dir=fdp_stringify(dataflow_test_helper.snippetcompiler.project_dir)
        )

    return asserter


def test_dataflow_graphic_simple_assignment(graphic_asserter: Callable[[str, str], None]) -> None:
    graphic_asserter(
        """
x = 0
        """,
        """
digraph {{
	assignable_x_{dir}maincf2 [label=x shape=ellipse]
	value_0 [label=0 shape=diamond]
	assignable_x_{dir}maincf2 -> value_0
}}
        """,  # noqa: E101, W191
    )
