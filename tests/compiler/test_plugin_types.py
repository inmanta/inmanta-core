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
from typing import Annotated, Any, Mapping, Sequence, Union

import pytest

import inmanta.ast.type as inmanta_type
from inmanta.ast import Namespace, Range, RuntimeException
from inmanta.plugins import Null, to_dsl_type
from inmanta.plugins.typing import InmantaType


def test_conversion(caplog):
    """
    Test behaviour of to_dsl_type function.
    """
    namespace = Namespace("dummy-namespace")
    namespace.primitives = inmanta_type.TYPES

    location: Range = Range("test", 1, 1, 2, 1)

    assert inmanta_type.NullableType(inmanta_type.Integer()) == to_dsl_type(
        Annotated[int | None, "something"], location, namespace
    )

    assert inmanta_type.TypedDict(inmanta_type.Type()) == to_dsl_type(
        Annotated[dict[str, int], InmantaType("dict")], location, namespace
    )
    assert inmanta_type.Integer() == to_dsl_type(int, location, namespace)
    assert inmanta_type.Float() == to_dsl_type(float, location, namespace)
    assert inmanta_type.NullableType(inmanta_type.Float()) == to_dsl_type(float | None, location, namespace)
    assert inmanta_type.List() == to_dsl_type(list, location, namespace)
    assert inmanta_type.TypedList(inmanta_type.String()) == to_dsl_type(list[str], location, namespace)
    assert inmanta_type.TypedList(inmanta_type.String()) == to_dsl_type(Sequence[str], location, namespace)
    assert inmanta_type.List() == to_dsl_type(Sequence, location, namespace)
    assert inmanta_type.List() == to_dsl_type(collections.abc.Sequence, location, namespace)
    assert inmanta_type.TypedList(inmanta_type.String()) == to_dsl_type(collections.abc.Sequence[str], location, namespace)
    assert inmanta_type.TypedDict(inmanta_type.Type()) == to_dsl_type(dict, location, namespace)
    assert inmanta_type.TypedDict(inmanta_type.Type()) == to_dsl_type(Mapping, location, namespace)
    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type(dict[str, str], location, namespace)
    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type(Mapping[str, str], location, namespace)

    assert inmanta_type.TypedDict(inmanta_type.String()) == to_dsl_type(collections.abc.Mapping[str, str], location, namespace)

    assert Null() == to_dsl_type(Union[None], location, namespace)

    assert isinstance(to_dsl_type(Any, location, namespace), inmanta_type.Type)

    with pytest.raises(RuntimeException):
        to_dsl_type(dict[int, int], location, namespace)

    with pytest.raises(RuntimeException):
        to_dsl_type(set[str], location, namespace)

    class CustomList[T](list[T]):
        pass

    class CustomDict[K, V](Mapping[K, V]):
        pass

    with pytest.raises(RuntimeException):
        to_dsl_type(CustomList[str], location, namespace)

    with pytest.raises(RuntimeException):
        to_dsl_type(CustomDict[str, str], location, namespace)

    # Check that a warning is produced when implicit cast to 'Any'
    caplog.clear()
    to_dsl_type(complex, location, namespace)
    warning_message = (
        "InmantaWarning: Python type <class 'complex'> was implicitly cast to 'Any' because no matching type "
        "was found in the Inmanta DSL. Please refer to the documentation for an overview of supported types at the "
        "plugin boundary."
    )
    assert warning_message in caplog.messages
