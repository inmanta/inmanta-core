"""
    Copyright 2019 Inmanta

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
from inmanta.ast import Location, Range
from inmanta.ast.attribute import RelationAttribute
from inmanta.ast.entity import Entity, Namespace
from inmanta.ast.statements import Literal, Resumer, Statement
from inmanta.ast.statements.assign import GradualSetAttributeHelper, SetAttribute, SetAttributeHelper
from inmanta.ast.statements.call import FunctionUnit
from inmanta.ast.variables import Reference
from inmanta.execute.dataflow import (
    AssignableNode,
    Assignment,
    AttributeNode,
    AttributeNodeReference,
    DataflowGraph,
    InstanceNode,
    InstanceNodeReference,
    NodeStub,
    ValueNode,
    ValueNodeReference,
    VariableNodeReference,
)
from inmanta.execute.runtime import (
    AttributeVariable,
    DelegateQueueScheduler,
    ExecutionUnit,
    HangUnit,
    Instance,
    ListVariable,
    OptionVariable,
    Promise,
    QueueScheduler,
    RawUnit,
    Resolver,
    ResultVariable,
    Waiter,
)


def assert_slotted(obj):
    assert not hasattr(obj, "__dict__")


def test_slots_rt():
    ns = Namespace("root", None)
    rs = Resolver(ns)
    e = Entity("xx", ns)
    qs = QueueScheduler(None, [], [], None, set())
    r = RelationAttribute(e, None, "xx", Location("", 1))
    i = Instance(e, rs, qs)
    sa = SetAttribute(Reference("a"), "a", Literal("a"))

    assert_slotted(ResultVariable())
    assert_slotted(AttributeVariable(None, None))
    assert_slotted(Promise(None, None))
    assert_slotted(ListVariable(r, i, qs))
    assert_slotted(OptionVariable(r, i, qs))

    assert_slotted(qs)
    assert_slotted(DelegateQueueScheduler(qs, None))

    assert_slotted(Waiter(qs))

    assert_slotted(ExecutionUnit(qs, r, ResultVariable(), {}, Literal(""), None))
    assert_slotted(HangUnit(qs, r, {}, None, Resumer()))
    assert_slotted(RawUnit(qs, r, {}, Resumer()))

    assert_slotted(FunctionUnit(qs, rs, ResultVariable(), {}, None))

    assert_slotted(i)
    assert_slotted(GradualSetAttributeHelper(sa, i, "A", ResultVariable()))
    assert_slotted(SetAttributeHelper(qs, rs, ResultVariable(), {}, Literal("A"), sa, i, "A"))


def test_slots_ast():
    assert_slotted(Location("", 0))
    assert_slotted(Range("", 0, 0, 0, 0))


def test_slots_dataflow():
    namespace: Namespace = Namespace("root", None)
    resolver: Resolver = Resolver(namespace)

    graph: DataflowGraph = DataflowGraph(resolver)
    assignable_node: AssignableNode = AssignableNode("node")
    value_node: ValueNode = ValueNode(42)
    instance_node: InstanceNode = InstanceNode([])

    assert_slotted(graph)
    assert_slotted(assignable_node)
    assert_slotted(assignable_node.equivalence)
    assert_slotted(value_node)
    assert_slotted(instance_node)

    assert_slotted(AttributeNodeReference(assignable_node.reference(), "attr"))
    assert_slotted(VariableNodeReference(assignable_node))
    assert_slotted(ValueNodeReference(value_node))
    assert_slotted(InstanceNodeReference(instance_node))
    assert_slotted(Assignment(assignable_node.reference(), value_node, Statement(), graph))
    assert_slotted(NodeStub("stub"))
    assert_slotted(AttributeNode(instance_node, "attr"))
