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

import contextlib
import uuid
from typing import Optional

import pydantic
import pytest

from inmanta import compiler
from inmanta.validation_type import HashKeyContainer, _cachable_validate_type, regex_string, validate_type


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


@pytest.mark.parametrize(
    "regex, value, is_valid",
    [
        ("^abc.*", "abc", True),
        ("^abc.*", "abcd", True),
        ("^abc.*", "xabc", False),
        ("^xabc.*", "xabc", True),
        ("^abc.*", "ab", False),
        (".*", True, False),
    ],
)
def test_regex_string(regex: str, value: object, is_valid: bool) -> None:
    with contextlib.nullcontext() if is_valid else pytest.raises(pydantic.ValidationError):
        pydantic.TypeAdapter(regex_string(regex)).validate_python(value)


def test_cache(snippetcompiler):
    # Verify we use the cache
    _cachable_validate_type.cache_clear()
    snippetcompiler.setup_for_snippet(
        """
        import std

        entity Tester:
          std::alfanum testfield
          std::any_http_url testfield3
        end

        implement Tester using std::none
        """
        + """
        Tester(testfield="A", testfield3="http://example.com/x")
        """ * 20
    )

    compiler.do_compile()
    # For each field: One miss, 19 hits
    assert _cachable_validate_type.cache_info().hits == 19 * 2
    assert _cachable_validate_type.cache_info().misses == 2


@pytest.mark.parametrize(
    "attr_type,validation_parameters,schema",
    [
        ("pydantic.constr", {"regex": "^test.*$"}, {"pattern": "^test.*$", "type": "string"}),
        (
            "pydantic.constr",
            {"regex": "^test.*$", "max_length": 10},
            {"maxLength": 10, "pattern": "^test.*$", "type": "string"},
        ),
    ],
)
def test_schema(attr_type: str, validation_parameters: dict[str, object], schema: dict[str, str | int]) -> None:
    type_validator = _cachable_validate_type(attr_type, HashKeyContainer(validation_parameters))
    assert type_validator.json_schema() == schema
