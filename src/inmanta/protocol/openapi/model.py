"""
    Copyright 2020 Inmanta

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
"""
Based on the OpenAPI 3.0.2 Specification:
https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md
Inspired by FastAPI:
https://github.com/tiangolo/fastapi
"""
from collections import abc
from enum import Enum
from typing import Any, Optional, Self, Union

import pydantic
from pydantic import AnyUrl, ConfigDict, Field

from inmanta.data.model import BaseModel


class License(BaseModel):
    name: str
    url: AnyUrl | None = None


class Info(BaseModel):
    title: str
    description: str | None = None
    license: License | None = None
    version: str


class Server(BaseModel):
    url: AnyUrl
    description: str | None = None


class Reference(BaseModel):
    ref: str = Field(..., alias="$ref")


class Schema(BaseModel):
    ref: str | None = Field(None, alias="$ref")
    title: str | None = None
    required: list[str] | None = None
    type: str | None = None
    items: Optional["Schema"] = None
    properties: dict[str, "Schema"] | None = None
    additionalProperties: Union["Schema", bool] | None = None
    description: str | None = None
    format: str | None = None
    default: Any | None = None
    nullable: bool | None = None
    readOnly: bool | None = None
    example: Any | None = None
    deprecated: bool | None = None
    anyOf: abc.Sequence["Schema"] | None = None
    allOf: abc.Sequence["Schema"] | None = None
    oneOf: abc.Sequence["Schema"] | None = None
    enum: list[str] | None = None

    @pydantic.model_validator(mode="after")
    def convert_null_any_of(self) -> Self:
        """
        Convert null in anyOf to the `nullable` property.

        The OpenAPI spec models nullable fields with the `nullable` property while internally we use `Optional[t]`, which is
        essentially `Union[None, t]`. `anyOf` is the OpenAPI equivalent of this union type. Therefore, if `null` appears in it,
        we have to drop it from the `anyOf` and mark the schema as `nullable` instead.
        """
        if self.anyOf is not None:
            without_null: abc.Sequence["Schema"] = [e for e in self.anyOf if e.type != "null"]
            if len(without_null) != len(self.anyOf):
                # if by dropping `null`, there is now only a single value in the `anyOf`, it is no longer an `anyOf`
                # => promote the single element to this schema's level by copying all its attributes
                if len(without_null) == 1:
                    # promote single child, which has already been validated at this point
                    child: "Schema" = without_null[0]
                    for field in child.model_fields_set:
                        setattr(self, field, getattr(child, field))
                    self.anyOf = None
                else:
                    # convert null option to nullable property
                    self.anyOf = without_null
                self.nullable = True
        return self

    def resolve(self, ref_prefix: str, known_schemas: dict[str, "Schema"]) -> "Schema":
        """
        Returns this object or the one this object is refering to.

        :param ref_prefix: The prefix this object ref should have if it is only a reference
        :param known_schemas: A dict of known schemas, the keys are the reference diminished from their prefix

        :raises ValueError: If the schema has a badly formed ref
        """
        if not self.ref:
            return self

        if not self.ref.startswith(ref_prefix):
            raise ValueError(f"Schema reference (={self.ref}) doesn't start with the expected prefix: '{ref_prefix}'")

        reference = self.ref[len(ref_prefix) :]
        return known_schemas[reference]

    def recursive_resolve(
        self, ref_prefix: str, known_schemas: dict[str, "Schema"], update: dict[str, Any], deep: bool = True
    ) -> "Schema":
        """
        Returns this object of the one this object is refering to, and resolve all the nested schema it contains.

        :param ref_prefix: The prefix this object ref should have if it is only a reference
        :param known_schemas: A dict of known schemas, the keys are the reference diminished from their prefix
        :param update: values to change/add in the new model.
            Note: the data is not validated before creating the new model: you should trust this data
            Note: this update is applied to every schema we resolve
            Note: this is passed directly to BaseModel.copy method
        :param deep: Whether to perform a deepcopy of the object

        :raises ValueError: If the schema has a badly formed ref
        """

        # Get this schema if it is not a ref, or a new schema pointed to by the ref
        schema = self.resolve(ref_prefix, known_schemas)

        # We only do a deepcopy if the parameter says so AND this object has not been newly built
        deep = deep and schema is not self

        # Duplicate the schema, and update some of its values
        duplicate = schema.copy(update=update, deep=deep)

        # We copy and resolve the anyOf if we have any
        if duplicate.anyOf is not None:
            duplicate.anyOf = [s.recursive_resolve(ref_prefix, known_schemas, update, deep=False) for s in duplicate.anyOf]

        # We copy and resolve the allOf if we have any
        if duplicate.allOf is not None:
            duplicate.allOf = [s.recursive_resolve(ref_prefix, known_schemas, update, deep=False) for s in duplicate.allOf]

        # We copy and resolve the oneOf if we have any
        if duplicate.oneOf is not None:
            duplicate.oneOf = [s.recursive_resolve(ref_prefix, known_schemas, update, deep=False) for s in duplicate.oneOf]

        # We copy and resolve the items if we have any
        if duplicate.items is not None:
            duplicate.items = duplicate.items.recursive_resolve(ref_prefix, known_schemas, update, deep=False)

        # We copy and resolve the properties if we have any
        if duplicate.properties is not None:
            duplicate.properties = {
                k: s.recursive_resolve(ref_prefix, known_schemas, update, deep=False) for k, s in duplicate.properties.items()
            }

        # We copy and resolve the additionalProperties if we have any
        if duplicate.additionalProperties is not None and not isinstance(duplicate.additionalProperties, bool):
            duplicate.additionalProperties = duplicate.additionalProperties.recursive_resolve(
                ref_prefix, known_schemas, update, deep=False
            )

        return duplicate


Schema.model_rebuild()


class Example(BaseModel):
    summary: str | None = None
    description: str | None = None
    value: Any | None = None
    externalValue: AnyUrl | None = None


class ParameterType(Enum):
    query = "query"
    header = "header"
    path = "path"
    cookie = "cookie"


class Encoding(BaseModel):
    contentType: str | None = None
    headers: dict[str, Any | Reference] | None = None
    allowReserved: bool | None = None


class MediaType(BaseModel):
    schema_: Schema | Reference | None = Field(None, alias="schema")
    example: Any | None = None
    examples: dict[str, Example | Reference] | None = None
    encoding: dict[str, Encoding] | None = None


class ParameterBase(BaseModel):
    description: str | None = None
    required: bool | None = None
    deprecated: bool | None = None
    allowReserved: bool | None = None
    schema_: Schema | Reference | None = Field(None, alias="schema")
    example: Any | None = None
    examples: dict[str, Example | Reference] | None = None
    content: dict[str, MediaType] | None = None


class Parameter(ParameterBase):
    name: str
    in_: ParameterType = Field(..., alias="in")
    model_config = ConfigDict(populate_by_name=True)


class Header(ParameterBase):
    pass


class RequestBody(BaseModel):
    description: str | None = None
    content: dict[str, MediaType]
    required: bool | None = None


class Response(BaseModel):
    description: str
    headers: dict[str, Header | Reference] | None = None
    content: dict[str, MediaType] | None = None


class Operation(BaseModel):
    operationId: str
    summary: str | None = None
    description: str | None = None
    parameters: list[Parameter | Reference] | None = None
    requestBody: RequestBody | Reference | None = None
    responses: dict[str, Response]
    deprecated: bool | None = None
    tags: list[str] | None = None


class PathItem(BaseModel):
    ref: str | None = Field(None, alias="$ref")
    summary: str | None = None
    description: str | None = None
    get: Operation | None = None
    put: Operation | None = None
    post: Operation | None = None
    delete: Operation | None = None
    options: Operation | None = None
    head: Operation | None = None
    patch: Operation | None = None
    trace: Operation | None = None
    parameters: list[Parameter | Reference] | None = None


class Components(BaseModel):
    schemas: dict[str, Schema] | None = None
    responses: dict[str, Response | Reference] | None = None
    parameters: dict[str, Parameter | Reference] | None = None
    examples: dict[str, Example | Reference] | None = None
    requestBodies: dict[str, RequestBody | Reference] | None = None
    headers: dict[str, Header | Reference] | None = None


class OpenAPI(BaseModel):
    openapi: str
    info: Info
    servers: list[Server] | None = None
    paths: dict[str, PathItem]
    components: Components | None = None


class OpenApiDataTypes(Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
