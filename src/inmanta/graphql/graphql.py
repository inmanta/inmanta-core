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

from inmanta.graphql.schema import GraphQLMetadata, get_schema
from inmanta.protocol import methods_v2
from inmanta.protocol.decorators import handle
from inmanta.server import SLICE_COMPILER, SLICE_GRAPHQL, protocol
from inmanta.server.protocol import Server
from inmanta.server.services.compilerservice import CompilerService


class GraphQLSlice(protocol.ServerSlice):
    metadata: GraphQLMetadata

    def __init__(self) -> None:
        super().__init__(name=SLICE_GRAPHQL)

    def get_dependencies(self) -> list[str]:
        return [SLICE_COMPILER]

    async def prestart(self, server: Server) -> None:
        compiler_service = server.get_slice(SLICE_COMPILER)
        assert isinstance(compiler_service, CompilerService)
        self.metadata = GraphQLMetadata(compiler_service=compiler_service)
        await super().prestart(server)

    @handle(methods_v2.graphql)
    async def graphql(self, query: str) -> Any:  # Actual return type: strawberry.types.execution.ExecutionResult
        return await get_schema(self.metadata).execute(query)
