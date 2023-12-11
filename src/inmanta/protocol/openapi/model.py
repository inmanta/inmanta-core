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
    url: Optional[AnyUrl] = None


class Info(BaseModel):
    title: str
    description: Optional[str] = None
    license: Optional[License] = None
    version: str


class Server(BaseModel):
    url: AnyUrl
    description: Optional[str] = None


class Reference(BaseModel):
    ref: str = Field(..., alias="$ref")


class Schema(BaseModel):
    ref: Optional[str] = Field(None, alias="$ref")
    title: Optional[str] = None
    required: Optional[list[str]] = None
    type: Optional[str] = None
    items: Optional["Schema"] = None
    properties: Optional[dict[str, "Schema"]] = None
    additionalProperties: Optional[Union["Schema", bool]] = None
    description: Optional[str] = None
    format: Optional[str] = None
    default: Optional[Any] = None
    nullable: Optional[bool] = None
    readOnly: Optional[bool] = None
    example: Optional[Any] = None
    deprecated: Optional[bool] = None
    anyOf: Optional[abc.Sequence["Schema"]] = None
    allOf: Optional[abc.Sequence["Schema"]] = None
    oneOf: Optional[abc.Sequence["Schema"]] = None
    enum: Optional[list[str]] = None

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
    summary: Optional[str] = None
    description: Optional[str] = None
    value: Optional[Any] = None
    externalValue: Optional[AnyUrl] = None


class ParameterType(Enum):
    query = "query"
    header = "header"
    path = "path"
    cookie = "cookie"


class Encoding(BaseModel):
    contentType: Optional[str] = None
    headers: Optional[dict[str, Union[Any, Reference]]] = None
    allowReserved: Optional[bool] = None


class MediaType(BaseModel):
    schema_: Optional[Union[Schema, Reference]] = Field(None, alias="schema")
    example: Optional[Any] = None
    examples: Optional[dict[str, Union[Example, Reference]]] = None
    encoding: Optional[dict[str, Encoding]] = None


class ParameterBase(BaseModel):
    description: Optional[str] = None
    required: Optional[bool] = None
    deprecated: Optional[bool] = None
    allowReserved: Optional[bool] = None
    schema_: Optional[Union[Schema, Reference]] = Field(None, alias="schema")
    example: Optional[Any] = None
    examples: Optional[dict[str, Union[Example, Reference]]] = None
    content: Optional[dict[str, MediaType]] = None


class Parameter(ParameterBase):
    name: str
    in_: ParameterType = Field(..., alias="in")
    model_config = ConfigDict(populate_by_name=True)


class Header(ParameterBase):
    pass


class RequestBody(BaseModel):
    description: Optional[str] = None
    content: dict[str, MediaType]
    required: Optional[bool] = None


class Response(BaseModel):
    description: str
    headers: Optional[dict[str, Union[Header, Reference]]] = None
    content: Optional[dict[str, MediaType]] = None


class Operation(BaseModel):
    operationId: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[list[Union[Parameter, Reference]]] = None
    requestBody: Optional[Union[RequestBody, Reference]] = None
    responses: dict[str, Response]
    deprecated: Optional[bool] = None
    tags: Optional[list[str]] = None


class PathItem(BaseModel):
    ref: Optional[str] = Field(None, alias="$ref")
    summary: Optional[str] = None
    description: Optional[str] = None
    get: Optional[Operation] = None
    put: Optional[Operation] = None
    post: Optional[Operation] = None
    delete: Optional[Operation] = None
    options: Optional[Operation] = None
    head: Optional[Operation] = None
    patch: Optional[Operation] = None
    trace: Optional[Operation] = None
    parameters: Optional[list[Union[Parameter, Reference]]] = None


class Components(BaseModel):
    schemas: Optional[dict[str, Schema]] = None
    responses: Optional[dict[str, Union[Response, Reference]]] = None
    parameters: Optional[dict[str, Union[Parameter, Reference]]] = None
    examples: Optional[dict[str, Union[Example, Reference]]] = None
    requestBodies: Optional[dict[str, Union[RequestBody, Reference]]] = None
    headers: Optional[dict[str, Union[Header, Reference]]] = None


class OpenAPI(BaseModel):
    openapi: str
    info: Info
    servers: Optional[list[Server]] = None
    paths: dict[str, PathItem]
    components: Optional[Components] = None


class OpenApiDataTypes(Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
