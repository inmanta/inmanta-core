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

from inmanta.ast import Namespace
from inmanta.ast.entity import Entity
from inmanta.ast.statements import Statement
from inmanta.execute.dataflow import (
    AssignableNodeReference,
    AttributeNodeReference,
    DataflowGraph,
    InstanceNode,
    VariableNodeReference,
)
from inmanta.execute.runtime import Resolver


def test_dataflow_hierarchy(graph: DataflowGraph) -> None:
    entity: Entity = Entity("DummyEntity", Namespace("dummy_namespace"))
    dummy_resolver: Resolver = Resolver(Namespace("dummy_namespace"))
    child: DataflowGraph = DataflowGraph(dummy_resolver, graph)
    assert child.entities() == {}
    assert graph.entities() == {}
    statement1: Statement = Statement()
    statement2: Statement = Statement()

    node1: InstanceNode = create_instance(child, entity, statement1)
    child.register_bidirectional_attribute(entity, "this", "other")

    assert child.entities() == graph.entities()
    assert entity in child.entities()
    assert child.entities()[entity].instances == [node1.reference()]
    assert child.entities()[entity].bidirectional_attributes == {"this": "other"}

    node2: InstanceNode = create_instance(child, entity, statement1)
    node3: InstanceNode = create_instance(child, entity, statement2)
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
