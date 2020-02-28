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

from typing import Iterator, List, Optional, Set

import pytest

import inmanta.compiler as compiler
from inmanta.ast import Namespace
from inmanta.ast.entity import Entity
from inmanta.ast.statements import Statement
from inmanta.execute.dataflow import (
    AssignableNode,
    AssignableNodeReference,
    Assignment,
    AttributeNode,
    AttributeNodeReference,
    DataflowGraph,
    DirectNodeReference,
    InstanceNode,
    Node,
    NodeReference,
    ValueNode,
    ValueNodeReference,
    VariableNodeReference,
)
from inmanta.execute.runtime import Resolver


@pytest.fixture(scope="function")
def graph() -> Iterator[DataflowGraph]:
    dummy_resolver: Resolver = Resolver(Namespace("dummy_namespace"))
    yield DataflowGraph(dummy_resolver)


def instance_node(attributes: Optional[List[str]] = None) -> InstanceNode:
    entity: Entity = Entity("DummyEntity", Namespace("dummy_namespace"))
    return InstanceNode(attributes if attributes is not None else [], entity, Statement(), graph)


def register_instance(
    graph: DataflowGraph, entity: Optional[Entity] = None, statement: Optional[Statement] = None
) -> InstanceNode:
    responsible: Statement = statement if statement is not None else Statement()
    return graph.own_instance_node_for_responsible(
        responsible,
        lambda: InstanceNode(
            [], entity if entity is not None else Entity("DummyEntity", Namespace("dummy_namespace")), responsible, graph
        ),
    )


def test_dataflow_hierarchy(graph: DataflowGraph) -> None:
    entity: Entity = Entity("DummyEntity", Namespace("dummy_namespace"))
    dummy_resolver: Resolver = Resolver(Namespace("dummy_namespace"))
    child: DataflowGraph = DataflowGraph(dummy_resolver, graph)
    assert child.instances() == {}
    assert graph.instances() == {}
    statement1: Statement = Statement()
    statement2: Statement = Statement()

    node1: InstanceNode = register_instance(child, entity, statement1)
    child.register_bidirectional_attribute(entity, "this", "other")

    assert child.instances() == graph.instances()
    assert entity in child.instances()
    assert child.instances()[entity].instances == [node1.reference()]
    assert child.instances()[entity].bidirectional_attributes == {"this": "other"}

    node2: InstanceNode = register_instance(child, entity, statement1)
    node3: InstanceNode = register_instance(child, entity, statement2)
    assert node1 == node2
    assert node2 != node3

    assert child.get_named_node("x") != graph.get_named_node("x")


def test_dataflow_simple_lookup(graph: DataflowGraph) -> None:
    x1: AssignableNodeReference = graph.get_named_node("x")
    x2: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    assert isinstance(x1, VariableNodeReference)
    assert x1.node.name == "x"
    assert x1 == x2
    assert isinstance(y, VariableNodeReference)
    assert y.node.name == "y"


def test_dataflow_attribute_lookup(graph: DataflowGraph) -> None:
    x_a_n: AssignableNodeReference = graph.get_named_node("x.a.n")
    x: AssignableNodeReference = graph.get_named_node("x")
    assert x_a_n == AttributeNodeReference(AttributeNodeReference(x, "a"), "n")


