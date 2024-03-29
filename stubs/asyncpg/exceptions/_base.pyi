# Stubs for asyncpg.exceptions._base (Python 3)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from typing import Any, Optional, Type


class PostgresMessageMeta(type): ...

class PostgresMessage(metaclass=PostgresMessageMeta): ...

class PostgresError(PostgresMessage, Exception): ...

class FatalPostgresError(PostgresError): ...
class UnknownPostgresError(FatalPostgresError): ...

class InterfaceMessage:
    detail: Any = ...
    hint: Any = ...
    def __init__(self, *, detail: Optional[Any] = ..., hint: Optional[Any] = ...) -> None: ...

class InterfaceError(InterfaceMessage, Exception):
    def __init__(self, msg: Any, *, detail: Optional[Any] = ..., hint: Optional[Any] = ...) -> None: ...

class DataError(InterfaceError, ValueError): ...

class InterfaceWarning(InterfaceMessage, UserWarning):
    def __init__(self, msg: Any, *, detail: Optional[Any] = ..., hint: Optional[Any] = ...) -> None: ...

class InternalClientError(Exception): ...
class ProtocolError(InternalClientError): ...

class OutdatedSchemaCacheError(InternalClientError):
    schema_name: Any = ...
    data_type_name: Any = ...
    position: Any = ...
    def __init__(self, msg: Any, *, schema: Optional[Any] = ..., data_type: Optional[Any] = ..., position: Optional[Any] = ...) -> None: ...

class PostgresLogMessage(PostgresMessage):
    def __setattr__(self, name: Any, val: Any) -> None: ...
