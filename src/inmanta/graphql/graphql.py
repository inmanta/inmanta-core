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
from inmanta.graphql.schema import GraphQLContext, get_schema
from inmanta.protocol import methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.decorators import handle
from inmanta.server import SLICE_COMPILER, SLICE_GRAPHQL, protocol
from inmanta.server.protocol import Server
from inmanta.server.services.compilerservice import CompilerService
from strawberry.schema.exceptions import CannotGetOperationTypeError
from strawberry.types.execution import ExecutionResult


class GraphQLSlice(protocol.ServerSlice):
    context: GraphQLContext | None

    def __init__(self) -> None:
        super().__init__(name=SLICE_GRAPHQL)
        self.context = None

    def get_dependencies(self) -> list[str]:
        return [SLICE_COMPILER]

    async def prestart(self, server: Server) -> None:
        compiler_service = server.get_slice(SLICE_COMPILER)
        assert isinstance(compiler_service, CompilerService)
        self.context = GraphQLContext(compiler_service=compiler_service)
        await super().prestart(server)

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
            execution_result = ExecutionResult(data=None, errors=[GraphQLError(e.as_http_error_reason())], extensions=None)
        graphql_result = GraphQLResult.from_execution_result(execution_result)
        return ReturnValue(status_code=graphql_result.status_code, response=graphql_result)

    @handle(methods_v2.graphql_schema)
    async def graphql_schema(self) -> dict[str, Any]:
        assert self.context is not None
        return get_schema(self.context).introspect()
