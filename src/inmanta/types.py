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
import uuid
from collections.abc import Coroutine, Mapping, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, NewType, Optional, Union

import pydantic
import typing_inspect

if TYPE_CHECKING:
    # Include imports from other modules here and use the quoted annotation in the definition to prevent import loops
    from inmanta.data.model import BaseModel  # noqa: F401
    from inmanta.protocol.common import ReturnValue  # noqa: F401


# Typing of dataclass.* methods relies entirely on the definition in typeshed that only exists during typechecking.
# This ensures that our code works during typechecking and at runtime.
if not TYPE_CHECKING:
    DataclassProtocol = object
else:
    import _typeshed

    DataclassProtocol = _typeshed.DataclassInstance

# kept for backwards compatibility
StrictNonIntBool = pydantic.StrictBool


def issubclass(sub: type, super: Union[type, tuple[type, ...]]) -> bool:
    """
    Alternative issubclass implementation that interpretes instances of NewType for the first argument as their super type.
    """
    if typing_inspect.is_new_type(sub):
        return issubclass(sub.__supertype__, super)
    return builtins.issubclass(sub, super)


PrimitiveTypes = Optional[uuid.UUID | bool | int | float | datetime | str]
SimpleTypes = Union["BaseModel", PrimitiveTypes]

JsonType = dict[str, Any]
ReturnTupple = tuple[int, Optional[JsonType]]
type StrictJson = dict[str, StrictJson] | list[StrictJson] | str | int | float | bool | None


ArgumentTypes = Union[SimpleTypes, Sequence[SimpleTypes], Mapping[str, SimpleTypes]]

ReturnTypes = Optional[ArgumentTypes]
MethodReturn = Union[ReturnTypes, "ReturnValue[ReturnTypes]"]
MethodType = Callable[..., MethodReturn]

Apireturn = Union[int, ReturnTupple, "ReturnValue[ReturnTypes]", "ReturnValue[None]", ReturnTypes]
Warnings = Optional[list[str]]
HandlerType = Callable[..., Coroutine[Any, Any, Apireturn]]


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
