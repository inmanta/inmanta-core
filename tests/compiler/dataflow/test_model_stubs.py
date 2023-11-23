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

from typing import Dict, List

import pytest

import inmanta.ast.type as inmanta_type
from compiler.dataflow.conftest import DataflowTestHelper, get_dataflow_node
from inmanta.execute.dataflow import (
    AssignableNodeReference,
    Assignment,
    DataflowGraph,
    NodeReference,
    NodeStub,
    ValueNodeReference,
    VariableNodeReference,
)


@pytest.mark.parametrize(
    "value_string,other_stmts",
    [
        ("[1,2,3]", []),
        ("{'a': 1}", []),
        ("std::replace('Hello World?', '?', '!')", []),
        ("true or true", []),
        ("true and true", []),
        ("not true", []),
        ("y is defined", ["y = 0"]),
        ("y['a']", ["y = {'a': 1}"]),
        (
            "A[n = 0]",
            [
                """
                entity A:
                    number n
                end

                index A(n)

                implement A using std::none
            """,
                "A(n = 0)",
            ],
        ),
        ("'{{y}}'", "y = 0"),
        ("true == true", []),
        ("1 < 0", []),
        ("1 > 0", []),
        ("1 <= 0", []),
        ("1 >= 0", []),
        ("1 != 0", []),
        ("1 in [1]", []),
    ],
)
def test_dataflow_nodestub(dataflow_test_helper: DataflowTestHelper, value_string: str, other_stmts: List[str]) -> None:
    dataflow_test_helper.compile(
        """
x = %s
%s
        """
        % (value_string, "\n".join(other_stmts)),
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()
    x: AssignableNodeReference = get_dataflow_node(graph, "x")
    assert isinstance(x, VariableNodeReference)
    assignments: List[Assignment] = list(x.node.assignments())
    assert len(assignments) == 1
    assert isinstance(assignments[0].rhs, ValueNodeReference)
    assert isinstance(assignments[0].rhs.node, NodeStub)


def test_dataflow_nodestub_regex(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
typedef my_type as string matching /test/
        """,
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()
    types: Dict[str, inmanta_type.Type] = dataflow_test_helper.get_types()
    type_string: str = "__config__::my_type"
    assert type_string in types
    my_type: inmanta_type.Type = types[type_string]
    assert isinstance(my_type, inmanta_type.ConstraintType)
    assert my_type.expression is not None
    regex_node_ref: NodeReference = my_type.expression.get_dataflow_node(graph)
    assert isinstance(regex_node_ref, ValueNodeReference)
    assert isinstance(regex_node_ref.node, NodeStub)
