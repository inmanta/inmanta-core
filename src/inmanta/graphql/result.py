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

import typing

from graphql.error import GraphQLError
from graphql.execution import IncrementalStreamResult, SubsequentIncrementalExecutionResult
from inmanta.graphql.incremental import IncrementalPayload, OperationPayload, PendingPartRegistry
from inmanta.types import BaseModel
from strawberry.schema.schema import StreamResult
from strawberry.types.execution import ExecutionResult

# One element of a path into the response document: either the name of a field or, when the element addresses an
# entry of a list, the position of that entry in the list.
type PathSegment = str | int


class GraphQLResult(BaseModel):
    """
    A result that conforms to the GraphQL spec and is compatible with ReturnValue
    """

    data: dict[str, typing.Any] | None
    errors: list[str] | None
    extensions: dict[str, typing.Any] | None = None

    @property
    def status_code(self) -> int:
        """
        The status code to send in ReturnValue
        """
        return 200 if self.data else 400

    @classmethod
    def from_execution_result(cls, execution_result: ExecutionResult) -> "GraphQLResult":
        """
        Creates a GraphQLResult object from the ExecutionResult returned by strawberry
        """
        return cls(
            data=execution_result.data,
            errors=[error.message for error in execution_result.errors] if execution_result.errors else None,
            extensions=execution_result.extensions,
        )

    @classmethod
    async def from_stream(cls, stream: StreamResult) -> "GraphQLResult":
        """
        Creates a GraphQLResult object from the payloads produced for a single GraphQL operation.

        A query that doesn't use the @defer or @stream directives produces a single payload, which already holds the
        complete response. A query that does use them produces one payload per deferred part of the query, each
        holding only that part of the response. This method waits for all of them and assembles them into one
        complete response document, for a client that is unable to consume the payloads as they arrive.
        """
        assembler = SingleDocumentAssembler()
        async for payload in stream:
            assembler.add_payload(payload)
        return assembler.to_result()


class SingleDocumentAssembler:
    """
    Assembles the payloads of one GraphQL operation into a single response document.
    """

    def __init__(self) -> None:
        self.data: dict[str, typing.Any] | None = None
        self.errors: list[GraphQLError] = []
        self.extensions: dict[str, typing.Any] | None = None
        self.pending_parts = PendingPartRegistry()

    def add_payload(self, payload: OperationPayload) -> None:
        """
        Merge a single payload into the response document under construction.
        """
        self.pending_parts.register_announced_parts(payload)

        if isinstance(payload, SubsequentIncrementalExecutionResult):
            for incremental_payload in payload.incremental or []:
                self.add_incremental_payload(incremental_payload)
            for completed_part in payload.completed or []:
                # A part of the operation that failed to resolve reports its errors when it completes, instead of
                # delivering data for them.
                self.errors.extend(completed_part.errors or [])
            return

        # The first payload holds the part of the response that was not deferred. It is the document that the data of
        # the deferred parts is merged into.
        self.data = payload.data
        self.errors.extend(payload.errors or [])
        self.extensions = payload.extensions

    def add_incremental_payload(self, incremental_payload: IncrementalPayload) -> None:
        """
        Merge the data of one resolved part of the operation into the response document, at the position that part
        was announced at.
        """
        self.errors.extend(incremental_payload.errors or [])
        pending_part = self.pending_parts.get_part_of(incremental_payload)
        target = self.resolve_path([*pending_part.path, *(incremental_payload.sub_path or [])])
        if isinstance(incremental_payload, IncrementalStreamResult):
            # A streamed field delivers further entries for a list that is already part of the response document.
            assert isinstance(target, list)
            target.extend(incremental_payload.items or [])
        else:
            # A deferred fragment delivers further fields for an object that is already part of the response document.
            assert isinstance(target, dict)
            target.update(incremental_payload.data or {})

    def resolve_path(self, path: typing.Sequence[PathSegment]) -> typing.Any:
        """
        Return the part of the response document at the given path. An empty path addresses the document itself.
        """
        target: typing.Any = self.data
        for segment in path:
            target = target[segment]
        return target

    def to_result(self) -> GraphQLResult:
        """
        Return the assembled response document.
        """
        return GraphQLResult(
            data=self.data,
            errors=[error.message for error in self.errors] if self.errors else None,
            extensions=self.extensions,
        )
