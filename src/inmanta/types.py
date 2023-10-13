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
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

import typing_inspect
from pydantic import errors, types

if TYPE_CHECKING:
    # Include imports from other modules here and use the quoted annotation in the definition to prevent import loops
    from inmanta.data.model import BaseModel  # noqa: F401
    from inmanta.protocol.common import ReturnValue  # noqa: F401

import re
from dataclasses import dataclass
from typing import Any

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue

from pydantic_core import CoreSchema, PydanticCustomError, core_schema


@dataclass
class PythonRegex:
    """A pydantic regex type use for constrained strings that use a regex instead of pattern"""

    regex: str

    def __get_pydantic_core_schema__(self, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        try:
            regex = re.compile(self.regex)
        except re.error as e:
            raise ValueError(f"Unable to compile regex {self.regex}: {e}")

        def match(v: str) -> str:
            if not regex.match(v):
                raise PydanticCustomError(
                    "string_pattern_mismatch",
                    "String should match regex '{regex}'",
                    {"regex": self.regex},
                )
            return v

        return core_schema.no_info_after_validator_function(
            match,
            handler(source_type),
        )

    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.regex
        return json_schema


class StrictNonIntBool(object):
    """
    StrictNonIntBool to allow for bools which are not type-coerced and that are not a subclass of int
    Based on StrictBool from pydantic
    """

    @classmethod
    def __get_validators__(cls) -> "types.CallableGenerator":
        yield cls.validate

    @classmethod
    def validate(cls, value: Any, info: Any) -> bool:
        """
        Ensure that we only allow bools.
        """
        if isinstance(value, bool):
            return value

        raise errors.StrictBoolError()

    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema["type"] = "boolean"
        return json_schema


def issubclass(sub: Type, super: Union[Type, Tuple[Type, ...]]) -> bool:
    """
    Alternative issubclass implementation that interpretes instances of NewType for the first argument as their super type.
    """
    if typing_inspect.is_new_type(sub):
        return issubclass(sub.__supertype__, super)
    return builtins.issubclass(sub, super)


PrimitiveTypes = Union[uuid.UUID, StrictNonIntBool, int, float, datetime, str]
SimpleTypes = Union["BaseModel", PrimitiveTypes]

JsonType = Dict[str, Any]
ReturnTupple = Tuple[int, Optional[JsonType]]

ArgumentTypes = Union[SimpleTypes, Sequence[SimpleTypes], Mapping[str, SimpleTypes]]

ReturnTypes = Optional[ArgumentTypes]
MethodReturn = Union[ReturnTypes, "ReturnValue[ReturnTypes]"]
MethodType = Callable[..., MethodReturn]

Apireturn = Union[int, ReturnTupple, "ReturnValue[ReturnTypes]", "ReturnValue[None]", ReturnTypes]
Warnings = Optional[List[str]]
HandlerType = Callable[..., Coroutine[Any, Any, Apireturn]]
