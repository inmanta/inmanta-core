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

import importlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Optional, cast

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

# Use a GraphQL input type as the body of a REST argument, so REST and GraphQL share one filter definition: the
# GraphQL type drives both request validation (graphql-core coercion) and OpenAPI (introspection). Declare an argument
# as Annotated[GraphQLFilter, graphql_input(<class or dotted path>)]; the class is resolved lazily so this module never
# imports schema at load time (which would cycle via compilerservice -> protocol).


@dataclass(frozen=True)
class ResolvedFilter:
    """Composed-filter artifacts attached to the core filter class at start: the graphql-core input type (for
    coercion/OpenAPI) and the strawberry composed type + components (for resolve_resource_ids)."""

    input_type: GraphQLInputObjectType
    composed_type: type
    components: tuple[type, ...]


class GraphQLFilter(BaseModel):
    """Marker for a GraphQL-filter argument. A BaseModel so it still validates as an object (and passes protocol
    type validation) if the graphql_input metadata is ever omitted."""

    model_config = ConfigDict(extra="allow")


@dataclass(frozen=True)
class graphql_input:
    """Annotated metadata naming the core filter class this argument mirrors, as the class or a dotted-path string
    (string for classes that would cycle if imported here). Resolved lazily, after the schema is built."""

    filter_class: type | str

    def _resolve_class(self) -> type:
        if isinstance(self.filter_class, str):
            module_path, _, class_name = self.filter_class.rpartition(".")
            return cast(type, getattr(importlib.import_module(module_path), class_name))
        return self.filter_class

    def _resolved(self) -> Optional[ResolvedFilter]:
        resolved: Optional[ResolvedFilter] = getattr(self._resolve_class(), "__resolved_filter__", None)
        return resolved

    def __get_pydantic_core_schema__(self, source_type: object, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # Built at import time, before the schema exists: only return a validator; resolve lazily per request.
        return core_schema.no_info_plain_validator_function(self._coerce)

    def __get_pydantic_json_schema__(self, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        # Runs at OpenAPI generation (after start). Fall back to a plain object if not resolved yet.
        resolved = self._resolved()
        if resolved is None:
            return {"type": "object"}
        return graphql_input_to_openapi(resolved.input_type)

    def _coerce(self, value: object) -> object:
        resolved = self._resolved()
        if resolved is None:
            raise ValueError(f"Filter class {self.filter_class!r} has no resolved filter (is the server started?).")
        errors: list[str] = []

        def on_error(path: Sequence[object], invalid_value: object, error: GraphQLError) -> None:
            location = ".".join(str(p) for p in path)
            errors.append(f"{location}: {error.message}" if location else error.message)

        coerced = coerce_input_value(value, resolved.input_type, on_error)
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


# ResourceFilter uses the string form because importing schema here would cycle; other filters can pass the class.
ResourceFilterArg = Annotated[GraphQLFilter, graphql_input("inmanta.graphql.schema.CoreResourceFilter")]
