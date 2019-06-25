from inmanta.ast import Locatable, Location, Range
from inmanta.ast.attribute import RelationAttribute
from inmanta.ast.entity import Entity, Namespace
from inmanta.ast.statements import Literal, Resumer
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
    r = RelationAttribute(e, None, "xx")
    i = Instance(e, rs, qs)

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

    assert_slotted(i)


def test_slots_ast():
    assert_slotted(Location("", 0))
    assert_slotted(Range("", 0, 0, 0, 0))
    assert_slotted(Locatable())
