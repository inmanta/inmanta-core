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

from typing import Any

from graphql.error import GraphQLError
from inmanta.graphql.result import GraphQLResult
from inmanta.graphql.schema import CoreResourceFilter, GraphQLContext, ResourceFilterABC, get_schema
from inmanta.protocol import methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.decorators import handle
from inmanta.server import SLICE_COMPILER, SLICE_GRAPHQL, protocol
from inmanta.server.protocol import Server
from inmanta.server.services.compilerservice import CompilerService
from strawberry import Schema
from strawberry.schema.exceptions import CannotGetOperationTypeError
from strawberry.types.execution import ExecutionResult


class GraphQLSlice(protocol.ServerSlice):
    compiler_service: CompilerService | None
    schema: Schema | None
    all_filters: dict[str, type[ResourceFilterABC]]

    def __init__(self) -> None:
        super().__init__(name=SLICE_GRAPHQL)
        self.compiler_service = None
        self.schema = None
        self.all_filters = {}

    def get_dependencies(self) -> list[str]:
        return [SLICE_COMPILER]

    def register_extension_filter(self, extension_name: str, filter_cls: type[ResourceFilterABC]) -> None:
        """
        Register an extension filter.
        This is only possible if the composed ResourceFilter has yet to be generated
        and if the extension name has not already been registered.
        """
        if self.schema is None:
            if extension_name in self.all_filters:
                raise Exception(f"Extension {extension_name} already registered.")
            self.all_filters[extension_name] = filter_cls
        else:
            raise Exception(
                f"Can't register extension filter for {extension_name} because the GraphQL schema has already been generated"
            )

    async def prestart(self, server: Server) -> None:
        compiler_service = server.get_slice(SLICE_COMPILER)
        assert isinstance(compiler_service, CompilerService)
        self.compiler_service = compiler_service
        self.all_filters[SLICE_GRAPHQL] = CoreResourceFilter
        await super().prestart(server)

    async def start(self) -> None:
        assert self.compiler_service is not None
        self.schema = get_schema(
            GraphQLContext(compiler_service=self.compiler_service, resource_filter_components=list(self.all_filters.values()))
        )
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
