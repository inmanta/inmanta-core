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
