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

import typing
from functools import reduce
from typing import Tuple

import pytest
from more_itertools import pairwise

from inmanta.ast import Location, Namespace, RuntimeException
from inmanta.ast.attribute import Attribute
from inmanta.ast.entity import Entity
from inmanta.ast.type import TYPES, Bool, Integer, LiteralDict, LiteralList, NullableType, Number, String, Type, TypedList
from inmanta.execute.util import NoneValue


@pytest.mark.parametrize("base_type_string", TYPES.keys())
@pytest.mark.parametrize("multi", [True, False])
@pytest.mark.parametrize("nullable", [True, False])
def test_dsl_types_type_string(base_type_string: str, multi: bool, nullable: bool):
    def apply_multi_if(tp: Type, type_string: str) -> Tuple[Type, str]:
        return (TypedList(tp), "%s[]" % type_string) if multi else (tp, type_string)

    def apply_nullable_if(tp: Type, type_string: str) -> Tuple[Type, str]:
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


def create_type(base_type: typing.Type[Type], multi: bool = False, nullable: bool = False) -> Type:
    base: Type = base_type()
    transformations: typing.List[typing.Callable[[Type], Type]] = [
        lambda t: TypedList(t) if multi else t,
        lambda t: NullableType(t) if nullable else t,
    ]
    return reduce(lambda acc, t: t(acc), transformations, base)


@pytest.mark.parametrize("base_type", [Bool, Integer, LiteralDict, LiteralList, Number, String])
def test_type_equals_simple(base_type: typing.Type[Type]) -> None:
    assert create_type(base_type) == create_type(base_type)


def test_type_equals_transformations() -> None:
    def all_transformations() -> typing.List[Type]:
        return [
            create_type(base_type, multi, nullable)
            for multi in [True, False]
            for nullable in [True, False]
            for base_type in [Integer, Number]
        ]

    l1: typing.List[Type] = all_transformations()
    l2: typing.List[Type] = all_transformations()
    assert l1 == l2
    for t1, t2 in pairwise(l1):
        assert t1 != t2
        assert t2 != t1
