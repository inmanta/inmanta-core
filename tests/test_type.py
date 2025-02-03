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

import inspect
import typing
from functools import reduce
from typing import Optional

import pytest
from more_itertools import pairwise

import utils
from inmanta import plugins
from inmanta.ast import Location, Namespace, RuntimeException, statements
from inmanta.ast.attribute import Attribute
from inmanta.ast.entity import Entity
from inmanta.ast.type import TYPES, Any, ConstraintType, Bool, Float, Integer, LiteralDict, LiteralList, NullableType, Number, String, Type, TypedDict, TypedList, Union
from inmanta.execute.util import NoneValue


@pytest.mark.parametrize("base_type_string", TYPES.keys())
@pytest.mark.parametrize("multi", [True, False])
@pytest.mark.parametrize("nullable", [True, False])
def test_dsl_types_type_string(base_type_string: str, multi: bool, nullable: bool):
    def apply_multi_if(tp: Type, type_string: str) -> tuple[Type, str]:
        return (TypedList(tp), "%s[]" % type_string) if multi else (tp, type_string)

    def apply_nullable_if(tp: Type, type_string: str) -> tuple[Type, str]:
        return (NullableType(tp), "%s?" % type_string) if nullable else (tp, type_string)

    assert base_type_string in TYPES
    tp, type_string = apply_nullable_if(*apply_multi_if(TYPES[base_type_string], base_type_string))

    assert tp.type_string() == type_string
    assert str(tp) == type_string


@pytest.mark.parametrize("multi", [True, False])
@pytest.mark.parametrize("nullable", [True, False])
def test_attribute_validate(multi: bool, nullable: bool) -> None:
    entity: Entity = Entity("DummyEntity", Namespace("dummy_namespace"))
    attribute: Attribute = Attribute(entity, Integer(), "my_attribute", Location("dummy.cf", 1), multi, nullable)

    def validate(value: object, success: bool) -> None:
        if success:
            attribute.validate(value)
        else:
            with pytest.raises(RuntimeException):
                attribute.validate(value)

    validate(42, not multi)
    validate(NoneValue(), nullable)
    validate([0, 1, 2], multi)
    validate([0, 1, NoneValue()], False)


def create_type(base_type: type[Type], multi: bool = False, nullable: bool = False) -> Type:
    base: Type = base_type()
    transformations: list[typing.Callable[[Type], Type]] = [
        lambda t: TypedList(t) if multi else t,
        lambda t: NullableType(t) if nullable else t,
    ]
    return reduce(lambda acc, t: t(acc), transformations, base)


@pytest.mark.parametrize("base_type", [Bool, Integer, Float, LiteralDict, LiteralList, Number, String])
def test_type_equals_simple(base_type: type[Type]) -> None:
    assert create_type(base_type) == create_type(base_type)


def test_type_equals_transformations() -> None:
    def all_transformations() -> list[Type]:
        return [
            create_type(base_type, multi, nullable)
            for multi in [True, False]
            for nullable in [True, False]
            for base_type in [Integer, Number]
        ]

    l1: list[Type] = all_transformations()
    l2: list[Type] = all_transformations()
    assert l1 == l2
    for t1, t2 in pairwise(l1):
        assert t1 != t2
        assert t2 != t1


def make_typedef(name: str, base_type: Type, constraint: Optional[statements.ExpressionStatement] = None) -> ConstraintType:
    tp = ConstraintType(Namespace("mymodule", parent=Namespace("__root__")), name)
    tp.basetype = base_type
    tp.constraint = (
        constraint
        if constraint is not None
        # typedef <name> as <base_type> matching true
        else statements.Literal(True)
    )
    return tp


def test_issubtype_of_own_python_type() -> None:
    """
    Verify round-trip compatibility of tp.issubtype(to_dsl_type(tp.as_python_type_string()))
    """
    verified_types: set[type[Type]] = set()

    primitives: Sequence[Type] = [Bool(), Integer(), Float(), String()]
    for tp in [
        *primitives,
        *[NullableType(primitive) for primitive in primitives],
        *[make_typedef("mytype", primitive) for primitive in primitives],
        Union(primitives),
        NullableType(Union(primitives)),
        Any(),
        *[TypedList(primitive) for primitive in primitives],
        *[TypedDict(primitive) for primitive in primitives],
        plugins.Null(),
    ]:
        assert tp.issubtype(plugins.to_dsl_type(eval(tp.as_python_type_string())))
        verified_types.add(type(tp))

    all_types = {tp_cls for tp_cls in utils.get_all_subclasses(Type) if not inspect.isabstract(tp_cls)}
    assert verified_types == all_types


def test_issubtype_widening() -> None:
    """
    Verify issubtype accepts wider types and rejects narrower or unrelated ones.
    """
    def verify(narrow: Type, wide: Type) -> None:
        assert narrow.issubtype(wide)
        assert not wide.issubtype(narrow)

    verify(Integer(), Union([Integer(), String()]))
    verify(Integer(), NullableType(Integer()))
    verify(Integer(), Any())

    assert not Integer().issubtype(String())

    verify(plugins.Null(), NullableType(Integer()))

    verify(Union([Integer(), String()]), Union([Integer(), TypedList(Float()), String()]))
    verify(Union([Integer(), String()]), Any())

    verify(make_typedef("mytype", Integer()), Integer())
    verify(make_typedef("mytype", Integer()), NullableType(Integer()))
    verify(make_typedef("mytype", Integer()), Union([Integer(), String()]))
    verify(make_typedef("mytype", Integer()), Any())
    assert not make_typedef("mytype", Integer()).issubtype(String())
    assert not make_typedef("mytype", Integer()).issubtype(make_typedef("othertype", Integer()))