def test_dataflow_reference_nodes(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    x_nodes: List[AssignableNode] = list(x.nodes())
    assert len(x_nodes) == 1
    assert isinstance(x, DirectNodeReference)
    assert x_nodes[0] == x.node


def test_dataflow_attribute_reference_nodes(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    x.assign(y, Statement(), graph)
    y.assign(instance_node(["n"]).reference(), Statement(), graph)

    assert isinstance(y, VariableNodeReference)
    assert len(y.node.instance_assignments) == 1

    y_n: AssignableNodeReference = graph.get_named_node("y.n")
    y_n.assign(ValueNode(42).reference(), Statement(), graph)

    x_n: AssignableNodeReference = graph.get_named_node("x.n")
    x_n_nodes: List[AssignableNode] = list(x_n.nodes())
    assert len(x_n_nodes) == 1
    assert x_n_nodes[0] == y.node.instance_assignments[0].rhs.node().get_attribute("n")


def test_dataflow_simple_leaf(graph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    leaves: List[AssignableNode] = list(x.leaves())
    assert isinstance(x, DirectNodeReference)
    assert leaves == [x.node]


def test_dataflow_variable_chain_leaf(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaves())
    assert isinstance(z, DirectNodeReference)
    assert leaves == {z.node}


@pytest.mark.parametrize("value_node", [ValueNode(42), instance_node()])
def test_dataflow_variable_tree_leaves(graph: DataflowGraph, value_node: Node) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    y.assign(value_node.reference(), Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaves())
    assert isinstance(y, DirectNodeReference)
    assert isinstance(z, DirectNodeReference)
    assert leaves == {y.node, z.node}


def test_dataflow_variable_loop_leaves(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    z.assign(x, Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaves())
    assert isinstance(x, DirectNodeReference)
    assert isinstance(y, DirectNodeReference)
    assert isinstance(z, DirectNodeReference)
    assert leaves == {x.node, y.node, z.node}


def test_dataflow_variable_loop_with_external_assignment_leaves(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    z.assign(x, Statement(), graph)

    u: AssignableNodeReference = graph.get_named_node("u")
    y.assign(u, Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaves())
    assert isinstance(u, DirectNodeReference)
    assert leaves == {u.node}


def test_dataflow_variable_loop_with_value_assignment_leaves(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    z.assign(x, Statement(), graph)

    y.assign(ValueNode(42).reference(), Statement(), graph)

    leaves: Set[AssignableNode] = set(x.leaves())
    assert isinstance(x, DirectNodeReference)
    assert isinstance(y, DirectNodeReference)
    assert isinstance(z, DirectNodeReference)
    # TODO: is this the desired result? Shouldn't only y.node be in the set?
    assert leaves == {x.node, y.node, z.node}


def test_dataflow_assignment_node_simple(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")

    x.assign(y, Statement(), graph)

    assert isinstance(x, VariableNodeReference)
    assert x.assignment_node() == x.node


@pytest.mark.parametrize("instantiate", [True, False])
def test_dataflow_assignment_node_attribute(graph: DataflowGraph, instantiate: bool) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)
    if instantiate:
        y.assign(instance_node().reference(), Statement(), graph)

    x_n: AssignableNodeReference = graph.get_named_node("x.n")

    assignment_node: AssignableNode = x_n.assignment_node()
    instance: InstanceNode
    if instantiate:
        assert isinstance(y, VariableNodeReference)
        assert len(y.node.instance_assignments) == 1
        instance = y.node.instance_assignments[0].rhs.node()
    else:
        assert isinstance(z, VariableNodeReference)
        assert z.node.tentative_instance is not None
        instance = z.node.tentative_instance
        # verify tentative nodes only get created once
        assignment_node2: AssignableNode = x_n.assignment_node()
        assert assignment_node == assignment_node2
    assert assignment_node == instance.get_attribute("n")


def test_dataflow_assignment_node_nested_tentative(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")

    x_a_n: AssignableNodeReference = graph.get_named_node("x.a.n")
    assignment_node: AssignableNode = x_a_n.assignment_node()

    assert isinstance(x, VariableNodeReference)
    instance: Optional[InstanceNode] = x.node.tentative_instance
    assert instance is not None
    a: Optional[AttributeNode] = instance.get_attribute("a")
    assert a is not None
    instance2: Optional[InstanceNode] = a.tentative_instance
    assert instance2 is not None
    n: Optional[AttributeNode] = instance2.get_attribute("n")

    assert assignment_node == n


def test_dataflow_primitive_assignment(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    statement: Statement = Statement()
    x.assign(ValueNode(42).reference(), statement, graph)
    assert isinstance(x, DirectNodeReference)
    assert len(x.node.value_assignments) == 1
    assignment: Assignment[ValueNodeReference] = x.node.value_assignments[0]
    assert assignment.lhs == x
    assert assignment.rhs.node == ValueNode(42)
    assert assignment.responsible == statement
    assert assignment.context == graph


@pytest.mark.parametrize("instantiate", [True, False])
def test_attribute_assignment(graph: DataflowGraph, instantiate: bool) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    x_n: AssignableNodeReference = graph.get_named_node("x.n")

    if instantiate:
        x.assign(instance_node().reference(), Statement(), graph)
    x_n.assign(ValueNode(42).reference(), Statement(), graph)

    assert isinstance(x, VariableNodeReference)
    instance: InstanceNode
    if instantiate:
        assert x.node.tentative_instance is None
        assert len(x.node.instance_assignments) == 1
        instance = x.node.instance_assignments[0].rhs.node()
    else:
        assert x.node.tentative_instance is not None
        instance = x.node.tentative_instance

    n: Optional[AttributeNode] = instance.get_attribute("n")
    assert n is not None
    assert len(n.value_assignments) == 1
    assert n.value_assignments[0].rhs == ValueNode(42).reference()


def test_dataflow_tentative_attribute_propagation(graph: DataflowGraph) -> None:
    x: AssignableNodeReference = graph.get_named_node("x")
    y: AssignableNodeReference = graph.get_named_node("y")
    z: AssignableNodeReference = graph.get_named_node("z")

    x.assign(y, Statement(), graph)
    y.assign(z, Statement(), graph)

    x_a_n: AssignableNodeReference = graph.get_named_node("x.a.n")
    x_a_n.assign(ValueNode(42).reference(), Statement(), graph)

    def assert_tentative_a_n(var: AssignableNode) -> None:
        instance: Optional[InstanceNode] = var.tentative_instance
        assert instance is not None
        a: Optional[AttributeNode] = instance.get_attribute("a")
        assert a is not None
        instance2: Optional[InstanceNode] = a.tentative_instance
        assert instance2 is not None
        n: Optional[AttributeNode] = instance2.get_attribute("n")
        assert n is not None
        assert len(n.value_assignments) == 1
        assert n.value_assignments[0].rhs.node == ValueNode(42)

    assert isinstance(z, VariableNodeReference)
    assert_tentative_a_n(z.node)

    u: AssignableNodeReference = graph.get_named_node("u")
    v: AssignableNodeReference = graph.get_named_node("v")

    u.assign(v, Statement(), graph)
    z.assign(u, Statement(), graph)

    assert isinstance(z, VariableNodeReference)
    assert z.node.tentative_instance is None
    assert isinstance(v, VariableNodeReference)
    assert_tentative_a_n(v.node)


@pytest.mark.parametrize("register_both_dirs", [True, False])
@pytest.mark.parametrize("assign_first", [True, False])
def test_dataflow_bidirectional_attribute(graph: DataflowGraph, register_both_dirs: bool, assign_first: bool) -> None:
    namespace: Namespace = Namespace("dummy_namespace")
    left_entity: Entity = Entity("Left", namespace)
    right_entity: Entity = Entity("Right", namespace)

    def register_attributes() -> None:
        graph.register_bidirectional_attribute(left_entity, "right", "left")
        if register_both_dirs:
            graph.register_bidirectional_attribute(right_entity, "left", "right")

    def assign_attribute(left: InstanceNode, right: NodeReference) -> None:
        left.assign_attribute("right", right, Statement(), graph)

    left = register_instance(graph, left_entity)
    right = register_instance(graph, right_entity)
    right_indirect = register_instance(graph, right_entity)
    x: AssignableNodeReference = graph.get_named_node("x")
    x.assign(right_indirect.reference(), Statement(), graph)
    assert isinstance(x, VariableNodeReference)
    assert len(x.node.instance_assignments) == 1

    if assign_first:
        assign_attribute(left, right.reference())
        assign_attribute(left, x)
        register_attributes()
    else:
        register_attributes()
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
    i1: InstanceNode = register_instance(graph, entity)
    i2: InstanceNode = register_instance(graph, entity)

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
    assert i1.get_self().get_all_index_nodes() == {i1, i2}


# TODO:
#   add model tests
#   fix TODO's in inmanta.execute.dataflow
#   add toggle option to inmanta.app
