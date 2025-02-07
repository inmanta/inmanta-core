"""
Copyright 2025 Inmanta

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

import collections.abc
from typing import Annotated, Any, Mapping, Optional, Sequence, Union

import pytest

import inmanta.ast.type as inmanta_type
from inmanta.ast import Namespace, Range, RuntimeException
from inmanta.plugins import ModelType, Null, to_dsl_type


def test_conversion(caplog):
    """
    Test behaviour of to_dsl_type function.
    """
    namespace = Namespace("dummy-namespace")
    namespace.primitives = inmanta_type.TYPES

    location: Range = Range("test", 1, 1, 2, 1)

    def to_dsl_type_simple(python_type: type[object]) -> inmanta_type.Type:
        return to_dsl_type(python_type, location, namespace)

    assert inmanta_type.NullableType(inmanta_type.Integer()) == to_dsl_type_simple(Annotated[int | None, "something"])
    # Union type should be ignored in favor of our InmantaType
    assert inmanta_type.TypedDict(inmanta_type.Type()) == to_dsl_type_simple(Annotated[int | None, InmantaType("dict")])

    assert inmanta_type.TypedDict(inmanta_type.Type()) == to_dsl_type_simple(Annotated[dict[str, int], ModelType["dict"]])
    assert inmanta_type.Integer() == to_dsl_type_simple(int)
    assert inmanta_type.Float() == to_dsl_type_simple(float)
    assert inmanta_type.NullableType(inmanta_type.Float()) == to_dsl_type_simple(float | None)
    assert inmanta_type.List() == to_dsl_type_simple(list)
    assert inmanta_type.TypedList(inmanta_type.String()) == to_dsl_type_simple(list[str])
    assert inmanta_type.TypedList(inmanta_type.String()) == to_dsl_type_simple(Sequence[str])
    assert inmanta_type.List() == to_dsl_type_simple(Sequence)
    assert inmanta_type.List() == to_dsl_type_simple(collections.abc.Sequence)
    assert inmanta_type.TypedList(inmanta_type.String()) == to_dsl_type_simple(collections.abc.Sequence[str])
    assert inmanta_type.TypedDict(inmanta_type.Type()) == to_dsl_type_simple(dict)
    assert inmanta_type.TypedDict(inmanta_type.Type()) == to_dsl_type_simple(Mapping)
    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type_simple(dict[str, str])
    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type_simple(Mapping[str, str])

    # Union types
    assert inmanta_type.Integer() == to_dsl_type_simple(Union[int])
    assert inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()]) == to_dsl_type_simple(Union[int, str])
    assert inmanta_type.NullableType(inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])) == to_dsl_type_simple(
        Union[None, int, str]
    )
    assert inmanta_type.NullableType(inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])) == to_dsl_type_simple(
        Optional[Union[int, str]]
    )
    assert inmanta_type.NullableType(inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])) == to_dsl_type_simple(
        Union[int, str] | None
    )
    assert inmanta_type.NullableType(inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])) == to_dsl_type_simple(
        None | Union[int, str]
    )
    # verify that nested unions are flattened and nested None values are considered for NullableType
    assert inmanta_type.NullableType(
        inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String(), inmanta_type.Float()])
    ) == to_dsl_type_simple(Union[int, Union[str, Union[float, None]]])

    # Union types
    assert inmanta_type.Integer() == to_dsl_type_simple(Union[int])
    assert inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()]) == to_dsl_type_simple(Union[int, str])
    assert inmanta_type.NullableType(inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])) == to_dsl_type_simple(
        Union[None, int, str]
    )
    assert inmanta_type.NullableType(inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])) == to_dsl_type_simple(
        Optional[Union[int, str]]
    )
    assert inmanta_type.NullableType(inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])) == to_dsl_type_simple(
        Union[int, str] | None
    )
    assert inmanta_type.NullableType(inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])) == to_dsl_type_simple(
        None | Union[int, str]
    )
    # verify that nested unions are flattened and nested None values are considered for NullableType
    assert inmanta_type.NullableType(
        inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String(), inmanta_type.Float()])
    ) == to_dsl_type_simple(Union[int, Union[str, Union[float, None]]])

    assert Null() == to_dsl_type_simple(Union[None])
    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type_simple(collections.abc.Mapping[str, str])

    assert Null() == to_dsl_type_simple(Union[None])

    assert isinstance(to_dsl_type_simple(Any), inmanta_type.Type)

    with pytest.raises(RuntimeException):
        to_dsl_type_simple(dict[int, int])

    with pytest.raises(RuntimeException):
        to_dsl_type_simple(set[str])

    class CustomList[T](list[T]):
        pass

    class CustomDict[K, V](Mapping[K, V]):
        pass

    with pytest.raises(RuntimeException):
        to_dsl_type_simple(CustomList[str])

    with pytest.raises(RuntimeException):
        to_dsl_type_simple(CustomDict[str, str])

    # Check that a warning is produced when implicit cast to 'Any'
    caplog.clear()
    to_dsl_type_simple(complex)
    warning_message = (
        "InmantaWarning: Python type <class 'complex'> was implicitly cast to 'Any' because no matching type "
        "was found in the Inmanta DSL. Please refer to the documentation for an overview of supported types at the "
        "plugin boundary."
    )
    assert warning_message in caplog.messages
