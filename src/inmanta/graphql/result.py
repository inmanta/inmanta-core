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

from graphql import GraphQLError
from inmanta.types import BaseModel
from strawberry.types.execution import ExecutionResult


class SerializableGraphQLError(BaseModel):
    """
    The original GraphQLError is not json serializable, so we created this class to properly return the error to the user
    """

    message: str
    path: list[str | int] | None
    locations: list[dict[str, int]] | None


class GraphQLResult(BaseModel):
    """
    A result that conforms to the GraphQL spec and is compatible with ReturnValue
    """

    data: dict[str, typing.Any] | None
    errors: list[SerializableGraphQLError] | None
    extensions: dict[str, typing.Any] | None = None

    @property
    def status_code(self) -> int:
        """
        The status code to send in ReturnValue
        """
        return 200 if self.data else 400

    @classmethod
    def _serialize_error(cls, error: GraphQLError) -> SerializableGraphQLError:
        """
        Converts the original GraphQLError into a serializable object
        """
        return SerializableGraphQLError(
            message=error.message,
            path=error.path,
            locations=[{"line": loc.line, "column": loc.column} for loc in (error.locations or [])],
        )

    @classmethod
    def from_execution_result(cls, execution_result: ExecutionResult) -> "GraphQLResult":
        """
        Creates a GraphQLResult object from the ExecutionResult returned by strawberry
        """
        return cls(
            data=execution_result.data,
            errors=[cls._serialize_error(error) for error in execution_result.errors] if execution_result.errors else None,
            extensions=execution_result.extensions,
        )
