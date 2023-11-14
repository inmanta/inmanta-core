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
from collections import abc
from typing import Annotated, Optional

import pydantic

from inmanta.stable_api import stable_api
from inmanta.types import PrimitiveTypes, PythonRegex


@stable_api
def parametrize_type(
    base_type: Type[object] | abc.Callable[..., Type[object]], type_name: str, validation_parameters: Optional[abc.Mapping[str, object]] = None
) -> Type[object]:
    # TODO: docstring
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
        * pydantic.stricturl:
            min_length: int = 1
            max_length: int = 2 ** 16
            tld_required: bool = True
            allowed_schemes: Optional[Set[str]] = None

    :raises ValueError: When the given fq_type_name is an unsupported type name or when otherwise invalid parameters are
        passed.
    :raises TypeError: When the given validation parameters are not valid with respect to the requested type.
    """
    custom_annotations: object = []
    validation_parameters: dict[str, object] = validation_parameters.copy() if validation_parameters is not None else {}

    # workaround for Pydantic v1 python regex support and removal of stricturl
    if base_type is pydantic.constr and validation_parameters is not None:
        # TODO: add tests for regex + other constr parameters -> tests/test_validation_type.py
        regex: object = validation_parameters.get("regex", None)
        if regex is not None:
            custom_annotations.append(PythonRegex(str(validation_parameters["regex"])))
        del validation_parameters["regex"]

    parametrized_type: object
    if inspect.isroutine(base_type):
        # TODO: test with non-routine callable (e.g. uuid.UUID)
        parametrized_type = base_type(**validation_parameters)
    elif validation_parameters is not None:
        raise ValueError(
            f"validate_type got validation parameters {validation_parameters}"
            f" but validation type {type_name} is not parametrized"
        )
    else:
        parametrized_type = base_type

    return parametrized_type if not custom_annotations else Annotated[parametrized_type, *custom_annotations]


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
        * pydantic.stricturl:
            min_length: int = 1
            max_length: int = 2 ** 16
            tld_required: bool = True
            allowed_schemes: Optional[Set[str]] = None

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

    module_name, type_name = fq_type_name.split(".", 1)
    module = importlib.import_module(module_name)
    requested_type: object = getattr(module, type_name)

    validation_type: Type[object] = pydantic.TypeAdapter(parametrize_type(requested_type, fq_type_name, validation_parameters))
    validation_type.validate_python(value)
