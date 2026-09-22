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

import uuid
from collections import defaultdict

import graphql
import inmanta.data.sqlalchemy
import strawberry
from graphql.error import GraphQLError
from inmanta.graphql import rest_filter
from inmanta.graphql.result import GraphQLResult
from inmanta.graphql.schema import (
    CONTRIBUTABLE_MODELS,
    GraphQLContribution,
    GraphQLTypeName,
    build_request_context,
    get_schema,
    graphql_type_name,
)
from inmanta.protocol import methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.decorators import handle
from inmanta.server import SLICE_COMPILER, SLICE_GRAPHQL, protocol
from inmanta.server.protocol import Server
from inmanta.server.services.compilerservice import CompilerService
from inmanta.types import ResourceIdStr
from strawberry.schema.exceptions import CannotGetOperationTypeError
from strawberry.types.execution import ExecutionResult

# The name of the extension that registered a contribution.
type ExtensionName = str

# The number of resources `filter_resources` fetches per page.
RESOURCE_PAGE_SIZE_INTERNAL: int = 500


class GraphQLSlice(protocol.ServerSlice):
    compiler_service: CompilerService | None
    schema: strawberry.Schema | None
    # Registered contributions, grouped by the name of the object type they target (e.g. "Resource") and then by the
    # name of the extension that registered them: {type_name: {extension_name: contribution}}.
    extension_contributions: defaultdict[GraphQLTypeName, dict[ExtensionName, type[GraphQLContribution]]]

    def __init__(self) -> None:
        super().__init__(name=SLICE_GRAPHQL)
        self.compiler_service = None
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
        contributable = CONTRIBUTABLE_MODELS.get(target_model)
        if contributable is None:
            raise Exception(
                f"Can't register a GraphQL contribution for {graphql_type_name(target_model)}: "
                f"only contributions for {', '.join(contributable.type_name for contributable in CONTRIBUTABLE_MODELS.values())} are supported."
            )
        contributions_for_type = self.extension_contributions[contributable.type_name]
        if extension_name in contributions_for_type:
            raise Exception(
                f"Extension {extension_name} already registered a GraphQL contribution for {contributable.type_name}."
            )
        contributions_for_type[extension_name] = contribution

    async def prestart(self, server: Server) -> None:
        compiler_service = server.get_slice(SLICE_COMPILER)
        assert isinstance(compiler_service, CompilerService)
        self.compiler_service = compiler_service
        await super().prestart(server)

    async def start(self) -> None:
        # get_schema only needs the contributions grouped by target type; the extension names are bookkeeping for
        # registration, so we drop them here.
        self.schema = get_schema(
            {type_name: list(by_extension.values()) for type_name, by_extension in self.extension_contributions.items()},
        )
        resource_contributable = CONTRIBUTABLE_MODELS[inmanta.data.sqlalchemy.Resource]
        # Strawberry does not expose GraphQL schema instance publicly, hence the private _schema access.
        # inmanta-core constrains the strawberry package so risk should be minimal.
        graphql_filter_type = self.schema._schema.type_map[resource_contributable.filter_type_name]
        if not isinstance(graphql_filter_type, graphql.GraphQLInputObjectType):
            raise Exception("GraphQL schema invariant violation. This implies a bug in the orchestrator's GraphQL slice.")
        rest_filter.RESOURCE_FILTER_SCHEMA.register_graphql_type(graphql_filter_type)
        await super().start()

    async def _execute_query(
        self, query: str, variables: dict[str, object] | None = None, operation_name: str | None = None
    ) -> GraphQLResult:
        assert self.schema is not None
        assert self.compiler_service is not None
        # Build a fresh execution context (and, crucially, a fresh DataLoader) for every request. The loader's
        # cache then lives only for this request, so relationship data (e.g. Resource.state) is never served from a
        # cache populated by an earlier request.
        context_value = build_request_context(self.compiler_service)
        try:
            execution_result = await self.schema.execute(
                query,
                variable_values=variables,
                operation_name=operation_name,
                context_value=context_value,
            )
        except CannotGetOperationTypeError as e:
            execution_result = ExecutionResult(
                data=None, errors=[GraphQLError(message=e.as_http_error_reason(), original_error=e)], extensions=None
            )
        except Exception as e:
            execution_result = ExecutionResult(
                data=None, errors=[GraphQLError(message=str(e), original_error=e)], extensions=None
            )
        return GraphQLResult.from_execution_result(execution_result)

    @handle(methods_v2.graphql, operation_name="operationName")
    async def graphql(
        self, query: str, variables: dict[str, object] | None = None, operation_name: str | None = None
    ) -> ReturnValue[GraphQLResult]:
        graphql_result = await self._execute_query(query, variables, operation_name)
        return ReturnValue(status_code=graphql_result.status_code, response=graphql_result)

    @handle(methods_v2.graphql_schema)
    async def graphql_schema(self) -> dict[str, object]:
        assert self.schema is not None
        return self.schema.introspect()

    # TODO: outstanding (out of scope) issue: RPC limit to scheduler => create follow-up ticket in scaling epic.
    async def filter_resources(self, environment: uuid.UUID, filter: rest_filter.ResourceFilterArg) -> set[ResourceIdStr]:
        """
        Execute a graphql query on the given environment and with the given resource filter, returning the ids of the matched
        resources. Pages internally on the GraphQL method and collects results in a single set.

        :param environment: the environment the resources belong to.
        :param filter: The graphql-compatible resource filter.

        :raises GraphQLExecutionError: If a graphql execution error occurs.
        """

        query: str = """\
            query filterResources($filter: ResourceFilter!, $first: Int, $after: String) {
              resources(filter: $filter, first: $first, after: $after) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                edges {
                  node {
                    resourceId
                  }
                }
              }
            }
        """.rstrip()

        resource_ids: set[ResourceIdStr] = set()
        cursor: str | None = None
        while True:
            result: GraphQLResult = await self._execute_query(
                query,
                variables={
                    "filter": {**filter, "environment": str(environment)},
                    "first": RESOURCE_PAGE_SIZE_INTERNAL,
                    "after": cursor,
                },
            )
            result.raise_for_errors()
            assert result.data is not None

            connection = result.data["resources"]
            resource_ids.update(ResourceIdStr(edge["node"]["resourceId"]) for edge in connection["edges"])
            page_info = connection["pageInfo"]
            if not page_info["hasNextPage"]:
                return resource_ids
            cursor = page_info["endCursor"]
