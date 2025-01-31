"""
Copyright 2023 Inmanta

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

import importlib
import inspect
import re
from collections import abc
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Optional

import pydantic

from inmanta.execute.proxy import DictProxy
from inmanta.stable_api import stable_api
from inmanta.types import PrimitiveTypes
from pydantic_core import CoreSchema, PydanticCustomError, core_schema


@dataclass
class Regex:
    """Custom regex class that uses python regexes. This implementation also ensure that a json schema is generated
    for the regex.
    """

    pattern: str

    def __get_pydantic_core_schema__(self, source_type: object, handler: pydantic.GetCoreSchemaHandler) -> CoreSchema:
        regex = re.compile(self.pattern)

        def match(v: str) -> str:
            if not regex.match(v):
                raise PydanticCustomError(
                    "string_pattern_mismatch",
                    "String should match pattern '{pattern}'",
                    {"pattern": self.pattern},
                )
            return v

        return core_schema.no_info_after_validator_function(
            match,
            handler(source_type),
        )

    def __get_pydantic_json_schema__(
        self, core_schema: CoreSchema, handler: pydantic.GetJsonSchemaHandler
    ) -> pydantic.json_schema.JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema["pattern"] = self.pattern
        return json_schema

    def __hash__(self) -> int:
        """The hash of the type is equal to the hash of the regex. Typing does deduplication, requiring this to be hashable."""
        return hash(self.pattern)


@stable_api
def regex_string(regex: str) -> object:
    """
    Returns a pydantic-compatible string type that validates values with the given Python regex.
    """
    return Annotated[str, Regex(regex)]


@stable_api
def parametrize_type(
    base_type: type[object] | abc.Callable[..., type[object]],
    validation_parameters: Optional[abc.Mapping[str, object]] = None,
    *,
    type_name: Optional[str] = None,
) -> object:
    """
    Add validation parameters to the given type, if it supports any. Returns the parametrized type as a pydantic compatible
    type, possibly through the use of typing.Annotated.

    :param base_type: The type to parametrize. Either a type or a callable that produces a type when parametrized.
    :param validation_parameters: Additional parameters to construct the validation type. Should only be passed if base_type
        is a type generator function.
    :param type_name: Optionally, the human-readable name of the type, for error messages.

    :raises ValueError: When invalid parameters are passed.
    :raises TypeError: When the given validation parameters are not valid with respect to the requested type.
    """
    type_name = type_name if type_name is not None else repr(base_type)

    custom_annotations: list[object] = []
    validation_parameters = dict(validation_parameters) if validation_parameters is not None else {}

    # backwards compatibility layer for Pydantic v1 python regex support
    if base_type is pydantic.constr and validation_parameters is not None and "regex" in validation_parameters:
        regex: object = validation_parameters["regex"]
        if regex is not None:
            custom_annotations.append(Regex(str(regex)))
        del validation_parameters["regex"]

    parametrized_type: object
    if inspect.isroutine(base_type):
        parametrized_type = base_type(**validation_parameters)
    elif validation_parameters:
        raise ValueError(f"got validation parameters {validation_parameters} but {type_name} does not accept parameters")
    else:
        parametrized_type = base_type

    return parametrized_type if not custom_annotations else Annotated[parametrized_type, *custom_annotations]


class HashKeyContainer:
    def __init__(self, validation_parameters: Optional[abc.Mapping[str, object]] = None):
        if isinstance(validation_parameters, DictProxy):
            validation_parameters = validation_parameters.unwrap(validation_parameters)

        self.validation_parameters = validation_parameters

    def __hash__(self) -> int:
        # We favor speed over accuracy here
        # We mostly get calls from the model, where the dict is effectively the same
        return id(self.validation_parameters)

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, HashKeyContainer)
        return self.validation_parameters == other.validation_parameters


@stable_api
def validate_type(
    fq_type_name: str, value: PrimitiveTypes, validation_parameters: Optional[abc.Mapping[str, object]] = None
) -> None:
    """
    Check whether `value` satisfies the constraints of type `fq_type_name`. When the given type (fq_type_name)
    requires validation_parameters, they can be provided using the optional `validation_parameters` argument.

    The following types require validation_parameters:

        * pydantic.condecimal:
            gt: Decimal = None
            ge: Decimal = None
            lt: Decimal = None
            le: Decimal = None
            max_digits: int = None
            decimal_places: int = None
            multiple_of: Decimal = None
        * pydantic.confloat and pydantic.conint:
            gt: float = None
            ge: float = None
            lt: float = None
            le: float = None
            multiple_of: float = None,
        * pydantic.constr:
            min_length: int = None
            max_length: int = None
            curtail_length: int = None (Only verify the regex on the first curtail_length characters)
            regex: str = None          (The regex is verified via Pattern.match())
            pattern: str = None        (The built-in pattern support of pydantic)

    :raises ValueError: When the given fq_type_name is an unsupported type name or when otherwise invalid parameters are
        passed.
    :raises TypeError: When the given validation parameters are not valid with respect to the requested type.
    :raises pydantic.ValidationError: The provided value didn't pass type validation.
    """
    if not (
        fq_type_name.startswith("pydantic.")
        or fq_type_name.startswith("datetime.")
        or fq_type_name.startswith("ipaddress.")
        or fq_type_name.startswith("uuid.")
    ):
        raise ValueError(f"Unknown fq_type_name: {fq_type_name}")
    validation_type = _cachable_validate_type(fq_type_name, HashKeyContainer(validation_parameters))
    validation_type.validate_python(value)


@lru_cache(maxsize=4096)
def _cachable_validate_type(fq_type_name: str, validation_parameters: HashKeyContainer) -> pydantic.TypeAdapter[object]:
    module_name, type_name = fq_type_name.split(".", 1)
    module = importlib.import_module(module_name)
    requested_type: object = getattr(module, type_name)

    validation_type: pydantic.TypeAdapter[object] = pydantic.TypeAdapter(
        parametrize_type(requested_type, validation_parameters.validation_parameters, type_name=fq_type_name)
    )

    return validation_type
