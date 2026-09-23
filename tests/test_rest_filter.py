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

import pytest

import inmanta.data.sqlalchemy as models
import strawberry
from graphql import GraphQLInputObjectType
from inmanta.graphql.rest_filter import GraphQLFilterSchema
from inmanta.graphql.schema import RESOURCE_CONTRIBUTABLE, GraphQLContribution, ResourceFilterABC, get_schema


@pytest.fixture(scope="module")
def resource_filter_type() -> GraphQLInputObjectType:
    """The composed resource filter input, as it appears in a freshly built schema."""
    filter_type = get_schema({})._schema.type_map[RESOURCE_CONTRIBUTABLE.filter_type_name]
    assert isinstance(filter_type, GraphQLInputObjectType)
    return filter_type


@pytest.fixture
def filter_schema(resource_filter_type: GraphQLInputObjectType) -> GraphQLFilterSchema:
    """A filter schema loaded with the built filter type, the way the GraphQL slice loads it when it starts."""
    filter_schema = GraphQLFilterSchema()
    filter_schema.register_graphql_type(resource_filter_type)
    return filter_schema


def test_filter_schema_requires_registration() -> None:
    """A filter schema has nothing to validate against until the GraphQL slice registers the built type."""
    filter_schema = GraphQLFilterSchema()
    with pytest.raises(Exception):
        filter_schema.graphql_type


def test_filter_schema_strips_environment(filter_schema: GraphQLFilterSchema) -> None:
    """The environment is passed as the tid of the request, so it is not part of the filter a REST caller sends."""
    assert "environment" not in filter_schema.graphql_type.fields
    with pytest.raises(ValueError, match="Field 'environment' is not defined"):
        filter_schema._validate({"environment": "3b9a1fd8-0e6a-4d1e-8a2f-7c5e9b0d4a11"})


def test_filter_schema_validates_and_rejects(filter_schema: GraphQLFilterSchema) -> None:
    """A body is validated against the composed filter input, which is what rejects fields it does not define."""
    # an empty filter selects everything, so it is valid
    assert filter_schema._validate({}) == {}
    assert filter_schema._validate({"agent": {"eq": ["agent1"]}}) == {"agent": {"eq": ["agent1"]}}
    with pytest.raises(ValueError, match="Field 'doesNotExist' is not defined"):
        filter_schema._validate({"doesNotExist": {"eq": ["x"]}})
    with pytest.raises(ValueError, match="Expected type 'ResourceFilterRestBody' to be a mapping"):
        filter_schema._validate(["not", "an", "object"])


def test_filter_schema_validate_returns_the_received_value(filter_schema: GraphQLFilterSchema) -> None:
    """
    Validation returns the body as received, not the coerced form. The body is passed on as a GraphQL variable, and
    the query coerces it itself; coercion is not idempotent for enums (name -> value), so coercing here too would
    make the query reject a body this accepted.
    """
    enum_filter = {"blocked": {"eq": ["NOT_BLOCKED"]}}
    validated = filter_schema._validate(enum_filter)

    assert validated == enum_filter
    # the enum name survives: the coerced form would hold a Blocked member, whose value is "not_blocked"
    assert validated["blocked"]["eq"] == ["NOT_BLOCKED"]

    # an enum name that does not exist is still rejected
    with pytest.raises(ValueError, match="does not exist in 'Blocked' enum"):
        filter_schema._validate({"blocked": {"eq": ["NOT_AN_ENUM_VALUE"]}})


def test_filter_openapi(filter_schema: GraphQLFilterSchema) -> None:
    """The OpenAPI schema for the argument is derived from the same composed filter input."""
    openapi = filter_schema.__get_pydantic_json_schema__(None, None)

    assert openapi["type"] == "object"
    assert openapi["additionalProperties"] is False
    assert "environment" not in openapi["properties"]
    assert {"agent", "resourceType", "resourceIdValue", "isOrphan", "modelVersion"} <= set(openapi["properties"])
    # enum filters are described by their GraphQL enum names
    assert openapi["properties"]["blocked"]["properties"]["eq"]["items"]["enum"]


def test_filter_schema_accepts_extension_contributed_fields() -> None:
    """
    A filter contributed by an extension is composed into the same filter input, so the REST layer accepts and
    describes the extension's fields without knowing anything about them.
    """

    @strawberry.input
    class ExampleResourceFilter(ResourceFilterABC):
        my_attr: str | None = strawberry.UNSET
        my_count: int | None = strawberry.UNSET

    class ExampleContribution(GraphQLContribution):
        @classmethod
        def get_target_model(cls) -> type:
            return models.Resource

        @classmethod
        def get_filter_input_class(cls) -> type[ResourceFilterABC] | None:
            return ExampleResourceFilter

    composed = get_schema({RESOURCE_CONTRIBUTABLE.type_name: [ExampleContribution]})
    filter_type = composed._schema.type_map[RESOURCE_CONTRIBUTABLE.filter_type_name]
    assert isinstance(filter_type, GraphQLInputObjectType)

    filter_schema = GraphQLFilterSchema()
    filter_schema.register_graphql_type(filter_type)

    # the extension's fields are part of the REST body, in their GraphQL (camelCase) form
    assert {"myAttr", "myCount"} <= set(filter_schema.graphql_type.fields)
    # ... alongside core's, and still without environment
    assert "agent" in filter_schema.graphql_type.fields
    assert "environment" not in filter_schema.graphql_type.fields

    # a body may combine core and extension fields
    body = {"agent": {"eq": ["agent1"]}, "myAttr": "my_value", "myCount": 3}
    assert filter_schema._validate(body) == body

    # the extension's fields are type checked like any other
    with pytest.raises(ValueError, match="Int cannot represent non-integer value"):
        filter_schema._validate({"myCount": "not-an-int"})

    # and they are described in the OpenAPI schema
    openapi = filter_schema.__get_pydantic_json_schema__(None, None)
    assert openapi["properties"]["myAttr"] == {"type": "string"}
    assert openapi["properties"]["myCount"] == {"type": "integer"}
