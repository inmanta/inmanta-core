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

from typing import Tuple

import pytest

from inmanta.ast import Namespace, RuntimeException
from inmanta.ast.attribute import Attribute
from inmanta.ast.entity import Entity
from inmanta.ast.type import TYPES, Integer, NullableType, Type, TypedList
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
    attribute: Attribute = Attribute(entity, Integer(), "my_attribute", multi, nullable)

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
