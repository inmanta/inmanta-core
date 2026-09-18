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

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
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
from pydantic_core import core_schema

# TODO: review comment
# Use a GraphQL input type as the body of a REST argument, so REST and GraphQL share one filter definition: the
# GraphQL type drives both request validation (graphql-core coercion) and OpenAPI. Declare an argument as
# Annotated[Mapping[str, object], graphql_input(<GraphQL type name>)].
#
# This module is deliberately a leaf: it is imported by methods_v2, whose annotations are resolved while it is being
# imported, and anything under inmanta.data would cycle back into it (inmanta.data imports inmanta.protocol, which
# imports methods_v2). So the composed filters are pushed in here by `inmanta.graphql.schema` once the schema has
# been built, rather than looked up there. They are derived once at server start, never per request.


# TODO: rework entire ComposedFilter, publish, get ...
@dataclass(frozen=True)
class ComposedFilter:
    """
    Everything derived from one object type's composed filter input, built once when the schema is built.

    :param components: the filter components the composed input was built from (the object type's core filter
        followed by one per extension contribution).
    :param strawberry_type: the composed `@strawberry.input` type, as accepted by the type's GraphQL query.
    :param input_type: the graphql-core input type a REST body is coerced against: `strawberry_type` as it appears
        in the built schema, minus `environment` (REST takes the environment from the tid).
    :param openapi: `input_type` as an OpenAPI/JSON-Schema object.
    """

    components: tuple[type, ...]
    strawberry_type: type
    input_type: GraphQLInputObjectType
    openapi: dict[str, object]

    @classmethod
    def build(cls, components: tuple[type, ...], strawberry_type: type, input_type: GraphQLInputObjectType) -> "ComposedFilter":
        """Derive everything from the composed filter input as it appears in the built schema."""
        return cls(
            components=components,
            strawberry_type=strawberry_type,
            input_type=input_type,
            openapi=graphql_input_to_openapi(input_type),
        )


# The composed filters, keyed by the name of the GraphQL object type they filter (e.g. "Resource"), as published by
# `inmanta.graphql.schema.get_schema`. Populated when the GraphQL slice builds the schema.
_composed_filters: dict[str, ComposedFilter] = {}


# TODO: review this block
def publish_composed_filter(type_name: str, composed_filter: ComposedFilter) -> None:
    """
    Make an object type's composed filter available to the REST layer. A server builds its schema once, but a single
    process can start more than one server (every test that uses the `server` fixture does), so a later build
    replaces what an earlier one published.

    :param type_name: the name of the GraphQL object type the filter filters (e.g. "Resource").
    :param composed_filter: what was derived from the composed filter input of that type.
    """
    _composed_filters[type_name] = composed_filter


# TODO: review this block
def get_composed_filter(type_name: str) -> ComposedFilter:
    """
    Return an object type's composed filter. Only available once the GraphQL schema has been built, which happens
    when the GraphQL slice starts.

    :param type_name: the name of the GraphQL object type the filter filters (e.g. "Resource").
    """
    if type_name not in _composed_filters:
        raise Exception(
            f"No composed filter for {type_name}: either the GraphQL schema has not been built yet, or {type_name} is"
            " not a type that can be filtered on."
        )
    return _composed_filters[type_name]


# TODO: review this block
@dataclass(frozen=True)
class graphql_input:
    """
    Annotated metadata naming the GraphQL object type whose composed filter input this argument mirrors.
    """

    type_name: str

    def __get_pydantic_core_schema__(self, source_type: object, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # Built while methods_v2 is imported, before the schema exists, so only a validator is returned here. It
        # reads the composed filter when it runs, which is always after start.
        return core_schema.no_info_plain_validator_function(self._coerce)

    def __get_pydantic_json_schema__(self, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        # Copy because the OpenAPI converter is free to mutate what it is given.
        return copy.deepcopy(get_composed_filter(self.type_name).openapi)

    def _coerce(self, value: object) -> object:
        errors: list[str] = []

        def on_error(path: Sequence[object], invalid_value: object, error: GraphQLError) -> None:
            location = ".".join(str(p) for p in path)
            errors.append(f"{location}: {error.message}" if location else error.message)

        # TODO: use pydantic validate instead
        coerced = coerce_input_value(value, get_composed_filter(self.type_name).input_type, on_error)
        if errors:
            raise ValueError("; ".join(errors))
        return coerced


def strip_input_field(input_type: GraphQLInputObjectType, field_name: str) -> GraphQLInputObjectType:
    """Return a copy of input_type without field_name (used to drop environment, which REST takes from the tid)."""
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


# TODO (Claude): both fallbacks below assert something we don't actually know, and do it silently.
#   - an unmapped scalar is documented as a string: right for most custom scalars, wrong for a JSON-ish one (a
#     generated client then types it str and, with additionalProperties false alongside it, a strict client-side
#     validator rejects a legitimate object body before sending it) and wrong for a numeric one (clients send "5").
#   - anything that is not a type handled above is documented as a contract-free object.
#   Nothing catches either: the spec validator (tests/test_openapi.py) checks the spec is valid, not correct, and
#   docs/reference/openapi.json is checked in. Core's filters only use mapped scalars today, so the exposure is
#   entirely on extension-contributed filter fields, whose author gets no signal at all.
#   The honest lenient form would be an empty schema (unconstrained, which is what we know) plus a warning naming
#   the scalar. Raising instead would make this refuse to boot over a documentation defect, since the translation
#   runs at server start.
def graphql_input_to_openapi(gql_type: object) -> dict[str, object]:
    """Map a GraphQL input type to an OpenAPI/JSON-Schema object (nested input objects inlined)."""
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


# TODO: name the graphql_input obj as ResourceValidator so that the slice can access it for registration
ResourceFilterArg = Annotated[Mapping[str, object], graphql_input("Resource")]


# TODO: main question is where and how do we want this?
#   - graphql slice could call schema to return both schema and types
#   - but how and where does this annotation type hook into it?
#   - how do the imports flow?
#   => depending on the answer graphql slice approach is good, or it may need to keep living in graphql schema
