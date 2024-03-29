"""
    Copyright 2024 Inmanta

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

import abc
from types import TracebackType
from typing import Callable, Optional, Type

from asyncpg import Connection


class ConnectionMaybeInTransaction(abc.ABC):
    """A connection that is perhaps in a transaction"""

    def __init__(self, connection: Optional[Connection] = None) -> None:
        self.connection = connection

    @abc.abstractmethod
    def call_after_tx(self, finalizer: Callable[[], object]) -> None:
        """Add a method to be called after the transaction has committed successfully."""
        ...

    def __enter__(self) -> "ConnectionMaybeInTransaction":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        return None


class ConnectionNotInTransaction(ConnectionMaybeInTransaction):
    """Connection that is not in a transaction or absent"""

    def call_after_tx(self, finalizer: Callable[[], object]) -> None:
        finalizer()


class ConnectionInTransaction(ConnectionMaybeInTransaction):
    def __init__(self, connection: Connection) -> None:
        super().__init__(connection)
        self.finished_callbacks: list[Callable[[], object]] = []

    def call_after_tx(self, finalizer: Callable[[], object]) -> None:
        self.finished_callbacks.append(finalizer)

    def __enter__(self) -> "ConnectionInTransaction":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if exc_type is None:
            for callback in self.finished_callbacks:
                callback()
        return None
