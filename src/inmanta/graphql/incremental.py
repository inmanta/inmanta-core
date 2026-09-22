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

Support for GraphQL incremental delivery.

A query can mark parts of itself with the @defer or @stream directive to indicate that they may be resolved
independently from the rest of the query. Such a query is not answered with a single response document. It produces a
sequence of payloads instead: a first one holding the part of the response that was not deferred, followed by one
payload per deferred part, sent as soon as that part is resolved.

This module turns that sequence of payloads into a response body for a client that can consume it in chunks. The
`inmanta.graphql.result` module covers the other case, where the payloads have to be assembled into a single document
because the client can only consume a complete response.
"""

import typing
from collections.abc import AsyncIterator, Callable

from graphql.execution import (
    IncrementalDeferResult,
    IncrementalStreamResult,
    InitialIncrementalExecutionResult,
    PendingResult,
    SubsequentIncrementalExecutionResult,
)
from strawberry.http import process_result
from strawberry.http.streaming import MultipartTransport
from strawberry.schema.schema import StreamResult
from strawberry.types.execution import ExecutionResult

# The media type a client has to accept to receive the payloads of a query as they are resolved, instead of receiving
# the complete response as a single document. It is the media type the GraphQL incremental delivery specification
# prescribes for this purpose.
MULTIPART_MIXED_CONTENT_TYPE = "multipart/mixed"

# One payload of a GraphQL operation, as produced by strawberry. An operation that doesn't defer or stream any part of
# itself produces a single ExecutionResult. One that does produces an InitialIncrementalExecutionResult followed by
# one SubsequentIncrementalExecutionResult per batch of resolved parts.
type OperationPayload = ExecutionResult | InitialIncrementalExecutionResult | SubsequentIncrementalExecutionResult
# A payload delivering the data of a single deferred (@defer) or streamed (@stream) part of an operation.
type IncrementalPayload = IncrementalDeferResult | IncrementalStreamResult
# A JSON encoder, used to serialize a payload into the response body.
type JsonEncoder = Callable[[object], str]


def accepts_incremental_delivery(accept_header: str | None) -> bool:
    """
    Return whether a client that sent the given Accept header is able to receive the payloads of a query as they are
    resolved.

    :param accept_header: the value of the Accept header of the request, or None when the request didn't set it.
    """
    if accept_header is None:
        return False
    return any(media_type.split(";")[0].strip() == MULTIPART_MIXED_CONTENT_TYPE for media_type in accept_header.split(","))


class PendingPartRegistry:
    """
    Keeps track of the parts of a GraphQL operation that are still being resolved.

    A payload that delivers the data of a deferred or streamed part of an operation identifies that part by id only.
    Where that part belongs in the response document, and the label the query gave it, are announced once, in an
    earlier payload. This registry records those announcements so that the data of a part can be related back to the
    position it belongs at.
    """

    def __init__(self) -> None:
        self.pending_parts: dict[str, PendingResult] = {}

    def register_announced_parts(self, payload: OperationPayload) -> None:
        """
        Record every part of the operation that the given payload announces as still being resolved.
        """
        for pending_part in getattr(payload, "pending", None) or []:
            self.pending_parts[pending_part.id] = pending_part

    def get_part_of(self, incremental_payload: IncrementalPayload) -> PendingResult:
        """
        Return the part of the operation that the given payload delivers the data of.
        """
        return self.pending_parts[incremental_payload.id]


class MultipartResponseEncoder:
    """
    Encodes the payloads of a GraphQL operation into a 'multipart/mixed' response body, in which every payload is a
    part of its own. That allows a client to process each of them as it arrives, rather than having to wait for the
    complete response.
    """

    def __init__(self, encode_json: JsonEncoder) -> None:
        """
        :param encode_json: the encoder used to serialize a payload into the body of a part.
        """
        self.encode_json = encode_json
        self.pending_parts = PendingPartRegistry()
        self.transport = MultipartTransport()

    @property
    def content_type(self) -> str:
        """
        The value to send as the Content-Type header of the response.
        """
        return self.transport.headers["Content-Type"]

    def encode(self, stream: StreamResult) -> AsyncIterator[str]:
        """
        Encode the payloads of a single operation into the chunks of the response body.
        """

        async def payload_documents() -> typing.AsyncGenerator[object, None]:
            async for payload in stream:
                yield self.to_document(payload)

        return self.transport.stream(payload_documents, self.encode_json)()

    def to_document(self, payload: OperationPayload) -> dict[str, typing.Any]:
        """
        Convert a payload into the JSON document that is sent to the client for it.

        The document follows the GraphQL incremental delivery specification: `hasNext` tells the client whether more
        payloads follow, `pending` announces the parts of the operation that are still being resolved, `incremental`
        carries the data of the parts that just resolved and `completed` reports the parts that are done.
        """
        self.pending_parts.register_announced_parts(payload)

        if isinstance(payload, SubsequentIncrementalExecutionResult):
            document: dict[str, typing.Any] = {"hasNext": payload.has_next, "extensions": payload.extensions}
            if payload.pending:
                document["pending"] = [pending_part.formatted for pending_part in payload.pending]
            if payload.completed:
                document["completed"] = [completed_part.formatted for completed_part in payload.completed]
            if payload.incremental:
                document["incremental"] = [
                    self.to_incremental_document(incremental_payload) for incremental_payload in payload.incremental
                ]
            return document

        if isinstance(payload, InitialIncrementalExecutionResult):
            return {
                "data": payload.data,
                **({"errors": [error.formatted for error in payload.errors]} if payload.errors else {}),
                "extensions": payload.extensions,
                "hasNext": payload.has_next,
                "pending": [pending_part.formatted for pending_part in payload.pending],
            }

        # The whole operation was resolved at once, so this single payload already holds the complete response.
        return dict(process_result(payload))

    def to_incremental_document(self, incremental_payload: IncrementalPayload) -> dict[str, typing.Any]:
        """
        Convert the data of one resolved part of the operation into the JSON document that is sent for it. The path
        and the label of the part are added, because the payload itself only identifies the part by id.
        """
        pending_part = self.pending_parts.get_part_of(incremental_payload)
        return {**incremental_payload.formatted, "path": pending_part.path, "label": pending_part.label}
