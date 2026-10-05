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

import dataclasses
import uuid
from collections import defaultdict
from typing import Any, cast

import graphql
import inmanta.data.sqlalchemy as models
import strawberry
from graphql.error import GraphQLError
from inmanta.data import get_session
from inmanta.graphql import exceptions, rest_filter
from inmanta.graphql.result import GraphQLResult
from inmanta.graphql.schema import (
    CONTRIBUTABLE_MODELS,
    RESOURCE_CONTRIBUTABLE,
    ComposedSchema,
    CoreGraphQLContribution,
    CoreResourceFilter,
    GraphQLContribution,
    GraphQLTypeName,
    build_request_context,
    get_schema,
    graphql_type_name,
    select_resources,
)
from inmanta.protocol import methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.decorators import handle
from inmanta.server import SLICE_COMPILER, SLICE_GRAPHQL, protocol
from inmanta.server.protocol import Server
from inmanta.server.services.compilerservice import CompilerService
from inmanta.types import ResourceIdStr
from sqlalchemy import select
from strawberry.schema.exceptions import CannotGetOperationTypeError
from strawberry.types.arguments import convert_argument
from strawberry.types.execution import ExecutionResult

# The name of the extension that registered a contribution.
type ExtensionName = str


@dataclasses.dataclass(frozen=True, kw_only=True)
class FilteredResources:
    """
    The resources matching a resource filter.

    :param resource_ids: The ids of the matching resources.
    :param model_version: The model version all matching resources belong to.
    """

    resource_ids: set[ResourceIdStr]
    model_version: int


class GraphQLSlice(protocol.ServerSlice):
    compiler_service: CompilerService | None
    schema: strawberry.Schema | None
    composed_schema: ComposedSchema | None
    # Registered contributions, grouped by the name of the object type they target (e.g. "Resource") and then by the
    # name of the extension that registered them: {type_name: {extension_name: contribution}}.
    extension_contributions: defaultdict[GraphQLTypeName, dict[ExtensionName, type[GraphQLContribution]]]

    def __init__(self) -> None:
        super().__init__(name=SLICE_GRAPHQL)
        self.compiler_service = None
        self.schema = None
        self.composed_schema = None
        self.extension_contributions = defaultdict(dict)
        self.register_graphql_contribution_for_extension("core", CoreGraphQLContribution)

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
            contributable_types: str = ", ".join(contributable.type_name for contributable in CONTRIBUTABLE_MODELS.values())
            raise Exception(
                f"Can't register a GraphQL contribution for {graphql_type_name(target_model)}: "
                f"only contributions for {contributable_types} are supported."
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
        self.composed_schema = get_schema(
            {type_name: list(by_extension.values()) for type_name, by_extension in self.extension_contributions.items()},
        )
        self.schema = self.composed_schema.schema

        # register resource filter schema for the filter_resources functionality
        #
        # Strawberry does not expose GraphQL schema instance publicly, hence the private _schema access.
        # inmanta-core constrains the strawberry package so risk should be minimal.
        graphql_filter_type = self.schema._schema.type_map[RESOURCE_CONTRIBUTABLE.filter_type_name]
        if not isinstance(graphql_filter_type, graphql.GraphQLInputObjectType):
            raise Exception("GraphQL schema invariant violation. This implies a bug in the orchestrator's GraphQL slice.")
        rest_filter.RESOURCE_FILTER_SCHEMA.register_graphql_type(graphql_filter_type)
        # assert schema invariants
        schema_fields = rest_filter.RESOURCE_FILTER_SCHEMA.graphql_type.fields
        assert rest_filter.MODEL_VERSION_FIELD in schema_fields
        assert rest_filter.IS_ORPHAN_FIELD in schema_fields

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
    async def graphql_schema(self) -> dict[str, Any]:
        assert self.schema is not None
        return self.schema.introspect()

    async def filter_resources(self, environment: uuid.UUID, filter: rest_filter.ResourceFilterArg) -> FilteredResources | None:
        """
        Return the resources that the GraphQL `resources` query returns for the given environment and resource filter.
        Runs the statement of that query in one go, and selects only the id and the model version of each resource.

        :param environment: the environment the resources belong to.
        :param filter: The graphql-compatible resource filter.

        :return: the resources matching the filter, and the model version they all belong to, or None when no resource
            matches.
        :raises InvalidFilter: The filter is invalid, or the matched resources belong to more than one model version.
        """
        assert self.schema is not None
        assert self.composed_schema is not None

        # Convert the filter to the filter argument of the `resources` query, the way GraphQL does
        graphql_filter_type = self.schema._schema.type_map[RESOURCE_CONTRIBUTABLE.filter_type_name]
        assert isinstance(graphql_filter_type, graphql.GraphQLInputObjectType)
        coerced_filter = graphql.coerce_input_value({**filter, "environment": str(environment)}, graphql_filter_type)
        # The REST layer already validated the filter against this type
        assert coerced_filter is not graphql.Undefined
        resource_filter = convert_argument(
            coerced_filter,
            self.composed_schema.resource_filter_input,
            scalar_registry=self.schema.schema_converter.scalar_registry,
            config=self.schema.config,
        )

        try:
            stmt, filter_instances = select_resources(
                select(models.ResourcePersistentState.resource_id, models.Configurationmodel.version).select_from(
                    models.Resource
                ),
                cast(CoreResourceFilter, resource_filter),
                self.composed_schema.resource_filter_components,
            )
            for filter_instance in filter_instances:
                stmt = filter_instance.apply_filter(stmt)
        except ValueError as e:
            raise exceptions.InvalidFilter(str(e)) from e
        async with get_session() as session:
            rows = (await session.execute(stmt)).all()

        model_versions = {model_version for _, model_version in rows}
        if len(model_versions) > 1:
            versions = ", ".join(str(version) for version in sorted(model_versions))
            raise exceptions.InvalidFilter(
                f"The resources matching the filter belong to multiple model versions ({versions}), while they must all"
                f" belong to one. This usually happens when you don't pin a specific version and isOrphan: True or unset."
            )
        if not rows:
            return None
        return FilteredResources(
            resource_ids={ResourceIdStr(resource_id) for resource_id, _ in rows}, model_version=model_versions.pop()
        )

    async def filter_resources_for_deploy(
        self, environment: uuid.UUID, filter: rest_filter.ResourceFilterArg
    ) -> set[ResourceIdStr]:
        """
        Execute a graphql query on the given environment and with the given resource filter for deploy purposes. Similar to
        filter_resources, but strengthens the filter with the implied "latest version" fields.

        :param environment: the environment the resources belong to.
        :param filter: The graphql-compatible resource filter.

        :raises InvalidFilter: The filter is invalid, or not suitable in the deploy context.
        """
        if filter.get(rest_filter.MODEL_VERSION_FIELD) is not None:
            raise exceptions.InvalidFilter(
                f"Cannot deploy a specific model version: '{rest_filter.MODEL_VERSION_FIELD}' is not allowed for deploy."
            )
        if filter.get(rest_filter.IS_ORPHAN_FIELD) is True:
            raise exceptions.InvalidFilter(
                f"Cannot deploy orphaned resources: the '{rest_filter.IS_ORPHAN_FIELD}' filter must be omitted or set to false."
            )

        deploy_filter = {**filter, rest_filter.IS_ORPHAN_FIELD: False}
        matched = await self.filter_resources(environment, deploy_filter)
        return matched.resource_ids if matched is not None else set()
