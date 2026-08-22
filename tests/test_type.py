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
    Integer,
    Literal,
    LiteralDict,
    LiteralList,
    NullableType,
    Number,
    String,
    Type,
    TypedList,
    shorten_value_str,
)
from inmanta.execute.util import NoneValue, Unknown
from inmanta.references import Reference, reference


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


def test_literal_validate_nested() -> None:
    """
    Validate nested literal structures, covering the exact-type fast path in Literal.validate.
    """
    nested = {
        "string": "value",
        "int": 42,
        "float": 1.5,
        "bool": True,
        "none": NoneValue(),
        "list": ["a", 1, [2.5, False], {"k": "v"}],
        "dict": {"deep": {"deeper": [{"leaf": "x"}]}},
    }
    for tp in [Literal(), LiteralDict(), TypedList(LiteralDict())]:
        value = nested if not isinstance(tp, TypedList) else [nested, nested]
        assert tp.validate(value)
    assert LiteralList().validate(["a", {"b": 1}])


def test_literal_validate_slow_path() -> None:
    """
    Values that are not plain Python data must still be validated through the union members.
    """

    class MyStr(str):
        pass

    class MyDict(dict):
        pass

    lit = Literal()
    # subclasses of the fast-path types fall through to the union and remain valid
    assert lit.validate(MyStr("sub"))
    assert lit.validate(MyDict({"a": 1}))
    # unknowns are accepted anywhere in the structure
    assert lit.validate({"a": [Unknown(source=None)]})

    @reference("test::TestLiteralRef")
    class TestReference(Reference[str]):
        def __init__(self, name: str) -> None:
            super().__init__()
            self.name = name

    ref = TestReference("name")
    # set by DynamicProxy.unwrap at the plugin boundary
    ref._model_type = String()
    assert lit.validate({"a": ref})
    assert lit.validate([ref, "x", 1])


def test_literal_validate_failure() -> None:
    """
    An invalid leaf deep inside a large structure raises an error about the leaf itself,
    without embedding the full structure in the message.
    """
    lit = Literal()
    big_sibling = {f"key{i}": "value" * 10 for i in range(1000)}
    with pytest.raises(RuntimeException) as e:
        lit.validate([{"sibling": big_sibling, "bad": object()}])
    assert "expected Literal" in str(e.value)
    assert len(str(e.value)) < 500


def test_shorten_value_str() -> None:
    assert shorten_value_str("short") == "short"
    assert shorten_value_str(42) == "42"
    long_string = "x" * 500
    assert len(shorten_value_str(long_string)) < 250
    big_dict = {f"key{i}": "value" * 20 for i in range(1000)}
    assert len(shorten_value_str(big_dict)) < 250
    assert len(shorten_value_str([big_dict] * 100)) < 250
