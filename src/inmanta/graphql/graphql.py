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
from typing import Any

import strawberry
from graphql.error import GraphQLError
from inmanta.graphql.result import GraphQLResult
from inmanta.graphql.schema import BaseResourceFilter, GraphQLContext, StrawberryFilter, StrFilter, get_schema
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


class ExampleResourceFilter(StrawberryFilter):
    my_attr: StrFilter | None = None

    def apply_filters[*Ts](self, stmt: Select[tuple[*Ts]]) -> Select[tuple[*Ts]]:
        LOGGER.error("EXAMPLE FILTERS")
        return stmt


class GraphQLSlice(protocol.ServerSlice):
    context: GraphQLContext | None
    resource_filters: list[type[StrawberryFilter]]
    _composed_resource_filter_cls: type | None

    def __init__(self) -> None:
        super().__init__(name=SLICE_GRAPHQL)
        self.context = None
        self.resource_filters = []
        self._composed_resource_filter_cls = None

    def get_dependencies(self) -> list[str]:
        return [SLICE_COMPILER]

    async def prestart(self, server: Server) -> None:
        compiler_service = server.get_slice(SLICE_COMPILER)
        assert isinstance(compiler_service, CompilerService)
        self.update_resource_filter(BaseResourceFilter)
        self.update_resource_filter(ExampleResourceFilter)
        self.context = GraphQLContext(compiler_service=compiler_service, graphql_service=self)
        await super().prestart(server)

    def update_resource_filter(self, ext_filter: type[StrawberryFilter]):
        self.resource_filters.append(ext_filter)
        self._composed_resource_filter_cls = None

    def build_resource_filter(self) -> type:
        if self._composed_resource_filter_cls is None:
            bases = tuple(self.resource_filters)

            class ResourceFilter(*bases):
                def apply_filters(self, stmt):
                    for base in bases:
                        # Call each extension's apply_filters independently
                        if hasattr(base, "apply_filters"):
                            stmt = base.apply_filters(self, stmt)
                    return stmt

            ResourceFilter.__name__ = "ResourceFilter"

            self._composed_resource_filter_cls = strawberry.input(ResourceFilter)
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
