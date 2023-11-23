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

from typing import List

import pytest

import inmanta.ast.type as inmanta_type
from compiler.dataflow.conftest import DataflowTestHelper, get_dataflow_node
from inmanta.ast.entity import Entity
from inmanta.execute.dataflow import AssignableNode


@pytest.mark.parametrize("explicit", [True, False])
def test_dataflow_model_implementation_assignment_from_self(dataflow_test_helper: DataflowTestHelper, explicit: bool) -> None:
    dataflow_test_helper.compile(
        """
entity A:
    number n
end

entity B:
    number n
end

A.b [1] -- B

implementation i for A:
    self.b = B(n = %s)
end

implement A using i
implement B using std::none

n = 0

x = A(n = 42)

b = x.b
        """
        % ("self.n" if explicit else "n"),
    )
    dataflow_test_helper.verify_graphstring(
        """
n -> 0
x -> <instance> x
<instance> x . n -> 42
<instance> x . b -> <instance> b
b -> x . b
        """,
    )
    dataflow_test_helper.verify_leaves({"b.n": {"x.n"}})
    leaves: List[AssignableNode] = list(get_dataflow_node(dataflow_test_helper.get_graph(), "b.n").leaf_nodes())
    assert len(leaves) == 1
    assert len(leaves[0].value_assignments) == 1
    assert leaves[0].value_assignments[0].rhs.node.value == 42


def test_dataflow_model_unnamed_instance_in_implementation(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity A:
end

entity B:
end

implementation i for A:
    B()
end

implement A using i
implement B using std::none

x = A()
        """,
    )
    entity_b: inmanta_type.Type = dataflow_test_helper.get_types()["__config__::B"]
    assert isinstance(entity_b, Entity)
    assert len(entity_b.get_all_instances()) == 1
