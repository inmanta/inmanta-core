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
import sys
import typing
from enum import Enum

import pydantic

from inmanta import types
from inmanta.data.model import BaseModel


def test_model_inheritance():
    """ Test if config classes inheritance
    """

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
    """ Test if pydantic correctly serializes a bool to bool and not int when using a Union.

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
