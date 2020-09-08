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

from typing import Optional

import inmanta.ast.type as inmanta_type
from compiler.dataflow.conftest import DataflowTestHelper
from inmanta.ast.entity import Entity
from inmanta.execute.dataflow import AssignableNodeReference, InstanceAttributeNodeReference, InstanceNodeReference
from inmanta.execute.runtime import Instance, ResultVariable, Typeorvalue


def test_dataflow_model_index_resultvariable_binding(dataflow_test_helper: DataflowTestHelper) -> None:
    dataflow_test_helper.compile(
        """
entity A:
    number n
    number m
end

index A(n)

implement A using std::none


A(n = 0, m = 0)
A(n = 0, m = 0)
        """,
    )
    entity: inmanta_type.Type = dataflow_test_helper.get_types()["__config__::A"]
    assert isinstance(entity, Entity)
    assert len(entity.get_all_instances()) == 1
    instance: Instance = entity.get_all_instances()[0]
    node: Optional[InstanceNodeReference] = instance.instance_node
    assert node is not None
    for attr in ["n", "m"]:
        resultvariable: Typeorvalue = instance.lookup(attr)
        assert isinstance(resultvariable, ResultVariable)
        rv_node: AssignableNodeReference = resultvariable.get_dataflow_node()
        assert isinstance(rv_node, InstanceAttributeNodeReference)
        assert rv_node.assignment_node() is node.node().get_attribute(attr)
