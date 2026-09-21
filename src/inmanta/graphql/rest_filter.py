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


# TODO: most recent note. Rework this. Ideally,
#   - review validation, coercion & OpenAPI
#   - review TODO notes

# TODO: review comment
# Use a GraphQL input type as the body of a REST argument, so REST and GraphQL share one filter definition: the
# GraphQL type drives both request validation (graphql-core coercion) and OpenAPI. Declare an argument as
# Annotated[Mapping[str, object], graphql_input(<GraphQL type name>)].
#
# This module is deliberately a leaf: it is imported by methods_v2, whose annotations are resolved while it is being
# imported, and anything under inmanta.data would cycle back into it (inmanta.data imports inmanta.protocol, which
# imports methods_v2). So the composed filters are pushed in here by `inmanta.graphql.schema` once the schema has
# been built, rather than looked up there. They are derived once at server start, never per request.


# TODO: review this block
class GraphQLFilterValidator:
    """
    Annotated metadata naming the GraphQL object type whose composed filter input this argument mirrors.
    """

    def __init__(self) -> None:
        self._graphql_type: GraphQLInputObjectType | None = None

    def register_graphql_type(self, graphql_type: GraphQLInputObjectType) -> None:
        # TODO: docstring. Expects to be called by slice

        # TODO: assert 'is None' somehow? Tests start multiple consecutive in-process servers so it breaks the naive assert
        # assert self._graphql_type is None

        # environment should always be part of the REST args directly, not the filter
        self._graphql_type = strip_input_field(graphql_type, "environment")

    @property
    def graphql_type(self) -> GraphQLInputObjectType:
        # TODO: proper check
        assert self._graphql_type is not None
        return self._graphql_type

    def __get_pydantic_core_schema__(self, source_type: object, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # Built while methods_v2 is imported, before the schema exists, so only a validator is returned here. It
        # reads the composed filter when it runs, which is always after start.
        # TODO: do we need to validate mapping, and then run *after* validator? Or does coerce include mapping validation?
        return core_schema.no_info_plain_validator_function(self._coerce)

    def __get_pydantic_json_schema__(self, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        # Copy because the OpenAPI converter is free to mutate what it is given.
        # TODO: copy no longer needed now that we call the convert method on each invocation?
        # TODO: consider caching if it's worth it.
        return copy.deepcopy(graphql_input_to_openapi(self.graphql_type))

    def _coerce(self, value: object) -> object:
        errors: list[str] = []

        def on_error(path: Sequence[object], invalid_value: object, error: GraphQLError) -> None:
            location = ".".join(str(p) for p in path)
            errors.append(f"{location}: {error.message}" if location else error.message)

        # TODO: use pydantic validate instead
        coerced = coerce_input_value(value, self.graphql_type, on_error)
        if errors:
            raise ValueError("; ".join(errors))
        return coerced


# TODO: make classmethod???
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


# TODO: if slice is responsible for loading these, how to make that explicit? It can not declare them for import reasons
#   Just document that the slice is coupled with this module?
# TODO: capitalization?
ResourceFilterValidator = GraphQLFilterValidator()
ResourceFilterArg = Annotated[Mapping[str, object], ResourceFilterValidator]
