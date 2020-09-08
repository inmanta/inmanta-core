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

from typing import List, Set

import pytest

from compiler.dataflow.conftest import create_instance, get_dataflow_node
from inmanta.ast.statements import Statement
from inmanta.execute.dataflow import (
    AssignableNode,
    AssignableNodeReference,
    DataflowGraph,
    DirectNodeReference,
    Node,
    ValueNode,
    VariableNodeReference,
)


def test_dataflow_reference_nodes(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    x_nodes: List[AssignableNode] = list(x.nodes())
    assert len(x_nodes) == 1
    assert isinstance(x, DirectNodeReference)
    assert x_nodes[0] == x.node


def test_dataflow_attribute_reference_nodes(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")
    x.assign(y, Statement(), graph)
    y.assign(create_instance().reference(), Statement(), graph)

    assert isinstance(y, VariableNodeReference)
    assert len(y.node.instance_assignments) == 1

    y_n: AssignableNodeReference = get_dataflow_node(graph, "y.n")
    y_n.assign(ValueNode(42).reference(), Statement(), graph)

    x_n: AssignableNodeReference = get_dataflow_node(graph, "x.n")
    x_n_nodes: List[AssignableNode] = list(x_n.nodes())
    assert len(x_n_nodes) == 1
    assert x_n_nodes[0] == y.node.instance_assignments[0].rhs.node().get_attribute("n")


def test_dataflow_simple_leaf(graph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    leaves: List[AssignableNode] = list(x.leaf_nodes())
    assert isinstance(x, DirectNodeReference)
    assert leaves == [x.node]


def test_dataflow_variable_chain_leaf(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")
    z: AssignableNodeReference = get_dataflow_node(graph, "z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaf_nodes())
    assert isinstance(z, DirectNodeReference)
    assert leaves == {z.node}


@pytest.mark.parametrize("value_node", [ValueNode(42), create_instance()])
def test_dataflow_variable_tree_leaves(graph: DataflowGraph, value_node: Node) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")
    z: AssignableNodeReference = get_dataflow_node(graph, "z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    y.assign(value_node.reference(), Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaf_nodes())
    assert isinstance(y, DirectNodeReference)
    assert isinstance(z, DirectNodeReference)
    assert leaves == {y.node, z.node}


def test_dataflow_variable_loop_leaves(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")
    z: AssignableNodeReference = get_dataflow_node(graph, "z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    z.assign(x, Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaf_nodes())
    assert isinstance(x, DirectNodeReference)
    assert isinstance(y, DirectNodeReference)
    assert isinstance(z, DirectNodeReference)
    assert leaves == {x.node, y.node, z.node}


def test_dataflow_variable_loop_with_external_assignment_leaves(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")
    z: AssignableNodeReference = get_dataflow_node(graph, "z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    z.assign(x, Statement(), graph)

    u: AssignableNodeReference = get_dataflow_node(graph, "u")
    y.assign(u, Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaf_nodes())
    assert isinstance(u, DirectNodeReference)
    assert leaves == {u.node}


def test_dataflow_variable_loop_with_value_assignment_leaves(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")
    z: AssignableNodeReference = get_dataflow_node(graph, "z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    z.assign(x, Statement(), graph)

    y.assign(ValueNode(42).reference(), Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaf_nodes())
    assert isinstance(x, DirectNodeReference)
    assert isinstance(y, DirectNodeReference)
    assert isinstance(z, DirectNodeReference)
    assert leaves == {y.node}
