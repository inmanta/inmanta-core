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

# This file defines named type definition for the Inmanta code base

import builtins
import datetime
import uuid
from collections.abc import Coroutine, Generator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Callable, NewType, Optional, Union

import pydantic
import typing_inspect

from inmanta.stable_api import stable_api

if TYPE_CHECKING:
    # Include imports from other modules here and use the quoted annotation in the definition to prevent import loops
    from inmanta.protocol.common import ReturnValue  # noqa: F401


# Typing of dataclass.* methods relies entirely on the definition in typeshed that only exists during typechecking.
# This ensures that our code works during typechecking and at runtime.
if not TYPE_CHECKING:
    DataclassProtocol = object
else:
    import _typeshed

    DataclassProtocol = _typeshed.DataclassInstance


def api_boundary_datetime_normalizer(value: datetime.datetime) -> datetime.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    else:
        return value


@stable_api
class DateTimeNormalizerModel(pydantic.BaseModel):
    """
    A model that normalizes all datetime values to be timezone aware. Assumes that all naive timestamps represent UTC times.
    """

    @pydantic.field_validator("*", mode="after")
    @classmethod
    def validator_timezone_aware_timestamps(cls: type, value: object) -> object:
        """
        Ensure that all datetime times are timezone aware.
        """
        if isinstance(value, datetime.datetime):
            return api_boundary_datetime_normalizer(value)
        else:
            return value


@stable_api
class BaseModel(DateTimeNormalizerModel):
    """
    Base class for all data objects in Inmanta
    """


# kept for backwards compatibility
StrictNonIntBool = pydantic.StrictBool


type AsyncioGenerator[R] = Generator[object, None, R]
"""
Asyncio-compatible generator as returned from a sync function, e.g. __await__.
"""
type AsyncioCoroutine[R] = Coroutine[object, None, R]
"""
Coroutine for use with asyncio, where we don't care about yield and send types.
"""


def issubclass(sub: type, super: Union[type, tuple[type, ...]]) -> bool:
    """
    Alternative issubclass implementation that interpretes instances of NewType for the first argument as their super type.
    """
    if typing_inspect.is_new_type(sub):
        return issubclass(sub.__supertype__, super)
    return builtins.issubclass(sub, super)


PrimitiveTypes = Optional[uuid.UUID | bool | int | float | datetime.datetime | str]
type SimpleTypes = BaseModel | PrimitiveTypes

JsonType = dict[str, Any]
ReturnTupple = tuple[int, Optional[JsonType]]
type StrictJson = dict[str, StrictJson] | list[StrictJson] | str | int | float | bool | None

type StrMapping[T] = Mapping[str, T] | Mapping[ResourceIdStr, T] | Mapping[ResourceVersionIdStr, T]

type SinglePageTypes = SimpleTypes | StrMapping[ArgumentTypes]
# only simple types allowed within list args, not dicts or lists.
# Typed as Sequence for necessity (covariance), though runtime checks and method overloads require list in practice.
# This is an unfortunate limitation of the Python type system, related to str being a Sequence, among other things.
# Luckily, list is the more conventional return type for method annotations, so as long as that convention is followed,
# it should not cause any trouble. And if it does after all, the only consequence will be that paging will not be supported
# through the Python client.
type PageableTypes = Sequence[SimpleTypes]

type ArgumentTypes = SinglePageTypes | PageableTypes
type ReturnTypes = SinglePageTypes | PageableTypes

type MethodReturn = ReturnTypes | "ReturnValue[ReturnTypes]"
type MethodType = Callable[..., MethodReturn]

type Apireturn = int | ReturnTupple | "ReturnValue[ReturnTypes]" | "ReturnValue[None]" | ReturnTypes
type Warnings = Optional[list[str]]
type HandlerType = Callable[..., AsyncioCoroutine[Apireturn]]


ResourceVersionIdStr = NewType("ResourceVersionIdStr", str)  # Part of the stable API
"""
    The resource id with the version included.
"""

ResourceIdStr = NewType("ResourceIdStr", str)  # Part of the stable API
"""
    The resource id without the version
"""

ResourceType = NewType("ResourceType", str)
"""
    The type of the resource
"""


type ResourceSets[R] = dict[Optional[str], list[R]]
