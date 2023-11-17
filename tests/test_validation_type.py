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
import uuid
from typing import Optional

import pydantic
import pytest

from inmanta.validation_type import validate_type


@pytest.mark.parametrize(
    "attr_type,value,validation_parameters,is_valid",
    [
        ("pydantic.condecimal", 8, {"gt": 0, "lt": 10}, True),
        ("pydantic.condecimal", 8, {"gt": 0, "lt": 5}, False),
        ("pydantic.confloat", 1.5, {"multiple_of": 0.5}, True),
        ("pydantic.confloat", 1.5, {"multiple_of": 0.2}, False),
        ("pydantic.conint", 4, {"ge": 4}, True),
        ("pydantic.conint", 4, {"ge": 5}, False),
        ("pydantic.constr", "test123", {"regex": "^test.*$"}, True),
        ("pydantic.constr", "test123", {"regex": "^tst.*$"}, False),
        ("pydantic.constr", "test123", {"regex": "^(tst.*$"}, False),
        # constr with non-regex parameters
        ("pydantic.constr", "nomatch", {"regex": "^test.*$", "max_length": 10}, False),
        ("pydantic.constr", "testbuttoolong", {"regex": "^test.*$", "max_length": 10}, False),
        ("pydantic.constr", "testgood", {"regex": "^test.*$", "max_length": 10}, True),
        ("pydantic.constr", "noregex", {"max_length": 10}, True),
        ("pydantic.constr", "noregexbuttoolong", {"max_length": 10}, False),
        ("uuid.UUID", uuid.uuid4(), {}, True),
    ],
)
def test_type_validation(attr_type: str, value: str, validation_parameters: dict[str, object], is_valid: bool) -> None:
    """
    Test the behavior of the inmanta.validation_type.validate_type method.
    """
    validation_error: Optional[pydantic.ValidationError] = None
    try:
        validate_type(attr_type, value, validation_parameters)
    except (pydantic.ValidationError, ValueError) as e:
        validation_error = e
    assert (validation_error is None) is is_valid, validation_error
