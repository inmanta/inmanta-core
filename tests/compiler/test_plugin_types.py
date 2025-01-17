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
from typing import Any, Mapping, Sequence, Union, Optional

import pytest

import inmanta.ast.type as inmanta_type
from inmanta.ast import RuntimeException
from inmanta.logging import Options
from inmanta.plugins import Null, to_dsl_type


def test_conversion():
    assert inmanta_type.Integer() == to_dsl_type(int)
    assert inmanta_type.Float() == to_dsl_type(float)
    assert inmanta_type.NullableType(inmanta_type.Float()) == to_dsl_type(float | None)
    assert inmanta_type.List() == to_dsl_type(list)
    assert inmanta_type.TypedList(inmanta_type.String()) == to_dsl_type(list[str])
    assert inmanta_type.TypedList(inmanta_type.String()) == to_dsl_type(Sequence[str])
    assert inmanta_type.List() == to_dsl_type(Sequence)
    assert inmanta_type.List() == to_dsl_type(collections.abc.Sequence)
    assert inmanta_type.TypedList(inmanta_type.String()) == to_dsl_type(collections.abc.Sequence[str])
    assert inmanta_type.TypedDict(inmanta_type.Type()) == to_dsl_type(dict)
    assert inmanta_type.TypedDict(inmanta_type.Type()) == to_dsl_type(Mapping)
    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type(dict[str, str])
    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type(Mapping[str, str])

    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type(collections.abc.Mapping[str, str])

    # Union types
    assert inmanta_type.Integer() == to_dsl_type(Union[int])
    assert inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()]) == to_dsl_type(Union[int, str])
    assert inmanta_type.NullableType(
        inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])
    ) == to_dsl_type(Union[None, int, str])
    assert inmanta_type.NullableType(
        inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])
    ) == to_dsl_type(Optional[Union[int, str]])
    assert inmanta_type.NullableType(
        inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])
    ) == to_dsl_type(Union[int, str] | None)
    assert inmanta_type.NullableType(
        inmanta_type.Union([inmanta_type.Integer(), inmanta_type.String()])
    ) == to_dsl_type(None | Union[int, str])

    assert Null() == to_dsl_type(Union[None])

    assert isinstance(to_dsl_type(Any), inmanta_type.Type)

    with pytest.raises(RuntimeException):
        to_dsl_type(dict[int, int])

    with pytest.raises(RuntimeException):
        to_dsl_type(set[str])

    class CustomList[T](list[T]):
        pass

    class CustomDict[K, V](Mapping[K, V]):
        pass

    with pytest.raises(RuntimeException):
        to_dsl_type(CustomList[str])

    with pytest.raises(RuntimeException):
        to_dsl_type(CustomDict[str, str])
