"""
Copyright 2026 Inmanta
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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Optional

from pydantic import ConfigDict, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue

from graphql import (
    GraphQLEnumType,
    GraphQLError,
    GraphQLInputObjectType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLScalarType,
    Undefined,
)
from graphql.utilities import coerce_input_value
from inmanta.types import BaseModel
from pydantic_core import core_schema

"""
This module lets a REST method argument reuse a GraphQL input type (e.g. the composed ``ResourceFilter`` of the
``resources`` query) as its body definition. The GraphQL input type is the single source of truth: it drives both
the request validation (via graphql-core input coercion) and the OpenAPI documentation (via GraphQL introspection),
so the REST and GraphQL filter languages can never drift.

An argument is declared as ``Annotated[GraphQLFilter, graphql_input("<TypeName>")]``. Because both hooks resolve the
GraphQL type lazily from ``graphql_input_registry`` (populated by the ``GraphQLSlice`` at server start), the marker
can be used in a statically-declared method even though the composed type only exists after start.
"""


class _GraphQLInputRegistry:
    """
    Maps the name referenced by ``graphql_input`` to the graphql-core input type used to validate and document the
    REST body. Populated by the ``GraphQLSlice`` once it has composed the schema.
    """

    def __init__(self) -> None:
        self._types: dict[str, GraphQLInputObjectType] = {}

    def publish(self, name: str, input_type: GraphQLInputObjectType) -> None:
        self._types[name] = input_type

    def get(self, name: str) -> Optional[GraphQLInputObjectType]:
        return self._types.get(name)


graphql_input_registry = _GraphQLInputRegistry()


class GraphQLFilter(BaseModel):
    """
    Static marker type for a method argument whose JSON value is a GraphQL filter input; the concrete shape is
    resolved from the composed GraphQL schema at server start (see ``graphql_input``).

    It is intentionally a ``BaseModel``: should the ``graphql_input`` metadata ever be omitted, the argument still
    validates as a JSON object rather than as an unchecked value, and the protocol type validation accepts it as a
    known (structured) argument type.
    """

    model_config = ConfigDict(extra="allow")


@dataclass(frozen=True)
class graphql_input:
    """
    ``Annotated`` metadata selecting the GraphQL input type that validates and documents an argument. Both the
    pydantic validation (``__get_pydantic_core_schema__`` -> graphql-core coercion) and the OpenAPI schema
    (``__get_pydantic_json_schema__`` -> GraphQL introspection) are derived from that type, resolved lazily from
    ``graphql_input_registry``.
    """

    type_name: str

    def __get_pydantic_core_schema__(self, source_type: object, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # Runs when the arguments model is built (import time), before the GraphQL schema exists. Only return a
        # validator; the registry is resolved lazily inside `_coerce` (per request, after start).
        return core_schema.no_info_plain_validator_function(self._coerce)

    def __get_pydantic_json_schema__(self, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        # Runs at OpenAPI generation (after start). Degrade to a permissive object schema if the type is not
        # published yet, so documentation generation never hard-fails.
        input_type = graphql_input_registry.get(self.type_name)
        if input_type is None:
            return {"type": "object"}
        return graphql_input_to_openapi(input_type)

    def _coerce(self, value: object) -> object:
        input_type = graphql_input_registry.get(self.type_name)
        if input_type is None:
            raise ValueError(f"GraphQL input type {self.type_name!r} is not available")
        errors: list[str] = []

        def on_error(path: Sequence[object], invalid_value: object, error: GraphQLError) -> None:
            location = ".".join(str(p) for p in path)
            errors.append(f"{location}: {error.message}" if location else error.message)

        coerced = coerce_input_value(value, input_type, on_error)
        if errors:
            raise ValueError("; ".join(errors))
        return coerced


def strip_input_field(input_type: GraphQLInputObjectType, field_name: str) -> GraphQLInputObjectType:
    """
    Return a copy of ``input_type`` without ``field_name``. Used to drop ``environment`` from the ``ResourceFilter``
    for the REST body, since the environment is supplied out of band (the ``tid``), not inside the filter.
    """
    return GraphQLInputObjectType(
        name=f"{input_type.name}RestBody",
        fields={name: field for name, field in input_type.fields.items() if name != field_name},
    )


_SCALAR_TO_OPENAPI: Mapping[str, dict[str, object]] = {
    "String": {"type": "string"},
    "Int": {"type": "integer"},
    "Float": {"type": "number"},
    "Boolean": {"type": "boolean"},
    "ID": {"type": "string"},
    "UUID": {"type": "string", "format": "uuid"},
}


def graphql_input_to_openapi(gql_type: object) -> dict[str, object]:
    """Map a GraphQL input type to an OpenAPI / JSON-Schema object (nested input objects are inlined)."""
    if isinstance(gql_type, GraphQLNonNull):
        return graphql_input_to_openapi(gql_type.of_type)
    if isinstance(gql_type, GraphQLList):
        return {"type": "array", "items": graphql_input_to_openapi(gql_type.of_type)}
    if isinstance(gql_type, GraphQLInputObjectType):
        properties: dict[str, object] = {}
        required: list[str] = []
        for name, field in gql_type.fields.items():
            properties[name] = graphql_input_to_openapi(field.type)
            if isinstance(field.type, GraphQLNonNull) and field.default_value is Undefined:
                required.append(name)
        schema: dict[str, object] = {"type": "object", "properties": properties, "additionalProperties": False}
        if required:
            schema["required"] = required
        return schema
    if isinstance(gql_type, GraphQLEnumType):
        return {"type": "string", "enum": list(gql_type.values.keys())}
    if isinstance(gql_type, GraphQLScalarType):
        return dict(_SCALAR_TO_OPENAPI.get(gql_type.name, {"type": "string"}))
    return {"type": "object"}


# Reusable argument alias for the composed ResourceFilter of the `resources` query.
ResourceFilterArg = Annotated[GraphQLFilter, graphql_input("ResourceFilter")]
