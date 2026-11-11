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

import pytest
from more_itertools import pairwise

from inmanta.ast import Location, Namespace, RuntimeException
from inmanta.ast.attribute import Attribute
from inmanta.ast.entity import Entity
from inmanta.ast.type import (
    TYPES,
    Bool,
    Float,
    Integer,
    Literal,
    LiteralDict,
    LiteralList,
    NullableType,
    Number,
    String,
    Type,
    TypedDict,
    TypedList,
    Union,
)
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


@pytest.mark.parametrize("base_type", [Bool, Integer, LiteralDict, LiteralList, Number, String])
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


def _any_member_accepts(union: Union, value: object) -> bool:
    for member in union.types:
        try:
            if member.validate(value):
                return True
        except RuntimeException:
            pass
    return False


@pytest.mark.parametrize(
    "union",
    [
        Literal(),
        Union([Integer(), String()]),
        Union([NullableType(Float()), Bool()]),
        Union([Number(), TypedList(String())]),
        Union([Float(), TypedDict(Integer())]),
    ],
)
@pytest.mark.parametrize(
    "value",
    ["a", 1, 1.5, True, False, NoneValue(), [1, "a"], ["a"], {"a": 1}, {"a": [1, {"b": "c"}]}, {"a": object()}, object()],
)
def test_union_validate_accepts_iff_a_member_accepts(union: Union, value: object) -> None:
    """
    A union accepts a value exactly when at least one of its member types accepts it.
    """
    if _any_member_accepts(union, value):
        assert union.validate(value)
    else:
        with pytest.raises(RuntimeException):
            union.validate(value)


def test_union_validate_skips_primitive_members_that_reject_by_type(monkeypatch) -> None:
    """
    Primitive members that reject a value based on its Python type are not tried, so they raise no exception.
    """
    tried: list[str] = []
    for primitive in (Float, Number, Bool):
        original = primitive.validate

        def recording_validate(self: Type, value: object, original=original, name=primitive.__name__) -> bool:
            tried.append(name)
            return original(self, value)

        monkeypatch.setattr(primitive, "validate", recording_validate)

    assert Literal().validate("a")
    assert Literal().validate({"a": ["b", {"c": "d"}]})
    assert tried == []


class FormatCountingStr(str):
    """
    A string that counts how often it is formatted into a message.
    """

    formatted: int = 0

    def __format__(self, format_spec: str) -> str:
        FormatCountingStr.formatted += 1
        return super().__format__(format_spec)


def test_union_validate_does_not_format_rejected_values() -> None:
    """
    The members of a union that reject a value don't format it into their error message unless that message is read.
    """
    FormatCountingStr.formatted = 0
    value = FormatCountingStr("a")
    assert Union([Number(), Bool(), TypedList(String()), TypedDict(String()), String()]).validate(value)
    assert FormatCountingStr.formatted == 0

    with pytest.raises(RuntimeException) as exc_info:
        Number().validate(value)
    assert FormatCountingStr.formatted == 0
    assert exc_info.value.get_message() == "Invalid value 'a', expected number"
    assert str(exc_info.value) == "Invalid value 'a', expected number"
    assert FormatCountingStr.formatted == 1
