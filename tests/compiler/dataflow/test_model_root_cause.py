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

from compiler.dataflow.conftest import DataflowTestHelper

from inmanta.ast import MultiException
from inmanta.execute.dataflow import AssignableNode, AssignableNodeReference, AttributeNode, DataflowGraph
from inmanta.execute.dataflow.root_cause import RootCauseAnalyzer


def get_attribute_node(graph: DataflowGraph, attr: str) -> AttributeNode:
    node_ref: AssignableNodeReference = graph.get_named_node(attr)
    node: AssignableNode = next(node_ref.nodes())
    assert isinstance(node, AttributeNode)
    return node


def test_dataflow_model_root_cause(dataflow_test_helper: DataflowTestHelper) -> None:
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
u = U()
x = X()
u.v = V(n = 42, i = c.i)
x.n = u.v.n
        """,
        MultiException,
    )
    graph: DataflowGraph = dataflow_test_helper.get_graph()

    x_n: AttributeNode = get_attribute_node(graph, "x.n")
    c_i: AttributeNode = get_attribute_node(graph, "c.i")
    u_v: AttributeNode = get_attribute_node(graph, "u.v")

    assert RootCauseAnalyzer([x_n, c_i, u_v]).root_causes() == {c_i}
