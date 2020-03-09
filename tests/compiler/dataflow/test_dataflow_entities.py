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

from compiler.dataflow.conftest import create_instance
from typing import Optional

import pytest

from inmanta.ast import Namespace
from inmanta.ast.entity import Entity
from inmanta.ast.statements import Statement
from inmanta.execute.dataflow import (
    AssignableNodeReference,
    AttributeNode,
    DataflowGraph,
    InstanceNode,
    NodeReference,
    VariableNodeReference,
)


@pytest.mark.parametrize("register_both_dirs", [True, False])
def test_dataflow_bidirectional_attribute(graph: DataflowGraph, register_both_dirs: bool) -> None:
    namespace: Namespace = Namespace("dummy_namespace")
    left_entity: Entity = Entity("Left", namespace)
    right_entity: Entity = Entity("Right", namespace)

    left = create_instance(graph, left_entity)
    right = create_instance(graph, right_entity)
    right_indirect = create_instance(graph, right_entity)
    x: AssignableNodeReference = graph.get_named_node("x")
    x.assign(right_indirect.reference(), Statement(), graph)
    assert isinstance(x, VariableNodeReference)
    assert len(x.node.instance_assignments) == 1

    def assign_attribute(left: InstanceNode, right: NodeReference) -> None:
        left.assign_attribute("right", right, Statement(), graph)

    graph.register_bidirectional_attribute(left_entity, "right", "left")
    if register_both_dirs:
        graph.register_bidirectional_attribute(right_entity, "left", "right")
    assign_attribute(left, right.reference())
    assign_attribute(left, x)

    left_right: Optional[AttributeNode] = left.get_attribute("right")
    right_left: Optional[AttributeNode] = right.get_attribute("left")
    x_left: Optional[AttributeNode] = x.node.instance_assignments[0].rhs.node().get_attribute("left")
    assert left_right is not None
    assert right_left is not None
    assert x_left is not None
    assert len(left_right.instance_assignments) == 1
    assert len(left_right.assignable_assignments) == 1
    assert len(right_left.instance_assignments) == 1
    assert len(x_left.instance_assignments) == 1
    assert left_right.instance_assignments[0].rhs.node() == right
    assert left_right.assignable_assignments[0].rhs == x
    assert right_left.instance_assignments[0].rhs.node() == left
    assert x_left.instance_assignments[0].rhs.node() == left


def test_dataflow_index(graph: DataflowGraph) -> None:
    entity: Entity = Entity("DummyEntity", Namespace("dummy_namespace"))
    i1: InstanceNode = create_instance(graph, entity)
    i2: InstanceNode = create_instance(graph, entity)

    assert i1.get_self() is i1
    assert i2.get_self() is i2
    assert i1 is not i2

    graph.add_index_match([i.reference() for i in [i1, i2]])
    # make sure adding them again in another order does not cause issues
    graph.add_index_match([i.reference() for i in [i2, i1]])

    assert i1.get_self() is i1
    assert i2.get_self() is i1
    assert i2.reference().node() is i1
    assert i2.reference().top_node() is i2
    assert i1.get_all_index_nodes() == {i1, i2}
