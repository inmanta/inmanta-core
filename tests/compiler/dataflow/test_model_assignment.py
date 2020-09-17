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

from typing import Dict, List, Optional

import pytest

import inmanta.ast.type as inmanta_type
from compiler.dataflow.conftest import DataflowTestHelper, get_dataflow_node
from inmanta.ast import DoubleSetException, NotFoundException, RuntimeException
from inmanta.ast.entity import Entity
from inmanta.ast.statements import Literal
from inmanta.ast.statements.assign import Assign, SetAttribute
from inmanta.ast.variables import Reference
from inmanta.execute.dataflow import (
    AssignableNode,
    AssignableNodeReference,
    Assignment,
    AttributeNode,
    DataflowGraph,
    ValueNode,
    ValueNodeReference,
    VariableNodeReference,
)
from inmanta.execute.runtime import Instance, ResultVariable, Typeorvalue


def test_dataflow_model_primitive_assignment_responsible(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = 42
        """,
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    assert isinstance(x, VariableNodeReference)
    assert len(x.node.value_assignments) == 1
    assignment: Assignment[ValueNodeReference] = x.node.value_assignments[0]
    assert isinstance(assignment.responsible, Assign)
    assert assignment.responsible.name == "x"
    assert isinstance(assignment.responsible.value, Literal)
    assert assignment.responsible.value.value == 42
    assert assignment.context == graph


def test_dataflow_model_primitive_double_assignment_responsible(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = 42
x = 0
        """,
        DoubleSetException,
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    assert isinstance(x, VariableNodeReference)
    assignments: List[Assignment] = x.node.value_assignments
    assert len(assignments) == 2
    zero_index: int = [assignment.rhs for assignment in assignments].index(ValueNode(0).reference())
    for i, assignment in enumerate(assignments):
        value: int = 0 if i == zero_index else 42
        assert assignment.context == graph
        assert isinstance(assignment.responsible, Assign)
        assert assignment.responsible.name == "x"
        assert isinstance(assignment.responsible.value, Literal)
        assert assignment.responsible.value.value == value


def test_dataflow_model_variable_assignment_responsible(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = 42
        """,
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    assert isinstance(x, VariableNodeReference)
    assert len(x.node.assignable_assignments) == 1
    assignment: Assignment[AssignableNodeReference] = x.node.assignable_assignments[0]
    assert isinstance(assignment.responsible, Assign)
    assert assignment.responsible.name == "x"
    assert isinstance(assignment.responsible.value, Reference)
    assert assignment.responsible.value.name == "y"
    assert assignment.context == graph


def test_dataflow_model_attribute_assignment_responsible(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity Test:
    number n
end
implement Test using std::none

x = Test()
x.n = 42
        """
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    assert isinstance(x, VariableNodeReference)
    assert len(x.node.instance_assignments) == 1
    n: Optional[AttributeNode] = x.node.instance_assignments[0].rhs.node().get_attribute("n")
    assert n is not None
    assert len(n.value_assignments) == 1
    assignment: Assignment[ValueNodeReference] = n.value_assignments[0]
    assert isinstance(assignment.responsible, SetAttribute)
    assert assignment.responsible.instance.name == "x"
    assert assignment.responsible.attribute_name == "n"
    assert isinstance(assignment.responsible.value, Literal)
    assert assignment.responsible.value.value == 42
    assert assignment.context == graph


def test_dataflow_model_simple_assignment(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = 42
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> 42
        """,
    )
    dataflow_test_helper.verify_leaves({"x": {"x"}})


def test_dataflow_model_variable_assignment(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = y
x = y
y = 42
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> [ y y ]
y -> 42
        """,
    )
    dataflow_test_helper.verify_leaves({"x": {"y"}, "y": {"y"}})


@pytest.mark.parametrize("same_value", [True, False])
def test_dataflow_model_variable_assignment_double(dataflow_test_helper: DataflowTestHelper, same_value: bool) -> None:
    x_value: int = 42 if same_value else 0
    dataflow_test_helper.compile(
        """
x = y
x = y
y = 42
x = %d
        """
        % x_value,
        None if same_value else DoubleSetException,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> [ y y %s ]
y -> 42
        """
        % x_value,
    )
    dataflow_test_helper.verify_leaves({"x": {"x", "y"}, "y": {"y"}})


def test_dataflow_model_unassigned_dependency_error(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
x = y
y = z
        """,
        NotFoundException,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> y
y -> z
        """,
    )
    dataflow_test_helper.verify_leaves({"x": {"z"}, "y": {"z"}})


@pytest.mark.parametrize("attr_init", [True, False])
def test_dataflow_model_assignment_from_attribute(dataflow_test_helper: DataflowTestHelper, attr_init: bool) -> None:
    dataflow_test_helper.compile(
        """
entity A:
    number n
end
implement A using std::none

n = 42
x = A(%s)

nn = x.n
        """
        % ("n = n" if attr_init else ""),
        None if attr_init else RuntimeException,
    )
    dataflow_test_helper.verify_graphstring(
        """
x -> <instance> 0
n -> 42
nn -> x . n
%s
        """
        % ("<instance> 0 . n -> n" if attr_init else ""),
    )
    dataflow_test_helper.verify_leaves({"nn": {"n"}} if attr_init else {"nn": {"x.n"}})


def test_dataflow_model_assignment_outside_constructor(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity A:
    number n
end
implement A using std::none

n = 42

x = A()
x.n = n
        """,
    )
    dataflow_test_helper.verify_graphstring(
        """
n -> 42
x -> <instance> 0
<instance> 0 . n -> n
        """,
    )
    dataflow_test_helper.verify_leaves({"x.n": {"n"}})


def test_dataflow_model_no_leaf_error(dataflow_test_helper: DataflowTestHelper) -> None:
    """
    Verify that tentative instance propagation does not crash when rhs is a reference with no leaf nodes.
    """
    dataflow_test_helper.compile(
        """
n = x.n
        """,
        NotFoundException,
    )


def test_dataflow_model_result_variable(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity A:
    number n
end

index A(n)

A.other [0:1] -- B

entity B:
end

implement A using std::none
implement B using std::none

x = A(n = 4)
x.other = B()

y = A(n = 4)
        """,
    )

    def assert_rv(result_variable: ResultVariable) -> None:
        node_ref: Optional[AssignableNodeReference] = result_variable.get_dataflow_node()
        assert node_ref is not None
        nodes: List[AssignableNode] = list(node_ref.nodes())
        assert len(nodes) == 1
        assert nodes[0].result_variable is result_variable

    x: Typeorvalue = dataflow_test_helper.get_namespace().lookup("x")
    assert isinstance(x, ResultVariable)
    assert_rv(x)

    types: Dict[str, inmanta_type.Type] = dataflow_test_helper.get_types()
    a_entity_str: str = "__config__::A"
    assert a_entity_str in types
    a_entity: inmanta_type.Type = types[a_entity_str]
    assert isinstance(a_entity, Entity)
    a_instances: List[Instance] = a_entity.get_all_instances()
    assert len(a_instances) == 1
    for attr in ["n", "other"]:
        assert_rv(a_instances[0].get_attribute(attr))
