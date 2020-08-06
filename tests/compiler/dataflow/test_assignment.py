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


from typing import Optional, Set

import pytest

from compiler.dataflow.conftest import create_instance, get_dataflow_node
from inmanta.ast.statements import Statement
from inmanta.execute.dataflow import (
    AssignableNode,
    AssignableNodeReference,
    Assignment,
    AttributeNode,
    DataflowGraph,
    DirectNodeReference,
    InstanceNode,
    ValueNode,
    ValueNodeReference,
    VariableNodeReference,
)


def test_dataflow_assignment_node_simple(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")

    x.assign(y, Statement(), graph)

    assert isinstance(x, VariableNodeReference)
    assert x.assignment_node() == x.node


@pytest.mark.parametrize("instantiate", [True, False])
def test_dataflow_assignment_node_attribute(graph: DataflowGraph, instantiate: bool) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")
    z: AssignableNodeReference = get_dataflow_node(graph, "z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    if instantiate:
        y.assign(create_instance().reference(), Statement(), graph)

    x_n: AssignableNodeReference = get_dataflow_node(graph, "x.n")

    assignment_node: AssignableNode = x_n.assignment_node()
    instance: InstanceNode
    if instantiate:
        assert isinstance(y, VariableNodeReference)
        assert len(y.node.instance_assignments) == 1
        instance = y.node.instance_assignments[0].rhs.node()
    else:
        assert isinstance(z, VariableNodeReference)
        assert z.node.equivalence.tentative_instance is not None
        instance = z.node.equivalence.tentative_instance
        # verify tentative nodes only get created once
        assignment_node2: AssignableNode = x_n.assignment_node()
        assert assignment_node == assignment_node2
    assert assignment_node == instance.get_attribute("n")


def test_dataflow_assignment_node_nested_tentative(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")

    x_a_n: AssignableNodeReference = get_dataflow_node(graph, "x.a.n")
    assignment_node: AssignableNode = x_a_n.assignment_node()

    assert isinstance(x, VariableNodeReference)
    instance: Optional[InstanceNode] = x.node.equivalence.tentative_instance
    assert instance is not None
    a: Optional[AttributeNode] = instance.get_attribute("a")
    assert a is not None
    instance2: Optional[InstanceNode] = a.equivalence.tentative_instance
    assert instance2 is not None
    n: Optional[AttributeNode] = instance2.get_attribute("n")

    assert assignment_node == n


def test_dataflow_primitive_assignment(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    statement: Statement = Statement()
    x.assign(ValueNode(42).reference(), statement, graph)
    assert isinstance(x, DirectNodeReference)
    assert len(x.node.value_assignments) == 1
    assignment: Assignment[ValueNodeReference] = x.node.value_assignments[0]
    assert assignment.lhs == x.node
    assert assignment.rhs.node == ValueNode(42)
    assert assignment.responsible == statement
    assert assignment.context == graph


@pytest.mark.parametrize("instantiate", [True, False])
def test_attribute_assignment(graph: DataflowGraph, instantiate: bool) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    x_n: AssignableNodeReference = get_dataflow_node(graph, "x.n")

    if instantiate:
        x.assign(create_instance().reference(), Statement(), graph)
    x_n.assign(ValueNode(42).reference(), Statement(), graph)

    assert isinstance(x, VariableNodeReference)
    instance: InstanceNode
    if instantiate:
        assert x.node.equivalence.tentative_instance is None
        assert len(x.node.instance_assignments) == 1
        instance = x.node.instance_assignments[0].rhs.node()
    else:
        assert x.node.equivalence.tentative_instance is not None
        instance = x.node.equivalence.tentative_instance

    n: Optional[AttributeNode] = instance.get_attribute("n")
    assert n is not None
    assert len(n.value_assignments) == 1
    assert n.value_assignments[0].rhs == ValueNode(42).reference()


def test_dataflow_tentative_attribute_propagation(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")
    z: AssignableNodeReference = get_dataflow_node(graph, "z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)

    x_a_n: AssignableNodeReference = get_dataflow_node(graph, "x.a.n")
    x_a_n.assign(ValueNode(42).reference(), Statement(), graph)

    def assert_tentative_a_n(var: AssignableNode, values: Optional[Set[int]] = None) -> None:
        if values is None:
            values = {42}
        instance: Optional[InstanceNode] = var.equivalence.tentative_instance
        assert instance is not None
        a: Optional[AttributeNode] = instance.get_attribute("a")
        assert a is not None
        instance2: Optional[InstanceNode] = a.equivalence.tentative_instance
        assert instance2 is not None
        n: Optional[AttributeNode] = instance2.get_attribute("n")
        assert n is not None
        assert len(n.value_assignments) == len(values)
        assert {assignment.rhs.node.value for assignment in n.value_assignments} == values

    assert isinstance(z, VariableNodeReference)
    assert_tentative_a_n(z.node)

    u: AssignableNodeReference = get_dataflow_node(graph, "u")
    v: AssignableNodeReference = get_dataflow_node(graph, "v")

    u.assign(v, Statement(), graph)
    z.assign(u, Statement(), graph)

    assert isinstance(z, VariableNodeReference)
    assert z.node.equivalence.tentative_instance is None
    assert isinstance(v, VariableNodeReference)
    assert_tentative_a_n(v.node)

    x_a_n.assign(ValueNode(0).reference(), Statement(), graph)
    assert_tentative_a_n(v.node, {0, 42})


def test_dataflow_tentative_attribute_propagation_on_equivalence(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")
    z: AssignableNodeReference = get_dataflow_node(graph, "z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    z.assign(x, Statement(), graph)

    x_n: AssignableNodeReference = get_dataflow_node(graph, "x.n")
    x_n.assign(ValueNode(42).reference(), Statement(), graph)

    assert isinstance(y, VariableNodeReference)
    assert len(y.node.instance_assignments) == 0

    y.assign(create_instance().reference(), Statement(), graph)

    assert len(y.node.instance_assignments) == 1
    y_n: Optional[AttributeNode] = y.node.instance_assignments[0].rhs.node().get_attribute("n")
    assert y_n is not None

    assert len(y_n.value_assignments) == 1
    assert y_n.value_assignments[0].rhs.node.value == 42


def test_dataflow_tentative_attribute_propagation_to_uninitialized_attribute(graph: DataflowGraph) -> None:
    x_u: AssignableNodeReference = get_dataflow_node(graph, "x.u")
    u: AssignableNodeReference = get_dataflow_node(graph, "u")
    u_n: AssignableNodeReference = get_dataflow_node(graph, "u.n")

    u_n.assign(ValueNode(42).reference(), Statement(), graph)
    u.assign(x_u, Statement(), graph)

    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    assert isinstance(x, VariableNodeReference)
    instance: Optional[InstanceNode] = x.node.equivalence.tentative_instance
    assert instance is not None
    u_node: Optional[AttributeNode] = instance.get_attribute("u")
    assert u_node is not None
    instance2: Optional[InstanceNode] = u_node.equivalence.tentative_instance
    assert instance2 is not None
    n: Optional[AttributeNode] = instance2.get_attribute("n")
    assert n is not None
    assert len(n.value_assignments) == 1
    assert n.value_assignments[0].rhs.node.value == 42


def test_dataflow_tentative_attribute_propagation_over_uninitialized_attribute(graph: DataflowGraph) -> None:
    x_y: AssignableNodeReference = get_dataflow_node(graph, "x.y")
    u_n: AssignableNodeReference = get_dataflow_node(graph, "u.n")
    y: AssignableNodeReference = get_dataflow_node(graph, "y")
    u: AssignableNodeReference = get_dataflow_node(graph, "u")

    u_n.assign(ValueNode(42).reference(), Statement(), graph)
    x_y.assign(y, Statement(), graph)
    u.assign(x_y, Statement(), graph)

    assert isinstance(y, VariableNodeReference)
    instance: Optional[InstanceNode] = y.node.equivalence.tentative_instance
    assert instance is not None
    n: Optional[AttributeNode] = instance.get_attribute("n")
    assert n is not None
    assert len(n.value_assignments) == 1
    assert n.value_assignments[0].rhs.node.value == 42
