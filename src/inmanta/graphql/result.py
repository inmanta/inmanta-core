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

from inmanta.types import BaseModel
from strawberry.types.execution import ExecutionResult


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
