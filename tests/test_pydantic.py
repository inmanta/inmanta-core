import datetime
import uuid
from typing import Any, Dict, Union

import pydantic

from inmanta import types


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

    # TODO: when passing strings as types you get weird errors


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
