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

import pytest

from compiler.dataflow.conftest import create_instance, get_dataflow_node
from inmanta.ast import Namespace
from inmanta.ast.entity import Entity
from inmanta.ast.statements import Statement
from inmanta.execute.dataflow import AssignableNodeReference, DataflowGraph, InstanceNode, ValueNode


@pytest.mark.parametrize("reverse", [True, False])
def test_dataflow_index(graph: DataflowGraph, reverse: bool) -> None:
    entity: Entity = Entity("DummyEntity", Namespace("dummy_namespace"))
    i1: InstanceNode = create_instance(graph, entity)
    i2: InstanceNode = create_instance(graph, entity)

    assert i1.get_self() is i1
    assert i2.get_self() is i2
    assert i1 is not i2

    graph.add_index_match([i.reference() for i in [i1, i2]])
    if reverse:
        # make sure adding them again in another order does not cause issues
        graph.add_index_match([i.reference() for i in [i2, i1]])

    assert i1.get_self() is i1
    assert i2.get_self() is i1
    assert i2.reference().node() is i1
    assert i2.reference().top_node() is i2
    assert i1.get_all_index_nodes() == {i1, i2}


def test_dataflow_index_nodes(graph: DataflowGraph) -> None:
    entity: Entity = Entity("DummyEntity", Namespace("dummy_namespace"))
    i1: InstanceNode = create_instance(graph, entity)
    i2: InstanceNode = create_instance(graph, entity)

    i1.register_attribute("n").assign(ValueNode(0).reference(), Statement(), graph)
    i1.register_attribute("n").assign(ValueNode(0).reference(), Statement(), graph)

    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")

    x.assign(i1.reference(), Statement(), graph)
    y.assign(i2.reference(), Statement(), graph)

    graph.add_index_match([i.reference() for i in [i1, i2]])

    x_n: AssignableNodeReference = get_dataflow_node(graph, "x.n")
    y_n: AssignableNodeReference = get_dataflow_node(graph, "y.n")

    assert set(x_n.nodes()) == set(y_n.nodes())
