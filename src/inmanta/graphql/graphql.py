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

import logging
import typing
from typing import Any

import strawberry
from graphql.error import GraphQLError
from inmanta.graphql.result import GraphQLResult
from inmanta.graphql.schema import BaseResourceFilter, CoreResourceFilter, GraphQLContext, get_schema
from inmanta.protocol import methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.decorators import handle
from inmanta.server import SLICE_COMPILER, SLICE_GRAPHQL, protocol
from inmanta.server.protocol import Server
from inmanta.server.services.compilerservice import CompilerService
from sqlalchemy import Select
from strawberry.schema.exceptions import CannotGetOperationTypeError
from strawberry.types.execution import ExecutionResult

LOGGER = logging.getLogger(__name__)


@strawberry.input
class ExampleFilter(BaseResourceFilter):
    my_attr: str | None = strawberry.UNSET

    @classmethod
    def apply_filter[*Ts](cls, stmt: Select[tuple[*Ts]], filter_instance: typing.Self) -> Select[tuple[*Ts]]:
        LOGGER.error(f"Applied filter {filter_instance.my_attr}")
        return stmt


class ResourceFilterEngine:
    def __init__(self) -> None:
        self.all_filters: list[type[BaseResourceFilter]] = []
        self.filter_fields: dict[str, type[BaseResourceFilter]] = {}

    def register_extension_filter(self, filter_cls: type[BaseResourceFilter]) -> None:
        self.all_filters.append(filter_cls)

    def build_strawberry_filter(self) -> type[BaseResourceFilter]:
        """
        Builds resource filter for use with Strawberry.
        """
        return strawberry.input(type("ResourceFilter", tuple(self.all_filters), {}), name="ResourceFilter")

    def apply_resource_filters[*Ts](self, stmt: Select[tuple[*Ts]], filter_instance: BaseResourceFilter) -> Select[tuple[*Ts]]:
        for filter_cls in self.all_filters:
            stmt = filter_cls.apply_filter(stmt=stmt, filter_instance=filter_instance)
        return stmt


class GraphQLSlice(protocol.ServerSlice):
    context: GraphQLContext | None
    _composed_resource_filter_cls: type[BaseResourceFilter] | None
    resource_filter_engine: ResourceFilterEngine

    def __init__(self) -> None:
        super().__init__(name=SLICE_GRAPHQL)
        self.context = None
        self._composed_resource_filter_cls = None
        self.resource_filter_engine = ResourceFilterEngine()

    def get_dependencies(self) -> list[str]:
        return [SLICE_COMPILER]

    async def prestart(self, server: Server) -> None:
        compiler_service = server.get_slice(SLICE_COMPILER)
        assert isinstance(compiler_service, CompilerService)
        self.resource_filter_engine.register_extension_filter(ExampleFilter)
        self.resource_filter_engine.register_extension_filter(CoreResourceFilter)
        self.context = GraphQLContext(compiler_service=compiler_service, graphql_service=self)
        await super().prestart(server)

    def update_resource_filter(self, ext_filter: type[BaseResourceFilter]) -> None:
        self.resource_filter_engine.register_extension_filter(ext_filter)
        self._composed_resource_filter_cls = None

    def build_resource_filter(self) -> type[BaseResourceFilter]:
        if self._composed_resource_filter_cls is None:
            self._composed_resource_filter_cls = self.resource_filter_engine.build_strawberry_filter()
        return self._composed_resource_filter_cls

    @handle(methods_v2.graphql, operation_name="operationName")
    async def graphql(
        self, query: str, variables: dict[str, Any] | None = None, operation_name: str | None = None
    ) -> ReturnValue[GraphQLResult]:
        assert self.context is not None
        try:
            execution_result = await get_schema(self.context).execute(
                query, variable_values=variables, operation_name=operation_name
            )
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
        assert self.context is not None
        return get_schema(self.context).introspect()
