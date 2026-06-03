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
from inmanta.data import get_session_factory
from inmanta.graphql.result import GraphQLResult
from inmanta.graphql.schema import _resource_query_contributions, get_schema
from inmanta.protocol import methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.decorators import handle
from inmanta.server import SLICE_COMPILER, SLICE_DRYRUN, SLICE_GRAPHQL, SLICE_ORCHESTRATION, protocol
from inmanta.server.protocol import Server
from inmanta.server.services.compilerservice import CompilerService
from inmanta.server.services.dryrunservice import DyrunService
from inmanta.server.services.orchestrationservice import OrchestrationService
from strawberry.schema.exceptions import CannotGetOperationTypeError
from strawberry.types.execution import ExecutionResult
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader


class GraphQLSlice(protocol.ServerSlice):
    compiler_service: CompilerService | None
    orchestration_service: OrchestrationService | None
    dryrun_service: DyrunService | None

    def __init__(self) -> None:
        super().__init__(name=SLICE_GRAPHQL)
        self.compiler_service = None
        self.orchestration_service = None
        self.dryrun_service = None

    def get_dependencies(self) -> list[str]:
        return [SLICE_COMPILER]

    async def prestart(self, server: Server) -> None:
        compiler_service = server.get_slice(SLICE_COMPILER)
        assert isinstance(compiler_service, CompilerService)
        self.compiler_service = compiler_service
        # Stored without adding formal slice dependencies to avoid a circular chain:
        # resource → graphql → orchestration → resource.
        # Both services are fully started before any requests can reach this slice
        # (transport waits for all slices), so accessing them at request time is safe.
        self.orchestration_service = server.get_slice(SLICE_ORCHESTRATION)  # type: ignore[assignment]
        self.dryrun_service = server.get_slice(SLICE_DRYRUN)  # type: ignore[assignment]
        await super().prestart(server)

    def _build_context(self) -> dict[str, Any]:
        loader = StrawberrySQLAlchemyLoader(async_bind_factory=get_session_factory())
        context: dict[str, Any] = {
            "sqlalchemy_loader": loader,
            "compiler_service": self.compiler_service,
            "orchestration_service": self.orchestration_service,
            "dryrun_service": self.dryrun_service,
        }
        for contribution in _resource_query_contributions:
            context.update(contribution.get_context_loaders())
        return context

    async def execute_query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
    ) -> ExecutionResult:
        """
        Execute a GraphQL query and return the raw ExecutionResult.

        Callers outside the GraphQL slice (e.g. REST handlers that translate their
        input to GraphQL) should use this method rather than calling the HTTP handler
        directly.  The context (DataLoaders, SQLAlchemy loader, compiler service) is
        built the same way as for HTTP GraphQL requests.
        """
        assert self.compiler_service is not None
        try:
            return await get_schema().execute(
                query, variable_values=variables, operation_name=operation_name, context_value=self._build_context()
            )
        except CannotGetOperationTypeError as e:
            return ExecutionResult(
                data=None, errors=[GraphQLError(message=e.as_http_error_reason(), original_error=e)], extensions=None
            )
        except Exception as e:
            return ExecutionResult(
                data=None, errors=[GraphQLError(message=str(e), original_error=e)], extensions=None
            )

    @handle(methods_v2.graphql, operation_name="operationName")
    async def graphql(
        self, query: str, variables: dict[str, Any] | None = None, operation_name: str | None = None
    ) -> ReturnValue[GraphQLResult]:
        assert self.compiler_service is not None
        execution_result = await self.execute_query(query, variables, operation_name)
        graphql_result = GraphQLResult.from_execution_result(execution_result)
        return ReturnValue(status_code=graphql_result.status_code, response=graphql_result)

    @handle(methods_v2.graphql_schema)
    async def graphql_schema(self) -> dict[str, Any]:
        assert self.compiler_service is not None
        return get_schema().introspect()
