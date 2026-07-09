"""
Copyright 2025 Inmanta
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

from collections import defaultdict
from typing import Any

from graphql import GraphQLInputObjectType
from graphql.error import GraphQLError
from inmanta.graphql.rest_filter import graphql_input_registry, strip_input_field
from inmanta.graphql.result import GraphQLResult
from inmanta.graphql.schema import (
    CONTRIBUTABLE_MODELS,
    GraphQLContext,
    GraphQLContribution,
    GraphQLTypeName,
    get_schema,
    graphql_type_name,
)
from inmanta.protocol import methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.decorators import handle
from inmanta.server import SLICE_COMPILER, SLICE_GRAPHQL, protocol
from inmanta.server.protocol import Server
from inmanta.server.services.compilerservice import CompilerService
from strawberry import Schema
from strawberry.schema.exceptions import CannotGetOperationTypeError
from strawberry.types.execution import ExecutionResult

# The name of the extension that registered a contribution.
type ExtensionName = str


class GraphQLSlice(protocol.ServerSlice):
    context: GraphQLContext | None
    schema: Schema | None
    # Registered contributions, grouped by the name of the object type they target (e.g. "Resource") and then by the
    # name of the extension that registered them: {type_name: {extension_name: contribution}}.
    extension_contributions: defaultdict[GraphQLTypeName, dict[ExtensionName, type[GraphQLContribution]]]

    def __init__(self) -> None:
        super().__init__(name=SLICE_GRAPHQL)
        self.context = None
        self.schema = None
        self.extension_contributions = defaultdict(dict)

    def get_dependencies(self) -> list[str]:
        return [SLICE_COMPILER]

    def register_graphql_contribution_for_extension(self, extension_name: str, contribution: type[GraphQLContribution]) -> None:
        """
        Register an extension contribution. Only possible before the slice starts (during the `prestart` stage) and
        only for one of the supported object types (see REGISTRABLE_MODELS). An extension can register several
        contributions (one per object type it extends), but not two contributions for the same object type.

        :param extension_name: the name of the extension registering the contribution. Used for bookkeeping (so an
            extension can't register two contributions for the same object type) and in error messages.
        :param contribution: the contribution to register. Its target object type is determined by
            `contribution.get_target_model()`.
        """
        if self.schema is not None:
            raise Exception(
                f"Can't register extension contribution for {extension_name} because the GraphQLSlice was already started."
            )
        target_model = contribution.get_target_model()
        type_name = graphql_type_name(target_model)
        if target_model not in CONTRIBUTABLE_MODELS:
            raise Exception(
                f"Can't register a GraphQL contribution for {type_name}: "
                f"only contributions for {', '.join(graphql_type_name(model) for model in CONTRIBUTABLE_MODELS)} are supported."
            )
        contributions_for_type = self.extension_contributions[type_name]
        if extension_name in contributions_for_type:
            raise Exception(f"Extension {extension_name} already registered a GraphQL contribution for {type_name}.")
        contributions_for_type[extension_name] = contribution

    async def prestart(self, server: Server) -> None:
        compiler_service = server.get_slice(SLICE_COMPILER)
        assert isinstance(compiler_service, CompilerService)
        self.context = GraphQLContext(compiler_service=compiler_service)
        await super().prestart(server)

    async def start(self) -> None:
        assert self.context is not None
        # get_schema only needs the contributions grouped by target type; the extension names are bookkeeping for
        # registration, so we drop them here.
        self.schema = get_schema(
            self.context,
            {type_name: list(by_extension.values()) for type_name, by_extension in self.extension_contributions.items()},
        )
        # Publish the composed ResourceFilter (minus `environment`, which REST supplies as the tid) so REST endpoints
        # can validate and document their filter body against the exact same GraphQL type (see rest_filter).
        resource_filter_type = self.schema._schema.type_map["ResourceFilter"]
        assert isinstance(resource_filter_type, GraphQLInputObjectType)
        graphql_input_registry.publish("ResourceFilter", strip_input_field(resource_filter_type, "environment"))
        await super().start()

    @handle(methods_v2.graphql, operation_name="operationName")
    async def graphql(
        self, query: str, variables: dict[str, Any] | None = None, operation_name: str | None = None
    ) -> ReturnValue[GraphQLResult]:
        assert self.schema is not None
        try:
            execution_result = await self.schema.execute(query, variable_values=variables, operation_name=operation_name)
        except CannotGetOperationTypeError as e:
            execution_result = ExecutionResult(
                data=None, errors=[GraphQLError(message=e.as_http_error_reason(), original_error=e)], extensions=None
            )
        except Exception as e:
            execution_result = ExecutionResult(
                data=None, errors=[GraphQLError(message=str(e), original_error=e)], extensions=None
            )
        graphql_result = GraphQLResult.from_execution_result(execution_result)
        return ReturnValue(status_code=graphql_result.status_code, response=graphql_result)

    @handle(methods_v2.graphql_schema)
    async def graphql_schema(self) -> dict[str, Any]:
        assert self.schema is not None
        return self.schema.introspect()
