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
import sys
import typing
from enum import Enum

import pydantic
import pytest

from inmanta import const, resources, types
from inmanta.data.model import BaseModel, LogLine, ResourceMinimal
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
    """Test if pydantic correctly serializes a bool to bool and not int when using a Union.

    Union in python < 3.7 removes all strict subtypes. bool and strictbool are subtypes of int
    """

    class Test(pydantic.BaseModel):
        attr1: typing.Union[pydantic.StrictBool, int]
        attr2: typing.Union[pydantic.StrictBool]
        attr3: pydantic.StrictBool
        attr4: typing.Union[types.StrictNonIntBool, int]

    x = Test(attr1=True, attr2=True, attr3=True, attr4=True)

    if sys.version_info[0] == 3 and sys.version_info[1] < 7:
        assert x.attr1 is not True and x.attr1 == 1
    else:
        assert x.attr1 is True

    assert x.attr2 is True
    assert x.attr3 is True
    assert x.attr4 is True


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
    with pytest.raises(ValueError) as excinfo:
        LogLine(level=11, msg="test", args=[], kwargs={}, timestamp=datetime.datetime.now())
    assert "value is not a valid enumeration member" in str(excinfo.value)


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


def test_resource_minimal_create_from_version():
    """
    Test whether the `ResourceMinimal.create_with_version()` works correctly.
    """
    res_id_str = "res::Resource[agent1,id_attr=val],v=11"
    initial_attributes = {
        "id": res_id_str,
        "attr1": "val",
        "version": 11,
        "requires": ["res::Resource[agent1,id_attr=dep1],v=11", "res::Resource[agent1,id_attr=dep2],v=11"],
    }
    resource_minimal = ResourceMinimal.create_with_version(
        new_version=12,
        id=resources.Id.parse_id(res_id_str).resource_version_str(),
        attributes=initial_attributes,
    )
    expected_serialization = {
        "id": "res::Resource[agent1,id_attr=val],v=12",
        "attr1": "val",
        "version": 12,
        "requires": ["res::Resource[agent1,id_attr=dep1],v=12", "res::Resource[agent1,id_attr=dep2],v=12"],
    }
    assert resource_minimal.dict() == expected_serialization
