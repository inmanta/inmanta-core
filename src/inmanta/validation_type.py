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
from collections import abc
from typing import Annotated, Optional

import pydantic

from inmanta.stable_api import stable_api
from inmanta.types import PrimitiveTypes, PythonRegex


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

    :raises ValueError: When the given fq_type_name is an unsupported type name or for workaround validation
    :raises pydantic.ValidationError: The provided value didn't pass type validation.
    """
    if not (
        fq_type_name.startswith("pydantic.")
        or fq_type_name.startswith("datetime.")
        or fq_type_name.startswith("ipaddress.")
        or fq_type_name.startswith("uuid.")
    ):
        raise ValueError(f"Unknown fq_type_name: {fq_type_name}")

    # workaround for Pydantic v1 python regex support and removal of stricturl
    if fq_type_name == "pydantic.constr":
        t = Annotated[str, PythonRegex(str(validation_parameters["regex"]))]
        validation_parameters = None
    elif fq_type_name == "pydantic.stricturl":
        if "min_length" in validation_parameters and len(value) < int(validation_parameters["min_length"]):
            raise ValueError(f"value does not match the minimal length {validation_parameters['min_length']}")
        if "tld_required" in validation_parameters and bool(validation_parameters["tld_required"]):
            # check if there is a . in the hostname, not if it is an existing tld
            if "." not in pydantic.AnyUrl(value).host:
                raise ValueError(f"value does not have a tld in host part")

        t = Annotated[
            pydantic.AnyUrl,
            pydantic.UrlConstraints(
                max_length=validation_parameters.get("max_length", None),
                allowed_schemes=validation_parameters.get("allowed_schemes", None),
            ),
        ]
        validation_parameters = None
    else:
        module_name, type_name = fq_type_name.split(".", 1)
        module = importlib.import_module(module_name)
        t = getattr(module, type_name)

    # Construct pydantic model
    if validation_parameters is not None:
        model = pydantic.create_model(fq_type_name, value=(t(**validation_parameters), ...))
    else:
        model = pydantic.create_model(fq_type_name, value=(t, ...))

    # Do validation
    model(value=value)
