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

from typing import Union

import pytest

from inmanta.ast import Namespace
from inmanta.ast.entity import Entity
from inmanta.execute.dataflow import (
    AssignableNode,
    AttributeNode,
    AttributeNodeReference,
    InstanceNode,
    Node,
    NodeReference,
    ValueNode,
)


def entity_instance(entity: str) -> InstanceNode:
    node: InstanceNode = InstanceNode([])
    node.entity = Entity(entity, Namespace("__config__", Namespace("__root_ns__")))
    return node


@pytest.mark.parametrize(
    "instance,expected_repr",
    [
        (ValueNode(42), "42"),
        (ValueNode("42"), "'42'"),
        (ValueNode(42).reference(), "42"),
        (ValueNode("Hello World!"), repr("Hello World!")),
        (AssignableNode("x"), "x"),
        (AssignableNode("x").reference(), "x"),
        (AttributeNodeReference(AttributeNodeReference(AssignableNode("x").reference(), "y"), "z"), "x.y.z"),
        (entity_instance("MyEntity"), "__config__::MyEntity instance"),
        (entity_instance("MyEntity").reference(), "__config__::MyEntity instance"),
        (AttributeNode(entity_instance("MyEntity"), "n"), "attribute n on __config__::MyEntity instance"),
    ],
)
def test_dataflow_repr(instance: Union[Node, NodeReference], expected_repr: str) -> None:
    assert repr(instance) == expected_repr
    assert str(instance) == expected_repr
