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
import datetime
import uuid
from typing import Any, Dict, Union

import pydantic


def test_method_validation() -> None:
    """Test how the method validation works using pydantic"""
    validator = pydantic.create_model(
        "set_setting_arguments",
        a=(str, None),
        b=(uuid.UUID, None),
        c=(Union[uuid.UUID, bool, int, float, datetime.datetime, str, Dict[str, Any]], None),
        __base__=pydantic.BaseModel,
    )

    data = {"a": "auto_deploy", "b": "3f828d00-5dda-41f6-940c-9d72ae62b0a4", "c": True}

    validator(**data)


def test_float_str() -> None:
    """Test parsing version numbers from yaml files"""

    class Value(pydantic.BaseModel):
        version: str

        @pydantic.field_validator("version", mode="before")
        @classmethod
        def is_pep440_version(cls, v: Union[str, float]) -> str:
            version = str(v)
            return version

    Value(version=0.1)
