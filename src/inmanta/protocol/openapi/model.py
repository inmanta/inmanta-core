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
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, TypeVar, Union

from pydantic import AnyUrl, Field

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


S = TypeVar("S", bound="SchemaBase")


class SchemaBase(BaseModel):
    ref: Optional[str] = Field(None, alias="$ref")
    title: Optional[str] = None
    required: Optional[List[str]] = None
    type: Optional[str] = None
    items: Optional[Any] = None
    properties: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    format: Optional[str] = None
    default: Optional[Any] = None
    nullable: Optional[bool] = None
    readOnly: Optional[bool] = None
    example: Optional[Any] = None
    deprecated: Optional[bool] = None
    anyOf: Optional[Sequence["SchemaBase"]] = None
    enum: Optional[List[str]] = None

    def from_dict(self: S, schema: Dict[str, Any]) -> S:
        """
        Build an object with the same type as this object

        :param schema: The schema of the object to build
        """
        return SchemaBase(**schema)

    def resolve(self: S, ref_prefix: str, known_schemas: Dict[str, Any]) -> S:
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
        return self.from_dict(known_schemas[reference])

    def recursive_resolve(
        self: S, ref_prefix: str, known_schemas: Dict[str, Any], update: Dict[str, Any], deep: bool = True
    ) -> S:
        """
        Returns this object of the one this object is refering to, and resolve all the nested schema it contains.

        :param ref_prefix: The prefix this object ref should have if it is only a reference
        :param known_schemas: A dict of known schemas, the keys are the reference diminished from their prefix
        :param update: A dict of attributes of this object to update
        :param deep: Whether to perform a deepcopy of the object

        :raises ValueError: If the schema has a badly formed ref
        """

        # Get this schema if it is not a ref, or a new schema pointed to by the ref
        schema: SchemaBase = self.resolve(ref_prefix, known_schemas)

        # We only do a deepcopy if the parameter says so AND this object has not been newly built
        deep = deep and schema is not self

        # Duplicate the schema, and update some of its values
        duplicate: SchemaBase = schema.copy(update=update, deep=deep)

        # We copy and resolve the list of schema
        if duplicate.anyOf is not None:
            duplicate.anyOf = [s.recursive_resolve(ref_prefix, known_schemas, update, deep=False) for s in duplicate.anyOf]

        return duplicate


SchemaBase.update_forward_refs()


class Schema(SchemaBase):
    items: Optional[Union["Schema", SchemaBase]] = None
    properties: Optional[Dict[str, Union["Schema", SchemaBase]]] = None
    additionalProperties: Optional[Union["Schema", SchemaBase, bool]] = None

    def from_dict(self: S, schema: Dict[str, Any]) -> S:
        return Schema(**schema)

    def recursive_resolve(
        self: S, ref_prefix: str, known_schemas: Dict[str, Any], update: Dict[str, Any], deep: bool = True
    ) -> S:
        duplicate: Schema = super().recursive_resolve(ref_prefix, known_schemas, update, deep=deep)

        if duplicate.items is not None:
            duplicate.items = duplicate.items.recursive_resolve(ref_prefix, known_schemas, update, deep=False)

        if duplicate.properties is not None:
            duplicate.properties = {
                k: s.recursive_resolve(ref_prefix, known_schemas, update, deep=False) for k, s in duplicate.properties.items()
            }

        if duplicate.additionalProperties is not None and not isinstance(duplicate.additionalProperties, bool):
            duplicate.additionalProperties = duplicate.additionalProperties.recursive_resolve(
                ref_prefix, known_schemas, update, deep=False
            )

        return duplicate


Schema.update_forward_refs()


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
    headers: Optional[Dict[str, Union[Any, Reference]]] = None
    allowReserved: Optional[bool] = None


class MediaType(BaseModel):
    schema_: Optional[Union[Schema, Reference]] = Field(None, alias="schema")
    example: Optional[Any] = None
    examples: Optional[Dict[str, Union[Example, Reference]]] = None
    encoding: Optional[Dict[str, Encoding]] = None


class ParameterBase(BaseModel):
    description: Optional[str] = None
    required: Optional[bool] = None
    deprecated: Optional[bool] = None
    allowReserved: Optional[bool] = None
    schema_: Optional[Union[Schema, Reference]] = Field(None, alias="schema")
    example: Optional[Any] = None
    examples: Optional[Dict[str, Union[Example, Reference]]] = None
    content: Optional[Dict[str, MediaType]] = None


class Parameter(ParameterBase):
    name: str
    in_: ParameterType = Field(..., alias="in")

    class Config:
        allow_population_by_field_name = True


class Header(ParameterBase):
    pass


class RequestBody(BaseModel):
    description: Optional[str] = None
    content: Dict[str, MediaType]
    required: Optional[bool] = None


class Response(BaseModel):
    description: str
    headers: Optional[Dict[str, Union[Header, Reference]]] = None
    content: Optional[Dict[str, MediaType]] = None


class Operation(BaseModel):
    operationId: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[List[Union[Parameter, Reference]]] = None
    requestBody: Optional[Union[RequestBody, Reference]] = None
    responses: Dict[str, Response]
    deprecated: Optional[bool] = None
    tags: Optional[List[str]] = None


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
    parameters: Optional[List[Union[Parameter, Reference]]] = None


class Components(BaseModel):
    schemas: Optional[Dict[str, Union[Schema, Reference]]] = None
    responses: Optional[Dict[str, Union[Response, Reference]]] = None
    parameters: Optional[Dict[str, Union[Parameter, Reference]]] = None
    examples: Optional[Dict[str, Union[Example, Reference]]] = None
    requestBodies: Optional[Dict[str, Union[RequestBody, Reference]]] = None
    headers: Optional[Dict[str, Union[Header, Reference]]] = None


class OpenAPI(BaseModel):
    openapi: str
    info: Info
    servers: Optional[List[Server]] = None
    paths: Dict[str, PathItem]
    components: Optional[Components] = None
