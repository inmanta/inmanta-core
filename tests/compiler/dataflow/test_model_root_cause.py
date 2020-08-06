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

from compiler.dataflow.conftest import DataflowTestHelper, get_dataflow_node
from inmanta.ast import MultiException
from inmanta.execute.dataflow import AssignableNode, AssignableNodeReference, AttributeNode, DataflowGraph
from inmanta.execute.dataflow.root_cause import UnsetRootCauseAnalyzer


def get_attribute_node(graph: DataflowGraph, attr: str) -> AttributeNode:
    node_ref: AssignableNodeReference = get_dataflow_node(graph, attr)
    node: AssignableNode = next(node_ref.nodes())
    assert isinstance(node, AttributeNode)
    return node


@pytest.mark.parametrize("attribute_equivalence", [True, False])
@pytest.mark.parametrize("variable_equivalence", [True, False])
def test_dataflow_model_root_cause(
    dataflow_test_helper: DataflowTestHelper, attribute_equivalence: bool, variable_equivalence: bool
) -> None:
    dataflow_test_helper.compile(
        """
entity C:
    number i
end


entity V:
    number n
    number i
end

index V(i)


entity U:
end

U.v [1] -- V


entity X:
    number n
end



implement C using std::none
implement V using std::none
implement U using std::none
implement X using std::none


c = C()
%s

u = U()
x = X()
u.v = V(n = 42, i = c.i)
x.n = u.v.n

%s
        """
        % (
            """
c.i = cc.i
cc = C(i = c.i)
            """
            if attribute_equivalence
            else "",
            """
c.i = i
i = c.i
            """
            if variable_equivalence
            else "",
        ),
        MultiException,
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()

    x_n: AttributeNode = get_attribute_node(graph, "x.n")
    c_i: AttributeNode = get_attribute_node(graph, "c.i")
    u_v: AttributeNode = get_attribute_node(graph, "u.v")

    attributes: List[AttributeNode] = [x_n, c_i, u_v]
    root_causes: Set[AttributeNode] = {c_i}

    if attribute_equivalence:
        cc_i: AttributeNode = get_attribute_node(graph, "cc.i")
        attributes.append(cc_i)
        root_causes.add(cc_i)

    assert UnsetRootCauseAnalyzer(attributes).root_causes() == root_causes


def test_cyclic_model_a(dataflow_test_helper: DataflowTestHelper):
    dataflow_test_helper.compile(
        """
entity A:
    number n
end

implement A using std::none


x = A()
y = A()
z = A()


x.n = y.n
y.n = x.n
x.n = z.n
""",
        MultiException,
    )

    graph: DataflowGraph = dataflow_test_helper.get_graph()

    x_n: AttributeNode = get_attribute_node(graph, "x.n")
    y_n: AttributeNode = get_attribute_node(graph, "y.n")
    z_n: AttributeNode = get_attribute_node(graph, "z.n")

    attributes: List[AttributeNode] = [x_n, y_n, z_n]
    root_causes: Set[AttributeNode] = {z_n}

    assert UnsetRootCauseAnalyzer(attributes).root_causes() == root_causes


def test_cyclic_model_b(dataflow_test_helper: DataflowTestHelper):
    """

    This model has an equivalence that
    1. is to be ignored as a root
    2. cause two things (that now become roots)

    """
    dataflow_test_helper.compile(
        """
entity A:
    number n
end

implement A using std::none


x = A()
y = A()


y.n = n
x.n = n


n = m
m = n
""",
        MultiException,
    )

    graph: DataflowGraph = dataflow_test_helper.get_graph()

    x_n: AttributeNode = get_attribute_node(graph, "x.n")
    y_n: AttributeNode = get_attribute_node(graph, "y.n")

    attributes: List[AttributeNode] = [x_n, y_n]
    root_causes: Set[AttributeNode] = {x_n, y_n}

    assert UnsetRootCauseAnalyzer(attributes).root_causes() == root_causes
