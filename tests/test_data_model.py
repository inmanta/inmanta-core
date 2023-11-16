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
import datetime
import json
import typing
from enum import Enum

import pydantic
import pytest

from inmanta import const, types
from inmanta.data.model import BaseModel, LogLine
from inmanta.protocol.common import json_encode


def test_model_inheritance():
    """Test if config classes inheritance"""

    class Choices(str, Enum):
        yes = "yes"
        no = "no"

    class Project(BaseModel):
        name: str
        opts: Choices

    project = Project(name="test", opts="no")
    ser = project.dict()

    assert ser["opts"] == "no"
    assert not isinstance(ser["opts"], Enum)


def test_union_bool_json():
    """
    Test if pydantic correctly serializes a bool to bool and not int when using a Union.

    With pydantic<1.10 a union of int and StrictBool would cause True to become 1, hence the need for StrictNonIntBool.
    With pydantic v2 even StrictBool is not required anymore because of smart unions.
    This test case verifies that bool, StrictBool and StrictNonIntBool all behave the same when used in a union.
    """

    class Test(pydantic.BaseModel):
        attr1: typing.Union[pydantic.StrictBool, int]
        attr2: typing.Union[pydantic.StrictBool]
        attr3: pydantic.StrictBool
        attr4: typing.Union[types.StrictNonIntBool, int]
        attr5: typing.Union[bool, int]
        attr6: typing.Union[int, bool]

    x = Test(attr1=True, attr2=True, attr3=True, attr4=True, attr5=True, attr6=True)

    assert x.attr1 is True
    assert x.attr2 is True
    assert x.attr3 is True
    assert x.attr4 is True
    assert x.attr5 is True
    assert x.attr6 is True


def test_log_line_serialization():
    """
    Ensure that the level field of a LogLine serializes and deserializes correctly
    using the name of the enum instead of the value.
    """
    log_line = LogLine(level=const.LogLevel.DEBUG, msg="test", args=[], kwargs={}, timestamp=datetime.datetime.now())
    serializes_log_line = json_encode(log_line)
    deserialized_log_line_dct = json.loads(serializes_log_line)
    assert deserialized_log_line_dct["level"] == const.LogLevel.DEBUG.name

    deserialized_log_line = LogLine(**deserialized_log_line_dct)
    assert deserialized_log_line.level == const.LogLevel.DEBUG

    assert log_line == deserialized_log_line


def test_log_line_deserialization():
    """
    Ensure that a proper error is raised when an invalid log level is used.
    """
    with pytest.raises(ValueError, match="validation error") as excinfo:
        LogLine(level="LOUD", msg="test", args=[], kwargs={}, timestamp=datetime.datetime.now())
    expected_output: str = (
        "Input should be 'CRITICAL' | 50, 'ERROR' | 40, 'WARNING' | 30, 'INFO' | 20, 'DEBUG' | 10 or 'TRACE' | 3"
    )
    assert expected_output in str(excinfo.value)

    with pytest.raises(ValueError, match="validation error") as excinfo:
        LogLine(level=43, msg="test", args=[], kwargs={}, timestamp=datetime.datetime.now())
    assert expected_output in str(excinfo.value)

    LogLine(level=50, msg="test", args=[], kwargs={}, timestamp=datetime.datetime.now())


def test_timezone_aware_fields_in_pydantic_object():
    """
    Verify that timestamp fields in pydantic object that extends from the inmanta
    BaseModel class, are made timezone aware.
    """

    class Test(BaseModel):
        timestamp: datetime.datetime

    timestamp = datetime.datetime.now()
    assert timestamp.tzinfo is None
    test = Test(timestamp=timestamp)
    assert test.timestamp.tzinfo is not None
