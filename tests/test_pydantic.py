"""
    Copyright 2024 Inmanta

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

import typing

import pydantic
from pydantic import EncodedStr, EncoderProtocol, PlainValidator, SerializerFunctionWrapHandler, WrapSerializer, WrapValidator

from pydantic_core import ValidationError, core_schema


def test_custom_serializer() -> None:
    """How a custom serializer works with subclasses"""

    class _CustomString(str):
        pass

    CustomString = typing.Annotated[_CustomString, PlainValidator(lambda x: {"$ref": str(x)})]

    class Parent(pydantic.BaseModel):
        ref: str

    class ChildA(Parent):
        attr: str | CustomString

    class ChildB(Parent):
        prop: str

    class Container(pydantic.BaseModel):
        children: list[ChildA | ChildB]

    c = Container(children=[ChildA(ref="a", attr=CustomString("test")), ChildB(ref="b", prop="bla")])

    dump = c.model_dump()

    print(dump)
    assert dump["children"][0]["attr"]["$ref"] == "test"
