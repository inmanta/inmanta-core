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
from typing import Annotated, ClassVar

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


class GraphQLFilterSchema:
    """
    Pydantic-compatible schema (typing.Annotated[Mapping[str, object], <schema>]) for a GraphQL filter type. Explicitly coupled
    with the GraphQL slice because the composed GraphQL type only becomes available during server `start`, while the static type
    must be available and inspectable at method import time.

    During server startup, the GraphQL slice must call the `register_graphql_type` method on each schema instance declared at
    the bottom of this file. At runtime, it must make sure to copy the "environment" REST argument into the provided filter.
    """

    _SCALAR_TO_OPENAPI: ClassVar[Mapping[str, dict[str, object]]] = {
        "String": {"type": "string"},
        "Int": {"type": "integer"},
        "Float": {"type": "number"},
        "Boolean": {"type": "boolean"},
        "ID": {"type": "string"},
        "UUID": {"type": "string", "format": "uuid"},
    }

    def __init__(self) -> None:
        self._graphql_type: GraphQLInputObjectType | None = None

    def register_graphql_type(self, graphql_type: GraphQLInputObjectType) -> None:
        """
        Register the grapqhl filter type for the composed schema. Called by the GraphQL slice during startup.

        This method excludes the "environment" field from the provided type's fields. The REST filter schema never includes the
        "environment" field since it should always be part of the REST args directly, not the filter. The GraphQL slice must
        make sure to copy the REST arg value into the filter at runtime.
        """
        # TODO: assert 'is None' somehow? Tests start multiple consecutive in-process servers so it breaks the naive assert
        # assert self._graphql_type is None
        self._graphql_type = GraphQLInputObjectType(
            name=f"{graphql_type.name}RestBody",
            fields={name: field for name, field in graphql_type.fields.items() if name != "environment"},
        )

    @property
    def graphql_type(self) -> GraphQLInputObjectType:
        if self._graphql_type is None:
            raise Exception("Uninitialized GraphQLFilterSchema. GraphQL slice should register filter type at startup.")
        return self._graphql_type

    def __get_pydantic_core_schema__(self, source_type: object, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # Built while methods_v2 is imported, before the schema exists, so only a validator is returned here. It
        # reads the composed filter when it runs, which is always after start.
        return core_schema.no_info_after_validator_function(self._coerce, handler(source_type))

    def __get_pydantic_json_schema__(self, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return self._graphql_input_to_openapi(self.graphql_type)

    # TODO: review implementation + name + docstring
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

    # TODO: review this method and this comment!!!
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
    @classmethod
    def _graphql_input_to_openapi(cls, graphql_type: object) -> dict[str, object]:
        """
        Map a GraphQL input type to an OpenAPI/JSON-Schema object (nested input objects inlined).
        """
        if isinstance(graphql_type, GraphQLNonNull):
            return cls._graphql_input_to_openapi(graphql_type.of_type)
        if isinstance(graphql_type, GraphQLList):
            return {"type": "array", "items": cls._graphql_input_to_openapi(graphql_type.of_type)}
        if isinstance(graphql_type, GraphQLInputObjectType):
            properties: dict[str, object] = {}
            required: list[str] = []
            for name, field in graphql_type.fields.items():
                properties[name] = cls._graphql_input_to_openapi(field.type)
                if isinstance(field.type, GraphQLNonNull) and field.default_value is Undefined:
                    required.append(name)
            schema: dict[str, object] = {"type": "object", "properties": properties, "additionalProperties": False}
            if required:
                schema["required"] = required
            return schema
        if isinstance(graphql_type, GraphQLEnumType):
            return {"type": "string", "enum": list(graphql_type.values.keys())}
        if isinstance(graphql_type, GraphQLScalarType):
            return dict(cls._SCALAR_TO_OPENAPI.get(graphql_type.name, {"type": "string"}))
        return {"type": "object"}


RESOURCE_FILTER_SCHEMA = GraphQLFilterSchema()

ResourceFilterArg = Annotated[Mapping[str, object], RESOURCE_FILTER_SCHEMA]
