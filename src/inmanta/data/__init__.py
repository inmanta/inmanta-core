"""
Copyright 2017 Inmanta

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

import asyncio
import copy
import datetime
import enum
import itertools
import json
import logging
import re
import typing
import uuid
import warnings
from abc import ABC, abstractmethod
from collections import abc, defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable, Collection, Iterable, Iterator, Sequence, Set
from configparser import RawConfigParser
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from itertools import chain
from re import Pattern
from typing import Generic, NewType, Optional, TypeVar, Union, cast, overload
from uuid import UUID

import asyncpg
import dateutil
import more_itertools
import pydantic
import pydantic.tools
import typing_inspect
from asyncpg import Connection
from asyncpg.exceptions import SerializationError
from asyncpg.protocol import Record

import inmanta.db.versions
import inmanta.protocol
import inmanta.types
from crontab import CronTab
from inmanta import const, resources, util
from inmanta.const import NAME_RESOURCE_ACTION_LOGGER, AgentStatus, LogLevel, ResourceState
from inmanta.data import model as m
from inmanta.data import schema
from inmanta.data.model import AttributeStateChange, AuthMethod, BaseModel, PagingBoundaries, PipConfig, ReleasedResourceState
from inmanta.data.sqlalchemy import AgentModules, InmantaModule, ModuleFiles
from inmanta.deploy import state
from inmanta.protocol.exceptions import BadRequest, NotFound
from inmanta.server import config
from inmanta.stable_api import stable_api
from inmanta.types import (
    JsonType,
    PrimitiveTypes,
    ResourceIdStr,
    ResourceType,
    ResourceVersionIdStr,
    api_boundary_datetime_normalizer,
)
from inmanta.util import parse_timestamp
from inmanta.vendor import pyformance
from sqlalchemy import URL, AdaptedConnection, NullPool
from sqlalchemy.dialects import registry
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import ConnectionPoolEntry

"""
Global reference to the SQL Alchemy engine
Main APIs to interact with it:
- start_engine()
- stop_engine()
"""
ENGINE: AsyncEngine | None = None

"""
Object that creates async sessions.
Used mainly by our GraphQL implementation via these APIs:
- get_session_factory()
- get_session()
"""
SESSION_FACTORY: async_sessionmaker[AsyncSession] | None = None


LOGGER = logging.getLogger(__name__)

DBLIMIT = 100000
APILIMIT = 1000

# TODO: disconnect
# TODO: difference between None and not set

# Used as the 'default' parameter value for the Field class, when no default value has been set
default_unset = object()

PRIMITIVE_SQL_TYPES = Union[str, int, bool, datetime.datetime, UUID]

"""
Locking order rules:
In general, locks should be acquired consistently with delete cascade lock order, which is top down. Additional lock orderings
are as follows. This list should be extended when new locks (explicit or implicit) are introduced. The rules below are written
as `A -> B`, meaning A should be locked before B in any transaction that acquires a lock on both.
- Agentprocess -> Agentinstance -> Agent
- ResourcePersistentState -> Scheduler
"""


class PartialBaseMissing(ValueError):
    """
    A base version was provided in the context of a partial export / partial model read, but the base version does not exist
    or does not meet criteria.
    """


@enum.unique
class QueryType(str, enum.Enum):
    def _generate_next_value_(name, start: int, count: int, last_values: abc.Sequence[object]) -> str:  # noqa: N805
        """
        Make enum.auto() return the name of the enum member in lower case.
        """
        return name.lower()

    EQUALS = enum.auto()  # The filter value equals the value in the database
    CONTAINS = enum.auto()  # Any of the filter values are equal to the value in the database (exact match)
    IS_NOT_NULL = enum.auto()  # The value is NULL in the database
    CONTAINS_PARTIAL = enum.auto()  # Any of the filter values are equal to the value in the database (partial match)
    RANGE = enum.auto()  # The values in the database are in the range described by the filter values and operators
    NOT_CONTAINS = enum.auto()  # None of the filter values are equal to the value in the database (exact match)
    COMBINED = enum.auto()  # The value describes a combination of other query types


class InvalidQueryType(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TableLockMode(enum.Enum):
    """
    Table level locks as defined in the PostgreSQL docs:

    https://www.postgresql.org/docs/13/explicit-locking.html#LOCKING-TABLES. When acquiring a lock, make sure to use the same
    locking order accross transactions (as described at the top of this module) to prevent deadlocks and to otherwise respect
    the consistency docs: https://www.postgresql.org/docs/13/applevel-consistency.html#NON-SERIALIZABLE-CONSISTENCY.

    Not all lock modes are currently supported to keep the interface minimal (only include what we actually use). This class
    may be extended when a new lock mode is required.
    """

    ROW_EXCLUSIVE = "ROW EXCLUSIVE"
    SHARE_UPDATE_EXCLUSIVE = "SHARE UPDATE EXCLUSIVE"
    SHARE = "SHARE"
    SHARE_ROW_EXCLUSIVE = "SHARE ROW EXCLUSIVE"


class RowLockMode(enum.Enum):
    """
    Row level locks as defined in the PostgreSQL docs: https://www.postgresql.org/docs/13/explicit-locking.html#LOCKING-ROWS.
    When acquiring a lock, make sure to use the same locking order accross transactions (as described at the top of this
    module) to prevent deadlocks and to otherwise respect the consistency docs:
    https://www.postgresql.org/docs/13/applevel-consistency.html#NON-SERIALIZABLE-CONSISTENCY.
    """

    FOR_UPDATE = "FOR UPDATE"
    FOR_NO_KEY_UPDATE = "FOR NO KEY UPDATE"
    FOR_SHARE = "FOR SHARE"
    FOR_KEY_SHARE = "FOR KEY SHARE"


class RangeOperator(enum.Enum):
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="

    @property
    def pg_value(self) -> str:
        return self.value

    @classmethod
    def parse(cls, text: str) -> "RangeOperator":
        try:
            return cls[text.upper()]
        except KeyError:
            raise ValueError(f"Failed to parse {text} as a RangeOperator")


RangeConstraint = Sequence[tuple[RangeOperator, int]]
DateRangeConstraint = Sequence[tuple[RangeOperator, datetime.datetime]]
QueryFilter = tuple[QueryType, object]


class PagingCounts:
    def __init__(self, total: int, before: int, after: int) -> None:
        self.total = total
        self.before = before
        self.after = after


class InvalidQueryParameter(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidFieldNameException(Exception):
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


ColumnNameStr = NewType("ColumnNameStr", str)
"""
    A valid database column name
"""

OrderStr = NewType("OrderStr", str)
"""
    A valid database ordering
"""


class ArgumentCollector:
    """
    Small helper to make placeholders for query arguments

    args = ArgumentCollector()
    query = f"SELECT * FROM table WHERE a = {args(a_value)} AND b = {args(b_value)}"
    con.fetch(query, *args.get_values())
    """

    def __init__(self, offset: int = 0, de_duplicate: bool = False) -> None:
        """

        :param offset: the smallest number already in use, the next one given out will be offset+1
        :param de_duplicate: if the value is the same, return the same number
        """
        self.args: list[object] = []
        self.offset = offset
        self.de_duplicate = de_duplicate

    def __call__(self, entry: object) -> typing.LiteralString:
        if self.de_duplicate and entry in self.args:
            return "$" + str(self.args.index(entry) + 1 + self.offset)
        self.args.append(entry)
        return "$" + str(len(self.args) + self.offset)

    def get_values(self) -> list[object]:
        return self.args


class PagingOrder(str, enum.Enum):
    ASC = "ASC"
    DESC = "DESC"

    def invert(self) -> "PagingOrder":
        if self == PagingOrder.ASC:
            return PagingOrder.DESC
        return PagingOrder.ASC

    def db_form(self, *, nullable: bool = True) -> OrderStr:
        # The current filtering and sorting framework has the built-in assumption that nulls are considered the lowest values,
        # hence we must deviate from postgres' default order. As a result, we may lose the opportunity to use indexes, which
        # use the same order.
        # The framework can not easily be refactored because
        #   1. Not all column types have a sane MAX value to coalesce to
        #   2. The alternative approach to use a window function `row_number() OVER (ORDER BY ...)`, selecting on the ids of
        #       the first and last elements in the page, is more accurate, and does hit the indexes, but it also builds the
        #       row number for each row, which ends up costing even more.
        if nullable:
            if self == PagingOrder.ASC:
                return OrderStr("ASC NULLS FIRST")
            return OrderStr("DESC NULLS LAST")
        # Luckily, for NOT NULL columns we will never encounter the COALESCE issue, so we can safely use the default order.
        else:
            return OrderStr(self.value)


class InvalidSort(Exception):
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class ColumnType:
    """
    Class encapsulating all handling of specific column types

    This implementation supports the PRIMITIVE_SQL_TYPES types, for more specific behavior, make a subclass.
    """

    def __init__(self, base_type: type[PRIMITIVE_SQL_TYPES], nullable: bool, table_prefix: Optional[str] = None) -> None:
        self.base_type = base_type
        self.nullable = nullable
        self.table_prefix = table_prefix
        self.table_prefix_dot = "" if table_prefix is None else f"{table_prefix}."

    def as_basic_filter_elements(self, name: str, value: object) -> Sequence[tuple[str, "ColumnType", object]]:
        """
        Break down this filter into more elementary filters

        :param name: column name, intended to be passed through get_accessor
        :param value: the value of this column
        :return: a list of (name, type, value) items
        """
        return [(name, self, self.get_value(value))]

    def as_basic_order_elements(self, name: str, order: PagingOrder) -> Sequence[tuple[str, "ColumnType", PagingOrder]]:
        """
        Break down this filter into more elementary filters

        :param name: column name, intended to be passed through get_accessor
        :return: a list of (name, type, order) items
        """
        return [(name, self, order)]

    def get_value(self, value: object) -> Optional[PRIMITIVE_SQL_TYPES]:
        """
        Prepare the actual value for use as an argument in a prepared statement for this type
        """
        if value is None:
            if not self.nullable:
                raise ValueError("None is not a valid value")
            else:
                return None
        if isinstance(value, self.base_type):
            # It is as expected
            return value
        if self.base_type == bool:
            ta = pydantic.TypeAdapter(bool)
            return ta.validate_python(value)
        if self.base_type == datetime.datetime and isinstance(value, str):
            return api_boundary_datetime_normalizer(dateutil.parser.isoparse(value))
        if issubclass(self.base_type, (str, int)) and isinstance(value, (str, int, bool)):
            # We can cast between those types
            return self.base_type(value)
        raise ValueError(f"{value} is not a valid value")

    def get_accessor(self, column_name: str, table_prefix: Optional[str] = None) -> str:
        """
        return the sql statement to get this column, as used in filter and other statements
        """
        table_prefix_value = self.table_prefix_dot if table_prefix is None else table_prefix + "."
        return table_prefix_value + column_name

    def coalesce_to_min(self, value_reference: str) -> str:
        """If the order by column is nullable, coalesce the parameter value to the minimum value of the specific type
        This is required for the comparisons used for paging, because comparing a value to
        NULL always yields NULL.
        """
        if self.nullable:
            if self.base_type == datetime.datetime:
                return f"COALESCE({value_reference}, to_timestamp(0))"
            elif self.base_type == bool:
                return f"COALESCE({value_reference}, FALSE)"
            elif self.base_type == int:
                # we only support positive ints up till now
                return f"COALESCE({value_reference}, -1)"
            elif self.base_type == str:
                return f"COALESCE({value_reference}, '')"
            elif self.base_type == UUID:
                return f"COALESCE({value_reference}, '00000000-0000-0000-0000-000000000000'::uuid)"
            else:
                assert False, "Unexpected argument type received, this should not happen"

        return value_reference

    def with_prefix(self, table_prefix: Optional[str]) -> "ColumnType":
        return ColumnType(self.base_type, self.nullable, table_prefix)


def TablePrefixWrapper(table_name: Optional[str], child: ColumnType) -> ColumnType:
    """
    This method is named like a class, because it replaces a former class.

    The functionality is not part ColumnType itself.
    """
    if table_name is None:
        return child
    return child.with_prefix(table_prefix=table_name)


class ForcedStringColumn(ColumnType):
    """A string that is explicitly cast to a specific string type"""

    def __init__(self, forced_type: str) -> None:
        super().__init__(base_type=str, nullable=False)
        self.forced_type = forced_type

    def get_accessor(self, column_name: str, table_prefix: Optional[str] = None) -> str:
        """
        return the sql statement to get this column, as used in filter and other statements
        """
        return super().get_accessor(column_name, table_prefix) + "::" + self.forced_type


StringColumn = ColumnType(base_type=str, nullable=False)
OptionalStringColumn = ColumnType(base_type=str, nullable=True)

DateTimeColumn = ColumnType(base_type=datetime.datetime, nullable=False)
OptionalDateTimeColumn = ColumnType(base_type=datetime.datetime, nullable=True)

PositiveIntColumn = ColumnType(base_type=int, nullable=False)
# Negatives ints require updating coalesce_to_min

TextColumn = ForcedStringColumn("text")

UUIDColumn = ColumnType(base_type=uuid.UUID, nullable=False)
BoolColumn = ColumnType(base_type=bool, nullable=False)


class DatabaseOrderV2(ABC):
    """
    Helper API for handling database order and filtering

    This class defines the consumer interface,

    It is made into a separate type, to make it very explicit what is exposed externally, to limit feature creep
    """

    @abstractmethod
    def as_filter(
        self,
        offset: int,
        column_value: Optional[PRIMITIVE_SQL_TYPES] = None,
        id_value: Optional[PRIMITIVE_SQL_TYPES] = None,
        start: bool = True,
    ) -> tuple[list[str], list[object]]:
        """
        Produce a filter for this order, to select all record before or after the given id

        :param offset: the next free number to use for query parameters
        :param column_value: the boundary value for the user specified order
        :param id_value: the boundary value for the built in order order
        :param start: is this the start filter? if so, retain all values`  > (column_value, id_value)`

        :return: The filter (as a string) and all associated query parameter values

        None values can have a double meaning here:
        - no value provided
        - the value is provided and None

        The distinction can be made as follows:
        1. at least one of the columns must be not nullable (otherwise the sorting is not unique)
        2. when both value are None, we are not paging and return '[],[]'
        3. when one of the values is effective, we produce a filter

        More specifically:
        1. when we have a single order, and `column_value` is not None, this singe value is used for filtering
        2. when we have a double order and the 'id_value' is not None and `self.get_order_by_column_type().nullable`,
            we consider the null an effective value and filter on both `column_value` and `id_value`
        3. when we have a double order and the 'id_value' is not None and `not self.get_order_by_column_type().nullable`,
            we consider the null not a value and filter only on `id_value`

        """

    @abstractmethod
    def get_order_by_statement(self, invert: bool = False, table: Optional[str] = None) -> str:
        """Get this order as an order_by statement"""

    @abstractmethod
    def get_order(self) -> PagingOrder:
        """Return the order of this paging request"""

    @abstractmethod
    def get_paging_boundaries(self, first: abc.Mapping[str, object], last: abc.Mapping[str, object]) -> PagingBoundaries:
        """Return the page boundaries, given the first and last record of the page"""


T_SELF = TypeVar("T_SELF", bound="SingleDatabaseOrder")


class SingleDatabaseOrder(DatabaseOrderV2, ABC):
    """
    Abstract Base class for ordering when using
    - a user specified order, that is always unique
    """

    def __init__(
        self,
        order_by_column: ColumnNameStr,
        order: PagingOrder,
    ) -> None:
        """The order_by_column and order parameters should be validated"""
        self.order_by_column = order_by_column
        self.order = order

    # Configuration methods
    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        """Return all valid columns for lookup and their type"""
        raise NotImplementedError()

    #  Factory
    @classmethod
    def parse_from_string(
        cls: type[T_SELF],
        sort: str,
    ) -> T_SELF:
        valid_sort_pattern: Pattern[str] = re.compile(
            f"^({'|'.join(cls.get_valid_sort_columns().keys())})\\.(asc|desc)$", re.IGNORECASE
        )
        match = valid_sort_pattern.match(sort)
        if match and len(match.groups()) == 2:
            order_by_column = match.groups()[0].lower()
            # Verify there is no escaping from the regex by exact match
            assert order_by_column in cls.get_valid_sort_columns()
            order = match.groups()[1].upper()
            return cls(order_by_column=ColumnNameStr(order_by_column), order=PagingOrder[order])
        raise InvalidSort(f"Sort parameter invalid: {sort}")

    # Internal helpers
    def get_order(self, invert: bool = False) -> PagingOrder:
        """The order string representing the direction the results should be sorted by"""
        return self.order.invert() if invert else self.order

    def get_order_by_column_type(self) -> ColumnType:
        """The type of the order by column"""
        return self.get_valid_sort_columns()[self.order_by_column]

    def get_order_by_column_api_name(self) -> str:
        """The name of the column that the results should be ordered by"""
        return self.order_by_column

    # External API
    def as_filter(
        self,
        offset: int,
        column_value: Optional[PRIMITIVE_SQL_TYPES] = None,
        id_value: Optional[PRIMITIVE_SQL_TYPES] = None,
        start: bool = True,
    ) -> tuple[list[str], list[object]]:
        """
        Produce a filter for this order, to select all record before or after the given id

        :param offset: the next free number to use for query parameters
        :param column_value: the value for the user specified order
        :param id_value: the value for the built in order order, if this class has one. Otherwise this value is ignored.
        :param start: is this the start filter? if so, retain all values`  > (column_value, id_value)`

        :return: The filter (as a string) and all associated query parameter values
        """
        relation = ">" if start else "<"

        if column_value is None:
            return [], []

        coll_type = self.get_order_by_column_type()
        col_name = self.order_by_column
        value = coll_type.get_value(column_value)

        ac = ArgumentCollector(offset=offset - 1)
        filter = f"{coll_type.get_accessor(col_name)} {relation} {ac(value)}"
        return [filter], ac.args

    def get_order_elements(self, invert: bool) -> Sequence[tuple[ColumnNameStr, ColumnType, PagingOrder]]:
        """
        return a list of column/column type/order triples, to format an ORDER BY or FILTER statement
        """
        order = self.get_order(invert)
        return [
            (self.order_by_column, self.get_order_by_column_type(), order),
        ]

    def get_order_by_statement(self, invert: bool = False, table: Optional[str] = None) -> str:
        """Return the actual order by statement, as derived from get_order_elements"""
        order_by_part = ", ".join(
            (
                f"{type.get_accessor(col, table)} {order.db_form(nullable=type.nullable)}"
                for col, type, order in self.get_order_elements(invert)
            )
        )
        return f" ORDER BY {order_by_part}"

    def get_paging_boundaries(self, first: abc.Mapping[str, object], last: abc.Mapping[str, object]) -> PagingBoundaries:
        """Return the page boundaries, given the first and last record returned"""
        if self.get_order() == PagingOrder.ASC:
            first, last = last, first

        order_column_name = self.order_by_column
        order_type: ColumnType = self.get_order_by_column_type()

        def assert_not_null(in_value: Optional[PRIMITIVE_SQL_TYPES]) -> PRIMITIVE_SQL_TYPES:
            # Make mypy happy
            assert in_value is not None
            return in_value

        return PagingBoundaries(
            start=assert_not_null(order_type.get_value(first[order_column_name])),
            first_id=None,
            end=assert_not_null(order_type.get_value(last[order_column_name])),
            last_id=None,
        )

    def __str__(self) -> str:
        # used to serialize the order back to a  paging url
        return f"{self.order_by_column}.{self.order.value.lower()}"


class AbstractDatabaseOrderV2(SingleDatabaseOrder, ABC):
    """
    Abstract Base class for ordering when using
    - a user specified order
    - an additional built in order to make the ordering unique (the id_collumn)
    """

    @property
    @abstractmethod
    def id_column(self) -> tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""

    # External API
    def as_filter(
        self,
        offset: int,
        column_value: Optional[PRIMITIVE_SQL_TYPES] = None,
        id_value: Optional[PRIMITIVE_SQL_TYPES] = None,
        start: bool = True,
    ) -> tuple[list[str], list[object]]:
        """
        Produce a filter for this order, to select all record before or after the given id

        :param offset: the next free number to use for query parameters
        :param column_value: the value for the user specified order
        :param id_value: the value for the built in order order
        :param start: is this the start filter? if so, retain all values`> (column_value, id_value)`,
            otherwise `< (column_value, id_value)`.

        :return: The filter (as a string) and all associated query parameter values
        """

        # All the filter elements:
        # 1. name of the actual collumn in the DB
        # 2. type of the collumn
        # 3. sanitized value of the collumn

        filter_elements: list[tuple[str, ColumnType, object]] = []

        order_by_collumns_type = self.get_order_by_column_type()
        paging_on_nullable = order_by_collumns_type.nullable and id_value is not None

        if column_value is not None or paging_on_nullable:
            # Have column value or paging on nullable
            filter_elements.extend(order_by_collumns_type.as_basic_filter_elements(self.order_by_column, column_value))

        if id_value is not None:
            # Have ID
            id_name, id_type = self.id_column
            if id_name != self.order_by_column:
                filter_elements.extend(id_type.as_basic_filter_elements(id_name, id_value))

        relation = ">" if start else "<"

        if len(filter_elements) == 0:
            return [], []

        ac = ArgumentCollector(offset=offset - 1)
        if len(filter_elements) == 1:
            col_name, coll_type, value = filter_elements[0]
            filter = f"{coll_type.get_accessor(col_name)} {relation} {ac(value)}"
            return [filter], ac.args
        else:
            # composed filter:
            # 1. comparison of two tuples (c_a, c_b) < (c_a, c_b)
            # 2. nulls must be removed to get proper comparison
            names_tuple = ", ".join(
                [coll_type.coalesce_to_min(coll_type.get_accessor(col_name)) for col_name, coll_type, value in filter_elements]
            )
            values_references_tuple = ", ".join(
                [coll_type.coalesce_to_min(ac(value)) for col_name, coll_type, value in filter_elements]
            )
            filter = f"({names_tuple}) {relation} ({values_references_tuple})"
            return [filter], ac.args

    def get_order_elements(self, invert: bool) -> list[tuple[ColumnNameStr, ColumnType, PagingOrder]]:
        """
        return a list of column/column type/order triples, to format an ORDER BY or FILTER statement
        """
        order = self.get_order(invert)
        id_name, id_type = self.id_column

        return list(
            self.get_order_by_column_type().as_basic_order_elements(self.order_by_column, order)
        ) + id_type.as_basic_order_elements(id_name, order)

    def get_paging_boundaries(self, first: abc.Mapping[str, object], last: abc.Mapping[str, object]) -> PagingBoundaries:
        """Return the page boundaries, given the first and last record returned"""
        if self.get_order() == PagingOrder.ASC:
            first, last = last, first

        order_column_name = self.order_by_column
        order_type: ColumnType = self.get_order_by_column_type()

        id_column, id_type = self.id_column

        return PagingBoundaries(
            start=order_type.get_value(first[order_column_name]),
            first_id=id_type.get_value(first[id_column]),
            end=order_type.get_value(last[order_column_name]),
            last_id=id_type.get_value(last[id_column]),
        )


class VersionedResourceOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which resources should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        return {
            ColumnNameStr("resource_type"): StringColumn,
            ColumnNameStr("agent"): StringColumn,
            ColumnNameStr("resource_id_value"): StringColumn,
        }

    @property
    def id_column(self) -> tuple[ColumnNameStr, ColumnType]:
        """Name of the id column of this database order"""
        return ColumnNameStr("resource_id"), StringColumn


class ResourceStatusOrder(VersionedResourceOrder):
    """
    Resources with a status field
    """

    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        return {
            **super().get_valid_sort_columns(),
            ColumnNameStr("resource_id"): StringColumn,
            ColumnNameStr("status"): TextColumn,
        }


class ResourceHistoryOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which resource history should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder"""
        return {ColumnNameStr("date"): DateTimeColumn}

    @property
    def id_column(self) -> tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("attribute_hash"), StringColumn)


class ResourceLogOrder(SingleDatabaseOrder):
    """Represents the ordering by which resource logs should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        return {
            ColumnNameStr("timestamp"): DateTimeColumn,
        }


class CompileReportOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which compile reports should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder"""
        return {ColumnNameStr("requested"): DateTimeColumn}

    @property
    def id_column(self) -> tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("id"), UUIDColumn)


class AgentOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which agents should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder"""
        return {
            ColumnNameStr("name"): TablePrefixWrapper("a", StringColumn),
            ColumnNameStr("process_name"): OptionalStringColumn,
            ColumnNameStr("paused"): BoolColumn,
            ColumnNameStr("last_failover"): OptionalDateTimeColumn,
            ColumnNameStr("status"): StringColumn,
        }

    @property
    def id_column(self) -> tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("name"), TablePrefixWrapper("a", StringColumn))


class DesiredStateVersionOrder(SingleDatabaseOrder):
    """Represents the ordering by which desired state versions should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        return {
            ColumnNameStr("version"): PositiveIntColumn,
        }


class ParameterOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which parameters should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        return {
            ColumnNameStr("name"): StringColumn,
            ColumnNameStr("source"): StringColumn,
            ColumnNameStr("updated"): OptionalDateTimeColumn,
        }

    @property
    def id_column(self) -> tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("id"), UUIDColumn)


class FactOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which facts should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        return {
            ColumnNameStr("name"): StringColumn,
            ColumnNameStr("resource_id"): StringColumn,
        }

    @property
    def id_column(self) -> tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("id"), UUIDColumn)


class NotificationOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which notifications should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder"""
        return {
            ColumnNameStr("created"): DateTimeColumn,
        }

    @property
    def id_column(self) -> tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("id"), UUIDColumn)


class DiscoveredResourceOrder(SingleDatabaseOrder):
    """Represents the ordering by which discovered resources should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> dict[ColumnNameStr, ColumnType]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder"""
        return {
            ColumnNameStr("discovered_resource_id"): StringColumn,
            ColumnNameStr("agent"): StringColumn,
            ColumnNameStr("resource_type"): StringColumn,
            ColumnNameStr("resource_id_value"): StringColumn,
        }


class BaseQueryBuilder(ABC):
    """Provides a way to build up a sql query from its parts.
    Each method returns a new query builder instance, with the additional parameters processed"""

    def __init__(
        self,
        select_clause: Optional[str] = None,
        from_clause: Optional[str] = None,
        filter_statements: Optional[list[str]] = None,
        values: Optional[list[object]] = None,
    ) -> None:
        """
        The parameters are the parts of an sql query,
        which can also be added to the builder with the appropriate methods

        :param select_clause: The select clause of the query
        :param from_clause: From clause of the query
        :param filter_statements: A list of filters for the query
        :param values: The values to be used for the filter statements
        """
        self.select_clause = select_clause
        self._from_clause = from_clause
        self.filter_statements = filter_statements or []
        self.values = values or []

    def _join_filter_statements(self, filter_statements: list[str]) -> str:
        """Join multiple filter statements"""
        if filter_statements:
            return "WHERE " + " AND ".join(filter_statements)
        return ""

    @abstractmethod
    def from_clause(self, from_clause: str) -> "BaseQueryBuilder":
        """Set the from clause of the query"""
        raise NotImplementedError()

    @property
    def offset(self) -> int:
        """The current offset of the values to be used for filter statements"""
        return len(self.values) + 1

    @abstractmethod
    def filter(self, filter_statements: list[str], values: list[object]) -> "BaseQueryBuilder":
        """Add filters to the query"""
        raise NotImplementedError()

    @abstractmethod
    def build(self) -> tuple[str, list[object]]:
        """Builds up the full query string, and the parametrized value list, ready to be executed"""
        raise NotImplementedError()


class SimpleQueryBuilder(BaseQueryBuilder):
    """A query builder suitable for most queries"""

    def __init__(
        self,
        select_clause: Optional[str] = None,
        from_clause: Optional[str] = None,
        filter_statements: Optional[list[str]] = None,
        values: Optional[list[object]] = None,
        db_order: Optional[DatabaseOrderV2] = None,
        limit: Optional[int] = None,
        backward_paging: bool = False,
        prelude: Optional[str] = None,
    ) -> None:
        """
        :param select_clause: The select clause of the query
        :param from_clause: The from clause of the query
        :param filter_statements: A list of filters for the query
        :param values: The values to be used for the filter statements
        :param db_order: The DatabaseOrder describing how the results should be ordered
        :param limit: Limit the results to this amount
        :param backward_paging: Whether the ordering of the results should be inverted,
                                used when going backward through the pages
        :param prelude: part of the query preceding all else, for use with 'with' binding
        """
        super().__init__(select_clause, from_clause, filter_statements, values)
        self.db_order = db_order
        self.limit = limit
        self.backward_paging = backward_paging
        self.prelude = prelude

    def select(self, select_clause: str) -> "SimpleQueryBuilder":
        """Set the select clause of the query"""
        return SimpleQueryBuilder(
            select_clause,
            self._from_clause,
            self.filter_statements,
            self.values,
            self.db_order,
            self.limit,
            self.backward_paging,
            self.prelude,
        )

    def from_clause(self, from_clause: str) -> "SimpleQueryBuilder":
        """Set the from clause of the query"""
        return SimpleQueryBuilder(
            self.select_clause,
            from_clause,
            self.filter_statements,
            self.values,
            self.db_order,
            self.limit,
            self.backward_paging,
            self.prelude,
        )

    def order_and_limit(
        self, db_order: DatabaseOrderV2, limit: Optional[int] = None, backward_paging: bool = False
    ) -> "SimpleQueryBuilder":
        """Set the order and limit of the query"""
        return SimpleQueryBuilder(
            self.select_clause,
            self._from_clause,
            self.filter_statements,
            self.values,
            db_order,
            limit,
            backward_paging,
            self.prelude,
        )

    def filter(self, filter_statements: list[str], values: list[object]) -> "SimpleQueryBuilder":
        return SimpleQueryBuilder(
            self.select_clause,
            self._from_clause,
            self.filter_statements + filter_statements,
            self.values + values,
            self.db_order,
            self.limit,
            self.backward_paging,
            self.prelude,
        )

    def build(self) -> tuple[str, list[object]]:
        if not self.select_clause or not self._from_clause:
            raise InvalidQueryParameter("A valid query must have a SELECT and a FROM clause")
        full_query = f"""{self.select_clause}
                         {self._from_clause}
                         {self._join_filter_statements(self.filter_statements)}
                         """
        if self.prelude:
            full_query = self.prelude + full_query
        if self.db_order:
            full_query += self.db_order.get_order_by_statement(self.backward_paging)
        if self.limit is not None:
            if self.limit > DBLIMIT:
                raise InvalidQueryParameter(f"Limit cannot be bigger than {DBLIMIT}, got {self.limit}")
            elif self.limit > 0:
                full_query += " LIMIT " + str(self.limit)
        if self.db_order and self.backward_paging:
            order_by = self.db_order.get_order_by_statement(table="matching_records")
            full_query = f"""SELECT * FROM ({full_query}) AS matching_records {order_by}"""

        return full_query, self.values


def json_encode(value: object) -> str:
    # see json_encode in tornado.escape
    return json.dumps(value, default=util.internal_json_encoder)


T = TypeVar("T")


class Field(Generic[T]):
    def __init__(
        self,
        field_type: type[T],
        required: bool = False,
        is_many: bool = False,
        part_of_primary_key: bool = False,
        ignore: bool = False,
        default: object = default_unset,
        **kwargs: object,
    ) -> None:
        """A field in a document/record in the database. This class holds the metadata one how the data layer should handle
        the field.

        :param field_type: The python type of the field. This type should work with isinstance
        :param required: Is this value required. This means that it is not optional and it cannot be None
        :param is_many: Set to true when this is a list type
        :param part_of_primary_key: Set to true when the field is part of the primary key.
        :param ignore: Should this field be ignored when saving it to the database. This can be used to add a field to a
                       a class that should not be saved in the database.
        :param default: The default value for this field.
        """

        self._field_type = field_type
        self._required = required
        self._ignore = ignore
        self._part_of_primary_key = part_of_primary_key
        self._is_many = is_many

        self._default_value: object
        if default != default_unset:
            self._default = True
            self._default_value = default
        else:
            self._default = False
            self._default_value = None

    def get_field_type(self) -> type[T]:
        return self._field_type

    field_type = property(get_field_type)

    def is_required(self) -> bool:
        return self._required

    required = property(is_required)

    def get_default(self) -> bool:
        return self._default

    default = property(get_default)

    def get_default_value(self) -> T:
        return copy.copy(self._default_value)

    default_value = property(get_default_value)

    @property
    def ignore(self) -> bool:
        return self._ignore

    def is_part_of_primary_key(self) -> bool:
        return self._part_of_primary_key

    part_of_primary_key = property(is_part_of_primary_key)

    @property
    def is_many(self) -> bool:
        return self._is_many

    def _validate_single(self, name: str, value: object) -> None:
        """Validate a single value against the types in this field."""
        if not isinstance(value, self.field_type):
            raise TypeError(
                "Field %s should have the correct type (%s instead of %s)"
                % (name, self.field_type.__name__, type(value).__name__)
            )

    def validate(self, name: str, value: T) -> None:
        """Validate the value against the constraint in this field. Treat value as list when is_many is true"""
        if value is None and self.required:
            raise TypeError("%s field is required" % name)

        if value is None:
            return None

        if self.is_many:
            if not isinstance(value, list):
                TypeError(f"Field {name} should be a list, but got {type(value).__name__}")
            else:
                [self._validate_single(name, v) for v in value]
        else:
            self._validate_single(name, value)

    def from_db(self, name: str, value: object) -> object:
        """Load values from database. Treat value as a list when is_many is true. Converts database
        representation to appropriately typed object."""
        if value is None and self.required:
            raise TypeError("%s field is required" % name)

        if value is None:
            return None

        if self.is_many:
            if not isinstance(value, list):
                TypeError(f"Field {name} should be a list, but got {type(value).__name__}")
            else:
                return [self._from_db_single(name, v) for v in value]
        return self._from_db_single(name, value)

    def _from_db_single(self, name: str, value: object) -> object:
        """Load a single database value. Converts database representation to appropriately typed object."""
        if isinstance(value, self.field_type):
            return value

        # asyncpg does not convert an enum field to an enum type
        if isinstance(value, str) and issubclass(self.field_type, enum.Enum):
            return self.field_type[value]
        # decode typed json
        if isinstance(value, dict) and issubclass(self.field_type, pydantic.BaseModel):
            return self.field_type(**value)
        if self.field_type == pydantic.AnyHttpUrl:
            return pydantic.TypeAdapter(pydantic.AnyHttpUrl).validate_python(value)

        raise TypeError(
            f"Field {name} should have the correct type ({self.field_type.__name__} instead of {type(value).__name__})"
        )


class DataDocument:
    """
    A baseclass for objects that represent data in inmanta. The main purpose of this baseclass is to group dict creation
    logic. These documents are not stored in the database
    (use BaseDocument for this purpose). It provides a to_dict method that the inmanta rpc can serialize. You can store
    DataDocument children in BaseDocument fields, they will be serialized to dict. However, on retrieval this is not
    performed.
    """

    def __init__(self, **kwargs: object) -> None:
        self._data = kwargs

    def to_dict(self) -> JsonType:
        """
        Return a dict representation of this object.
        """
        return self._data


class InvalidAttribute(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DocumentMeta(type):
    def __new__(cls, class_name: str, bases: tuple[type, ...], dct: dict[str, object]) -> type:
        dct["_fields_metadata"] = {}
        new_type: type[BaseDocument] = type.__new__(cls, class_name, bases, dct)
        if class_name != "BaseDocument":
            new_type.load_fields()
        return new_type


TBaseDocument = TypeVar("TBaseDocument", bound="BaseDocument")  # Part of the stable API
TransactionResult = TypeVar("TransactionResult")


@stable_api
class BaseDocument(metaclass=DocumentMeta):
    """
    A base document in the database. Subclasses of this document determine collections names. This type is mainly used to
    bundle query methods and generate validate and query methods for optimized DB access. This is not a full ODM.

    Fields are
    modelled using type annotations similar to protocol and pydantic. The following is supported:

    - Attributes are defined at class level with type annotations
    - Attributes do not need a default value. When no default is provided, they are marked as required.
    - When a value does not have to be set: either a default value or making it optional can be used. When a field is optional
      without a default value, none will be set as default value so that the field is available.
    - Fields that should be ignored, can be added to __ignore_fields__ This attribute is a tuple of strings
    - Fields that are part of the primary key should be added to the __primary_key__ attributes. This attribute is a tuple of
      strings.
    """

    _connection_pool: Optional[asyncpg.pool.Pool] = None
    _fields_metadata: dict[str, Field]
    __primary_key__: tuple[str, ...]
    __ignore_fields__: tuple[str, ...]

    def __init__(self, from_postgres: bool = False, **kwargs: object) -> None:
        """
        :param kwargs: The values to create the document. When id is defined in the fields but not provided, a new UUID is
                       generated.
        """
        self.__process_kwargs(from_postgres, kwargs)

    @classmethod
    def get_connection(
        cls, connection: Optional[asyncpg.connection.Connection] = None
    ) -> AbstractAsyncContextManager[asyncpg.connection.Connection]:
        """
        Returns a context manager to acquire a connection. If an existing connection is passed, returns a dummy context manager
        wrapped around that connection instance. This allows for transparent usage, regardless of whether a connection has
        already been acquired.
        """
        if connection is not None:
            return util.nullcontext(connection)

        # Make mypy happy

        assert cls._connection_pool is not None

        return cls._connection_pool.acquire()

    @classmethod
    def table_name(cls) -> str:
        """
        Return the name of the collection
        """
        return cls.__name__.lower()

    @classmethod
    def get_field_metadata(cls) -> dict[str, Field]:
        return cls._fields_metadata.copy()

    @staticmethod
    def _annotation_to_field(
        attribute: str,
        annotation: type[object],
        has_value: bool = True,
        value: Optional[object] = None,
        part_of_primary_key: bool = False,
        ignore_field: bool = False,
    ) -> Field:
        """Convert an annotated definition to a Field instance. The conversion rules are the following:
        - The value assigned to the field is the default value
        - When the default value is None the type has to be Optional
        - When the field is not optional, None is not a valid value
        - When the field has no default value, it is not required
        """
        field_type: type[object] = annotation
        required: bool = not has_value
        default: object = default_unset
        is_many: bool = False

        # Only union with None (optional) is support
        if typing_inspect.is_union_type(annotation) and not typing_inspect.is_optional_type(annotation):
            raise InvalidAttribute(f"A union that is not an optional in field {attribute} is not supported.")

        if typing_inspect.is_optional_type(annotation):
            # The value optional. When no default is set, it will be None.
            required = False
            default = None

            # Filter out the None from the union
            type_args = typing_inspect.get_args(annotation, evaluate=True)
            if len(type_args) != 2:
                raise InvalidAttribute(f"Only optionals with one type are supported, field {attribute} has more.")
            field_type = [typ for typ in type_args if typ][0]

        if has_value:
            # A default value is available, so not required. When optional type, override the default None
            required = False
            default = value

        if typing_inspect.is_generic_type(field_type):
            orig = typing_inspect.get_origin(field_type)
            # First two are for python3.6, the last two for 3.7 and up
            if orig in [list, typing.Sequence, list, abc.Sequence]:
                is_many = True
                type_args = typing_inspect.get_args(field_type)
                if len(type_args) == 0 or isinstance(type_args[0], typing.TypeVar):
                    # In python3.8 type_args is not empty when you write List but it will contain an instance of TypeVar
                    raise InvalidAttribute(f"Generic type of field {attribute} requires a type argument.")
                field_type = type_args[0]

                # List of Dict for example still cannot be validated. If the type is still a generic. Set the type to List of
                # object.
                if typing_inspect.is_generic_type(field_type):
                    field_type = object

            elif orig in [typing.Mapping, dict, abc.Mapping, dict]:
                field_type = dict

        if typing_inspect.is_new_type(field_type):
            # Python 3.10 and later NewType is a real type and an isinstance will work. On older version NewType is a function.
            # If this is the case we need to get the real supertype
            if callable(field_type):
                field_type = field_type.__supertype__

        return Field(
            field_type=field_type,
            required=required,
            default=default,
            is_many=is_many,
            part_of_primary_key=part_of_primary_key,
            ignore=ignore_field,
        )

    @classmethod
    def load_fields(cls) -> None:
        """Load the field metadata from the class definition. This method supports two different mechanisms:
        1. Using the field class as the value of the attribute.
        2. Using type annotations on the attributes
        """
        primary_key: tuple[str, ...] = tuple()
        ignore: tuple[str, ...] = tuple()
        if "__primary_key__" in cls.__dict__:
            primary_key = cls.__primary_key__

        if "__ignore_fields__" in cls.__dict__:
            ignore = cls.__ignore_fields__

        for attribute, value in cls.__dict__.items():
            if attribute.startswith("_"):
                continue
            elif isinstance(value, Field):
                warnings.warn(f"Field {attribute} should be defined using annotations instead of Field.")
                cls._fields_metadata[attribute] = value
            elif cls.__annotations__ and attribute in cls.__annotations__:
                annotation = cls.__annotations__[attribute]
                cls._fields_metadata[attribute] = cls._annotation_to_field(
                    attribute,
                    annotation,
                    has_value=True,
                    value=value,
                    part_of_primary_key=attribute in primary_key,
                    ignore_field=attribute in ignore,
                )

        # attributes that do not have a default value will only be present in __annotations__ and not in __dict__
        for attribute, annotation in cls.__annotations__.items():
            if not attribute.startswith("_") and attribute not in cls._fields_metadata:
                cls._fields_metadata[attribute] = cls._annotation_to_field(
                    attribute,
                    annotation,
                    has_value=False,
                    part_of_primary_key=attribute in primary_key,
                    ignore_field=attribute in ignore,
                )

    @classmethod
    def get_field_names(cls) -> typing.KeysView[str]:
        """Returns all field names in the document"""
        return cls.get_field_metadata().keys()

    def __process_kwargs(self, from_postgres: bool, kwargs: dict[str, object]) -> None:
        """This helper method process the kwargs provided to the constructor and populates the fields of the object."""
        fields = self.get_field_metadata()

        if "id" in fields and "id" not in kwargs:
            kwargs["id"] = uuid.uuid4()

        for name, value in kwargs.items():
            if name not in fields:
                raise AttributeError(f"{name} field is not defined for this document {type(self).__name__.lower()}")

            field = fields[name]
            if not from_postgres:
                field.validate(name, value)
            elif not field.ignore:
                value = field.from_db(name, value)
            else:
                value = None

            setattr(self, name, value)

            del fields[name]

        required_fields = []
        for name, field in fields.items():
            # when a default value is used, make sure it is copied
            if field.default:
                setattr(self, name, copy.deepcopy(field.default_value))

            # update the list of required fields
            elif fields[name].required:
                required_fields.append(name)

        if len(required_fields) > 0:
            raise AttributeError("The fields %s are required and no value was provided." % ", ".join(required_fields))

    @classmethod
    def get_valid_field_names(cls) -> list[str]:
        return list(cls.get_field_names())

    @classmethod
    def _get_names_of_primary_key_fields(cls) -> list[str]:
        return [name for name, value in cls.get_field_metadata().items() if value.is_part_of_primary_key()]

    def _get_filter_on_primary_key_fields(self, offset: int = 1) -> tuple[str, list[object]]:
        names_primary_key_fields = self._get_names_of_primary_key_fields()
        query = {field_name: self.__getattribute__(field_name) for field_name in names_primary_key_fields}
        return self._get_composed_filter(offset=offset, **query)

    @classmethod
    def _new_id(cls) -> uuid.UUID:
        """
        Generate a new ID. Override to use something else than uuid4
        """
        return uuid.uuid4()

    @classmethod
    def set_connection_pool(cls, pool: asyncpg.pool.Pool) -> None:
        if cls._connection_pool:
            raise Exception(f"Connection already set on {cls} ({cls._connection_pool})!")
        cls._connection_pool = pool

    @classmethod
    def remove_connection_pool(cls) -> None:
        if not cls._connection_pool:
            return
        cls._connection_pool = None

    def __setattr__(self, name: str, value: object) -> None:
        if name[0] == "_":
            return object.__setattr__(self, name, value)

        fields = self.get_field_metadata()
        if name in fields:
            field = fields[name]
            # validate
            field.validate(name, value)
            object.__setattr__(self, name, value)
            return

        raise AttributeError(name)

    @classmethod
    def _convert_field_names_to_db_column_names(cls, field_dict: dict[str, object]) -> dict[str, object]:
        return field_dict

    def get_value(self, name: str, default_value: Optional[object] = None) -> object:
        """Check if a value is set for a field. Fields that are declared but that do not have a value are only present
        in annotations but not as attribute (in __dict__)"""
        if hasattr(self, name):
            return getattr(self, name)
        return default_value

    def _get_column_names_and_values(self) -> tuple[list[str], list[object]]:
        column_names: list[str] = []
        values: list[object] = []
        for name, metadata in self.get_field_metadata().items():
            if metadata.ignore:
                continue

            value = self.get_value(name)

            if metadata.required and value is None:
                raise TypeError(f"{self.__name__} should have field '{name}'")

            metadata.validate(name, value)
            column_names.append(name)
            values.append(self._get_value(value))

        return column_names, values

    async def insert(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Insert a new document based on the instance passed. Validation is done based on the defined fields.
        """
        column_names, values = self._get_column_names_and_values()
        column_names_as_sql_string = ",".join(column_names)
        values_as_parameterized_sql_string = ",".join(["$" + str(i) for i in range(1, len(values) + 1)])
        query = (
            f"INSERT INTO {self.table_name()} "
            f"({column_names_as_sql_string}) "
            f"VALUES ({values_as_parameterized_sql_string})"
        )
        await self._execute_query(query, *values, connection=connection)

    async def insert_with_overwrite(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Insert a new document based on the instance passed. If the document already exists, overwrite it.
        """
        return await self.insert_many_with_overwrite([self], connection=connection)

    @classmethod
    async def _fetchval(cls, query: str, *values: object, connection: Optional[asyncpg.connection.Connection] = None) -> object:
        async with cls.get_connection(connection) as con:
            return await con.fetchval(query, *values)

    @classmethod
    async def _fetch_int(cls, query: str, *values: object, connection: Optional[asyncpg.connection.Connection] = None) -> int:
        """Fetch a single integer value"""
        value = await cls._fetchval(query, *values, connection=connection)
        assert isinstance(value, int)
        return value

    @classmethod
    async def _fetchrow(
        cls, query: str, *values: object, connection: Optional[asyncpg.connection.Connection] = None
    ) -> Optional[Record]:
        async with cls.get_connection(connection) as con:
            return await con.fetchrow(query, *values)

    @classmethod
    async def _fetch_query(
        cls, query: str, *values: object, connection: Optional[asyncpg.connection.Connection] = None
    ) -> Sequence[Record]:
        async with cls.get_connection(connection) as con:
            return await con.fetch(query, *values)

    @classmethod
    async def _execute_query(
        cls, query: str, *values: object, connection: Optional[asyncpg.connection.Connection] = None
    ) -> str:
        async with cls.get_connection(connection) as con:
            return await con.execute(query, *values)

    @classmethod
    async def lock_table(cls, mode: TableLockMode, connection: asyncpg.connection.Connection) -> None:
        """
        Acquire a table-level lock on a single environment. Callers should adhere to a consistent locking order accross
        transactions as described at the top of this module.
        Passing a connection object is mandatory. The connection is expected to be in a transaction.
        """
        await cls._execute_query(f"LOCK TABLE {cls.table_name()} IN {mode.value} MODE", connection=connection)

    async def _xact_lock(
        self, lock_key: int, instance_key: uuid.UUID, *, shared: bool = False, connection: asyncpg.Connection
    ) -> None:
        """
        Acquires a transaction-level advisory lock for concurrency control

        :param lock_key: the key identifying this lock (32 bit signed int)
        :param instance_key: the key identifying the instance to lock.
        We only use the lower 32 bits, so it can collide.

        :param shared: If true, doesn't conflict with other shared locks, only with non-shared ones.
        :param connection: The connection hosting the transaction for which to acquire a lock.
        """
        lock: str = "pg_advisory_xact_lock_shared" if shared else "pg_advisory_xact_lock"
        await connection.execute(
            # Advisory lock keys are only 32 bit (or a single 64 bit key), while a full uuid is 128 bit.
            # Since locking slightly too strictly at extremely low odds is acceptable, we only use a 32 bit subvalue
            # of the uuid. For uuid4, time_low is (despite the name) randomly generated. Since it is an unsigned
            # integer while Postgres expects a signed one, we shift it by 2**31.
            f"SELECT {lock}($1, $2)",
            lock_key,
            instance_key.time_low - 2**31,
        )

    @classmethod
    async def insert_many(
        cls, documents: Sequence["BaseDocument"], *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        """
        Insert multiple objects at once
        """
        if not documents:
            return

        columns = cls.get_field_names()
        records: list[tuple[object, ...]] = []
        for doc in documents:
            current_record = []
            for col in columns:
                current_record.append(cls._get_value(doc.__getattribute__(col)))
            records.append(tuple(current_record))

        async with cls.get_connection(connection) as con:
            await con.copy_records_to_table(table_name=cls.table_name(), columns=columns, records=records, schema_name="public")

    @classmethod
    async def insert_many_with_overwrite(
        cls, documents: Sequence["BaseDocument"], *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        """
        Insert new documents. If the document already exists, overwrite it.
        """
        if not documents:
            return
        column_names = cls.get_field_names()
        primary_key_fields = cls._get_names_of_primary_key_fields()
        primary_key_string = ",".join(primary_key_fields)
        update_set = set(column_names) - set(cls._get_names_of_primary_key_fields())
        update_set_string = ",\n".join([f"{item} = EXCLUDED.{item}" for item in update_set])

        values: list[list[object]] = [document._get_column_names_and_values()[1] for document in documents]

        column_names_as_sql_string = ", ".join(column_names)

        number_of_columns = len(values[0])
        placeholders = ", ".join(
            [
                "(" + ", ".join([f"${doc * number_of_columns + col}" for col in range(1, number_of_columns + 1)]) + ")"
                for doc in range(len(values))
            ]
        )

        query = f"""INSERT INTO {cls.table_name()}
                    ({column_names_as_sql_string})
                    VALUES {placeholders}
                    ON CONFLICT ({primary_key_string})
                    DO UPDATE SET
                    {update_set_string};"""

        flattened_values = [item for sublist in values for item in sublist]
        await cls._execute_query(query, *flattened_values)

    def add_default_values_when_undefined(self, **kwargs: object) -> dict[str, object]:
        result = dict(kwargs)
        for name, field in self._fields.items():
            if name not in kwargs:
                default_value = field.default_value
                result[name] = default_value
        return result

    async def update(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: object) -> None:
        """
        Update this document in the database. It will update the fields in this object and send a full update to database.
        Use update_fields to only update specific fields.
        """
        kwargs = self._convert_field_names_to_db_column_names(kwargs)
        for name, value in kwargs.items():
            setattr(self, name, value)
        column_names, values = self._get_column_names_and_values()
        values_as_parameterized_sql_string = ",".join([column_names[i - 1] + "=$" + str(i) for i in range(1, len(values) + 1)])
        filter_statement, values_for_filter = self._get_filter_on_primary_key_fields(offset=len(column_names) + 1)
        values = values + values_for_filter
        query = "UPDATE " + self.table_name() + " SET " + values_as_parameterized_sql_string + " WHERE " + filter_statement
        await self._execute_query(query, *values, connection=connection)

    def _get_set_statement(self, **kwargs: object) -> tuple[str, list[object]]:
        counter = 1
        parts_of_set_statement = []
        values = []
        for name, value in kwargs.items():
            setattr(self, name, value)
            parts_of_set_statement.append(name + "=$" + str(counter))
            values.append(self._get_value(value))
            counter += 1
        set_statement = ",".join(parts_of_set_statement)
        return (set_statement, values)

    async def update_fields(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: object) -> None:
        """
        Update the given fields of this document in the database. It will update the fields in this object and do a specific
        $set in the database on this document.
        """
        if len(kwargs) == 0:
            return
        kwargs = self._convert_field_names_to_db_column_names(kwargs)
        for name, value in kwargs.items():
            setattr(self, name, value)
        set_statement, values_set_statement = self._get_set_statement(**kwargs)
        filter_statement, values_for_filter = self._get_filter_on_primary_key_fields(offset=len(kwargs) + 1)
        values = values_set_statement + values_for_filter
        query = "UPDATE " + self.table_name() + " SET " + set_statement + " WHERE " + filter_statement
        await self._execute_query(query, *values, connection=connection)

    @classmethod
    async def get_by_id(
        cls: type[TBaseDocument], doc_id: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None
    ) -> Optional[TBaseDocument]:
        """
        Get a specific document based on its ID

        :return: An instance of this class with its fields filled from the database.
        """
        result = await cls.get_list(id=doc_id, connection=connection)
        if len(result) > 0:
            return result[0]
        return None

    @classmethod
    async def get_one(
        cls: type[TBaseDocument],
        connection: Optional[asyncpg.connection.Connection] = None,
        lock: Optional[RowLockMode] = None,
        **query: object,
    ) -> Optional[TBaseDocument]:
        results = await cls.get_list(
            connection=connection,
            order_by_column=None,
            order=None,
            limit=1,
            offset=None,
            no_obj=None,
            lock=lock,
            **query,
        )
        if results:
            return results[0]
        return None

    @classmethod
    def _validate_order(cls, order_by_column: str, order: str) -> tuple[ColumnNameStr, OrderStr]:
        """Validate the correct values for order and if the order column is an existing column name
        :param order_by_column: The name of the column to order by
        :param order: The sorting order.
        :return:
        """
        for o in order.split(" "):
            possible = ["ASC", "DESC", "NULLS", "FIRST", "LAST"]
            if o not in possible:
                raise RuntimeError(f"The following order can not be applied: {order}, {o} should be one of {possible}")

        if order_by_column not in cls.get_field_names():
            raise RuntimeError(f"{order_by_column} is not a valid field name.")

        return ColumnNameStr(order_by_column), OrderStr(order)

    @classmethod
    def _validate_order_strict(cls, order_by_column: str, order: str) -> tuple[ColumnNameStr, PagingOrder]:
        """Validate the correct values for order ('ASC' or 'DESC')  and if the order column is an existing column name
        :param order_by_column: The name of the column to order by
        :param order: The sorting order.
        :return:
        """
        for o in order.split(" "):
            possible = ["ASC", "DESC"]
            if o not in possible:
                raise RuntimeError(f"The following order can not be applied: {order}, {o} should be one of {possible}")

        if order_by_column not in cls.get_valid_field_names():
            raise RuntimeError(f"{order_by_column} is not a valid field name.")

        return ColumnNameStr(order_by_column), PagingOrder[order]

    @classmethod
    async def get_list(
        cls: type[TBaseDocument],
        *,
        # All defaults None rather actual values to allow explicitly requesting defaults to improve type safety with **query
        order_by_column: Optional[str] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: Optional[bool] = None,
        lock: Optional[RowLockMode] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: object,
    ) -> list[TBaseDocument]:
        """
        Get a list of documents matching the filter args
        """
        return await cls.get_list_with_columns(
            order_by_column=order_by_column,
            order=order,
            limit=limit,
            offset=offset,
            no_obj=no_obj,
            lock=lock,
            connection=connection,
            columns=None,
            **query,
        )

    @classmethod
    async def get_list_with_columns(
        cls: type[TBaseDocument],
        *,
        order_by_column: Optional[str] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: Optional[bool] = None,
        lock: Optional[RowLockMode] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        columns: Optional[list[str]] = None,
        **query: object,
    ) -> list[TBaseDocument]:
        """
        Get a list of documents matching the filter args
        """
        if order is None:
            order = "ASC"
        if order_by_column:
            cls._validate_order(order_by_column, order)

        if no_obj is None:
            no_obj = False

        query = cls._convert_field_names_to_db_column_names(query)
        filter_statement, values = cls._get_composed_filter(**query)
        selected_columns = " * "
        if columns:
            selected_columns = ",".join([cls.validate_field_name(column) for column in columns])
        sql_query = f"SELECT {selected_columns} FROM " + cls.table_name()
        if filter_statement:
            sql_query += " WHERE " + filter_statement
        if order_by_column is not None:
            sql_query += f" ORDER BY {order_by_column} {order}"
        if limit is not None and limit > 0:
            sql_query += " LIMIT $" + str(len(values) + 1)
            values.append(int(limit))
        if offset is not None and offset > 0:
            sql_query += " OFFSET $" + str(len(values) + 1)
            values.append(int(offset))
        if lock is not None:
            sql_query += f" {lock.value}"
        result = await cls.select_query(sql_query, values, no_obj=no_obj, connection=connection)
        return result

    @classmethod
    async def get_list_paged(
        cls: type[TBaseDocument],
        *,
        page_by_column: str,
        order_by_column: Optional[str] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        no_obj: Optional[bool] = None,
        lock: Optional[RowLockMode] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: object,
    ) -> list[TBaseDocument]:
        """
        Get a list of documents matching the filter args, with paging support

        :param page_by_column: The name of the column in the database on which the paging should be applied
        :param order_by_column: The name of the column in the database the sorting should be based on
        :param order: The order to apply to the sorting
        :param limit: If specified, the maximum number of entries to return
        :param start: A value conforming the sorting column type, all returned rows will have greater value in the sorted column
        :param end: A value conforming the sorting column type, all returned rows will have lower value in the sorted column
        :param no_obj: Whether not to cast the query result into a matching object
        :param connection: An optional connection
        :param **query: Any additional filter to apply
        """
        if order is None:
            order = "ASC"
        if order_by_column:
            cls._validate_order(order_by_column, order)

        if no_obj is None:
            no_obj = False

        query = cls._convert_field_names_to_db_column_names(query)
        filter_statement, values = cls._get_composed_filter(**query)
        filter_statements = filter_statement.split(" AND ") if filter_statement != "" else []
        if start is not None:
            filter_statements.append(f"{page_by_column} > $" + str(len(values) + 1))
            values.append(cls._get_value(start))
        if end is not None:
            filter_statements.append(f"{page_by_column} < $" + str(len(values) + 1))
            values.append(cls._get_value(end))
        sql_query = "SELECT * FROM " + cls.table_name()
        if len(filter_statements) > 0:
            sql_query += " WHERE " + " AND ".join(filter_statements)
        if order_by_column is not None:
            sql_query += f" ORDER BY {order_by_column} {order}"
        if limit is not None and limit > 0:
            sql_query += " LIMIT $" + str(len(values) + 1)
            values.append(int(limit))
        if lock is not None:
            sql_query += f" {lock.value}"

        result = await cls.select_query(sql_query, values, no_obj=no_obj, connection=connection)
        return result

    @classmethod
    async def delete_all(cls, connection: Optional[asyncpg.connection.Connection] = None, **query: object) -> int:
        """
        Delete all documents that match the given query
        """
        query = cls._convert_field_names_to_db_column_names(query)
        filter_statement, values = cls._get_composed_filter(**query)
        query = "DELETE FROM " + cls.table_name()
        if filter_statement:
            query += " WHERE " + filter_statement
        result = await cls._execute_query(query, *values, connection=connection)
        record_count = int(result.split(" ")[1])
        return record_count

    @classmethod
    def _get_composed_filter(
        cls, offset: int = 1, col_name_prefix: Optional[str] = None, **query: object
    ) -> tuple[str, list[object]]:
        filter_statements = []
        values = []
        index_count = max(1, offset)
        for key, value in query.items():
            cls.validate_field_name(key)
            name = cls._add_column_name_prefix_if_needed(key, col_name_prefix)
            filter_statement, value = cls._get_filter(name, value, index_count)
            filter_statements.append(filter_statement)
            values.extend(value)
            index_count += len(value)
        filter_as_string = " AND ".join(filter_statements)
        return (filter_as_string, values)

    @classmethod
    def _get_filter(cls, name: str, value: object, index: int) -> tuple[str, list[object]]:
        if value is None:
            return (name + " IS NULL", [])
        filter_statement = name + "=$" + str(index)
        value = cls._get_value(value)
        return (filter_statement, [value])

    @classmethod
    def _get_value(cls, value: object) -> object:
        if isinstance(value, dict):
            return json_encode(value)

        if isinstance(value, (DataDocument, BaseModel)):
            return json_encode(value)

        if isinstance(value, list):
            return [cls._get_value(x) for x in value]

        if isinstance(value, enum.Enum):
            return value.name

        if isinstance(value, uuid.UUID):
            return str(value)

        return value

    @classmethod
    def get_composed_filter_with_query_types(
        cls, offset: int = 1, col_name_prefix: Optional[str] = None, **query: QueryFilter
    ) -> tuple[list[str], list[object]]:
        filter_statements = []
        values: list[object] = []
        index_count = max(1, offset)
        for key, value_with_query_type in query.items():
            query_type, value = value_with_query_type
            filter_statement: str
            filter_values: list[object]
            name = cls._add_column_name_prefix_if_needed(key, col_name_prefix)
            filter_statement, filter_values = cls.get_filter_for_query_type(query_type, name, value, index_count)
            filter_statements.append(filter_statement)
            values.extend(filter_values)
            index_count += len(filter_values)

        return (filter_statements, values)

    @classmethod
    def get_filter_for_query_type(
        cls, query_type: QueryType, key: str, value: object, index_count: int
    ) -> tuple[str, list[object]]:
        match query_type:
            case QueryType.EQUALS:
                filter_statement, filter_values = cls._get_filter(key, value, index_count)
            case QueryType.IS_NOT_NULL:
                filter_statement, filter_values = cls.get_is_not_null_filter(key)
            case QueryType.CONTAINS:
                filter_statement, filter_values = cls.get_contains_filter(key, value, index_count)
            case QueryType.CONTAINS_PARTIAL:
                filter_statement, filter_values = cls.get_contains_partial_filter(key, value, index_count)
            case QueryType.RANGE:
                filter_statement, filter_values = cls.get_range_filter(key, value, index_count)
            case QueryType.NOT_CONTAINS:
                filter_statement, filter_values = cls.get_not_contains_filter(key, value, index_count)
            case QueryType.COMBINED:
                filter_statement, filter_values = cls.get_filter_for_combined_query_type(
                    key, cast(dict[QueryType, object], value), index_count
                )
            case _ as _never:
                typing.assert_never(_never)
        return (filter_statement, filter_values)

    @classmethod
    def validate_field_name(cls, name: str) -> ColumnNameStr:
        """Check if the name is a valid database column name for the current type"""
        if name not in cls.get_valid_field_names():
            raise InvalidFieldNameException(f"{name} is not valid for a query on {cls.table_name()}")
        return ColumnNameStr(name)

    @classmethod
    def _add_column_name_prefix_if_needed(cls, filter_statement: str, col_name_prefix: Optional[str] = None) -> str:
        if col_name_prefix is not None:
            filter_statement = f"{col_name_prefix}.{filter_statement}"
        return filter_statement

    @classmethod
    def get_is_not_null_filter(cls, name: str) -> tuple[str, list[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that are not null.
        """
        filter_statement = f"{name} IS NOT NULL"
        return (filter_statement, [])

    @classmethod
    def get_contains_filter(cls, name: str, value: object, index: int) -> tuple[str, list[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that are contained in a given
        collection.
        """
        filter_statement = f"{name} = ANY (${str(index)})"
        value = cls._get_value(value)
        return (filter_statement, [value])

    @classmethod
    def get_filter_for_combined_query_type(
        cls, name: str, combined_value: dict[QueryType, object], index: int
    ) -> tuple[str, list[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter a single column
        based on the defined query types
        """
        filters = []
        for query_type, value in combined_value.items():
            filter_statement, filter_values = cls.get_filter_for_query_type(query_type, name, value, index)
            filters.append((filter_statement, filter_values))
            index += len(filter_values)
        filter_statement, values = cls._combine_filter_statements(filters)

        return (filter_statement, values)

    @classmethod
    def get_not_contains_filter(cls, name: str, value: object, index: int) -> tuple[str, list[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that are not contained in a given
        collection.
        """
        filter_statement = f"NOT ({name} = ANY (${str(index)}))"
        value = cls._get_value(value)
        return (filter_statement, [value])

    @classmethod
    def get_contains_partial_filter(cls, name: str, value: object, index: int) -> tuple[str, list[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that are contained in a given
        collection.
        """

        filter_statement = f"{name} ILIKE ANY (${str(index)})"
        value = cls._get_value(value)
        value = [f"%{v}%" for v in value]
        return (filter_statement, [value])

    @classmethod
    def get_range_filter(
        cls, name: str, value: Union[DateRangeConstraint, RangeConstraint], index: int
    ) -> tuple[str, list[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that match a given range
        constraint.
        """
        filter_statement: str
        values: list[object]
        filter_statement, values = cls._combine_filter_statements(
            (
                f"{name} {operator.pg_value} ${str(index + i)}",
                [cls._get_value(bound)],
            )
            for i, (operator, bound) in enumerate(value)
        )
        return (filter_statement, [cls._get_value(v) for v in values])

    @staticmethod
    def _combine_filter_statements(statements_and_values: Iterable[tuple[str, list[object]]]) -> tuple[str, list[object]]:
        filter_statements: tuple[str]
        values: tuple[list[object]]
        filter_statements, values = zip(*statements_and_values)  # type: ignore
        return (
            " AND ".join(s for s in filter_statements if s != ""),
            list(chain.from_iterable(values)),
        )

    @classmethod
    def _add_start_filter(
        cls,
        offset: int,
        order_by_column: ColumnNameStr,
        id_column: ColumnNameStr,
        start: Optional[object] = None,
        first_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> tuple[list[str], list[object]]:
        filter_statements = []
        values: list[object] = []
        if start is not None and first_id:
            filter_statements.append(f"({order_by_column}, {id_column}) > (${str(offset + 1)}, ${str(offset + 2)})")
            values.append(cls._get_value(start))
            values.append(cls._get_value(first_id))
        elif start is not None:
            filter_statements.append(f"{order_by_column} > ${str(offset + 1)}")
            values.append(cls._get_value(start))
        return filter_statements, values

    @classmethod
    def _add_end_filter(
        cls,
        offset: int,
        order_by_column: ColumnNameStr,
        id_column: ColumnNameStr,
        end: Optional[object] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> tuple[list[str], list[object]]:
        filter_statements = []
        values: list[object] = []
        if end is not None and last_id:
            filter_statements.append(f"({order_by_column}, {id_column}) < (${str(offset + 1)}, ${str(offset + 2)})")
            values.append(cls._get_value(end))
            values.append(cls._get_value(last_id))
        elif end is not None:
            filter_statements.append(f"{order_by_column} < ${str(offset + 1)}")
            values.append(cls._get_value(end))
        return filter_statements, values

    @classmethod
    def _join_filter_statements(cls, filter_statements: list[str]) -> str:
        if filter_statements:
            return "WHERE " + " AND ".join(filter_statements)
        return ""

    async def delete(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Delete this document
        """
        filter_as_string, values = self._get_filter_on_primary_key_fields()
        query = "DELETE FROM " + self.table_name() + " WHERE " + filter_as_string
        await self._execute_query(query, *values, connection=connection)

    async def delete_cascade(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        await self.delete(connection=connection)

    @classmethod
    @overload
    async def select_query(
        cls: type[TBaseDocument], query: str, values: list[object], connection: Optional[asyncpg.connection.Connection] = None
    ) -> Sequence[TBaseDocument]:
        """Return a sequence of objects of cls type."""
        ...

    @classmethod
    @overload
    async def select_query(
        cls: type[TBaseDocument],
        query: str,
        values: list[object],
        no_obj: bool,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> Sequence[Record]:
        """Return a sequence of records instances"""
        ...

    @classmethod
    async def select_query(
        cls: type[TBaseDocument],
        query: str,
        values: list[object],
        no_obj: bool = False,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> Sequence[Union[Record, TBaseDocument]]:
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                result: list[Union[Record, TBaseDocument]] = []
                async for record in con.cursor(query, *values):
                    if no_obj:
                        result.append(record)
                    else:
                        result.append(cls(from_postgres=True, **record))
                return result

    def to_dict(self) -> JsonType:
        """
        Return a dict representing the document
        """
        result = {}
        for name, metadata in self.get_field_metadata().items():
            value = self.get_value(name)

            if metadata.required and value is None:
                raise TypeError(f"{self.__name__} should have field '{name}'")

            if value is not None:
                metadata.validate(name, value)
                result[name] = value

            elif metadata.default:
                result[name] = metadata.default_value

        return result

    @classmethod
    async def execute_in_retryable_transaction(
        cls,
        fnc: Callable[[Connection], Awaitable[TransactionResult]],
        tx_isolation_level: Optional[str] = None,
    ) -> TransactionResult:
        """
        Execute the queries in fnc using the transaction isolation level `tx_isolation_level` and return the
        result returned by fnc. This method performs retries when the transaction is aborted due to a
        serialization error.
        """
        async with cls.get_connection() as postgresql_client:
            attempt = 1
            while True:
                try:
                    async with postgresql_client.transaction(isolation=tx_isolation_level):
                        return await fnc(postgresql_client)
                except SerializationError:
                    if attempt > 3:
                        raise Exception("Failed to execute transaction after 3 attempts.")
                    else:
                        # Exponential backoff
                        await asyncio.sleep(pow(10, attempt) / 1000)
                        attempt += 1


class Project(BaseDocument):
    """
    An inmanta configuration project

    :param name: The name of the configuration project.
    """

    __primary_key__ = ("id",)

    id: uuid.UUID
    name: str

    def to_dto(self) -> m.Project:
        return m.Project(id=self.id, name=self.name, environments=[])

    async def delete_cascade(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        This method doesn't rely on the DELETE CASCADE functionality of PostgreSQL because it causes deadlocks.
        As such, we perform the deletes on each table in a separate transaction.
        """
        async with self.get_connection(connection=connection) as con:
            envs_in_project: abc.Sequence[Environment] = await Environment.get_list(project=self.id, connection=con)
            for env in envs_in_project:
                await env.delete_cascade(connection=con)
            await self.delete(connection=con)


def convert_boolean(value: Union[bool, str]) -> bool:
    if isinstance(value, bool):
        return value

    if value.lower() not in RawConfigParser.BOOLEAN_STATES:
        raise ValueError("Not a boolean: %s" % value)
    return RawConfigParser.BOOLEAN_STATES[value.lower()]


def convert_int(value: Union[float, int, str]) -> Union[int, float]:
    if isinstance(value, (int, float)):
        return value

    f_value = float(value)
    i_value = int(value)

    if i_value == f_value:
        return i_value
    return f_value


def convert_positive_float(value: Union[float, int, str]) -> float:
    if isinstance(value, float):
        float_value = value
    else:
        float_value = float(value)
    if float_value < 0:
        raise ValueError(f"This value should be positive, got: {value}")
    return float_value


def translate_to_postgres_type(type: str) -> str:
    if type not in TYPE_MAP:
        raise Exception("Type '" + type + "' is not a valid type for a settings entry")
    return TYPE_MAP[type]


def convert_agent_trigger_method(value: object) -> str:
    if isinstance(value, const.AgentTriggerMethod):
        return value
    value = str(value)
    valid_values = [x.name for x in const.AgentTriggerMethod]
    if value not in valid_values:
        raise ValueError("{} is not a valid agent trigger method. Valid value: {}".format(value, ",".join(valid_values)))
    return value


def validate_cron_or_int(value: Union[int, str]) -> str:
    try:
        return str(int(value))
    except ValueError:
        try:
            assert isinstance(value, str)  # Make mypy happy
            return validate_cron(value, allow_empty=False)
        except ValueError as e:
            raise ValueError(f"'{value}' is not a valid cron expression or int: {e}")


def validate_cron(value: str, allow_empty: bool = True) -> str:
    if not value:
        if allow_empty:
            return ""
        raise ValueError("The given cron expression is an empty string")
    try:
        CronTab(value)
    except ValueError as e:
        raise ValueError(f"'{value}' is not a valid cron expression: {e}")
    return value


TYPE_MAP = {
    "int": "integer",
    "bool": "boolean",
    "dict": "jsonb",
    "str": "varchar",
    "enum": "varchar",
    "positive_float": "double precision",
}

AUTO_DEPLOY = "auto_deploy"
AUTOSTART_AGENT_DEPLOY_INTERVAL = "autostart_agent_deploy_interval"
AUTOSTART_AGENT_REPAIR_INTERVAL = "autostart_agent_repair_interval"
RESET_DEPLOY_PROGRESS_ON_START = "reset_deploy_progress_on_start"
AUTOSTART_ON_START = "autostart_on_start"
AGENT_AUTH = "agent_auth"
SERVER_COMPILE = "server_compile"
AUTO_FULL_COMPILE = "auto_full_compile"
RESOURCE_ACTION_LOGS_RETENTION = "resource_action_logs_retention"
PROTECTED_ENVIRONMENT = "protected_environment"
NOTIFICATION_RETENTION = "notification_retention"
AVAILABLE_VERSIONS_TO_KEEP = "available_versions_to_keep"
RECOMPILE_BACKOFF = "recompile_backoff"
ENVIRONMENT_METRICS_RETENTION = "environment_metrics_retention"


class Setting:
    """
    A class to define a new environment setting.
    """

    def __init__(
        self,
        name: str,
        typ: str,
        default: Optional[m.EnvSettingType] = None,
        doc: Optional[str] = None,
        validator: Optional[Callable[[m.EnvSettingType], m.EnvSettingType]] = None,
        recompile: bool = False,
        update_model: bool = False,
        agent_restart: bool = False,
        allowed_values: Optional[list[m.EnvSettingType]] = None,
        section: Optional[str] = None,
    ) -> None:
        """
        :param name: The name of the setting.
        :param type: The type of the value. This type is mainly used for documentation purpose.
        :param default: An optional default value for this setting. When a default is set and the
                        is requested from the database, it will return the default value and also store
                        the default value in the database.
        :param doc: The documentation/help string for this setting
        :param validator: A validation and casting function for input settings. Should raise ValueError if validation fails.
        :param recompile: Trigger a recompile of the model when a setting is updated?
        :param update_model: Update the configuration model (git pull on project and repos)
        :param agent_restart: Restart autostarted agents when this settings is updated.
        :param allowed_values: list of possible values (if type is enum)
        :param section: the config section this parameter should go into, optional for backward compatibility with <iso9
        """
        self.name: str = name
        self.typ: str = typ
        self._default = default
        self.doc = doc
        self.validator = validator
        self.recompile = recompile
        self.update = update_model
        self.agent_restart = agent_restart
        self.allowed_values = allowed_values
        self.section = section

    @property
    def default(self) -> Optional[m.EnvSettingType]:
        if self._default and isinstance(self._default, dict):
            # Dicts are mutable objects. Return a copy.
            return dict(self._default)
        else:
            return self._default

    def get_setting_definition_for_api(
        self, setting_details: m.EnvironmentSettingDetails | None
    ) -> m.EnvironmentSettingDefinitionAPI:
        """
        Returns the definition of the given setting as it would be served out over the API.

        :param setting_details: The setting details as stored in the database or None if this
                                setting is not present in the database.
        """
        return m.EnvironmentSettingDefinitionAPI(
            name=self.name,
            type=self.typ,
            default=self._default,
            doc=self.doc,
            recompile=self.recompile,
            update_model=self.update,
            agent_restart=self.agent_restart,
            allowed_values=self.allowed_values,
            section=self.section,
            protected=setting_details.protected if setting_details else False,
            protected_by=setting_details.protected_by if setting_details else None,
        )

    def to_dict(self) -> JsonType:
        return {
            "type": self.typ,
            "default": self.default,
            "doc": self.doc,
            "recompile": self.recompile,
            "update": self.update,
            "agent_restart": self.agent_restart,
            "allowed_values": self.allowed_values,
            "section": self.section,
        }

    def to_dto(self) -> m.EnvironmentSetting:
        return m.EnvironmentSetting(
            name=self.name,
            type=self.typ,
            default=self.default,
            doc=self.doc,
            recompile=self.recompile,
            update_model=self.update,
            agent_restart=self.agent_restart,
            allowed_values=self.allowed_values,
            section=self.section,
        )


class EnvironmentSettingsContainer(BaseModel):
    """
    Container object that stores all the environment settings for a certain environment in the db.
    """

    settings: dict[str, m.EnvironmentSettingDetails] = {}

    def has(self, setting_name: str) -> bool:
        """
        Return True iff the given setting_name is present in this settings container.
        """
        return setting_name in self.settings

    def get_all(self) -> dict[str, m.EnvironmentSettingDetails]:
        return {k: v.model_copy(deep=True) for k, v in self.settings.items()}

    def get(self, setting_name: str) -> m.EnvironmentSettingDetails:
        return self.settings[setting_name]

    def get_value(self, setting_name: str) -> m.EnvSettingType:
        """
        Return the value of the given setting in this settings container.
        A KeyError is raised if the given setting is not present in this settings container.
        """
        return self.settings[setting_name].value

    def set(self, setting_name: str, env_setting_details: m.EnvironmentSettingDetails) -> None:
        """
        Set the details for the given setting.
        """
        self.settings[setting_name] = env_setting_details

    def remove(self, setting_name: str) -> None:
        """
        Remove the given setting from this settings container.
        """
        self.settings.pop(setting_name, None)

    def get_all_setting_values(self) -> dict[str, m.EnvSettingType]:
        """
        Return a dictionary with as key the name of a setting and as value the value for that setting
        in this settings container.
        """
        return {setting_name: setting_details.value for setting_name, setting_details in self.settings.items()}

    def is_protected(self, setting_name: str) -> bool:
        """
        Return True iff the given setting is protected.
        """
        return setting_name in self.settings and self.settings[setting_name].protected

    def get_protected_by(self, setting_name: str) -> m.ProtectedBy | None:
        try:
            protected_by = self.settings[setting_name].protected_by
        except KeyError:
            return None
        else:
            if protected_by is None:
                return None
            else:
                return m.ProtectedBy(protected_by)

    def get_protected_by_description(self, setting_name: str) -> str | None:
        """
        Returns a detail description about why the given setting is protected.
        Or None, if the given setting is not protected.
        """
        protected_by: m.ProtectedBy | None = self.get_protected_by(setting_name)
        if not protected_by:
            return None
        return protected_by.get_detailed_description()

    def _clear_protection(self, setting_name: str) -> None:
        """
        Mark the given environent setting as unprotected.
        """
        if setting_name in self.settings:
            self.settings[setting_name].protected = False
            self.settings[setting_name].protected_by = None

    def set_and_protect(
        self,
        protected_settings: dict[str, m.EnvSettingType],
        protected_by: m.ProtectedBy,
    ) -> None:
        """
        Set the values for the given environment settings and mark them as protected.
        All other environment settings protected by the same ProtectedBy marker will
        have their protection status cleared.
        """
        # Update settings and mark as protected
        for setting_name, setting_value in protected_settings.items():
            self.set(
                setting_name,
                m.EnvironmentSettingDetails(
                    value=setting_value,
                    protected=True,
                    protected_by=protected_by,
                ),
            )
        # Remove protection status other settings
        for setting_name in self.settings.keys() - protected_settings.keys():
            if self.is_protected(setting_name) and self.get_protected_by(setting_name) is protected_by:
                self._clear_protection(setting_name)


@stable_api
class Environment(BaseDocument):
    """
    A deployment environment of a project

    :param id: A unique, machine generated id
    :param name: The name of the deployment environment.
    :param project: The project this environment belongs to.
    :param repo_url: The repository url that contains the configuration model code for this environment.
    :param repo_branch: The repository branch that contains the configuration model code for this environment.
    :param settings: Key/value settings for this environment. This dictionary does not necessarily contain a key
                     for every environment setting known by the server.
    :param last_version: The last version number that was reserved for this environment
    :param description: The description of the environment
    :param icon: An icon for the environment
    """

    __primary_key__ = ("id",)

    id: uuid.UUID
    name: str
    project: uuid.UUID
    repo_url: str = ""
    repo_branch: str = ""
    settings: EnvironmentSettingsContainer = EnvironmentSettingsContainer()
    last_version: int = 0
    halted: bool = False
    description: str = ""
    icon: str = ""
    is_marked_for_deletion: bool = False

    def to_dto(self) -> m.Environment:
        return m.Environment(
            id=self.id,
            name=self.name,
            project_id=self.project,
            repo_url=self.repo_url,
            repo_branch=self.repo_branch,
            settings=self.settings.get_all_setting_values(),
            halted=self.halted,
            is_marked_for_deletion=self.is_marked_for_deletion,
            description=self.description,
            icon=self.icon,
        )

    _settings: dict[str, Setting] = {
        AUTO_DEPLOY: Setting(
            name=AUTO_DEPLOY,
            typ="bool",
            default=True,
            doc="When this boolean is set to true, the orchestrator will automatically release a new version "
            "that was compiled by the orchestrator itself.",
            validator=convert_boolean,
            section="deploy",
        ),
        AUTOSTART_AGENT_DEPLOY_INTERVAL: Setting(
            name=AUTOSTART_AGENT_DEPLOY_INTERVAL,
            typ="str",
            default="600",
            doc=(
                "Set the frequency of deploy runs (i.e. only trigger a deploy for resources that are not "
                "compliant as far as we know). "
                "When specified as an integer, this will set the wait time (in seconds) before attempting to redeploy a "
                "resource after an unsuccessful deployment, on a per-resource basis. "
                "When specified as a cron-like expression, a global deploy (i.e. for all resources that have a known "
                "divergence with their desired state) will be run following a cron-like time-to-run specification, interpreted "
                "in UTC. The expected format is ``[sec] min hour dom month dow [year]`` (If only 6 values are provided, they "
                "are interpreted as ``min hour dom month dow year``). A deploy will be requested at the scheduled time. "
                "Set this to 0 to disable the scheduled deploy runs. "
                "When specified as an integer, it must be smaller than the repair interval."
            ),
            validator=validate_cron_or_int,
            agent_restart=False,
            section="agent",
        ),
        AUTOSTART_AGENT_REPAIR_INTERVAL: Setting(
            name=AUTOSTART_AGENT_REPAIR_INTERVAL,
            typ="str",
            default="86400",
            doc=(
                "Set the frequency of repair runs (i.e. trigger a deploy regardless of the assumed "
                "state of the resource(s)). When specified as an integer, this will set the wait time (in seconds) before "
                "re-scheduling a resource for deployment after the previous deployment has ended, regardless of success or "
                "failure, on a per-resource basis. When specified as a cron-like expression, a global repair (i.e. a full "
                "deploy for all resources, regardless of their assumed desired state and regardless of their actual state) "
                "will be run following a cron-like time-to-run specification, interpreted in UTC. The expected format is "
                "`[sec] min hour dom month dow [year]` ( If only 6 values are provided, they are interpreted as "
                "`min hour dom month dow year`). A repair will be requested at the scheduled time. "
                "Setting this to 0 to disable the scheduled repair runs. When specified as an integer, it must be "
                "larger than the deploy interval."
            ),
            validator=validate_cron_or_int,
            agent_restart=False,
            section="agent",
        ),
        RESET_DEPLOY_PROGRESS_ON_START: Setting(
            name=RESET_DEPLOY_PROGRESS_ON_START,
            typ="bool",
            default=False,
            doc=(
                "By default the orchestrator picks up the deployment process where it was when it restarted (or halted)."
                " When this option is enabled, the orchestrator restarts the deployment based on the last known deployment"
                " state. It is recommended to leave this disabled because in most cases it is faster (because we can skip some"
                " redundant work) and it has more accurate state and progress reporting (because we retain more state to reason"
                " on). Enable this in case there are issues with restoring the deployment state at restart."
            ),
            agent_restart=True,
            section="scheduler",
        ),
        AUTOSTART_ON_START: Setting(
            name=AUTOSTART_ON_START,
            default=True,
            typ="bool",
            validator=convert_boolean,
            doc="Automatically start agents when the server starts instead of only just in time.",
            section="agent",
        ),
        SERVER_COMPILE: Setting(
            name=SERVER_COMPILE,
            default=True,
            typ="bool",
            validator=convert_boolean,
            doc="Allow the server to compile the configuration model.",
            section="compiler",
        ),
        AUTO_FULL_COMPILE: Setting(
            name=AUTO_FULL_COMPILE,
            default="",
            typ="str",
            validator=validate_cron,
            doc=(
                "Periodically run a full compile following a cron-like time-to-run specification interpreted in UTC with format"
                " `[sec] min hour dom month dow [year]` (If only 6 values are provided, they are interpreted as"
                " `min hour dom month dow year`). A compile will be requested at the scheduled time. The actual"
                " compilation may have to wait in the compile queue for some time, depending on the size of the queue and the"
                " RECOMPILE_BACKOFF environment setting. This setting has no effect when server_compile is disabled."
            ),
            section="compiler",
        ),
        RESOURCE_ACTION_LOGS_RETENTION: Setting(
            name=RESOURCE_ACTION_LOGS_RETENTION,
            default=7,
            typ="int",
            validator=convert_int,
            doc="The number of days to retain resource-action logs",
            section="storage",
        ),
        AVAILABLE_VERSIONS_TO_KEEP: Setting(
            name=AVAILABLE_VERSIONS_TO_KEEP,
            default=100,
            typ="int",
            validator=convert_int,
            doc="The number of versions to keep stored in the database, excluding the latest released version.",
            section="storage",
        ),
        PROTECTED_ENVIRONMENT: Setting(
            name=PROTECTED_ENVIRONMENT,
            default=False,
            typ="bool",
            validator=convert_boolean,
            doc="When set to true, this environment cannot be cleared or deleted.",
            section="environment",
        ),
        NOTIFICATION_RETENTION: Setting(
            name=NOTIFICATION_RETENTION,
            default=365,
            typ="int",
            validator=convert_int,
            doc="The number of days to retain notifications for",
            section="storage",
        ),
        RECOMPILE_BACKOFF: Setting(
            name=RECOMPILE_BACKOFF,
            default=0.1,
            typ="positive_float",
            validator=convert_positive_float,
            doc="""The number of seconds to wait before the server may attempt to do a new recompile.
                    Recompiles are triggered after facts updates for example.""",
            section="compiler",
        ),
        ENVIRONMENT_METRICS_RETENTION: Setting(
            name=ENVIRONMENT_METRICS_RETENTION,
            typ="int",
            default=336,
            doc="The number of hours that environment metrics have to be retained before they are cleaned up. "
            "Default=336 hours (2 weeks). Set to 0 to disable automatic cleanups.",
            validator=convert_int,
            section="storage",
        ),
    }

    @classmethod
    def get_default_for_setting(cls, setting_name: str) -> Optional[m.EnvSettingType]:
        """
        Returns the default value for the setting with the given name.
        """
        if setting_name not in cls._settings:
            raise KeyError()
        return cls._settings[setting_name].default

    @classmethod
    def get_setting_definitions_for_api(
        cls, settings: dict[str, m.EnvironmentSettingDetails]
    ) -> dict[str, m.EnvironmentSettingDefinitionAPI]:
        """
        Returns a dictionary that maps each of the given settings to their definitions as they would be served out over the API.
        """
        return {
            setting_name: setting_def.get_setting_definition_for_api(setting_details=settings.get(setting_name, None))
            for setting_name, setting_def in cls._settings.items()
        }

    async def get(self, key: str, connection: Optional[asyncpg.connection.Connection] = None) -> m.EnvSettingType:
        """
        Get a setting in this environment.

        :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
        """
        if key not in self._settings:
            raise KeyError()

        if self.settings.has(key):
            return self.settings.get_value(key)

        default_value = self._settings[key].default
        if default_value is None:
            raise KeyError()

        await self.set(key, default_value, connection=connection, allow_override=False)
        return self.settings.get_value(key)

    async def set(
        self,
        key: str,
        value: m.EnvSettingType,
        connection: Optional[asyncpg.connection.Connection] = None,
        allow_override: bool = True,
    ) -> None:
        """
        Set a new setting in this environment.

        :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
        :param value: The value of the settings. The value should be of type as defined in _settings
        :param allow_override: If set to False, don't set the given environment setting when it already exists in the setting
                               dictionary in the database.
        """
        if key not in self._settings:
            raise KeyError()
        # TODO: convert this to a string
        if callable(self._settings[key].validator):
            value = self._settings[key].validator(value)

        type = translate_to_postgres_type(self._settings[key].typ)
        filter_statement, values = self._get_composed_filter(name=self.name, project=self.project, offset=5)
        query = f"""
                UPDATE {self.table_name()}
                SET settings=(
                    CASE
                        WHEN $1 IS FALSE AND (settings->'settings') ? $2::text
                            -- The name of the setting is present in the settings dictionary,
                            -- but allow_override is disabled -> Don't change it
                            THEN settings
                        WHEN (settings->'settings') ? $2::text
                            -- The name of the setting is present in the settings dictionary.
                            -- -> Only update the value field.
                            THEN jsonb_set(settings,  ARRAY['settings', $2, 'value'], to_jsonb($3::{type}), TRUE)
                        ELSE
                            -- The name of the setting is not present in the settings dictionary.
                            -- Put a full EnvironmentSettingsDetails dictionary in place.
                            jsonb_set(settings,  ARRAY['settings', $2], $4::jsonb, TRUE)
                    END
                )
                WHERE {filter_statement}
                RETURNING settings
        """
        values = [
            allow_override,
            self._get_value(key),
            self._get_value(value),
            self._get_value(m.EnvironmentSettingDetails(value=value)),
        ] + values
        new_value = await self._fetchval(query, *values, connection=connection)
        new_value_parsed = cast(
            EnvironmentSettingsContainer, self.get_field_metadata()["settings"].from_db(name="settings", value=new_value)
        )
        self.settings.set(setting_name=key, env_setting_details=new_value_parsed.settings[key])

    async def unset(self, key: str) -> None:
        """
        Unset a setting in this environment. If a default value is provided, this value will replace the current value.

        :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
        """
        if key not in self._settings:
            raise KeyError()

        if self._settings[key].default is None:
            filter_statement, values = self._get_composed_filter(name=self.name, project=self.project, offset=2)
            query = f"""
                UPDATE {self.table_name()}
                SET settings->'settings'=(settings->'settings') - $1
                WHERE {filter_statement}
            """
            values = [self._get_value(key)] + values
            await self._execute_query(query, *values)
            self.settings.remove(key)
        else:
            await self.set(key, self._settings[key].default)

    async def set_protected_environment_settings(
        self,
        protected_settings: dict[str, m.EnvSettingType],
        protected_by: m.ProtectedBy,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        # Perform update in-memory without altering self
        settings_copy = self.settings.model_copy(deep=True)
        settings_copy.set_and_protect(protected_settings, protected_by)
        # Update the database
        await self.update_fields(settings=settings_copy, connection=connection)
        # The database update succeeded -> we can update self
        self.settings = settings_copy

    async def mark_for_deletion(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """Mark an environment as being in the process of deletion."""
        await self.update_fields(is_marked_for_deletion=True, connection=connection)

    async def delete_cascade(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Completely remove this environment from the db
        """
        async with self.get_connection(connection=connection) as con:
            await self.clear(connection=con)
            await self.delete(connection=con)

    async def clear(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Delete everything related to this environment from the db, except the entry in the Environment table.

        This method doesn't rely on the DELETE CASCADE functionality of PostgreSQL because it causes deadlocks.
        This is especially true for the tables resourceaction_resource, resource and resourceaction, because they
        have a high read/write load. As such, we perform the deletes on each table in a separate transaction.
        """
        async with self.get_connection(connection=connection) as con:
            await Agent.delete_all(environment=self.id, connection=con)
            await AgentInstance.delete_all(tid=self.id, connection=con)
            await AgentProcess.delete_all(environment=self.id, connection=con)
            await Compile.delete_all(environment=self.id, connection=con)  # Triggers cascading delete on report table
            await Parameter.delete_all(environment=self.id, connection=con)
            await Notification.delete_all(environment=self.id, connection=con)

            await AgentModules.delete_all(environment=self.id, connection=con)
            await InmantaModule.delete_all(environment=self.id, connection=con)
            await ModuleFiles.delete_all(environment=self.id, connection=con)

            await DiscoveredResource.delete_all(environment=self.id, connection=con)
            await EnvironmentMetricsGauge.delete_all(environment=self.id, connection=con)
            await EnvironmentMetricsTimer.delete_all(environment=self.id, connection=con)
            await DryRun.delete_all(environment=self.id, connection=con)
            await UnknownParameter.delete_all(environment=self.id, connection=con)
            await self._execute_query(
                "DELETE FROM public.resourceaction_resource WHERE environment=$1", self.id, connection=con
            )
            await ResourceAction.delete_all(environment=self.id, connection=con)
            await self._execute_query(
                "DELETE FROM public.resource_set_configuration_model WHERE environment=$1", self.id, connection=con
            )
            await ResourceSet.delete_all(environment=self.id, connection=con)
            # Resources are deleted via cascade
            await ConfigurationModel.delete_all(environment=self.id, connection=con)
            await ResourcePersistentState.delete_all(environment=self.id, connection=con)
            await Scheduler.delete_all(environment=self.id, connection=con)

    async def get_next_version(self, connection: Optional[asyncpg.connection.Connection] = None) -> int:
        """
        Reserves the next available version and returns it. Increments the last_version counter.
        """
        record = await self._fetchrow(
            f"""
UPDATE {self.table_name()}
SET last_version = last_version + 1
WHERE id = $1
RETURNING last_version;
""",
            self.id,
            connection=connection,
        )
        version = cast(int, record[0])
        self.last_version = version
        return version

    @classmethod
    def register_setting(cls, setting: Setting) -> None:
        """
        Adds a new environment setting that was defined by an extension.

        :param setting: the setting that should be added to the existing settings
        """
        if setting.name in cls._settings:
            raise KeyError()
        cls._settings[setting.name] = setting

    @classmethod
    async def get_list(
        cls: type[TBaseDocument],
        *,
        order_by_column: Optional[str] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: Optional[bool] = None,
        lock: Optional[RowLockMode] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        details: bool = True,
        **query: object,
    ) -> list[TBaseDocument]:
        """
        Get a list of documents matching the filter args.

        """
        if details:
            return await super().get_list(
                order_by_column=order_by_column,
                order=order,
                limit=limit,
                offset=offset,
                no_obj=no_obj,
                lock=lock,
                connection=connection,
                **query,
            )
        return await cls.get_list_without_details(
            order_by_column=order_by_column,
            order=order,
            limit=limit,
            offset=offset,
            no_obj=no_obj,
            lock=lock,
            connection=connection,
            **query,
        )

    @classmethod
    async def get_list_without_details(
        cls: type[TBaseDocument],
        *,
        order_by_column: Optional[str] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: Optional[bool] = None,
        lock: Optional[RowLockMode] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: object,
    ) -> list[TBaseDocument]:
        """
        Get a list of environments matching the filter args.
        Don't return the description and icon columns.
        """
        columns = [column_name for column_name in cls.get_valid_field_names() if column_name not in {"description", "icon"}]
        return await super().get_list_with_columns(
            order_by_column=order_by_column,
            order=order,
            limit=limit,
            offset=offset,
            no_obj=no_obj,
            lock=lock,
            connection=connection,
            columns=columns,
            **query,
        )

    @classmethod
    async def get_by_id(
        cls: type[TBaseDocument],
        doc_id: uuid.UUID,
        connection: Optional[asyncpg.connection.Connection] = None,
        details: bool = True,
    ) -> Optional[TBaseDocument]:
        """
        Get a specific environment based on its ID

        :return: An instance of this class with its fields filled from the database.
        """
        result = await cls.get_list(id=doc_id, connection=connection, details=details)
        if len(result) > 0:
            return result[0]
        return None

    async def acquire_release_version_lock(self, *, shared: bool = False, connection: asyncpg.Connection) -> None:
        """
        Acquires a transaction-level advisory lock for concurrency control between release_version and
        calls that need the latest version.

        This lock should also be held when updating any resource state in any other way than the normal agent deploy path
        Up to now, this means
        - setting resource state after increment calculation on release
        - propagation of resource state from a stale deploy to the latest version
        - setting resource state after increment calculation on agent pull

        :param env: The environment to acquire the lock for.
        :param shared: If true, doesn't conflict with other shared locks, only with non-shared ones.
        :param connection: The connection hosting the transaction for which to acquire a lock.
        """
        await self._xact_lock(const.PG_ADVISORY_KEY_RELEASE_VERSION, self.id, shared=shared, connection=connection)

    async def put_version_lock(self, *, shared: bool = False, connection: asyncpg.Connection) -> None:
        """
        Acquires a transaction-level advisory lock for concurrency control between put_version and put_partial.

        :param env: The environment to acquire the lock for.
        :param shared: If true, doesn't conflict with other shared locks, only with non-shared ones.
        :param connection: The connection hosting the transaction for which to acquire a lock.
        """
        await self._xact_lock(const.PG_ADVISORY_KEY_PUT_VERSION, self.id, shared=shared, connection=connection)


class Parameter(BaseDocument):
    """
    A parameter that can be used in the configuration model

    :param name: The name of the parameter
    :param value: The value of the parameter
    :param environment: The environment this parameter belongs to
    :param source: The source of the parameter
    :param resource_id: An optional resource id
    :param updated: When was the parameter updated last
    :param expires: Boolean denoting whether this parameter expires.

    :todo Add history
    """

    __primary_key__ = ("id", "name", "environment")

    id: uuid.UUID
    name: str
    value: str = ""
    environment: uuid.UUID
    source: str
    resource_id: ResourceIdStr = ""
    updated: Optional[datetime.datetime] = None
    metadata: Optional[JsonType] = None
    expires: bool

    @classmethod
    async def get_updated_before_active_env(
        cls,
        updated_before: datetime.datetime,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> list["Parameter"]:
        """
        Retrieve the list of parameters that were updated before a specified datetime for environments that are not halted
        """
        query = f"""
        WITH latest_released_version AS(
            SELECT max(c.version) AS version, c.environment
            FROM {ConfigurationModel.table_name()} AS c
            WHERE c.released
            GROUP BY c.environment
        )
        SELECT p.*
        FROM {cls.table_name()} AS p
        INNER JOIN {Environment.table_name()} AS e
            ON p.environment=e.id
        WHERE NOT e.halted
            AND p.updated < $1
            AND p.expires
            AND (
                -- If it's a fact, it needs to belong to the latest released version.
                p.resource_id IS NULL
                OR p.resource_id = ''
                OR EXISTS(
                    SELECT 1
                    FROM {Resource.table_name()} AS r
                    INNER JOIN resource_set_configuration_model AS rscm
                        ON rscm.environment=r.environment
                        AND rscm.resource_set=r.resource_set
                    INNER JOIN latest_released_version AS lrv
                        ON rscm.model=lrv.version
                        AND rscm.environment=lrv.environment
                    WHERE r.environment=p.environment
                        AND r.resource_id=p.resource_id
                )
            );
        """
        values = [cls._get_value(updated_before)]
        return await cls.select_query(query, values, connection=connection)

    @classmethod
    async def list_parameters(cls, env_id: uuid.UUID, **metadata_constraints: str) -> list["Parameter"]:
        query = "SELECT * FROM " + cls.table_name() + " WHERE environment=$1"
        values = [cls._get_value(env_id)]
        for key, value in metadata_constraints.items():
            query_param_index = len(values) + 1
            query += " AND metadata @> $" + str(query_param_index) + "::jsonb"
            dict_value = {key: value}
            values.append(cls._get_value(dict_value))
        query += " ORDER BY name"
        result = await cls.select_query(query, values)
        return result

    def as_fact(self) -> m.Fact:
        assert self.source == "fact"
        return m.Fact(
            id=self.id,
            name=self.name,
            value=self.value,
            environment=self.environment,
            resource_id=self.resource_id,
            source=self.source,
            updated=self.updated,
            metadata=self.metadata,
            expires=self.expires,
        )

    def as_param(self) -> m.Parameter:
        return m.Parameter(
            id=self.id,
            name=self.name,
            value=self.value,
            environment=self.environment,
            source=self.source,
            updated=self.updated,
            metadata=self.metadata,
        )


class UnknownParameter(BaseDocument):
    """
    A parameter that the compiler indicated that was unknown. This parameter causes the configuration model to be
    incomplete for a specific environment.

    :param name:
    :param resource_id:
    :param source:
    :param environment:
    :param version: The version id of the configuration model on which this parameter was reported
    """

    __primary_key__ = ("id",)

    id: uuid.UUID
    name: str
    environment: uuid.UUID
    source: str
    resource_id: ResourceIdStr = ""
    version: int
    metadata: Optional[dict[str, object]]
    resolved: bool = False

    def copy(self, new_version: int) -> "UnknownParameter":
        """
        Create a new UnknownParameter using this object as a template. The returned object will
        have the id field unset and the version field set the new_version.
        """
        return UnknownParameter(
            name=self.name,
            environment=self.environment,
            source=self.source,
            resource_id=self.resource_id,
            version=new_version,
            metadata=self.metadata,
            resolved=self.resolved,
        )

    @classmethod
    async def get_unknowns_in_latest_released_model_versions(
        cls, connection: asyncpg.Connection
    ) -> Sequence["UnknownParameter"]:
        """
        Returns all the unknowns in the latest released model version of each non-halted environment.
        """
        query = f"""
        SELECT u.*
        FROM {cls.table_name()} AS u INNER JOIN {Environment.table_name()} AS e ON u.environment=e.id
        WHERE NOT e.halted
            AND u.version=(
                SELECT max(c.version)
                FROM {ConfigurationModel.table_name()} AS c
                WHERE c.environment=e.id AND c.released
            )
            AND NOT u.resolved;
        """
        return await cls.select_query(query, values=[], connection=connection)

    @classmethod
    async def get_unknowns_to_copy_in_partial_compile(
        cls,
        environment: uuid.UUID,
        source_version: int,
        updated_resource_sets: abc.Set[str],
        deleted_resource_sets: abc.Set[str],
        rids_in_partial_compile: abc.Set[ResourceIdStr],
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> list["UnknownParameter"]:
        """
        Returns a subset of the unknowns in source_version of environment. It returns the unknowns that:
            * Are not associated with a resource
            * Are associated with a resource that:
               - don't belong to the resource set updated_resource_sets and deleted_resource_sets
               - and, don't have a resource_id in rids_in_partial_compile (An unknown might belong to a shared resource that
                 is not exported by the partial compile)
        """
        query = f"""
            WITH resources_with_version AS (
                SELECT r.resource_id,
                       rs.name AS resource_set_name,
                       r.environment,
                       rscm.model
                FROM resource_set_configuration_model AS rscm
                INNER JOIN {ResourceSet.table_name()} AS rs
                    ON rscm.environment=rs.environment
                    AND rscm.resource_set=rs.id
                INNER JOIN {Resource.table_name()} AS r
                    ON rs.environment=r.environment AND rs.id=r.resource_set
                WHERE rscm.environment=$1 AND rscm.model=$2
            )
            SELECT u.*
            FROM {cls.table_name()} AS u
            LEFT JOIN resources_with_version AS rwv
                ON u.environment=rwv.environment AND u.version=rwv.model AND u.resource_id=rwv.resource_id
            WHERE
                u.environment=$1
                AND u.version=$2
                AND u.resolved IS FALSE
                AND (rwv.resource_id IS NULL OR NOT rwv.resource_id=ANY($4))
                AND (rwv.resource_set_name IS NULL OR NOT rwv.resource_set_name=ANY($3))
        """
        async with cls.get_connection(connection) as con:
            result = await con.fetch(
                query,
                environment,
                source_version,
                list(updated_resource_sets | deleted_resource_sets),
                list(rids_in_partial_compile),
            )
            return [cls(from_postgres=True, **uk) for uk in result]


class AgentProcess(BaseDocument):
    """
    A process in the infrastructure that has (had) a session as an agent.

    :param hostname: The hostname of the device.
    :param environment: To what environment is this process bound
    :param last_seen: When did the server receive data from the node for the last time.
    """

    __primary_key__ = ("sid",)

    sid: uuid.UUID
    hostname: str
    environment: uuid.UUID
    first_seen: Optional[datetime.datetime] = None
    last_seen: Optional[datetime.datetime] = None
    expired: Optional[datetime.datetime] = None

    @classmethod
    async def get_live(cls, environment: Optional[uuid.UUID] = None) -> list["AgentProcess"]:
        if environment is not None:
            result = await cls.get_list(
                limit=DBLIMIT, environment=environment, expired=None, order_by_column="last_seen", order="ASC NULLS LAST"
            )
        else:
            result = await cls.get_list(limit=DBLIMIT, expired=None, order_by_column="last_seen", order="ASC NULLS LAST")
        return result

    @classmethod
    async def get_by_sid(
        cls, sid: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None
    ) -> Optional["AgentProcess"]:
        objects = await cls.get_list(limit=DBLIMIT, connection=connection, expired=None, sid=sid)
        if len(objects) == 0:
            return None
        elif len(objects) > 1:
            LOGGER.exception("Multiple objects with the same unique id found!")
            return objects[0]
        else:
            return objects[0]

    @classmethod
    async def seen(
        cls,
        env: uuid.UUID,
        nodename: str,
        sid: uuid.UUID,
        now: datetime.datetime,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Update the last_seen parameter of the process and mark as not expired.
        """
        proc = await cls.get_one(connection=connection, sid=sid)
        if proc is None:
            proc = cls(hostname=nodename, environment=env, first_seen=now, last_seen=now, sid=sid)
            await proc.insert(connection=connection)
        else:
            await proc.update_fields(connection=connection, last_seen=now, expired=None)

    @classmethod
    async def update_last_seen(
        cls, sid: uuid.UUID, last_seen: datetime.datetime, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        aps = await cls.get_by_sid(sid=sid, connection=connection)
        if aps:
            await aps.update_fields(connection=connection, last_seen=last_seen)

    @classmethod
    async def expire_process(
        cls, sid: uuid.UUID, now: datetime.datetime, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        aps = await cls.get_by_sid(sid=sid, connection=connection)
        if aps is not None:
            await aps.update_fields(connection=connection, expired=now)

    @classmethod
    async def expire_all(cls, now: datetime.datetime, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        query = f"""
                UPDATE {cls.table_name()}
                SET expired=$1
                WHERE expired IS NULL
        """
        await cls._execute_query(query, cls._get_value(now), connection=connection)

    @classmethod
    async def cleanup(cls, nr_expired_records_to_keep: int) -> None:
        query = f"""
            WITH halted_env AS (
                SELECT id FROM environment WHERE halted = true
            )
            DELETE FROM {cls.table_name()} AS a1
            WHERE a1.expired IS NOT NULL AND
                  a1.environment NOT IN (SELECT id FROM halted_env) AND
                  (
                    -- Take nr_expired_records_to_keep into account
                    SELECT count(*)
                    FROM {cls.table_name()} a2
                    WHERE a1.environment=a2.environment AND
                          a1.hostname=a2.hostname AND
                          a2.expired IS NOT NULL AND
                          a2.expired > a1.expired
                  ) >= $1
                  AND
                  -- Agent process only has expired agent instances
                  NOT EXISTS(
                    SELECT 1
                    FROM {cls.table_name()} AS agentprocess
                    INNER JOIN {AgentInstance.table_name()} AS agentinstance
                    ON agentinstance.process = agentprocess.sid
                    WHERE agentprocess.sid = a1.sid AND agentinstance.expired IS NULL
                  );
        """
        await cls._execute_query(query, cls._get_value(nr_expired_records_to_keep))

    def to_dict(self) -> JsonType:
        result = super().to_dict()
        # Ensure backward compatibility API
        result["id"] = result["sid"]
        return result

    def to_dto(self) -> m.AgentProcess:
        return m.AgentProcess(
            sid=self.sid,
            hostname=self.hostname,
            environment=self.environment,
            first_seen=self.first_seen,
            last_seen=self.last_seen,
            expired=self.expired,
        )


TAgentInstance = TypeVar("TAgentInstance", bound="AgentInstance")


class AgentInstance(BaseDocument):
    """
    A physical server/node in the infrastructure that reports to the management server.

    :param hostname: The hostname of the device.
    :param last_seen: When did the server receive data from the node for the last time.
    """

    __primary_key__ = ("id",)

    # TODO: add env to speed up cleanup
    id: uuid.UUID
    process: uuid.UUID
    name: str
    expired: Optional[datetime.datetime] = None
    tid: uuid.UUID

    @classmethod
    async def active_for(
        cls: type[TAgentInstance],
        tid: uuid.UUID,
        endpoint: str,
        process: Optional[uuid.UUID] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> list[TAgentInstance]:
        if process is not None:
            objects = await cls.get_list(expired=None, tid=tid, name=endpoint, connection=connection)
        else:
            objects = await cls.get_list(expired=None, tid=tid, name=endpoint, connection=connection)
        return objects

    @classmethod
    async def active(cls: type[TAgentInstance]) -> list[TAgentInstance]:
        objects = await cls.get_list(expired=None)
        return objects

    @classmethod
    async def log_instance_creation(
        cls: type[TAgentInstance],
        tid: uuid.UUID,
        process: uuid.UUID,
        endpoints: set[str],
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Create new agent instances for a given session.
        """
        if not endpoints:
            return
        async with cls.get_connection(connection) as con:
            await con.executemany(
                f"""
                INSERT INTO
                {cls.table_name()}
                (id, tid, process, name, expired)
                VALUES ($1, $2, $3, $4, null)
                ON CONFLICT ON CONSTRAINT {cls.table_name()}_unique DO UPDATE
                SET expired = null
                ;
                """,
                [tuple(map(cls._get_value, (cls._new_id(), tid, process, name))) for name in endpoints],
            )

    @classmethod
    async def log_instance_expiry(
        cls: type[TAgentInstance],
        sid: uuid.UUID,
        endpoints: set[str],
        now: datetime.datetime,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Expire specific instances for a given session id.
        """
        if not endpoints:
            return
        instances: list[TAgentInstance] = await cls.get_list(connection=connection, process=sid)
        for ai in instances:
            if ai.name in endpoints:
                await ai.update_fields(connection=connection, expired=now)

    @classmethod
    async def expire_all(cls, now: datetime.datetime, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        query = f"""
                UPDATE {cls.table_name()}
                SET expired=$1
                WHERE expired IS NULL
        """
        await cls._execute_query(query, cls._get_value(now), connection=connection)


class Agent(BaseDocument):
    """
    An inmanta agent

    :param environment: The environment this resource is defined in
    :param name: The name of this agent
    :param last_failover: Moment at which the primary was last changed
    :param paused: is this agent paused (if so, skip it)
    :param primary: what is the current active instance (if none, state is down). Only relevant for the $__scheduler agent.
    :param unpause_on_resume: whether this agent should be unpaused when resuming from environment-wide halt. Used to
        persist paused state when halting.
    """

    __primary_key__ = ("environment", "name")

    environment: uuid.UUID
    name: str
    last_failover: Optional[datetime.datetime] = None
    paused: bool = False
    id_primary: Optional[uuid.UUID] = None
    unpause_on_resume: Optional[bool] = None

    @property
    def primary(self) -> Optional[uuid.UUID]:
        return self.id_primary

    @classmethod
    def get_valid_field_names(cls) -> list[str]:
        # Allow the computed fields
        return super().get_valid_field_names() + ["process_name", "status"]

    @classmethod
    async def get_statuses(
        cls, env_id: uuid.UUID, agent_names: Set[str], *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> dict[str, Optional[AgentStatus]]:
        result: dict[str, Optional[AgentStatus]] = {}
        for agent_name in agent_names:
            agent = await cls.get_one(environment=env_id, name=agent_name, connection=connection)
            if agent:
                result[agent_name] = agent.get_status()
            else:
                result[agent_name] = None
        return result

    def get_status(self) -> AgentStatus:
        if self.paused:
            return AgentStatus.paused
        if self.primary is not None:
            return AgentStatus.up
        return AgentStatus.down

    def to_dict(self) -> JsonType:
        base = BaseDocument.to_dict(self)
        if self.last_failover is None:
            base["last_failover"] = ""

        if self.primary is None:
            base["primary"] = ""
        else:
            base["primary"] = base["id_primary"]
            del base["id_primary"]

        base["state"] = self.get_status().value

        return base

    @classmethod
    def _convert_field_names_to_db_column_names(cls, field_dict: dict[str, object]) -> dict[str, object]:
        if "primary" in field_dict:
            field_dict["id_primary"] = field_dict["primary"]
            del field_dict["primary"]
        return field_dict

    @classmethod
    async def get(
        cls,
        env: uuid.UUID,
        endpoint: str,
        connection: Optional[asyncpg.connection.Connection] = None,
        lock: Optional[RowLockMode] = None,
    ) -> "Agent":
        obj = await cls.get_one(environment=env, name=endpoint, connection=connection, lock=lock)
        return obj

    @classmethod
    async def insert_if_not_exist(
        cls, environment: uuid.UUID, endpoint: str, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        query = """
            INSERT INTO agent
            (last_failover,paused,id_primary,unpause_on_resume,environment,name)
            VALUES (now(),FALSE,NULL,NULL,$1,$2)
            ON CONFLICT DO NOTHING
        """
        values = [cls._get_value(environment), cls._get_value(endpoint)]
        await cls._execute_query(query, *values, connection=connection)

    @classmethod
    async def persist_on_halt(cls, env: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Persists paused state when halting all agents.
        """
        await cls._execute_query(
            f"UPDATE {cls.table_name()} SET unpause_on_resume=NOT paused WHERE environment=$1 AND unpause_on_resume IS NULL",
            cls._get_value(env),
            connection=connection,
        )

    @classmethod
    async def persist_on_resume(cls, env: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None) -> list[str]:
        """
        Restores default halted state. Returns a list of agents that should be unpaused.
        """

        async with cls.get_connection(connection) as con:
            async with con.transaction():
                unpause_on_resume = await cls._fetch_query(
                    # lock FOR UPDATE to avoid deadlocks: next query in this transaction updates the row
                    f"SELECT name FROM {cls.table_name()} WHERE environment=$1 AND unpause_on_resume FOR NO KEY UPDATE",
                    cls._get_value(env),
                    connection=con,
                )
                await cls._execute_query(
                    f"UPDATE {cls.table_name()} SET unpause_on_resume=NULL WHERE environment=$1",
                    cls._get_value(env),
                    connection=con,
                )
                return sorted([r["name"] for r in unpause_on_resume])

    @classmethod
    async def pause(
        cls, env: uuid.UUID, endpoint: Optional[str], paused: bool, connection: Optional[asyncpg.connection.Connection] = None
    ) -> list[str]:
        """
        Pause a specific agent or all agents in an environment when endpoint is set to None.

        :return A list of agent names that have been paused/unpaused by this method.
        """
        if endpoint is None:
            query = f"UPDATE {cls.table_name()} SET paused=$1 WHERE environment=$2 AND name!=$3 RETURNING name"
            values = [cls._get_value(paused), cls._get_value(env), const.AGENT_SCHEDULER_ID]
        else:
            query = f"UPDATE {cls.table_name()} SET paused=$1 WHERE environment=$2 AND name=$3 RETURNING name"
            values = [cls._get_value(paused), cls._get_value(env), cls._get_value(endpoint)]
        result = await cls._fetch_query(query, *values, connection=connection)
        return sorted([r["name"] for r in result])

    @classmethod
    async def set_unpause_on_resume(
        cls,
        env: uuid.UUID,
        endpoint: Optional[str],
        should_be_unpaused_on_resume: bool,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Set the unpause_on_resume field of a specific agent or all agents in an environment when endpoint is set to None.
        """
        if endpoint is None:
            query = f"UPDATE {cls.table_name()} SET unpause_on_resume=$1 WHERE environment=$2"
            values = [cls._get_value(should_be_unpaused_on_resume), cls._get_value(env)]
        else:
            query = f"UPDATE {cls.table_name()} SET unpause_on_resume=$1 WHERE environment=$2 AND name=$3"
            values = [cls._get_value(should_be_unpaused_on_resume), cls._get_value(env), cls._get_value(endpoint)]
        await cls._execute_query(query, *values, connection=connection)

    @classmethod
    async def update_primary(
        cls,
        env: uuid.UUID,
        endpoints_with_new_primary: Sequence[tuple[str, Optional[uuid.UUID]]],
        now: datetime.datetime,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Update the primary agent instance for agents present in the database.

        :param env: The environment of the agent
        :param endpoints_with_new_primary: Contains a tuple (agent-name, sid) for each agent that has got a new
                                           primary agent instance. The sid in the tuple is the session id of the new
                                           primary. If the session id is None, the Agent doesn't have a primary anymore.
        :param now: Timestamp of this failover
        """
        for endpoint, sid in endpoints_with_new_primary:
            # Lock mode is required because we will update in this transaction
            # Deadlocks with cleanup otherwise
            agent = await cls.get(env, endpoint, connection=connection, lock=RowLockMode.FOR_NO_KEY_UPDATE)
            if agent is None:
                continue

            if sid is None:
                await agent.update_fields(last_failover=now, primary=None, connection=connection)
            else:
                instances = await AgentInstance.active_for(tid=env, endpoint=agent.name, process=sid, connection=connection)
                if instances:
                    await agent.update_fields(last_failover=now, id_primary=instances[0].id, connection=connection)
                else:
                    await agent.update_fields(last_failover=now, id_primary=None, connection=connection)

    @classmethod
    async def mark_all_as_non_primary(cls, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        query = f"""
                UPDATE {cls.table_name()}
                SET id_primary=NULL
                WHERE id_primary IS NOT NULL
        """
        await cls._execute_query(query, connection=connection)

    @classmethod
    async def clean_up(cls, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        query = """
DELETE FROM public.agent AS a
WHERE -- have no primary ID set (that are down)
      id_primary IS NULL
      -- not used by any version
      AND NOT EXISTS (
          SELECT 1
          FROM public.resource AS re
          WHERE a.environment=re.environment
          AND a.name=re.agent
      )
      AND a.environment IN (
          SELECT id
          FROM public.environment
          WHERE NOT halted
      )
      -- Never delete the scheduler record.
      AND a.name != $1;
"""
        await cls._execute_query(query, const.AGENT_SCHEDULER_ID, connection=connection)


@stable_api
class Report(BaseDocument):
    """
    A report of a substep of compilation

    :param started: when the substep started
    :param completed: when it ended
    :param command: the command that was executed
    :param name: The name of this step
    :param errstream: what was reported on system err
    :param outstream: what was reported on system out
    """

    __primary_key__ = ("id",)

    id: uuid.UUID
    started: datetime.datetime
    completed: Optional[datetime.datetime]
    command: str
    name: str
    errstream: str = ""
    outstream: str = ""
    returncode: Optional[int]
    compile: uuid.UUID

    async def update_streams(self, out: str = "", err: str = "") -> None:
        if not out and not err:
            return
        await self._execute_query(
            f"UPDATE {self.table_name()} SET outstream = outstream || $1, errstream = errstream || $2 WHERE id = $3",
            self._get_value(out),
            self._get_value(err),
            self._get_value(self.id),
        )


@stable_api
class Compile(BaseDocument):
    """
    A run of the compiler

    :param environment: The environment this resource is defined in
    :param requested: Time the compile was requested
    :param started: Time the compile started
    :param completed: Time to compile was completed
    :param do_export: should this compile perform an export
    :param force_update: should this compile definitely update
    :param metadata: exporter metadata to be passed to the compiler
    :param requested_environment_variables: environment variables requested to be passed to the compiler
    :param mergeable_environment_variables: environment variables to be passed to the compiler.
            These env vars can be compacted over multiple compiles.
            If multiple values are compacted, they will be joined using spaces.
    :param used_environment_variables: environment variables passed to the compiler, None before the compile is started
    :param success: was the compile successful
    :param handled: were all registered handlers executed?
    :param version: version exported by this compile
    :param remote_id: id as given by the requestor, used by the requestor to distinguish between different requests
    :param compile_data: json data as exported by compiling with the --export-compile-data parameter
    :param substitute_compile_id: id of this compile's substitute compile, i.e. the compile request that is similar
        to this one that actually got compiled.
    :param partial: True if the compile only contains the entities/resources for the resource sets that should be updated
    :param removed_resource_sets: indicates the resource sets that should be removed from the model
    :param exporter_plugin: Specific exporter plugin to use
    :param notify_failed_compile: if true use the notification service to notify that a compile has failed.
        By default, notifications are enabled only for exporting compiles.
    :param failed_compile_message: Optional message to use when a notification for a failed compile is created
    :param soft_delete: Prevents deletion of resources in removed_resource_sets if they are being exported.
    :param links: An object that contains relevant links to this compile.
        It is a dictionary where the key is something that identifies one or more links
        and the value is a list of urls. i.e. {"instances": ["link-1',"link-2"], "compiles": ["link-3"]}
    :param reinstall_project_and_venv: True iff perform a clean checkout of the project and re-create the compiler venv.
    """

    __primary_key__ = ("id",)

    id: uuid.UUID
    remote_id: Optional[uuid.UUID] = None
    environment: uuid.UUID
    requested: Optional[datetime.datetime] = None
    started: Optional[datetime.datetime] = None
    completed: Optional[datetime.datetime] = None

    do_export: bool = False
    force_update: bool = False
    metadata: JsonType = {}
    requested_environment_variables: dict[str, str] = {}
    mergeable_environment_variables: dict[str, str] = {}
    used_environment_variables: Optional[dict[str, str]] = None

    success: Optional[bool]
    handled: bool = False
    version: Optional[int] = None

    # Compile queue might be collapsed if it contains similar compile requests.
    # In that case, substitute_compile_id will reference the actually compiled request.
    substitute_compile_id: Optional[uuid.UUID] = None

    compile_data: Optional[JsonType] = None

    partial: bool = False
    removed_resource_sets: list[str] = []

    exporter_plugin: Optional[str] = None

    notify_failed_compile: Optional[bool] = None
    failed_compile_message: Optional[str] = None

    soft_delete: bool = False
    links: dict[str, list[str]] = {}
    reinstall_project_and_venv: bool = False

    @classmethod
    async def get_substitute_by_id(cls, compile_id: uuid.UUID, connection: Optional[Connection] = None) -> Optional["Compile"]:
        """
        Get a compile's substitute compile if it exists, otherwise get the compile by id.

        :param compile_id: The id of the compile for which to get the substitute compile.
        :return: The compile object for compile c2 that is the substitute of compile c1 with the given id. If c1 does not have
            a substitute, returns c1 itself.
        """
        async with Compile.get_connection(connection=connection) as con:
            result: Optional[Compile] = await cls.get_by_id(compile_id, connection=con)
            if result is None:
                return None
            if result.substitute_compile_id is None:
                return result
            return await cls.get_substitute_by_id(result.substitute_compile_id, connection=con)

    @classmethod
    # TODO: Use join
    async def get_report(
        cls, compile_id: uuid.UUID, order_by: Optional[str] = None, order: Optional[str] = None
    ) -> Optional[dict]:
        """
        Get the compile and the associated reports from the database
        """
        result: Optional[Compile] = await cls.get_substitute_by_id(compile_id)
        if result is None:
            return None

        dict_model = result.to_dict()
        reports = await Report.get_list(compile=result.id, order_by_column=order_by, order=order)
        dict_model["reports"] = [r.to_dict() for r in reports]

        return dict_model

    @classmethod
    async def get_last_run(cls, environment_id: uuid.UUID) -> Optional["Compile"]:
        """Get the last run for the given environment"""
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} where environment=$1 AND completed IS NOT NULL ORDER BY completed DESC LIMIT 1",
            [cls._get_value(environment_id)],
        )
        if not results:
            return None
        return results[0]

    @classmethod
    async def get_next_run(
        cls, environment_id: uuid.UUID, *, connection: Optional[asyncpg.Connection] = None
    ) -> Optional["Compile"]:
        """Get the next compile in the queue for the given environment"""
        async with cls.get_connection(connection) as con:
            results = await cls.select_query(
                f"SELECT * FROM {cls.table_name()} WHERE environment=$1 AND completed IS NULL ORDER BY requested ASC LIMIT 1",
                [cls._get_value(environment_id)],
                connection=con,
            )
            if not results:
                return None
            return results[0]

    @classmethod
    async def get_next_run_all(cls, *, connection: Optional[asyncpg.Connection] = None) -> "Sequence[Compile]":
        """Get the next compile in the queue for each environment"""
        async with cls.get_connection(connection) as con:
            results = await cls.select_query(
                f"SELECT DISTINCT ON (environment) * FROM {cls.table_name()} WHERE completed IS NULL ORDER BY environment, "
                f"requested ASC",
                [],
                connection=con,
            )
            return results

    @classmethod
    async def get_unhandled_compiles(cls) -> "Sequence[Compile]":
        """Get all compiles that have completed but for which listeners have not been notified yet."""
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} WHERE NOT handled and completed IS NOT NULL ORDER BY requested ASC", []
        )
        return results

    @classmethod
    async def get_next_compiles_for_environment(cls, environment_id: uuid.UUID) -> "Sequence[Compile]":
        """Get the queue of compiles that are scheduled in FIFO order."""
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} WHERE environment=$1 AND NOT handled and completed IS NULL "
            "ORDER BY requested ASC",
            [cls._get_value(environment_id)],
        )
        return results

    @classmethod
    async def get_total_length_of_all_compile_queues(cls, exclude_started_compiles: bool = True) -> int:
        """
        Return the total length of all the compile queues on the Inmanta server.

        :param exclude_started_compiles: True iff don't count compiles that started running, but are not finished yet.
        """
        query = f"SELECT count(*) FROM {cls.table_name()} WHERE completed IS NULL"
        if exclude_started_compiles:
            query += " AND started IS NULL"
        return await cls._fetch_int(query)

    @classmethod
    async def get_by_remote_id(
        cls, environment_id: uuid.UUID, remote_id: uuid.UUID, *, connection: Optional[asyncpg.Connection] = None
    ) -> "Sequence[Compile]":
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} WHERE environment=$1 AND remote_id=$2",
            [cls._get_value(environment_id), cls._get_value(remote_id)],
            connection=connection,
        )
        return results

    @classmethod
    async def delete_older_than(
        cls, oldest_retained_date: datetime.datetime, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        query = f"""
        WITH non_halted_envs AS (
          SELECT id FROM public.environment WHERE NOT halted
        )
        DELETE FROM {cls.table_name()}
        WHERE environment IN (
          SELECT id FROM non_halted_envs
        ) AND completed <= $1::timestamp with time zone;
        """
        await cls._execute_query(query, oldest_retained_date, connection=connection)

    @classmethod
    async def get_compile_details(cls, environment: uuid.UUID, id: uuid.UUID) -> Optional[m.CompileDetails]:
        """Find all of the details of a compile, with reports from a substituted compile, if there was one"""

        # Recursively join the requested compile with the substituted compiles (if there was one), and the corresponding reports
        query = f"""
            WITH RECURSIVE compiledetails AS (
            SELECT
                c.id,
                c.remote_id,
                c.environment,
                c.requested,
                c.started,
                c.completed,
                c.success,
                c.version,
                c.do_export,
                c.force_update,
                c.metadata,
                c.requested_environment_variables ,
                c.mergeable_environment_variables,
                c.used_environment_variables,
                c.compile_data,
                c.substitute_compile_id,
                c.partial,
                c.removed_resource_sets,
                c.exporter_plugin,
                c.notify_failed_compile,
                c.failed_compile_message,
                c.links,
                r.id as report_id,
                r.started report_started,
                r.completed report_completed,
                r.command,
                r.name,
                r.errstream,
                r.outstream,
                r.returncode
            FROM
                {cls.table_name()} c LEFT JOIN public.report r on c.id = r.compile
            WHERE
                c.environment = $1 AND c.id = $2
            UNION
                SELECT
                    comp.id,
                    comp.remote_id,
                    comp.environment,
                    comp.requested,
                    comp.started,
                    comp.completed,
                    comp.success,
                    comp.version,
                    comp.do_export,
                    comp.force_update,
                    comp.metadata,
                    comp.requested_environment_variables,
                    comp.mergeable_environment_variables,
                    comp.used_environment_variables,
                    comp.compile_data,
                    comp.substitute_compile_id,
                    comp.partial,
                    comp.removed_resource_sets,
                    comp.exporter_plugin,
                    comp.notify_failed_compile,
                    comp.failed_compile_message,
                    comp.links,
                    rep.id as report_id,
                    rep.started as report_started,
                    rep.completed as report_completed,
                    rep.command,
                    rep.name,
                    rep.errstream,
                    rep.outstream,
                    rep.returncode
                FROM
                    /* Lookup the compile with the id that matches the subsitute_compile_id of the current one */
                    {cls.table_name()} comp
                    INNER JOIN compiledetails cd ON cd.substitute_compile_id = comp.id
                    LEFT JOIN public.report rep on comp.id = rep.compile
        ) SELECT * FROM compiledetails ORDER BY report_started ASC;
        """
        values = [cls._get_value(environment), cls._get_value(id)]
        result = await cls.select_query(query, values, no_obj=True)
        result = cast(list[Record], result)
        # The result is a list of Compiles joined with Reports
        # This includes the Compile with the requested id,
        # as well as Compile(s) that have been used as a substitute for the requested Compile (if there are any)
        if not result:
            return None

        # The details, such as the requested timestamp, etc. should be returned from
        # the compile that matches the originally requested id
        records = list(filter(lambda r: r["id"] == id, result))
        if not records:
            return None
        requested_compile = records[0]

        # Concatenate the links of the requested compile and all substitute compiles
        links: dict[str, set[str]] = defaultdict(set)
        reports = []
        for compile in result:
            # Reports should be included from the substituted compile (as well)
            if compile.get("report_id"):
                reports.append(
                    m.CompileRunReport(
                        id=compile["report_id"],
                        started=compile["report_started"],
                        completed=compile["report_completed"],
                        command=compile["command"],
                        name=compile["name"],
                        errstream=compile["errstream"],
                        outstream=compile["outstream"],
                        returncode=compile["returncode"],
                    )
                )
            for name, url in cast(dict[str, list[str]], compile.get("links", {})).items():
                links[name].add(*url)

        return m.CompileDetails(
            id=requested_compile["id"],
            remote_id=requested_compile["remote_id"],
            environment=requested_compile["environment"],
            requested=requested_compile["requested"],
            started=requested_compile["started"],
            completed=requested_compile["completed"],
            success=requested_compile["success"],
            version=requested_compile["version"],
            do_export=requested_compile["do_export"],
            force_update=requested_compile["force_update"],
            metadata=requested_compile["metadata"] or {},
            environment_variables=requested_compile["used_environment_variables"] or {},
            requested_environment_variables=requested_compile["requested_environment_variables"],
            mergeable_environment_variables=requested_compile["mergeable_environment_variables"],
            partial=requested_compile["partial"],
            removed_resource_sets=requested_compile["removed_resource_sets"],
            exporter_plugin=requested_compile["exporter_plugin"],
            notify_failed_compile=requested_compile["notify_failed_compile"],
            failed_compile_message=requested_compile["failed_compile_message"],
            compile_data=requested_compile["compile_data"],
            reports=reports,
            links={key: sorted(list(links)) for key, links in links.items()},
        )

    def to_dto(self) -> m.CompileRun:
        return m.CompileRun(
            id=self.id,
            remote_id=self.remote_id,
            environment=self.environment,
            requested=self.requested,
            started=self.started,
            do_export=self.do_export,
            force_update=self.force_update,
            metadata=self.metadata,
            environment_variables=self.used_environment_variables,
            requested_environment_variables=self.requested_environment_variables,
            mergeable_environment_variables=self.mergeable_environment_variables,
            compile_data=None if self.compile_data is None else m.CompileData(**self.compile_data),
            partial=self.partial,
            removed_resource_sets=self.removed_resource_sets,
            exporter_plugin=self.exporter_plugin,
            notify_failed_compile=self.notify_failed_compile,
            failed_compile_message=self.failed_compile_message,
            links=self.links,
        )

    def to_dict(self) -> JsonType:
        """produce dict directly, for untyped endpoints"""
        # mangle the output for backward compatibility
        # we have to do it because we have no DTO here
        environment_variables = self.used_environment_variables
        if environment_variables is None:
            environment_variables = {}
            environment_variables.update(self.requested_environment_variables)
            environment_variables.update(self.mergeable_environment_variables)

        out = super().to_dict()
        out["environment_variables"] = environment_variables
        return out


class LogLine(DataDocument):
    """
    LogLine data document.

    An instance of this class only has one attribute: _data.
    This unique attribute is a dict, with the following keys:
        - msg: the message to write to logs (value type: str)
        - args: the args that can be passed to the logger (value type: list)
        - level: the log level of the message (value type: str, example: "CRITICAL")
        - kwargs: the key-word args that were used to generate the log (value type: list)
        - timestamp: the time at which the LogLine was created (value type: datetime.datetime)
    """

    @property
    def msg(self) -> str:
        return self._data["msg"]

    @property
    def args(self) -> list:
        return self._data["args"]

    @property
    def log_level(self) -> LogLevel:
        level: str = self._data["level"]
        return LogLevel[level]

    @property
    def timestamp(self) -> datetime.datetime:
        return cast(datetime.datetime, self._data["timestamp"])

    def write_to_logger(self, logger: logging.Logger) -> None:
        logger.log(self.log_level.to_int, self.msg, *self.args)

    def write_to_logger_for_resource(
        self, agent: str, resource_version_string: ResourceVersionIdStr, exc_info: bool = False
    ) -> None:
        logging.getLogger(NAME_RESOURCE_ACTION_LOGGER).getChild(agent).log(
            self.log_level.to_int, "resource %s: %s", resource_version_string, self._data["msg"], exc_info=exc_info
        )

    @classmethod
    def log(
        cls,
        level: Union[int, const.LogLevel],
        msg: str,
        timestamp: Optional[datetime.datetime] = None,
        **kwargs: object,
    ) -> "LogLine":
        if timestamp is None:
            timestamp = datetime.datetime.now().astimezone()

        log_line = msg % kwargs
        return cls(level=LogLevel(level).name, msg=log_line, args=[], kwargs=kwargs, timestamp=timestamp)

    def __getstate__(self) -> str:
        if "timestamp" not in self._data:
            self._data["timestamp"] = datetime.datetime.now().astimezone()
        # make pickle use json to keep leaking stuff
        # Will make the objects into json-like things
        # This method exists only to keep IPC light compatible with the json based RPC
        return json_encode(self._data)

    def __setstate__(self, state: str) -> None:
        # This method exists only to keep IPC light compatible with the json based RPC
        self._data = json.loads(state)
        self._data["timestamp"] = parse_timestamp(cast(str, self._data["timestamp"]))


@stable_api
class ResourceAction(BaseDocument):
    """
    Log related to actions performed on a specific resource version by Inmanta.

    :param environment: The environment this action belongs to.
    :param version: The version of the configuration model this action belongs to.
    :param resource_version_ids: The resource version ids of the resources this action relates to.
    :param action_id: This id distinguishes the actions from each other. Action ids have to be unique per environment.
    :param action: The action performed on the resource
    :param started: When did the action start
    :param finished: When did the action finish
    :param messages: The log messages associated with this action
    :param status: The status of the resource when this action was finished
    :param changes: A dict with key the resource id and value a dict of fields -> value. Value is a dict that can
                   contain old and current keys and the associated values. An empty dict indicates that the field
                   was changed but not data was provided by the agent.
    :param change: The change result of an action
    """

    __primary_key__ = ("action_id",)

    environment: uuid.UUID
    version: int
    resource_version_ids: list[ResourceVersionIdStr]

    action_id: uuid.UUID
    action: const.ResourceAction

    started: datetime.datetime
    finished: Optional[datetime.datetime] = None

    messages: Optional[list[dict[str, object]]] = None
    status: Optional[const.ResourceState] = None
    changes: Optional[dict[ResourceVersionIdStr, dict[str, object]]] = None
    change: Optional[const.Change] = None

    def __init__(self, from_postgres: bool = False, **kwargs: object) -> None:
        super().__init__(from_postgres, **kwargs)
        self._updates = {}

        # rewrite some data
        if self.changes == {}:
            self.changes = None

        if from_postgres and self.messages:
            new_messages = []
            for message in self.messages:
                if "timestamp" in message:
                    ta = pydantic.TypeAdapter(datetime.datetime)
                    # use pydantic instead of datetime.strptime because strptime has trouble parsing isoformat timezone offset
                    timestamp = ta.validate_python(message["timestamp"])
                    if timestamp.tzinfo is None:
                        raise Exception("Found naive timestamp in the database, this should not be possible")
                    message["timestamp"] = timestamp
                new_messages.append(message)
            self.messages = new_messages

    @classmethod
    async def get_by_id(cls, doc_id: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None) -> "ResourceAction":
        return await cls.get_one(action_id=doc_id, connection=connection)

    @classmethod
    async def get_log(
        cls,
        environment: uuid.UUID,
        resource_version_id: ResourceVersionIdStr,
        action: Optional[str] = None,
        limit: int = 0,
        connection: Optional[Connection] = None,
    ) -> list["ResourceAction"]:
        query = """
        SELECT ra.* FROM public.resourceaction as ra
                    INNER JOIN public.resourceaction_resource as jt
                        ON ra.action_id = jt.resource_action_id
                    WHERE jt.environment=$1 AND jt.resource_id = $2 AND  jt.resource_version = $3
        """
        id = resources.Id.parse_id(resource_version_id)
        values = [cls._get_value(environment), id.resource_str(), id.version]
        if action is not None:
            query += " AND action=$4"
            values.append(cls._get_value(action))
        query += " ORDER BY started DESC"
        if limit is not None and limit > 0:
            query += " LIMIT $%d" % (len(values) + 1)
            values.append(cls._get_value(limit))
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                return [cls(**dict(record), from_postgres=True) async for record in con.cursor(query, *values)]

    @classmethod
    async def get_logs_for_version(
        cls,
        environment: uuid.UUID,
        version: int,
        action: Optional[str] = None,
        limit: int = 0,
        connection: Optional[Connection] = None,
    ) -> list["ResourceAction"]:
        query = f"""SELECT *
                        FROM {cls.table_name()}
                        WHERE environment=$1 AND version=$2
                     """
        values = [cls._get_value(environment), cls._get_value(version)]
        if action is not None:
            query += " AND action=$3"
            values.append(cls._get_value(action))
        query += " ORDER BY started DESC"
        if limit is not None and limit > 0:
            query += " LIMIT $%d" % (len(values) + 1)
            values.append(cls._get_value(limit))
        async with cls.get_connection(connection=connection) as con:
            async with con.transaction():
                return [cls(**dict(record), from_postgres=True) async for record in con.cursor(query, *values)]

    @classmethod
    def get_valid_field_names(cls) -> list[str]:
        return super().get_valid_field_names() + ["timestamp", "level", "msg"]

    @classmethod
    async def get(cls, action_id: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None) -> "ResourceAction":
        return await cls.get_one(action_id=action_id, connection=connection)

    async def insert(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        async with self.get_connection(connection) as con:
            async with con.transaction():
                await super().insert(con)

                # Also do the join table in the same transaction
                assert self.resource_version_ids

                parsed_rv = [resources.Id.parse_resource_version_id(id) for id in self.resource_version_ids]
                # No additional checking of field validity is done here, because the insert above validates all fields
                await con.execute(
                    "INSERT INTO public.resourceaction_resource "
                    "(resource_id, resource_version, environment, resource_action_id) "
                    "SELECT unnest($1::text[]), unnest($2::int[]), $3, $4",
                    [id.resource_str() for id in parsed_rv],
                    [id.get_version() for id in parsed_rv],
                    self.environment,
                    self.action_id,
                )

    def set_field(self, name: str, value: object) -> None:
        self._updates[name] = value

    def add_logs(self, messages: Optional[str]) -> None:
        if not messages:
            return
        if "messages" not in self._updates:
            self._updates["messages"] = []
        self._updates["messages"] += messages

    def add_changes(self, changes: dict[ResourceVersionIdStr, dict[str, object]]) -> None:
        for resource, values in changes.items():
            for field, change in values.items():
                if "changes" not in self._updates:
                    self._updates["changes"] = {}
                if resource not in self._updates["changes"]:
                    self._updates["changes"][resource] = {}
                self._updates["changes"][resource][field] = change

    async def set_and_save(
        self,
        messages: list[dict[str, object]],
        changes: dict[ResourceVersionIdStr, dict[str, object]],
        status: Optional[const.ResourceState],
        change: Optional[const.Change],
        finished: Optional[datetime.datetime],
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        if len(messages) > 0:
            self.add_logs(messages)

        if len(changes) > 0:
            self.add_changes(changes)

        if status is not None:
            self.set_field("status", status)

        if change is not None:
            self.set_field("change", change)

        if finished is not None:
            self.set_field("finished", finished)

        await self.save(connection=connection)

    async def save(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Save the changes
        """
        if len(self._updates) == 0:
            return
        assert (
            "resource_version_ids" not in self._updates
        ), "Updating the associated resource_version_ids of a ResourceAction is not currently supported"
        await self.update_fields(connection=connection, **self._updates)
        self._updates = {}

    @classmethod
    async def purge_logs(cls) -> None:
        default_retention_time = Environment._settings[RESOURCE_ACTION_LOGS_RETENTION].default

        query = f"""
            WITH non_halted_envs AS (
                SELECT
                    id,
                    (
                        COALESCE((settings->'settings'->'resource_action_logs_retention'->>'value')::int, $1)
                    ) AS retention_days
                FROM {Environment.table_name()}
                WHERE NOT halted
            )
            DELETE FROM {cls.table_name()}
            USING non_halted_envs
            WHERE environment = non_halted_envs.id
                AND started < now() AT TIME ZONE 'UTC' - make_interval(days => non_halted_envs.retention_days)
        """
        await cls._execute_query(query, default_retention_time)

    @classmethod
    async def query_resource_actions(
        cls,
        environment: uuid.UUID,
        resource_type: Optional[str] = None,
        agent: Optional[str] = None,
        attribute: Optional[str] = None,
        attribute_value: Optional[str] = None,
        resource_id_value: Optional[str] = None,
        log_severity: Optional[str] = None,
        limit: int = 0,
        action_id: Optional[uuid.UUID] = None,
        first_timestamp: Optional[datetime.datetime] = None,
        last_timestamp: Optional[datetime.datetime] = None,
        action: Optional[const.ResourceAction] = None,
        resource_id: Optional[ResourceIdStr] = None,
        exclude_changes: Optional[list[const.Change]] = None,
    ) -> list["ResourceAction"]:
        query = """SELECT DISTINCT ra.*
                    FROM public.resource_set_configuration_model as rscm
                    INNER JOIN public.resource as r
                        ON r.resource_set=rscm.resource_set
                        AND r.environment=rscm.environment
                    INNER JOIN public.resourceaction_resource as jt
                        ON r.environment = jt.environment
                        AND r.resource_id = jt.resource_id
                        AND rscm.model = jt.resource_version
                    INNER JOIN public.resourceaction as ra
                        ON ra.action_id = jt.resource_action_id
                        WHERE r.environment=$1 AND ra.environment=$1"""
        values: list[object] = [cls._get_value(environment)]

        parameter_index = 2
        if resource_type:
            query += f" AND resource_type=${parameter_index}"
            values.append(cls._get_value(resource_type))
            parameter_index += 1
        if agent:
            query += f" AND agent=${parameter_index}"
            values.append(cls._get_value(agent))
            parameter_index += 1
        if attribute and attribute_value:
            # The query uses a like query to match resource id with a resource_version_id. This means we need to escape the %
            # and _ characters in the query
            escaped_value = attribute_value.replace("#", "##").replace("%", "#%").replace("_", "#_") + "%"
            query += f" AND attributes->>${parameter_index} LIKE ${parameter_index + 1} ESCAPE '#' "
            values.append(cls._get_value(attribute))
            values.append(cls._get_value(escaped_value))
            parameter_index += 2
        if resource_id_value:
            query += f" AND r.resource_id_value = ${parameter_index}::varchar"
            values.append(cls._get_value(resource_id_value))
            parameter_index += 1
        if resource_id:
            query += f" AND r.resource_id = ${parameter_index}::varchar"
            values.append(cls._get_value(resource_id))
            parameter_index += 1
        if log_severity:
            # <@ Is contained by
            query += f" AND ${parameter_index} <@ ANY(messages)"
            values.append(cls._get_value({"level": log_severity.upper()}))
            parameter_index += 1
        if action is not None:
            query += f" AND ra.action=${parameter_index}"
            values.append(cls._get_value(action))
            parameter_index += 1
        if first_timestamp and action_id:
            query += f" AND (started, action_id) > (${parameter_index}, ${parameter_index + 1})"
            values.append(cls._get_value(first_timestamp))
            values.append(cls._get_value(action_id))
            parameter_index += 2
        elif first_timestamp:
            query += f" AND started > ${parameter_index}"
            values.append(cls._get_value(first_timestamp))
            parameter_index += 1
        if last_timestamp and action_id:
            query += f" AND (started, action_id) < (${parameter_index}, ${parameter_index + 1})"
            values.append(cls._get_value(last_timestamp))
            values.append(cls._get_value(action_id))
            parameter_index += 2
        elif last_timestamp:
            query += f" AND started < ${parameter_index}"
            values.append(cls._get_value(last_timestamp))
            parameter_index += 1

        if exclude_changes:
            # Create a string with placeholders for each item in exclude_changes
            exclude_placeholders = ", ".join([f"${parameter_index + i}" for i in range(len(exclude_changes))])
            query += f" AND ra.change NOT IN ({exclude_placeholders})"
            values.extend([cls._get_value(change) for change in exclude_changes])
            parameter_index += len(exclude_changes)

        if first_timestamp:
            query += " ORDER BY started, action_id"
        else:
            query += " ORDER BY started DESC, action_id DESC"
        if limit is not None and limit > 0:
            query += " LIMIT $%d" % parameter_index
            values.append(cls._get_value(limit))
            parameter_index += 1
        if first_timestamp:
            query = f"""SELECT * FROM ({query}) AS matching_actions
                        ORDER BY matching_actions.started DESC, matching_actions.action_id DESC"""

        async with cls.get_connection() as con:
            async with con.transaction():
                return [cls(**record, from_postgres=True) async for record in con.cursor(query, *values)]

    @classmethod
    async def get_resource_events(
        cls, env: Environment, resource_id: "resources.Id", exclude_change: Optional[const.Change] = None
    ) -> dict[ResourceIdStr, list["ResourceAction"]]:
        """
        Get all events that should be processed by this specific resource, for the current deployment

        This method searches across versions!

        This means:
        1. assure a deployment is ongoing
        2. get the time range between the start of this deployment and the last successful deploy
        3. get all resources required by this resource
        4. get all resource actions of type deploy emitted by the resource of step 3 in the time interval of step 2

        :param env: environment to consider
        :param resource_id: resource to consider, should be in deploying state
        :param exclude_change: in step 4, exclude all resource actions with this specific type of change
        """

        # This is bang on the critical path for the agent
        # Squeeze out as much performance from postgresql as we can

        resource_version_id_str = resource_id.resource_version_str()
        resource_id_str = resource_id.resource_str()

        # These two variables are actually of type datetime.datetime
        # but mypy doesn't know as they come from the DB
        # mypy also doesn't care, because they go back into the DB
        last_deploy_start: Optional[object]

        async with cls.get_connection() as connection:
            # Step 1: Get the resource
            # also check we are currently deploying

            resource: Optional[Resource] = await Resource.get_resource_for_version(
                environment=env.id, resource_id=resource_id_str, version=resource_id.version, connection=connection
            )

            if resource is None:
                raise NotFound(f"Resource with id {resource_version_id_str} was not found in environment {env.id}")

            resource_state: Optional[ResourcePersistentState] = await ResourcePersistentState.get_one(
                environment=env.id, resource_id=resource_id_str, connection=connection
            )
            assert resource_state is not None  # resource state must exist if resource exists

            if not resource_state.is_deploying:
                raise BadRequest(
                    "Fetching resource events only makes sense when the resource is currently deploying. Current deploy state"
                    f" for resource {resource_version_id_str} is {resource_state.last_non_deploying_status}."
                )

            # Step 2:
            # find the interval between the current deploy (now) and the previous successful deploy
            last_deploy_start = resource_state.last_success

            # Step 3: get the relevant resource actions
            # Do it in one query for all dependencies

            # Construct the query
            arg = ArgumentCollector(offset=2)

            # First make the filter
            filter = ""
            if last_deploy_start:
                filter += f" AND ra.started > {arg(last_deploy_start)}"
            if exclude_change:
                filter += f" AND ra.change <> {arg(exclude_change.value)}"

            # then the query around it
            get_all_query = f"""
    SELECT jt.resource_id, ra.*
        FROM public.resourceaction_resource as jt
        INNER JOIN public.resourceaction as ra
            ON ra.action_id = jt.resource_action_id
        WHERE jt.environment=$1 AND ra.environment=$1 AND jt.resource_id=ANY($2::varchar[]) AND ra.action='deploy' {filter}
        ORDER BY ra.started DESC;
            """

            # Convert resource version ids into resource ids
            ids = [resources.Id.parse_id(req).resource_str() for req in resource.attributes["requires"]]
            # Get the result
            result2 = await connection.fetch(get_all_query, env.id, ids, *arg.get_values())
            # Collect results per resource_id
            collector: dict[ResourceIdStr, list["ResourceAction"]] = {
                rid: [] for rid in ids
            }  # eagerly initialize, we expect one entry per dependency, even when empty
            for record in result2:
                fields = dict(record)
                del fields["resource_id"]
                collector[cast(ResourceIdStr, record[0])].append(ResourceAction(from_postgres=True, **fields))

        return collector

    def to_dto(self) -> m.ResourceAction:
        return m.ResourceAction(
            environment=self.environment,
            version=self.version,
            resource_version_ids=self.resource_version_ids,
            action_id=self.action_id,
            action=self.action,
            started=self.started,
            finished=self.finished,
            messages=self.messages,
            status=self.status,
            changes=self.changes,
            change=self.change,
        )


class ResourcePersistentState(BaseDocument):
    """
    To avoid write contention, the `Compliance` is split up in different fields that are written from different code
    paths. See get_compliance_status() for the associated logic.
    """

    @classmethod
    def table_name(cls) -> str:
        return "resource_persistent_state"

    __primary_key__ = ("environment", "resource_id")

    environment: uuid.UUID

    # ID related
    resource_id: ResourceIdStr
    resource_type: str
    agent: str
    resource_id_value: str

    # When this resource was first created
    created: datetime.datetime
    # Field based on content from the resource actions
    last_handler_run_at: Optional[datetime.datetime] = None
    # When a resource is updated in a new model version, it might take some time until this update reaches the scheduler.
    # This is the attribute hash that the scheduler considers the last released attribute hash for the given resource.
    current_intent_attribute_hash: Optional[str] = None
    # Last deployment completed of any kind, including marking-deployed-for-know-good-state for increments
    # i.e. the end time of the last deploy
    last_deployed_attribute_hash: Optional[str] = None
    # Hash used in last_handler_run_at
    last_deployed_version: Optional[int] = None
    # Model version of last_handler_run_at
    last_success: Optional[datetime.datetime] = None
    # last actual deployment completed without failure. i.e start time of the last deploy where status == ResourceState.deployed
    last_produced_events: Optional[datetime.datetime] = None
    # Last produced an event. i.e. the end time of the last deploy where we had an effective change
    # (change is not None and change != Change.nochange)

    # Written at version release time
    is_undefined: bool
    # Written when a new version is processed by the scheduler
    is_orphan: bool
    # Set to true when a version starts its deployment, set to false when it finishes
    is_deploying: bool
    # Written at deploy time (except for NEW -> no race condition possible with deploy path)
    last_handler_run: state.HandlerResult
    # Was the last run compliant, used for recovering scheduler state
    last_handler_run_compliant: Optional[bool] = None
    # Written both when processing a new version and at deploy time. As such, this should be updated
    # under the scheduler lock to prevent race conditions with the deploy time updates.
    blocked: state.Blocked

    # Written at deploy time (Exception for initial record creation  -> no race condition possible with deploy path)
    last_non_deploying_status: const.NonDeployingResourceState = const.NonDeployingResourceState.available

    # A foreign key to the resource_diff table.
    # It is populated on `send_deploy_done` when the handler sets the resource state to `non_compliant`.
    # It is cleaned up also on `send_deploy_done` when the handler reports any other resource state.
    # This field is only meaningful when the Compliance of this resource is `NON_COMPLIANT` according to get_compliance_status()
    non_compliant_diff: Optional[uuid.UUID] = None

    @classmethod
    async def mark_as_orphan(
        cls, environment: UUID, resource_ids: Set[ResourceIdStr], connection: Optional[Connection] = None
    ) -> None:
        """
        Set the is_orphan column to True on all given resources
        """
        query = f"""
            UPDATE {cls.table_name()}
            SET is_orphan=TRUE
            WHERE environment=$1 AND resource_id=ANY($2)
        """
        await cls._execute_query(query, environment, resource_ids, connection=connection)

    @classmethod
    async def update_resource_intent(
        cls,
        environment: uuid.UUID,
        intent: dict[ResourceIdStr, tuple[state.ResourceState, state.ResourceIntent]],
        update_blocked_state: bool,
        connection: Optional[Connection] = None,
    ) -> None:
        """
        Update the intent of the given resources in the resource_persistent_state table. This method is called
        when the intent of a resource, as processed by the scheduler, changes. This method must not be called
        for orphaned resources. The update_orphan_state() method should be used for that.

        :param update_blocked_state: True iff this method should update the blocked column in the database.
        """
        values = [
            (
                environment,
                resource_id,
                resource_details.attribute_hash,
                resource_state.compliance is state.Compliance.UNDEFINED,
                False,
                *([resource_state.blocked.db_value().name] if update_blocked_state else []),
            )
            for resource_id, (resource_state, resource_details) in intent.items()
        ]
        async with cls.get_connection(connection=connection) as con:
            await con.executemany(
                f"""
                    UPDATE {cls.table_name()}
                    SET
                        current_intent_attribute_hash=$3,
                        is_undefined=$4,
                        is_orphan=$5
                        {", blocked=$6" if update_blocked_state else ""}
                    WHERE environment=$1 AND resource_id=$2
                """,
                values,
            )

    @classmethod
    async def trim(cls, environment: UUID, connection: Optional[Connection] = None) -> None:
        """Remove all records that have no corresponding resource anymore"""
        await cls._execute_query(
            f"""
            DELETE FROM {cls.table_name()} rps
            WHERE NOT EXISTS(
                SELECT r.resource_id
                FROM {Resource.table_name()} r
                WHERE r.resource_id = rps.resource_id and r.environment=$1
            ) and rps.environment=$1
            """,
            environment,
            connection=connection,
        )

    @classmethod
    async def populate_for_version(
        cls, environment: uuid.UUID, model_version: int, connection: Optional[Connection] = None
    ) -> None:
        """
        Make sure that the resource_persistent_state table has a record for each resource present in the
        given model version. This method assumes that the given model_version is the latest released version and that the table
        has already been populated for the previously released version.
        """
        await cls._execute_query(
            f"""
            WITH previous_released_version AS (
                SELECT max(c.version) AS version
                FROM {ConfigurationModel.table_name()} AS c
                WHERE c.environment = $1 AND c.released AND c.version < $2
            )
            INSERT INTO {cls.table_name()} (
                environment,
                resource_id,
                resource_type,
                agent,
                resource_id_value,
                current_intent_attribute_hash,
                is_undefined,
                is_orphan,
                is_deploying,
                last_handler_run,
                blocked,
                created
            )
            SELECT
                r.environment,
                r.resource_id,
                r.resource_type,
                r.agent,
                r.resource_id_value,
                r.attribute_hash,
                r.is_undefined,
                FALSE,
                FALSE,
                'NEW',
                CASE
                    WHEN
                        r.is_undefined
                    THEN 'BLOCKED'
                    ELSE 'NOT_BLOCKED'
                END,
                now()
            FROM resource_set_configuration_model AS rscm
            INNER JOIN {Resource.table_name()} AS r
                ON rscm.environment=r.environment
                AND rscm.resource_set=r.resource_set
            WHERE rscm.environment=$1 AND rscm.model=$2
                AND NOT EXISTS (
                    SELECT 1
                    FROM resource_set_configuration_model AS prev_rscm
                    INNER JOIN previous_released_version AS prev
                        ON prev_rscm.model = prev.version
                    WHERE prev_rscm.environment = rscm.environment
                        AND prev_rscm.resource_set = rscm.resource_set
                )
            ON CONFLICT DO NOTHING
            """,
            environment,
            model_version,
            connection=connection,
        )

    @classmethod
    async def persist_non_compliant_diff(
        cls,
        environment: uuid.UUID,
        resource_id: ResourceIdStr,
        created_at: datetime.datetime,
        diff: abc.Mapping[str, object],
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> uuid.UUID:
        """
        Persist the non-compliant diff into the resource_diff table.

        :returns: the id of the created diff
        """
        query = """
            INSERT INTO resource_diff (id, environment, resource_id, created, diff)
            VALUES (gen_random_uuid(), $1, $2, $3, $4)
            RETURNING id
        """
        record = await cls._fetchrow(query, environment, resource_id, created_at, json.dumps(diff), connection=connection)
        assert record  # make mypy happy
        return uuid.UUID(str(record["id"]))

    @classmethod
    async def purge_old_diffs(cls) -> None:
        """
        Purge every diff that is older than RESOURCE_ACTION_LOGS_RETENTION
        and not currently referenced by the rps table
        """
        default_retention_time = Environment._settings[RESOURCE_ACTION_LOGS_RETENTION].default

        query = f"""
            WITH non_halted_envs AS (
                SELECT
                    id,
                    (
                        COALESCE((settings->'settings'->'resource_action_logs_retention'->>'value')::int, $1)
                    ) AS retention_days
                FROM {Environment.table_name()}
                WHERE NOT halted
            )
            DELETE FROM public.resource_diff AS rd
            USING non_halted_envs
            WHERE rd.environment=non_halted_envs.id
                AND rd.created < now() AT TIME ZONE 'UTC' - make_interval(days => non_halted_envs.retention_days)
                AND NOT EXISTS (
                  SELECT 1
                  FROM {cls.table_name()} AS rps
                  WHERE rps.environment=rd.environment
                    AND rps.resource_id=rd.resource_id
                    AND rps.non_compliant_diff=rd.id
              );
        """
        await cls._execute_query(query, default_retention_time)

    @classmethod
    async def update_persistent_state(
        cls,
        environment: uuid.UUID,
        resource_id: ResourceIdStr,
        is_deploying: bool | None = None,
        last_handler_run_at: datetime.datetime | None = None,
        last_deployed_version: int | None = None,
        last_non_deploying_status: Optional[const.NonDeployingResourceState] = None,
        last_success: Optional[datetime.datetime] = None,
        last_produced_events: Optional[datetime.datetime] = None,
        last_deployed_attribute_hash: Optional[str] = None,
        last_handler_run_compliant: Optional[bool] = None,
        non_compliant_diff: Optional[uuid.UUID] = None,
        cleanup_non_compliant_diff: Optional[bool] = False,
        connection: Optional[asyncpg.connection.Connection] = None,
        # TODO[#8541]: accept state.ResourceState and write blocked status as well
        last_handler_run: Optional[state.HandlerResult] = None,
    ) -> None:
        """Update the data in the resource_persistent_state table"""
        args = ArgumentCollector(2)

        invalues = {
            "is_deploying": is_deploying,
            "last_handler_run_at": last_handler_run_at,
            "last_non_deploying_status": last_non_deploying_status,
            "last_success": last_success,
            "last_produced_events": last_produced_events,
            "last_deployed_attribute_hash": last_deployed_attribute_hash,
            "last_deployed_version": last_deployed_version,
            "last_handler_run_compliant": last_handler_run_compliant,
            "non_compliant_diff": non_compliant_diff,
        }
        query_parts = [f"{k}={args(v)}" for k, v in invalues.items() if v is not None]
        if last_handler_run:
            query_parts.append(f"last_handler_run={args(last_handler_run.name)}")
        if not query_parts:
            return
        if cleanup_non_compliant_diff:
            if non_compliant_diff is not None:
                raise Exception("Cannot provide both non_compliant_diff and cleanup_non_compliant_diff")
            query_parts.append("non_compliant_diff=NULL")
        query = f"UPDATE public.resource_persistent_state SET {','.join(query_parts)} WHERE environment=$1 and resource_id=$2"

        result = await cls._execute_query(query, environment, resource_id, *args.args, connection=connection)
        if result == "UPDATE 0":
            raise NotFound(
                "Unable to find an entry in the resource_persistent_state table "
                f"for resource with id {resource_id} in environment {environment}"
            )

    def get_compliance_status(self) -> Optional[state.Compliance]:
        """
        Return the Compliance associated with this resource_persistent_state. Returns None for orphaned resources.
        """
        return state.get_compliance_status(
            self.is_orphan,
            self.is_undefined,
            self.last_deployed_attribute_hash,
            self.current_intent_attribute_hash,
            self.last_handler_run_compliant,
        )

    @classmethod
    async def get_compliance_report(
        cls, env: uuid.UUID, resource_ids: Sequence[ResourceIdStr]
    ) -> dict[ResourceIdStr, m.ResourceComplianceDiff]:
        async with cls.get_connection() as connection:
            query = f"""
            SELECT r.resource_id,
                COALESCE((r.attributes->>'report_only')::boolean, false) AS report_only,
                rd.diff,
                rps.last_handler_run_at AS last_handler_run_at,
                rps.is_undefined,
                rps.last_deployed_attribute_hash,
                rps.current_intent_attribute_hash,
                rps.last_handler_run,
                rps.blocked,
                rps.last_handler_run_compliant
            FROM {Scheduler.table_name()} AS s
            INNER JOIN public.resource_set_configuration_model AS rscm
                ON s.environment=rscm.environment
                AND s.last_processed_model_version=rscm.model
            INNER JOIN {Resource.table_name()} AS r
                ON rscm.environment=r.environment
                AND rscm.resource_set=r.resource_set
            INNER JOIN UNNEST($2::text[]) AS requested_rids(resource_id)
                ON requested_rids.resource_id=r.resource_id
            INNER JOIN {cls.table_name()} AS rps
                ON r.environment=rps.environment
                AND r.resource_id=rps.resource_id
            LEFT JOIN public.resource_diff AS rd
                ON rps.non_compliant_diff=rd.id
            WHERE
                NOT rps.is_orphan
                AND rps.environment=$1
            """
            result = await cls.select_query(query, [env, resource_ids], no_obj=True, connection=connection)
            if len(result) != len(resource_ids):
                missing_rids = set(resource_ids) - {ResourceIdStr(str(r["resource_id"])) for r in result}
                raise NotFound(f"Unable to find the following resource ids in the active version: {missing_rids}")
            diff: dict[ResourceIdStr, m.ResourceComplianceDiff] = {}
            for record in result:
                compliance_status = state.get_compliance_status(
                    is_orphan=False,  # We filter out orphan resources in the query
                    is_undefined=cast(bool, record["is_undefined"]),
                    last_deployed_attribute_hash=cast(str | None, record["last_deployed_attribute_hash"]),
                    current_intent_attribute_hash=cast(str | None, record["current_intent_attribute_hash"]),
                    last_handler_run_compliant=cast(bool, record["last_handler_run_compliant"]),
                )
                diff[ResourceIdStr(str(record["resource_id"]))] = m.ResourceComplianceDiff(
                    report_only=cast(bool, record["report_only"]),
                    attribute_diff=(
                        cast(dict[str, AttributeStateChange] | None, record["diff"])
                        if compliance_status is state.Compliance.NON_COMPLIANT
                        else None
                    ),
                    compliance=compliance_status,
                    last_handler_run=state.HandlerResult(str(record["last_handler_run"]).lower()),
                    last_handler_run_at=cast(datetime.datetime | None, record["last_handler_run_at"]),
                )
            return diff


class InvalidResourceSetMigration(Exception):
    """
    Raise this exception when a resource is migrated to another resource set in a partial compile
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ResourceSet(BaseDocument):
    """
    A set of resources

    :param environment: The environment this resource set belongs to
    :param id: The id of this resource set. Unique per environment.
    :param name: The name of this resource set, None if it is the default set
    """

    environment: uuid.UUID
    id: uuid.UUID
    name: Optional[str]

    @classmethod
    def table_name(cls) -> str:
        return "resource_set"

    @classmethod
    def get_printable_name_for_resource_set(cls, native: str | None) -> str:
        if native is None:
            return "<SHARED>"
        return native

    @classmethod
    async def get_resource_sets_in_version(
        cls, environment: uuid.UUID, version: int, connection: Optional[asyncpg.connection.Connection] = None
    ) -> list["ResourceSet"]:
        """
        Returns the resource sets in the given version. Only meant for testing.
        """
        query = f"""
            SELECT rs.*
            FROM public.resource_set_configuration_model rscm
            INNER JOIN {cls.table_name()} rs
                ON rs.id=rscm.resource_set
            WHERE rscm.environment=$1 AND rscm.model=$2
                """
        query_result = await cls._fetch_query(
            query,
            environment,
            version,
            connection=connection,
        )
        result = [cls(from_postgres=True, **record) for record in query_result]
        # Could not express this constraint in the database
        assert len({rs.name for rs in result}) == len(
            result
        ), "Inconsistency in the database, a resource set cannot be present more than once in the same model version"
        return result

    @classmethod
    async def validate_resource_sets_in_version(
        cls,
        environment: uuid.UUID,
        version: int,
        updated_resource_sets: set[str | None],
        *,
        connection: asyncpg.connection.Connection,
    ) -> None:
        """
        Checks for duplicate resources and resource_sets in the target version.
        This should only happen when we try to migrate a resource to another resource set (base -> target)
        while the base resource set is not present in the partial compile.
        """
        query = """
            SELECT
              r.resource_id, array_agg(rs.name) AS name
            FROM resource_set_configuration_model AS rscm
            INNER JOIN resource_set AS rs
                ON rscm.environment=rs.environment
                AND rscm.resource_set=rs.id
            INNER JOIN resource AS r
                ON rs.environment=r.environment
                AND rs.id=r.resource_set
            WHERE rscm.environment=$1
                AND rscm.model=$2
            GROUP BY r.resource_id
            HAVING COUNT(*) > 1
        """
        records = await cls._fetch_query(query, environment, version, connection=connection)
        if records:
            rid_to_resource_sets: dict[str, dict[str, str]] = {}
            for record in records:
                resource_id = str(record["resource_id"])
                resource_set_names = list(record["name"])
                if len(resource_set_names) > 2:
                    # Should never be possible for a resource id to be present in more than 2 resource sets at this stage
                    # suggests a bug in one of the sql queries
                    raise Exception(
                        f"Resource {resource_id} appears in {len(resource_set_names)} resource sets "
                        f"on version {version}: {resource_set_names}."
                        "This should not be possible. Please create a support ticket. "
                        f"Updated resource sets: {updated_resource_sets}"
                    )
                rid_to_resource_sets[resource_id] = {}
                for name in resource_set_names:
                    key = "new" if name in updated_resource_sets else "old"
                    if key in rid_to_resource_sets[resource_id]:
                        # Should never be possible for a resource id to be present in either:
                        # - 2 updated resource sets
                        # - 2 unchanged resource sets
                        # It means we have a bug somewhere
                        resource_set_type = "updated" if key == "new" else "unchanged"
                        raise Exception(
                            f"Resource {resource_id} appears in multiple {resource_set_type} resource sets: "
                            f"[{name}, {rid_to_resource_sets[resource_id]}] on version {version} of the model. "
                            "This should not be possible. Please create a support ticket. "
                            f"Updated resource sets: {updated_resource_sets}"
                        )
                    rid_to_resource_sets[resource_id][key] = name

            # This is the only case that should be reachable by the user.
            # The other 2 are just fail safes
            msg = (
                "The following Resource(s) cannot be migrated to a different resource set using a partial compile, "
                "a full compile is necessary for this process:\n"
            )
            msg += "\n".join(
                f"    {rid} moved from {cls.get_printable_name_for_resource_set(resource_sets["old"])} "
                f"to {cls.get_printable_name_for_resource_set(resource_sets["new"])}"
                for rid, resource_sets in rid_to_resource_sets.items()
            )
            raise InvalidResourceSetMigration(msg)

    @classmethod
    async def insert_sets_and_resources(
        cls,
        environment: uuid.UUID,
        target_version: int,
        updated_resources: abc.Collection[m.Resource],
        base_version: Optional[int] = None,
        deleted_resource_sets: Optional[abc.Set[str]] = None,
        *,
        connection: asyncpg.connection.Connection,
    ) -> None:
        """
        Inserts resources and resource sets and links resource sets to the target version.

        In case of a full compile, expects to receive every resource set.

        In case of a partial compile, expects to receive all sets with changes, and all resources for those sets (including
        the shared set, which is treated like any other). We insert the updated resource sets and we link to the target version:
            - The resource sets that we just updated
            - Every resource set in the base version except:
                - Resource sets we want to delete
                - Resource sets with the same name as one of the updated resource sets (they are now outdated)

        :param environment: The environment of these resources.
        :param target_version: The version which we want to link the resource sets to
        :param updated_resources: A list of resources to insert.
            On a full compile, this list should contain all resources present in the version.
            On a partial compile, this list should contain all resources belonging to a resource set that was changed.
        :param base_version: This is the version which the partial compile is based on. None if we are doing a full compile.
        :param deleted_resource_sets: These are the resource set names from the base version which were removed
            in this partial compile. Not applicable for a full compile.
        :param connection: The connection to use. Must be in a transaction context.
        """

        is_partial_update = base_version is not None

        updated_resource_sets: set[str | None] = set()
        resource_data: dict[str, list[object]] = defaultdict(list)
        for r in updated_resources:
            updated_resource_sets.add(r.resource_set)
            resource_data["resource_id"].append(str(r.resource_id))
            resource_data["resource_type"].append(r.resource_type)
            resource_data["resource_id_value"].append(r.resource_id_value)
            resource_data["agent"].append(r.agent)
            resource_data["attributes"].append(r.attributes)
            resource_data["attribute_hash"].append(util.make_attribute_hash(r.resource_id, r.attributes))
            resource_data["is_undefined"].append(r.is_undefined)
            resource_data["resource_set"].append(r.resource_set)
        resource_data_db: dict[str, object] = {k: cls._get_value(v) for k, v in resource_data.items()}

        # common arguments to all queries
        # $1: environment
        # $2: target_version
        common_values: tuple[object, object] = (cls._get_value(environment), cls._get_value(target_version))

        if is_partial_update:
            # copy all old sets except for the ones that are being exported or deleted in this partial update
            deleted_resource_sets = deleted_resource_sets if deleted_resource_sets is not None else set()

            has_shared_resource_set = None in updated_resource_sets
            # link every resource_set that was present in the base version to the target version
            with pyformance.timer("sql.insert_sets_and_resources.copy_sets").time():
                await cls._execute_query(
                    f"""\
                    INSERT INTO public.resource_set_configuration_model(
                        environment,
                        model,
                        resource_set
                    )
                    SELECT
                        $1,
                        $2,
                        rscm.resource_set
                    FROM public.resource_set_configuration_model AS rscm
                    INNER JOIN resource_set AS rs
                        ON rscm.environment=rs.environment
                        AND rscm.resource_set=rs.id
                    WHERE rscm.environment=$1
                        AND rscm.model=$3
                        -- only insert resource sets that are not on updated_resource_sets --
                        AND (
                            SELECT rs.name = ANY($4::text[]) {'OR rs.name IS NULL' if has_shared_resource_set else ''}
                            FROM resource_set AS rs
                            WHERE
                                rs.environment = rscm.environment
                                AND rs.id = rscm.resource_set
                        ) IS NOT true
                    """,
                    *common_values,
                    cls._get_value(base_version),
                    cls._get_value((updated_resource_sets | deleted_resource_sets) - {None}),
                    connection=connection,
                )

        # insert the updated resource sets and resources into the database and link everything together
        # (resource -> set and set -> model)
        with pyformance.timer("sql.insert_sets_and_resources.insert").time():
            await cls._execute_query(
                """\
                -- insert resource sets and keep track of name-id mapping
                WITH inserted_resource_sets AS (
                    INSERT INTO public.resource_set (environment, id, name)
                    SELECT
                        $1,
                        gen_random_uuid() AS id,
                        UNNEST($3::text[])
                    RETURNING name, id
                -- link resource sets to model version
                ), linked_resource_sets AS (
                    INSERT INTO public.resource_set_configuration_model(
                       environment,
                       model,
                       resource_set
                    )
                    SELECT
                        $1,
                        $2,
                        irs.id
                    FROM inserted_resource_sets AS irs
                ), resource_data AS (
                    SELECT
                        UNNEST($4::text[]) AS resource_id,
                        UNNEST($5::text[]) AS resource_type,
                        UNNEST($6::text[]) AS resource_id_value,
                        UNNEST($7::text[]) AS agent,
                        UNNEST($8::jsonb[]) AS attributes,
                        UNNEST($9::text[]) AS attribute_hash,
                        UNNEST($10::boolean[]) AS is_undefined,
                        UNNEST($11::text[]) AS resource_set
                )
                -- insert resources
                INSERT INTO public.resource(
                    environment,
                    resource_id,
                    resource_type,
                    resource_id_value,
                    agent,
                    attributes,
                    attribute_hash,
                    is_undefined,
                    resource_set
                )
                SELECT
                    $1,
                    r.resource_id,
                    r.resource_type,
                    r.resource_id_value,
                    r.agent,
                    r.attributes,
                    r.attribute_hash,
                    r.is_undefined,
                    rs.id
                FROM resource_data AS r
                -- this join has been tested to be up to four times faster than joining with
                -- resource_configuration_model, even if the latter would have the name column directly
                -- (for 5k models, 5k sets, updating 1-1000 sets, with 100-10k resources per set).
                -- Order of magnitude for reference: 0.5s when updating 10 sets with 1k resources per set.
                INNER JOIN inserted_resource_sets AS rs
                    ON r.resource_set IS NOT DISTINCT FROM rs.name
                """,
                *common_values,
                cls._get_value(updated_resource_sets),
                # insert as separate arrays rather than jsonb because jsob has a size limit
                resource_data_db.get("resource_id", []),
                resource_data_db.get("resource_type", []),
                resource_data_db.get("resource_id_value", []),
                resource_data_db.get("agent", []),
                resource_data_db.get("attributes", []),
                resource_data_db.get("attribute_hash", []),
                resource_data_db.get("is_undefined", []),
                resource_data_db.get("resource_set", []),
                connection=connection,
            )

        if is_partial_update:
            with pyformance.timer("sql.insert_sets_and_resources.validate").time():
                await cls.validate_resource_sets_in_version(
                    environment=environment,
                    version=target_version,
                    updated_resource_sets=updated_resource_sets,
                    connection=connection,
                )

    @classmethod
    async def clear_resource_sets_in_version(
        cls,
        environment: uuid.UUID,
        version: int,
        *,
        connection: asyncpg.connection.Connection,
    ) -> None:
        """
        Deletes entries on resource_set_configuration_model that relate to this environment and version.
        Deletes resource sets that no longer have entries in resource_set_configuration_model
        Deletes resources associated with those resource sets (via cascade).

        :param environment: The environment from which to delete the resource sets
        :param version: The version to delete from the resource_set_configuration_model table.
        :param connection: The connection to use
        """

        # Delete all links from the resource set to this version
        await cls._execute_query(
            """
            DELETE FROM resource_set_configuration_model AS rscm
            WHERE rscm.environment=$1 AND rscm.model=$2
            RETURNING rscm.resource_set
            """,
            environment,
            version,
            connection=connection,
        )
        # Delete resource sets that are no longer linked to a configuration model
        await cls._execute_query(
            """
            DELETE FROM resource_set AS rs
            WHERE NOT EXISTS (
                SELECT 1
                FROM resource_set_configuration_model AS rscm
                WHERE rscm.environment=rs.environment
                AND rscm.resource_set=rs.id
            ) AND rs.environment=$1
            """,
            environment,
            connection=connection,
        )


@stable_api
class Resource(BaseDocument):
    """
    A specific version of a resource. This entity contains the desired state of a resource.

    :param environment: The environment this resource version is defined in
    :param resource_id: The id of the resource (without the version)
    :param resource_type: The type of the resource
    :param resource_id_value: The attribute value from the resource id
    :param agent: The name of the agent responsible for deploying this resource
    :param attributes: The desired state for this version of the resource as a dict of attributes
    :param attribute_hash: hash of the attributes, excluding requires, provides and version,
                           used to determine if a resource describes the same state across versions
    :param is_undefined: If the desired state for resource is undefined
    :param resource_set: The id of the resource set this resource belongs to.
    """

    __primary_key__ = ("environment", "resource_set", "resource_id")

    environment: uuid.UUID

    # ID related
    resource_id: ResourceIdStr
    resource_type: ResourceType
    resource_id_value: str

    agent: str

    # State related
    attributes: dict[str, object] = {}
    attribute_hash: Optional[str]
    is_undefined: bool = False

    resource_set: uuid.UUID

    def make_hash(self) -> None:
        self.attribute_hash = util.make_attribute_hash(self.resource_id, self.attributes)

    @classmethod
    async def get_resources(
        cls,
        environment: uuid.UUID,
        resource_version_ids: list[ResourceVersionIdStr],
        lock: Optional[RowLockMode] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> list["Resource"]:
        """
        Get all resources listed in resource_version_ids
        """
        if not resource_version_ids:
            return []

        query_lock: str = lock.value if lock is not None else ""

        def convert_or_ignore(rvid: ResourceVersionIdStr) -> resources.Id | None:
            """Method to retain backward compatibility, ignore bad ID's"""
            try:
                return resources.Id.parse_resource_version_id(rvid)
            except ValueError:
                return None

        parsed_rv = (convert_or_ignore(id) for id in resource_version_ids)
        effective_parsed_rv = [id for id in parsed_rv if id is not None]

        if not effective_parsed_rv:
            return []

        query = f"""
            SELECT r.*
                FROM resource_set_configuration_model AS rscm
                INNER JOIN {cls.table_name()} AS r
                    ON rscm.environment=r.environment
                    AND rscm.resource_set=r.resource_set
                INNER JOIN unnest($2::resource_id_version_pair[]) AS requested(resource_id, model)
                    ON r.resource_id=requested.resource_id
                    AND rscm.model=requested.model
                WHERE rscm.environment=$1
            {query_lock}
        """
        out = await cls.select_query(
            query,
            [cls._get_value(environment), [(id.resource_str(), id.get_version()) for id in effective_parsed_rv]],
            connection=connection,
        )
        return out

    @classmethod
    async def get_latest_resource_states(
        cls, env: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None
    ) -> tuple[Optional[int], abc.Mapping[ResourceIdStr, ResourceState]]:
        """
        Fetches the states of the resources in the latest scheduled version.
        """
        query = f"""
            SELECT
                s.last_processed_model_version AS model,
                rps.resource_id,
                {const.SQL_RESOURCE_STATUS_SELECTOR} AS status
            FROM {ResourcePersistentState.table_name()} AS rps
            INNER JOIN {Scheduler.table_name()} AS s
                ON rps.environment=s.environment
            WHERE rps.environment=$1 AND NOT rps.is_orphan
        """
        results = await cls.select_query(query, [env], no_obj=True, connection=connection)
        if not results:
            return None, {}
        return (int(results[0]["model"]), {r["resource_id"]: const.ResourceState[r["status"]] for r in results})

    @stable_api
    @classmethod
    async def get_current_resource_state(cls, env: uuid.UUID, rid: ResourceIdStr) -> Optional[const.ResourceState]:
        """
        Return the current state of the given resource
        or None if the resource is not present in the latest version (marked as an orphan).
        """
        query = f"""
            SELECT
            {const.SQL_RESOURCE_STATUS_SELECTOR} AS status
            FROM resource_persistent_state AS rps
            WHERE rps.environment=$1 AND rps.resource_id=$2 AND NOT rps.is_orphan
            """
        results = await cls.select_query(query, [env, rid], no_obj=True)
        if not results:
            return None
        assert len(results) == 1
        return const.ResourceState(results[0]["status"])

    @classmethod
    async def reset_resource_state(
        cls,
        environment: uuid.UUID,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Update resources on the latest released version of the model stuck in "deploying" state.
        The status will be reset to the latest non deploying status.
        The is_deploying flag will also be set to "False" on the ResourcePersistentState table.

        :param environment: The environment impacted by this
        :param connection: The connection to use
        """

        update_rps_query = f"""
            UPDATE {ResourcePersistentState.table_name()} rps
            SET is_deploying=FALSE
            WHERE environment=$1
        """
        values = [cls._get_value(environment)]
        async with cls.get_connection(connection) as connection:
            await connection.execute(update_rps_query, *values)

    @classmethod
    async def get_resources_in_latest_version_as_dto(
        cls,
        environment: uuid.UUID,
        resource_type: Optional[ResourceType] = None,
        attributes: dict[PrimitiveTypes, PrimitiveTypes] = {},
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> list[m.Resource]:
        """
        Returns the resources (in dto format) in the latest version of the configuration model of the given environment,
        that satisfy the given constraints.

        :param environment: The resources should belong to this environment.
        :param resource_type: The environment should have this resource_type.
        :param attributes: The resource should contain these key-value pairs in its attributes list.
        """
        values = [cls._get_value(environment)]
        query = f"""
            SELECT r.*, rs.name AS resource_set_name
            FROM {Resource.table_name()} AS r
            INNER JOIN {ResourceSet.table_name()} AS rs
                ON r.environment=rs.environment
                AND r.resource_set=rs.id
            INNER JOIN resource_set_configuration_model AS rscm
                ON rs.environment=rscm.environment
                AND rs.id=rscm.resource_set
            WHERE rscm.environment=$1 AND rscm.model=(SELECT MAX(cm.version)
                                              FROM {ConfigurationModel.table_name()} AS cm
                                              WHERE cm.environment=$1)
            """
        if resource_type:
            query += " AND r.resource_type=$2"
            values.append(cls._get_value(resource_type))

        result = []
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    resource = m.Resource.from_postgres_record(record)
                    # The constraints on the attributes field are checked in memory.
                    # This prevents injection attacks.
                    if util.is_sub_dict(attributes, resource.attributes):
                        result.append(resource)
        return result

    @classmethod
    async def get_resources_for_version(
        cls,
        environment: uuid.UUID,
        version: int,
        agent: Optional[str] = None,
        no_obj: bool = False,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> list["Resource"]:
        values = [environment, version]
        if agent:
            values.append(agent)
        query = f"""
            SELECT r.*
                FROM resource_set_configuration_model AS rscm
                INNER JOIN {Resource.table_name()} AS r
                    ON rscm.environment=r.environment
                    AND rscm.resource_set=r.resource_set
                WHERE rscm.environment=$1 AND rscm.model=$2
                {'AND r.agent=$3' if agent else ''}
        """
        resources_list: Union[list[Resource], list[dict[str, object]]] = []
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    if no_obj:
                        record = dict(record)
                        resources_list.append(record)
                    else:
                        resources_list.append(cls(from_postgres=True, **record))
        return resources_list

    @classmethod
    async def get_resources_for_version_as_dto(
        cls,
        environment: uuid.UUID,
        version: int,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> list[m.Resource]:
        values = [environment, version]
        query = f"""
            SELECT r.*, rs.name AS resource_set_name
                FROM resource_set_configuration_model AS rscm
                INNER JOIN {ResourceSet.table_name()} AS rs
                    ON rscm.environment=rs.environment
                    AND rscm.resource_set=rs.id
                INNER JOIN {Resource.table_name()} AS r
                    ON rs.environment=r.environment
                    AND rs.id=r.resource_set
                WHERE rscm.environment=$1 AND rscm.model=$2
        """
        resources_list: list[m.Resource] = []
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    resources_list.append(m.Resource.from_postgres_record(record))
        return resources_list

    @classmethod
    async def get_resources_for_version_raw(
        cls,
        environment: uuid.UUID,
        *,
        version: Optional[int] = None,
        projection: Collection[typing.LiteralString],
        projection_persistent: Collection[typing.LiteralString] = (),
        project_attributes: Collection[typing.LiteralString] = (),
        connection: Optional[Connection] = None,
    ) -> Optional[tuple[int, inmanta.types.ResourceSets[dict[str, object]]]]:
        """
        Returns resources grouped by resource set for the given version (released or not). If no version is specified, returns
        the resources for the latest released version.

        :param version: The version for which to return the resources. If not specified, returns resources for the latest
            released version.
        :param projection: The resource columns to include in the returned resource dictionaries.
            Must not overlap with other projection parameters.
        :param projection_persistent: The resource_persistent_state columns to include in the returned resource dictionaries.
            Must not overlap with other projection parameters.
        :param project_attributes: The resource attributes to include as top-level keys in the returned resource dictionaries.
            Must not overlap with other projection parameters.

        :returns: Tuple of the requested model version and the resources it contains, grouped by resource set. Returns None iff
            the requested model version does not exist (anymore). If the model exists but contains no resources, the resource
            sets collection will simply be empty.
        """
        version_query: typing.LiteralString = (
            "SELECT $2::int AS version"
            if version is not None
            else f"""\
                SELECT MAX(version) AS version
                FROM {ConfigurationModel.table_name()}
                WHERE
                    environment = $1
                    AND released = true
            """
        )
        r_projection_selector: Sequence[typing.LiteralString] = [f"r.{col}" for col in projection]
        rps_projection_selector: Sequence[typing.LiteralString] = [f"rps.{col}" for col in projection_persistent]
        attributes_projection_selector: Sequence[typing.LiteralString] = [
            f"r.attributes->'{v}' AS {v}" for v in project_attributes
        ]

        projection_keys: typing.Sequence[typing.LiteralString] = list(
            itertools.chain(projection, projection_persistent, project_attributes)
        )
        if len(projection_keys) != len(set(projection_keys)):
            raise ValueError("Projection keys must not overlap")
        projection_selectors: typing.LiteralString = ", ".join(
            itertools.chain(r_projection_selector, rps_projection_selector, attributes_projection_selector)
        )

        rps_join: typing.LiteralString
        if rps_projection_selector:
            rps_join = f"""\
                LEFT JOIN {ResourcePersistentState.table_name()} AS rps
                    ON rps.environment = r.environment
                    AND rps.resource_id = r.resource_id
            """
        else:
            rps_join = ""

        # We query the database for all resources in the latest version.
        # Structure of the result table:
        #   returns 0 rows iff the requested version (version number / latest released) does not exist
        #   columns:
        #       - version NOT NULL
        #       - resource_set_name -> NULL is name of the shared set
        #       - resource_set_id -> NULL iff LEFT JOIN didn't match any resource sets => model exists but is empty
        #       - <projection_fields> -> NULL iff LEFT join didn't match any resources => empty resource set
        query: typing.LiteralString = f"""
            WITH version AS (
                {version_query}
            )
            SELECT
                cm.version,
                rs.name AS resource_set_name,
                rscm.resource_set,
                {projection_selectors}
            FROM version AS version
            INNER JOIN {ConfigurationModel.table_name()} AS cm
                ON cm.environment = $1
                AND cm.version = version.version
            LEFT JOIN resource_set_configuration_model AS rscm
                ON rscm.environment = $1
                AND rscm.model = cm.version
            LEFT JOIN {ResourceSet.table_name()} AS rs
                ON rs.environment = rscm.environment
                AND rs.id = rscm.resource_set
            LEFT JOIN {cls.table_name()} AS r
                ON r.environment = rs.environment
                AND r.resource_set = rs.id
            {rps_join}
            ORDER BY rs.name, r.resource_id
        """
        with pyformance.timer("sql.get_resources_for_version_raw").time():
            resource_records = await cls._fetch_query(
                query,
                cls._get_value(environment),
                *([version] if version is not None else []),
                connection=connection,
            )

        records: Iterator[asyncpg.Record]
        spy: Sequence[asyncpg.Record]
        spy, records = more_itertools.spy(resource_records)
        if not spy:
            # requested version does not exist
            return None
        db_version: int = spy[0]["version"]
        if spy[0]["resource_set"] is None:
            # LEFT JOIN produced no resource sets => empty model
            return (db_version, {})

        sets: inmanta.types.ResourceSets[dict[str, object]] = {
            resource_set_name: [{k: record[k] for k in projection_keys} for record in records]
            for resource_set_name, records in itertools.groupby(records, key=lambda r: r["resource_set_name"])
        }
        return (db_version, sets)

    @classmethod
    async def get_partial_resources_since_version_raw(
        cls,
        environment: uuid.UUID,
        *,
        since: int,
        projection: Collection[typing.LiteralString],
        connection: Optional[Connection] = None,
    ) -> list[tuple[int, inmanta.types.ResourceSets[dict[str, object]]]]:
        """
        Returns all released model versions with associated resources since (excluding) the given model version.
        Returned versions are returned as partial versions. In other words, only resource sets that changed since the previous
        version are included. Resource sets that were deleted are represented as empty sets.

        Note that a partial model version on this layer does not map one on one with how it was exported. Notably, if a partial
        model version contains the shared set, it will contain all of its resources, rather than only those that were present in
        the associated export.

        :param since: The boundary version (excluding). This version should exist and be released.
        :param projection: The resource columns to include in the returned resource dictionaries.
            Must not overlap with other projection parameters.

        :returns: A list of model versions and resources, grouped by resource set.
        :raises PartialBaseMissing: The `since` version does not exist or has not been released.
        """
        projection_selectors: typing.LiteralString = ", ".join([f"r.{col}" for col in projection])

        # We query the database for all resources in all released versions since the requested one. For each version, we
        # request the diff with the previous version.
        # Structure of the result table:
        #   returns at least 1 row (all LEFT JOINs)
        #   columns: "RETURN" marker between column specifications implies that all following fields will be NULL depending on
        #       the previous result, regardless of the "NULL IFF" semantics in the fields' own description.
        #
        #       - exists NOT NULL -> false iff the `since` model doesn't exist at all.
        #       RETURN if not exists
        #       - version -> NULL iff no newer released versions were found
        #       RETURN if version is NULL
        #       - empty_model NOT NULL -> true iff the model has no resource sets
        #       RETURN if empty_model
        #       - resource_set_name -> NULL is name of the shared set
        #       - resource_set_id: resource set id in the new version iff it differs from the previous version
        #           -> NULL iff resource set with this name was deleted in this version
        #       - <projection_fields> -> NULL iff LEFT join didn't match any resources => empty resource set
        query: typing.LiteralString = f"""\
        WITH
        -- `since` model iff it exists and has been released
        reference_model AS (
            SELECT EXISTS(
                SELECT *
                FROM {ConfigurationModel.table_name()} AS cm
                WHERE cm.environment = $1
                    AND cm.version = $2::int
                    AND cm.released
            ) AS exists
        -- all released models starting from `since`
        ), models AS (
            SELECT *
            FROM {ConfigurationModel.table_name()} AS cm
            WHERE cm.environment = $1
                AND cm.version > $2::int - 1
                AND cm.released
        -- resource_set_configuration_model for relevant versions with resource_set.name joined in
        ), rs_with_name AS (
            SELECT
                rscm.*,
                rs.name
            FROM models AS cm
            INNER JOIN resource_set_configuration_model AS rscm
                ON rscm.environment = cm.environment
                AND rscm.model = cm.version
            INNER JOIN {ResourceSet.table_name()} AS rs
                ON rs.environment = rscm.environment
                AND rs.id = rscm.resource_set
        -- pairwise (two-by-two) model versions to build the diff incrementally
        ), model_pairs AS (
            SELECT *
            FROM (
                SELECT
                    first_value(version) OVER pairs AS old,
                    last_value(version) OVER pairs AS new
                FROM models AS cm
                WINDOW pairs AS (ORDER BY cm.version ROWS 1 PRECEDING)
                ORDER BY cm.version
            )
            -- drop first row where there is no PRECEDING for the window function
            WHERE old != new
        )
        SELECT
            reference_model.exists,
            model_pairs.new AS version,
            -- each row of the diff will always have at least one of the resource set ids set.
            -- => if both are NULL, there were no records at all on the rhs of the LEFT JOIN
            (diff.old_resource_set IS NULL AND diff.resource_set IS NULL) AS empty_model,
            diff.name AS resource_set_name,
            diff.resource_set,
            {projection_selectors}
        FROM reference_model
        LEFT JOIN model_pairs ON true
        -- Calculate the diff by joining pairwise with both versions' resource sets.
        -- Returns only differing sets:
        --  - name -> NULL is name of shared set
        --  - old_resource_set -> NULL if no set with this name existed in old version
        --  - new_resource_set -> NULL if set with this name was deleted in new version
        LEFT JOIN LATERAL (
            -- DISTINCT because join results in two null rows for shared set. ORDER BY below ensures we keep the latest one
            SELECT DISTINCT ON (rs_new.name, rs_old.name)
                -- if the set exists in only one of the models, report that one
                COALESCE(rs_new.name, rs_old.name) AS name,
                -- we're only interested in the latest id, or the absence of it
                rs_old.resource_set AS old_resource_set,
                rs_new.resource_set
            FROM (SELECT * FROM rs_with_name WHERE model = model_pairs.old) AS rs_old
            FULL JOIN (SELECT * FROM rs_with_name WHERE model = model_pairs.new) AS rs_new
                ON rs_old.name = rs_new.name
            -- filter out all sets that remained unchanged
            WHERE rs_new.resource_set IS DISTINCT FROM rs_old.resource_set
            -- make sure SELECT DISTINCT matches the new id for the shared set, if it exists
            ORDER BY rs_new.name, rs_old.name, rs_new.resource_set NULLS LAST
        ) AS diff
        ON true
        -- fetch all resources for the relevant sets
        LEFT JOIN {cls.table_name()} as r
            ON r.environment = $1
            AND r.resource_set = diff.resource_set
        ORDER BY model_pairs.new, diff.name, r.resource_id
        """
        with pyformance.timer("sql.get_partial_resources_since_version_raw").time():
            resource_records = await cls._fetch_query(
                query,
                cls._get_value(environment),
                cls._get_value(since),
                connection=connection,
            )

        assert resource_records
        if not resource_records[0]["exists"]:
            raise PartialBaseMissing()
        if len(resource_records) == 1 and resource_records[0]["version"] is None:
            # LEFT JOIN with model_pairs resulted in None row => no new versions
            return []

        type Model = tuple[int, inmanta.types.ResourceSets[dict[str, object]]]
        result: list[Model] = []
        version: int
        records: Iterator[asyncpg.Record]
        for version, records in itertools.groupby(resource_records, key=lambda r: r["version"]):
            spy: Sequence[asyncpg.Record]
            spy, records = more_itertools.spy(records)
            assert spy  # groupby can not produce empty groups
            if spy[0]["empty_model"]:
                result.append((version, {}))
                continue
            resource_set_name: Optional[str]
            model_sets: inmanta.types.ResourceSets[dict[str, object]] = {}
            for resource_set_name, records in itertools.groupby(records, key=lambda r: r["resource_set_name"]):
                model_sets[resource_set_name] = []  # add even if there are no resources, to indicate an empty / deleted set
                spy, records = more_itertools.spy(records)
                assert spy  # groupby can not produce empty groups
                if spy[0]["resource_id"] is None:
                    # left join with resource did not match => empty or deleted resource set
                    continue
                record: asyncpg.Record
                for record in records:
                    model_sets[resource_set_name].append({k: record[k] for k in projection})
            result.append((version, model_sets))
        return result

    @staticmethod
    def get_details_from_resource_id(resource_id: ResourceIdStr) -> m.ResourceIdDetails:
        parsed_id = resources.Id.parse_id(resource_id)
        return m.ResourceIdDetails(
            resource_type=parsed_id.entity_type,
            agent=parsed_id.agent_name,
            attribute=parsed_id.attribute,
            resource_id_value=parsed_id.attribute_value,
        )

    @classmethod
    async def get_resource_for_version(
        cls,
        environment: uuid.UUID,
        resource_id: ResourceIdStr,
        version: int,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> Optional["Resource"]:
        """
        Get a resource with this id for this version
        """
        query = f"""
                SELECT r.*
                FROM {Resource.table_name()} AS r
                INNER JOIN resource_set_configuration_model AS rscm
                    ON r.environment=rscm.environment AND r.resource_set=rscm.resource_set
                WHERE r.environment=$1 AND r.resource_id=$2 AND rscm.model=$3
                """
        records = await cls.select_query(query, [environment, resource_id, version], connection=connection)
        if not records:
            return None
        return records[0]

    @classmethod
    async def get(
        cls,
        environment: uuid.UUID,
        resource_version_id: ResourceVersionIdStr,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> Optional["Resource"]:
        """
        Get a resource with the given resource version id
        """
        parsed_id = resources.Id.parse_id(resource_version_id)
        return await cls.get_resource_for_version(environment, parsed_id.resource_str(), parsed_id.version, connection)

    @classmethod
    def new(
        cls, environment: uuid.UUID, resource_version_id: ResourceVersionIdStr, resource_set: ResourceSet, **kwargs: object
    ) -> "Resource":
        rid = resources.Id.parse_id(resource_version_id)

        attr = dict(
            environment=environment,
            resource_id=rid.resource_str(),
            resource_type=rid.entity_type,
            agent=rid.agent_name,
            resource_id_value=rid.attribute_value,
            resource_set=resource_set.id,
        )

        attr.update(kwargs)

        return cls(**attr)

    @classmethod
    async def get_released_resource_details(
        cls, env: uuid.UUID, resource_id: ResourceIdStr
    ) -> Optional[m.ReleasedResourceDetails]:

        query = f"""
        SELECT DISTINCT ON (resource_id)
            r.resource_id,
            rscm.model AS latest_model,
            r.resource_id as latest_resource_id,
            r.resource_type,
            r.agent,
            r.resource_id_value,
            rps.created as first_generated_time,
            rps.last_handler_run_at as latest_deploy,
            r.attributes,
            {const.SQL_RESOURCE_STATUS_SELECTOR} AS status
        FROM resource AS r
        INNER JOIN resource_set_configuration_model AS rscm
            ON r.environment=rscm.environment AND r.resource_set=rscm.resource_set
        INNER JOIN configurationmodel AS cm
            ON rscm.model=cm.version AND rscm.environment=cm.environment
        INNER JOIN resource_persistent_state AS rps
            ON rps.resource_id=r.resource_id AND r.environment=rps.environment
        WHERE r.environment=$1 AND r.resource_id=$2 AND cm.released
        ORDER BY r.resource_id, rscm.model desc;
        """
        values = [cls._get_value(env), cls._get_value(resource_id)]

        with pyformance.timer("sql.get_released_resource_details.get_first_and_latest").time():
            result = await cls.select_query(query, values, no_obj=True)

        if not result:
            return None
        record = result[0]
        parsed_id = resources.Id.parse_id(record["latest_resource_id"])
        attributes = record["attributes"]
        requires = [resources.Id.parse_id(req).resource_str() for req in attributes["requires"]]

        # fetch the status of each of the requires. This is not calculated in the database because the lack of joinable
        # fields requires to calculate the status for each resource record, before it is filtered
        status_query = f"""
        SELECT rps.resource_id,
        {const.SQL_RESOURCE_STATUS_SELECTOR} AS status
        FROM resource_persistent_state AS rps
        WHERE rps.environment=$1 AND rps.resource_id = ANY($2)
        """

        with pyformance.timer("sql.get_released_resource_details.get_status_of_each_requires").time():
            status_result = await cls.select_query(status_query, [cls._get_value(env), cls._get_value(requires)], no_obj=True)

        return m.ReleasedResourceDetails(
            resource_id=cast(ResourceIdStr, record["latest_resource_id"]),
            resource_type=cast(ResourceType, record["resource_type"]),
            agent=cast(str, record["agent"]),
            id_attribute=cast(str, parsed_id.attribute),
            id_attribute_value=cast(str, record["resource_id_value"]),
            last_deploy=cast(datetime.datetime, record["latest_deploy"]),
            first_generated_time=cast(datetime.datetime, record["first_generated_time"]),
            attributes=cast(JsonType, attributes),
            status=cast(ReleasedResourceState, record["status"]),
            requires_status={
                cast(ResourceIdStr, record["resource_id"]): cast(ReleasedResourceState, record["status"])
                for record in status_result
            },
        )

    @classmethod
    async def get_versioned_resource_details(
        cls, environment: uuid.UUID, version: int, resource_id: ResourceIdStr
    ) -> Optional[m.VersionedResourceDetails]:
        resource = await cls.get_resource_for_version(environment, resource_id, version)
        if not resource:
            return None
        parsed_id = resources.Id.parse_id(resource.resource_id)
        parsed_id.set_version(version)
        return m.VersionedResourceDetails(
            resource_id=resource.resource_id,
            resource_version_id=parsed_id.resource_version_str(),
            resource_type=resource.resource_type,
            agent=resource.agent,
            id_attribute=parsed_id.attribute,
            id_attribute_value=resource.resource_id_value,
            version=version,
            attributes=resource.attributes,
        )

    @classmethod
    async def get_resource_deploy_summary(cls, environment: uuid.UUID) -> m.ResourceDeploySummary:
        inner_query = f"""
        SELECT rps.resource_id as resource_id,
            {const.SQL_RESOURCE_STATUS_SELECTOR} AS status
        FROM resource_persistent_state as rps
        WHERE rps.environment=$1 AND NOT rps.is_orphan
        """

        query = f"""
            SELECT COUNT(ro.resource_id) as count,
                   ro.status
            FROM ({inner_query}) as ro
            GROUP BY ro.status
        """
        raw_results = await cls._fetch_query(query, cls._get_value(environment))
        results = {}
        for row in raw_results:
            results[row["status"]] = row["count"]
        return m.ResourceDeploySummary.create_from_db_result(results)

    @classmethod
    async def get_resources_in_resource_sets_as_dto(
        cls,
        environment: uuid.UUID,
        version: int,
        resource_sets: abc.Set[str],
        include_shared_resources: bool = False,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> abc.Mapping[ResourceIdStr, m.Resource]:
        """
        Returns the resources (in dto format) in the given environment and version
        that belong to any of the given resource sets.
        This method also returns the resources in the share resource set iff the include_shared_resources boolean
        is set to True.
        """
        if include_shared_resources:
            resource_set_filter_statement = "(rs.name IS NULL OR rs.name=ANY($3))"
        else:
            resource_set_filter_statement = "rs.name=ANY($3)"
        query = f"""
            SELECT r.*, rs.name AS resource_set_name
                FROM resource_set_configuration_model AS rscm
                INNER JOIN {ResourceSet.table_name()} AS rs
                    ON rs.environment=rscm.environment
                    AND rs.id=rscm.resource_set
                INNER JOIN {cls.table_name()} AS r
                    ON r.environment=rs.environment
                    AND r.resource_set=rs.id
                WHERE rscm.environment=$1 AND rscm.model=$2
                    AND {resource_set_filter_statement}
        """
        async with cls.get_connection(connection) as con:
            result = await con.fetch(query, environment, version, resource_sets)
            return {record["resource_id"]: m.Resource.from_postgres_record(record) for record in result}

    async def insert(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        self.make_hash()
        await super().insert(connection=connection)

    @classmethod
    async def insert_many(
        cls, documents: Sequence["Resource"], *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        for doc in documents:
            doc.make_hash()
        await super().insert_many(documents, connection=connection)

    async def update(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: object) -> None:
        self.make_hash()
        await super().update(connection=connection, **kwargs)

    async def update_fields(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: object) -> None:
        self.make_hash()
        await super().update_fields(connection=connection, **kwargs)

    def get_requires(self) -> abc.Sequence[ResourceIdStr]:
        """
        Returns the content of the requires field in the attributes.
        """
        if "requires" not in self.attributes:
            return []
        return list(self.attributes["requires"])


@stable_api
class ConfigurationModel(BaseDocument):
    """
    A specific version of the configuration model.

    :param version: The version of the configuration model, represented by a unix timestamp.
    :param environment: The environment this configuration model is defined in
    :param date: The date this configuration model was created
    :param partial_base: If this version was calculated from a partial export, the version the partial was applied on.
    :param released: Is this model released and available for deployment?
    :param deployed: Is this model deployed?
    :param result: The result of the deployment. Success or error.
    :param version_info: Version metadata
    :param total: The total number of resources
    :param is_suitable_for_partial_compiles: This boolean indicates whether the model can later on be updated using a
                                             partial compile. In other words, the value is True iff no cross resource set
                                             dependencies exist between the resources.
    """

    __primary_key__ = ("version", "environment")

    version: int
    environment: uuid.UUID
    date: datetime.datetime | None = None
    partial_base: Optional[int] = None

    pip_config: PipConfig | None = None

    released: bool = False
    version_info: dict[str, object] | None = None
    is_suitable_for_partial_compiles: bool

    total: int = 0

    # cached state for release
    undeployable: list[ResourceIdStr] = []
    skipped_for_undeployable: list[ResourceIdStr] = []

    project_constraints: str | None = None

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

    @classmethod
    def get_valid_field_names(cls) -> list[str]:
        return super().get_valid_field_names() + ["model"]

    @classmethod
    async def create_for_partial_compile(
        cls,
        env_id: uuid.UUID,
        version: int,
        total: int,
        version_info: JsonType | None,
        undeployable: abc.Sequence[ResourceIdStr],
        skipped_for_undeployable: abc.Sequence[ResourceIdStr],
        partial_base: int,
        pip_config: PipConfig | None,
        updated_resource_sets: abc.Set[str],
        deleted_resource_sets: abc.Set[str],
        connection: Connection | None = None,
        project_constraints: str | None = None,
    ) -> "ConfigurationModel":
        """
        Create and insert a new configurationmodel that is the result of a partial compile. The new ConfigurationModel will
        contain all the undeployables and skipped_for_undeployables present in the partial_base version that are not part of
        the partial compile, i.e. not present in rids_in_partial_compile.
        """
        query = f"""
            WITH base_version_exists AS (
                SELECT EXISTS(
                    SELECT 1
                    FROM {cls.table_name()} AS c1
                    WHERE c1.environment=$1 AND c1.version=$8
                ) AS base_version_found
            ),
            resources_in_this_version AS (
                SELECT r.*
                FROM resource_set_configuration_model AS rscm
                INNER JOIN {ResourceSet.table_name()} AS rs
                    ON rscm.environment=rs.environment
                    AND rscm.resource_set=rs.id
                INNER JOIN {Resource.table_name()} AS r
                    ON rs.environment=r.environment
                    AND rs.id=r.resource_set
                WHERE rscm.environment=$1 AND rscm.model=$8
                -- Keep only resources that belong to the shared resource set or a resource set that was not updated
                    AND (rs.name IS NULL OR NOT rs.name=ANY($9))
            ),
            rids_undeployable_base_version AS (
                SELECT t.rid
                FROM (
                    SELECT DISTINCT unnest(c2.undeployable) AS rid
                    FROM {cls.table_name()} AS c2
                    WHERE c2.environment=$1 AND c2.version=$8
                ) AS t(rid)
                WHERE (
                    EXISTS (
                        SELECT 1
                        FROM resources_in_this_version AS r
                        WHERE r.resource_id=t.rid
                    )
                )
            ),
            rids_skipped_for_undeployable_base_version AS (
                SELECT t.rid
                FROM(
                    SELECT DISTINCT unnest(c3.skipped_for_undeployable) AS rid
                    FROM {cls.table_name()} AS c3
                    WHERE c3.environment=$1 AND c3.version=$8
                ) AS t(rid)
                WHERE (
                    EXISTS (
                        SELECT 1
                        FROM resources_in_this_version AS r
                        WHERE r.resource_id=t.rid
                    )
                )
            )
            INSERT INTO {cls.table_name()}(
                environment,
                version,
                date,
                total,
                version_info,
                undeployable,
                skipped_for_undeployable,
                partial_base,
                is_suitable_for_partial_compiles,
                pip_config,
                project_constraints
            ) VALUES(
                $1,
                $2,
                $3,
                $4,
                $5,
                (
                    SELECT coalesce(array_agg(rid), '{{}}')
                    FROM (
                        -- Undeployables in previous version of the model that are not part of the partial compile.
                        (
                            SELECT rid FROM rids_undeployable_base_version AS undepl
                        )
                        UNION
                        -- Undeployables part of the partial compile.
                        (
                            SELECT DISTINCT rid FROM unnest($6::varchar[]) AS undeploy_filtered_new(rid)
                        )
                    ) AS all_undeployable
                ),
                (
                    SELECT coalesce(array_agg(rid), '{{}}')
                    FROM (
                        -- skipped_for_undeployables in previous version of the model that are not part of the partial
                        -- compile.
                        (
                            SELECT skipped.rid FROM rids_skipped_for_undeployable_base_version AS skipped
                        )
                        UNION
                        -- Skipped_for_undeployables part of the partial compile.
                        (
                            SELECT DISTINCT rid FROM unnest($7::varchar[]) AS skipped_filtered_new(rid)
                        )
                    ) AS all_skipped
                ),
                $8,
                True,
                $10::jsonb,
                $11
            )
            RETURNING
                (SELECT base_version_found FROM base_version_exists LIMIT 1) AS base_version_found,
                environment,
                version,
                date,
                total,
                version_info,
                undeployable,
                skipped_for_undeployable,
                partial_base,
                released,
                is_suitable_for_partial_compiles,
                pip_config
        """
        async with cls.get_connection(connection) as con:
            with pyformance.timer("sql.configuration_model.create_for_partial_compile").time():
                result = await con.fetchrow(
                    query,
                    env_id,
                    version,
                    datetime.datetime.now().astimezone(),
                    total,
                    cls._get_value(version_info),
                    undeployable,
                    skipped_for_undeployable,
                    partial_base,
                    updated_resource_sets | deleted_resource_sets,
                    cls._get_value(pip_config),
                    project_constraints,
                )
            # Make mypy happy
            assert result is not None
            if not result["base_version_found"]:
                raise Exception(f"Model with version {partial_base} not found in environment {env_id}")
            fields = {name: val for name, val in result.items() if name != "base_version_found"}
            return cls(from_postgres=True, **fields)

    @classmethod
    async def get_list(
        cls,
        *,
        order_by_column: Optional[str] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: Optional[bool] = None,
        lock: Optional[RowLockMode] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: object,
    ) -> list["ConfigurationModel"]:
        # sanitize and validate order parameters
        if order is None:
            order = "ASC"
        if order_by_column:
            cls._validate_order(order_by_column, order)

        if no_obj is None:
            no_obj = False

        # ensure limit and offset is an integer
        if limit is not None:
            limit = int(limit)
        if offset is not None:
            offset = int(offset)

        filterstr, values = cls._get_composed_filter(col_name_prefix="c", offset=1, **query)
        values = values
        where_statement = f"WHERE {filterstr} " if filterstr else ""
        order_by_statement = f"ORDER BY {order_by_column} {order} " if order_by_column else ""
        limit_statement = f"LIMIT {limit} " if limit is not None and limit > 0 else ""
        offset_statement = f"OFFSET {offset} " if offset is not None and offset > 0 else ""
        lock_statement = f" {lock.value} " if lock is not None else ""
        query_string = f"""SELECT c.*
                    FROM {cls.table_name()} AS c
                    {where_statement}
                    GROUP BY c.environment, c.version
                    {order_by_statement}
                    {limit_statement}
                    {offset_statement}
                    {lock_statement}"""
        query_result = await cls._fetch_query(query_string, *values, connection=connection)
        result = []
        for in_record in query_result:
            record = dict(in_record)
            if no_obj:
                result.append(record)
            else:
                obj = cls(from_postgres=True, **record)
                result.append(obj)
        return result

    @classmethod
    async def version_exists(cls, environment: uuid.UUID, version: int) -> bool:
        query = f"""SELECT 1
                            FROM {ConfigurationModel.table_name()}
                            WHERE environment=$1 AND version=$2"""
        result = await cls._fetchrow(query, cls._get_value(environment), cls._get_value(version))
        if not result:
            return False
        return True

    @classmethod
    async def get_version(
        cls,
        environment: uuid.UUID,
        version: int,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
        lock: Optional[RowLockMode] = None,
    ) -> Optional["ConfigurationModel"]:
        """
        Get a specific version
        """
        result = await cls.get_one(environment=environment, version=version, connection=connection, lock=lock)
        return result

    @classmethod
    async def get_version_internal(
        cls,
        environment: uuid.UUID,
        version: int,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
        lock: Optional[RowLockMode] = None,
    ) -> Optional["ConfigurationModel"]:
        """Return a version, but don't populate the status and done fields, which are expensive to construct"""
        query = f"""SELECT *
                          FROM {ConfigurationModel.table_name()}
                          WHERE environment=$1 AND version=$2 {lock.value};
                          """
        result = await cls.select_query(query, [environment, version], connection=connection)
        if not result:
            return None
        return result[0]

    @classmethod
    async def get_latest_version(
        cls,
        environment: uuid.UUID,
        *,
        connection: Optional[Connection] = None,
    ) -> Optional["ConfigurationModel"]:
        """
        Get the latest released (most recent) version for the given environment
        """
        versions = await cls.get_list(
            order_by_column="version", order="DESC", limit=1, environment=environment, released=True, connection=connection
        )
        if len(versions) == 0:
            return None

        return versions[0]

    @classmethod
    async def get_version_nr_latest_version(
        cls,
        environment: uuid.UUID,
        connection: Optional[Connection] = None,
    ) -> Optional[int]:
        """
        Get the version number of the latest released version in the given environment.
        """
        query = f"""SELECT version
                    FROM {ConfigurationModel.table_name()}
                    WHERE environment=$1 AND released=true
                    ORDER BY version DESC
                    LIMIT 1
                    """
        result = await cls._fetchrow(query, cls._get_value(environment), connection=connection)
        if not result:
            return None
        return int(result["version"])

    @classmethod
    async def get_agents(
        cls, environment: uuid.UUID, version: int, *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> list[str]:
        """
        Returns a list of all agents that have resources defined in this configuration model
        """
        query = f"""
            SELECT DISTINCT agent
            FROM {Resource.table_name()} AS r
            INNER JOIN resource_set_configuration_model AS rscm
                ON r.environment=rscm.environment
                AND r.resource_set=rscm.resource_set
            WHERE r.environment=$1 AND rscm.model=$2
            """
        result = []
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                async for record in con.cursor(query, environment, version):
                    result.append(record["agent"])
        return result

    @classmethod
    async def get_versions(
        cls, environment: uuid.UUID, start: int = 0, limit: int = DBLIMIT, connection: Optional[Connection] = None
    ) -> list["ConfigurationModel"]:
        """
        Get all versions for an environment ordered descending
        """
        versions = await cls.get_list(
            order_by_column="version", order="DESC", limit=limit, offset=start, environment=environment, connection=connection
        )
        return versions

    async def delete_cascade(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        This method doesn't rely on the DELETE CASCADE functionality of PostgreSQL because it causes deadlocks.
        As such, we perform the deletes on each table in a separate transaction.
        """
        async with self.get_connection(connection=connection) as con:
            # Delete of compile record triggers cascading delete report table
            await Compile.delete_all(environment=self.environment, version=self.version, connection=con)
            await DryRun.delete_all(environment=self.environment, model=self.version, connection=con)

            await AgentModules.delete_version(environment=self.environment, model_version=self.version, connection=con)
            await InmantaModule.delete_version(environment=self.environment, model_version=self.version, connection=con)
            await ModuleFiles.delete_version(environment=self.environment, model_version=self.version, connection=con)

            await UnknownParameter.delete_all(environment=self.environment, version=self.version, connection=con)
            await self._execute_query(
                "DELETE FROM public.resourceaction_resource WHERE environment=$1 AND resource_version=$2",
                self.environment,
                self.version,
                connection=con,
            )
            await ResourceAction.delete_all(environment=self.environment, version=self.version, connection=con)
            await ResourceSet.clear_resource_sets_in_version(environment=self.environment, version=self.version, connection=con)
            await self.delete(connection=con)

            # Delete facts when the resources in this version are the only
            await self._execute_query(
                f"""
                DELETE FROM {Parameter.table_name()} p
                WHERE(
                    environment=$1 AND
                    resource_id<>'' AND
                    NOT EXISTS(
                        SELECT 1
                        FROM {Resource.table_name()} r
                        WHERE p.environment=r.environment
                        AND p.resource_id=r.resource_id
                    )
                )
                """,
                self.environment,
                connection=con,
            )

    def get_undeployable(self) -> list[ResourceIdStr]:
        """
        Returns a list of resource ids (NOT resource version ids) of resources with an undeployable state
        """
        return self.undeployable

    def get_skipped_for_undeployable(self) -> list[ResourceIdStr]:
        """
        Returns a list of resource ids (NOT resource version ids)
        of resources which should get a skipped_for_undeployable state
        """
        return self.skipped_for_undeployable

    async def recalculate_total(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Make the total field of this ConfigurationModel in-line with the number
        of resources that are associated with it.
        """
        query = f"""
            UPDATE {self.table_name()} AS c_outer
            SET total=(
                SELECT COUNT(*)
                FROM {self.table_name()} AS c
                INNER JOIN resource_set_configuration_model AS rscm
                    ON c.environment=rscm.environment AND c.version=rscm.model
                INNER JOIN {Resource.table_name()} AS r
                    ON rscm.environment=r.environment AND rscm.resource_set=r.resource_set
                WHERE c.environment=$1 AND c.version=$2
            )
            WHERE c_outer.environment=$1 AND c_outer.version=$2
            RETURNING total
        """
        new_total = await self._fetchval(query, self.environment, self.version, connection=connection)
        if new_total is None:
            raise KeyError(f"Configurationmodel {self.version} in environment {self.environment} was deleted.")
        self.total = new_total


class DryRun(BaseDocument):
    """
    A dryrun of a model version

    :param id: The id of this dryrun
    :param environment: The environment this code belongs to
    :param model: The configuration model
    :param date: The date the run was requested
    :param resource_total: The number of resources that do a dryrun for
    :param resource_todo: The number of resources left to do
    :param resources: Changes for each of the resources in the version
    """

    __primary_key__ = ("id",)

    id: uuid.UUID
    environment: uuid.UUID
    model: int
    date: datetime.datetime
    total: int = 0
    todo: int = 0
    resources: dict[str, object] = {}

    @classmethod
    async def update_resource(cls, dryrun_id: uuid.UUID, resource_id: ResourceVersionIdStr, dryrun_data: JsonType) -> None:
        """
        Register a resource update with a specific query that sets the dryrun_data and decrements the todo counter, only
        if the resource has not been saved yet.
        """
        jsonb_key = uuid.uuid5(dryrun_id, resource_id)
        query = (
            "UPDATE "
            + cls.table_name()
            + " SET todo = todo - 1, resources=jsonb_set(resources, $1::text[], $2) "
            + "WHERE id=$3 and NOT resources ? $4"
        )
        values = [
            cls._get_value([jsonb_key]),
            cls._get_value(dryrun_data),
            cls._get_value(dryrun_id),
            cls._get_value(jsonb_key),
        ]
        await cls._execute_query(query, *values)

    @classmethod
    async def create(cls, environment: uuid.UUID, model: int, total: int, todo: int) -> "DryRun":
        obj = cls(
            environment=environment,
            model=model,
            date=datetime.datetime.now().astimezone(),
            resources={},
            total=total,
            todo=todo,
        )
        await obj.insert()
        return obj

    @classmethod
    async def list_dryruns(
        cls,
        order_by_column: Optional[str] = None,
        order: str = "ASC",
        **query: object,
    ) -> list[m.DryRun]:
        records = await cls.get_list_with_columns(
            order_by_column=order_by_column,
            order=order,
            columns=["id", "environment", "model", "date", "total", "todo"],
            limit=None,
            offset=None,
            no_obj=None,
            connection=None,
            lock=None,
            **query,
        )
        return [
            m.DryRun(
                id=record.id,
                environment=record.environment,
                model=record.model,
                date=record.date,
                total=record.total,
                todo=record.todo,
            )
            for record in records
        ]

    def to_dict(self) -> JsonType:
        dict_result = BaseDocument.to_dict(self)
        resources = {r["id"]: r for r in dict_result["resources"].values()}
        dict_result["resources"] = resources
        return dict_result

    def to_dto(self) -> m.DryRun:
        return m.DryRun(
            id=self.id,
            environment=self.environment,
            model=self.model,
            date=self.date,
            total=self.total,
            todo=self.todo,
        )


class Notification(BaseDocument):
    """
    A notification in an environment

    :param id: The id of this notification
    :param environment: The environment this notification belongs to
    :param created: The date the notification was created at
    :param title: The title of the notification
    :param message: The actual text of the notification
    :param severity: The severity of the notification
    :param uri: A link to an api endpoint of the server, that is relevant to the message,
                and can be used to get further information about the problem.
                For example a compile related problem should have the uri: `/api/v2/compilereport/<compile_id>`
    :param read: Whether the notification was read or not
    :param cleared: Whether the notification was cleared or not
    """

    __primary_key__ = ("id", "environment")

    id: uuid.UUID
    environment: uuid.UUID
    created: datetime.datetime
    title: str
    message: str
    severity: const.NotificationSeverity = const.NotificationSeverity.message
    uri: Optional[str] = None
    compile_id: Optional[uuid.UUID] = None
    read: bool = False
    cleared: bool = False

    @classmethod
    async def clean_up_notifications(cls) -> None:
        default_retention_time = Environment._settings[NOTIFICATION_RETENTION].default
        LOGGER.info("Cleaning up notifications")
        query = f"""
                   WITH non_halted_envs AS (
                       SELECT
                           id,
                           (
                               COALESCE((settings->'settings'->'notification_retention'->>'value')::int, $1)
                           ) AS retention_days
                       FROM {Environment.table_name()}
                       WHERE NOT halted
                   )
                   DELETE FROM {cls.table_name()}
                   USING non_halted_envs
                   WHERE environment = non_halted_envs.id
                       AND created < now() AT TIME ZONE 'UTC' - make_interval(days => non_halted_envs.retention_days)
               """
        await cls._execute_query(query, default_retention_time)

    def to_dto(self) -> m.Notification:
        return m.Notification(
            id=self.id,
            title=self.title,
            message=self.message,
            severity=self.severity,
            created=self.created,
            read=self.read,
            cleared=self.cleared,
            uri=self.uri,
            environment=self.environment,
            compile_id=self.compile_id,
        )


class EnvironmentMetricsGauge(BaseDocument):
    """
    A metric that is of type gauge

    :param environment: the environment to which this metric is related
    :param metric_name: The name of the metric
    :param timestamp: The timestamps at which a new record is created
    :category: The name of the group/category this metric represents (e.g. red if grouped by color).
               __None__ iff metrics of this type are not divided in groups.
    :param count: the counter for the metric for the given timestamp
    """

    environment: uuid.UUID
    metric_name: str
    category: str
    timestamp: datetime.datetime
    count: int

    __primary_key__ = ("environment", "metric_name", "category", "timestamp")


class EnvironmentMetricsTimer(BaseDocument):
    """
    A metric that is type timer

    :param environment: the environment to which this metric is related
    :param metric_name: The name of the metric
    :category: The name of the group/category this metric represents (e.g. red if grouped by color).
               __None__ iff metrics of this type are not divided in groups.
    :param timestamp: The timestamps at which a new record is created
    :param count: the number of occurrences of the monitored event in the interval [previous.timestamp, self.timestamp[
    :param value: the sum of the values of the metric for each occurrence in the interval [previous.timestamp, self.timestamp[
    """

    environment: uuid.UUID
    metric_name: str
    category: str
    timestamp: datetime.datetime
    count: int
    value: float

    __primary_key__ = ("environment", "metric_name", "category", "timestamp")


class User(BaseDocument):
    """A user that can authenticate against inmanta"""

    __primary_key__ = ("id",)

    id: uuid.UUID
    username: str
    password_hash: str
    auth_method: AuthMethod
    is_admin: bool = False

    @classmethod
    def table_name(cls) -> str:
        """
        Return the name of table. we call it inmanta_user to differentiate it from the pg user table.
        """
        return "inmanta_user"

    def to_dao(self) -> m.User:
        return m.User(username=self.username, auth_method=self.auth_method, is_admin=self.is_admin)

    @classmethod
    async def set_is_admin(cls, username: str, is_admin: bool) -> None:
        query = f"UPDATE {cls.table_name()} SET is_admin=$1 WHERE username=$2 RETURNING 1"
        result = await cls._fetch_query(query, is_admin, username)
        if not result:
            # No user exists with the given username
            raise KeyError()

    @classmethod
    async def list_users_with_roles(cls) -> list[m.UserWithRoles]:
        query = f"""
            SELECT
                u.username,
                u.auth_method,
                u.is_admin,
                role_a.environment AS role_environment,
                r.name AS role_name
            FROM {cls.table_name()} AS u
                LEFT JOIN role_assignment AS role_a ON role_a.user_id=u.id
                LEFT JOIN {Role.table_name()} AS r ON r.id=role_a.role_id
            ORDER BY u.username ASC, role_a.environment ASC, r.name ASC
        """
        async with cls.get_connection() as con:
            records = await con.fetch(query)
        result = {}
        for username, group_elem_iterator in itertools.groupby(records, lambda r: r["username"]):
            records_for_group = list(group_elem_iterator)
            roles: dict[uuid.UUID, list[str]] = {}
            for record in records_for_group:
                if record["role_environment"] is not None and record["role_name"] is not None:
                    if record["role_environment"] in roles:
                        roles[record["role_environment"]].append(record["role_name"])
                    else:
                        roles[record["role_environment"]] = [record["role_name"]]
            result[username] = m.UserWithRoles(
                username=records_for_group[0]["username"],
                auth_method=records_for_group[0]["auth_method"],
                is_admin=records_for_group[0]["is_admin"],
                roles=roles,
            )
        return list(result.values())


class RoleStillAssignedException(Exception):
    """
    The role is still assigned to a user.
    """


class CannotAssignRoleException(Exception):
    """
    Role cannot be assigned to user.
    """


class Role(BaseDocument):

    __primary_key__ = ("id", "name")

    id: uuid.UUID
    name: str

    @classmethod
    async def assign_role_to_user(cls, username: str, environment: uuid.UUID, role: str) -> None:
        """
        Assign the given role to the given user.
        """
        assign_role_query = f"""
            INSERT INTO public.role_assignment(user_id, environment, role_id)
            VALUES(
                (SELECT id FROM {User.table_name()} WHERE username=$1),
                $2,
                (SELECT id FROM {cls.table_name()} WHERE name=$3)
            )
        """
        try:
            await cls._execute_query(assign_role_query, username, environment, role)
        except (asyncpg.NotNullViolationError, asyncpg.ForeignKeyViolationError):
            raise CannotAssignRoleException()

    @classmethod
    async def unassign_role_from_user(cls, username: str, environment: uuid.UUID, role: str) -> None:
        """
        Unassign the given role from the given user.
        """
        unassign_role_query = f"""
            DELETE FROM public.role_assignment
            WHERE user_id=(SELECT id FROM {User.table_name()} WHERE username=$1)
                  AND environment=$2
                  AND role_id=(SELECT id FROM {cls.table_name()} WHERE name=$3)
            RETURNING *
        """
        result = await cls._fetchrow(unassign_role_query, username, environment, role)
        if result is None:
            raise KeyError()

    @classmethod
    async def get_roles_for_user(cls, username: str) -> m.RoleAssignmentsPerEnvironment:
        query = f"""
            SELECT ras.environment, rol.name
            FROM {User.table_name()} AS u
                INNER JOIN public.role_assignment AS ras ON u.id=ras.user_id
                INNER JOIN {cls.table_name()} AS rol ON ras.role_id=rol.id
            WHERE u.username=$1
            ORDER BY ras.environment, rol.name
        """
        assignments: dict[uuid.UUID, list[str]] = {}
        for record in await cls._fetch_query(query, username):
            if record["environment"] in assignments:
                assignments[record["environment"]].append(record["name"])
            else:
                assignments[record["environment"]] = [record["name"]]
        return m.RoleAssignmentsPerEnvironment(assignments=assignments)

    @classmethod
    async def ensure_roles(cls, roles: Sequence[str]) -> None:
        """
        Insert the given roles into the role table if they don't exist yet.
        """
        values_str = ",\n".join(f"(${1 + (i * 2)}, ${2 + (i * 2)})" for i in range(len(roles)))
        query = f"""
            INSERT INTO {cls.table_name()}(id, name)
            VALUES {values_str}
            ON CONFLICT DO NOTHING
        """
        value_pairs = [(uuid.uuid4(), role) for role in roles]
        values = list(itertools.chain.from_iterable(value_pairs))
        await cls._execute_query(query, *values)

    @classmethod
    async def delete_role(cls, name: str) -> None:
        query = f"""
           DELETE FROM {cls.table_name()} AS rol
           WHERE name=$1
           returning *
        """
        try:
            result = await cls._fetchrow(query, name)
        except asyncpg.ForeignKeyViolationError:
            # Role is still assigned to a certain user
            raise RoleStillAssignedException()
        else:
            if result is None:
                # Role doesn't exist
                raise KeyError()


class DiscoveredResource(BaseDocument):
    """
    :param environment: the environment of the resource
    :param discovered_resource_id: The id of the resource
    :param discovery_resource_id: The id of the discovery resource responsible for discovering this resource
    :param values: The values associated with the discovered_resource
    """

    environment: uuid.UUID
    discovered_at: datetime.datetime

    discovered_resource_id: ResourceIdStr
    agent: str
    resource_type: ResourceType
    resource_id_value: str

    discovery_resource_id: ResourceIdStr
    values: dict[str, object]

    __primary_key__ = ("environment", "discovered_resource_id")

    def to_dto(self) -> m.DiscoveredResourceOutput:
        return m.DiscoveredResourceOutput(
            discovered_resource_id=self.discovered_resource_id,
            resource_type=self.resource_type,
            agent=self.agent,
            resource_id_value=self.resource_id_value,
            values=self.values,
            discovery_resource_id=self.discovery_resource_id,
        )


class File(BaseDocument):
    content_hash: str
    content: bytes

    @classmethod
    async def has_file_with_hash(cls, content_hash: str) -> bool:
        """
        Return True iff a file exists with the given content_hash.
        """
        query = f"""
            SELECT EXISTS (
                SELECT 1 FROM {cls.table_name()} WHERE content_hash=$1
            )
        """
        result = await cls._fetchval(query, content_hash)
        assert isinstance(result, bool)
        return result

    @classmethod
    async def get_non_existing_files(cls, content_hashes: Iterable[str]) -> set[str]:
        """
        Return a sub-list of content_hashes, with only those hashes that are not present in this database table.
        The returned list will not contain duplicates.
        """
        query = f"""
            SELECT DISTINCT tmp_table.h_content_hash AS content_hash
            FROM (
                SELECT f.content_hash AS f_content_hash, h.content_hash as h_content_hash
                FROM {cls.table_name()} AS f RIGHT OUTER JOIN unnest($1::varchar[]) AS h(content_hash)
                     ON f.content_hash = h.content_hash
            ) as tmp_table
            -- Only keep records for which no matching hash was found in the file table
            WHERE tmp_table.f_content_hash IS NULL
        """
        result = await cls._fetch_query(query, content_hashes)
        return {cast(str, r["content_hash"]) for r in result}


class Scheduler(BaseDocument):
    """
    :param environment: The environment this scheduler belongs to
    :param last_processed_model_version: The latest released model version that was fully processed by the scheduler,
                                         i.e. the in-memory scheduler state was updated correctly and this state was
                                         flushed back to the resource_persistent_state database table, so that it can be
                                         used to recover the scheduler state when the server starts.
    """

    environment: uuid.UUID
    last_processed_model_version: Optional[int]

    __primary_key__ = ("environment",)

    @classmethod
    async def set_last_processed_model_version(
        cls, environment: uuid.UUID, version: int, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        await cls._execute_query(
            f"""
            UPDATE {cls.table_name()}
            SET last_processed_model_version=$1
            WHERE environment=$2
            """,
            version,
            environment,
            connection=connection,
        )


_classes = [
    Project,
    Environment,
    UnknownParameter,
    AgentProcess,
    AgentInstance,
    Agent,
    Resource,
    ResourceAction,
    ResourcePersistentState,
    ResourceSet,
    ConfigurationModel,
    Parameter,
    DryRun,
    Compile,
    Report,
    Notification,
    EnvironmentMetricsGauge,
    EnvironmentMetricsTimer,
    User,
    DiscoveredResource,
    File,
    Scheduler,
    Role,
]

PACKAGE_WITH_UPDATE_FILES = inmanta.db.versions


# Name of core schema in the DB schema verions
# prevent import loop
CORE_SCHEMA_NAME = schema.CORE_SCHEMA_NAME


def set_connection_pool(pool: asyncpg.pool.Pool) -> None:
    BaseDocument.set_connection_pool(pool)


def get_connection_pool() -> asyncpg.pool.Pool:
    assert BaseDocument._connection_pool is not None
    return BaseDocument._connection_pool


async def connect_pool(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    create_db_schema: bool = True,
    connection_pool_min_size: int = 10,
    connection_pool_max_size: int = 10,
    connection_timeout: float = 60,
) -> asyncpg.pool.Pool:

    pool = await asyncpg.create_pool(
        host=host,
        port=port,
        database=database,
        user=username,
        password=password,
        min_size=connection_pool_min_size,
        max_size=connection_pool_max_size,
        timeout=connection_timeout,
        init=asyncpg_on_connect,
    )
    try:
        set_connection_pool(pool)
        if create_db_schema:
            async with pool.acquire() as con:
                await schema.DBSchema(CORE_SCHEMA_NAME, PACKAGE_WITH_UPDATE_FILES, con).ensure_db_schema()
            # expire connections after db schema migration to ensure cache consistency
            await pool.expire_connections()
        return pool
    except Exception as e:
        await disconnect_pool()
        raise e


async def disconnect_pool() -> None:
    LOGGER.debug("Disconnecting connection pool")

    if BaseDocument._connection_pool is None:
        return
    try:
        await asyncio.wait_for(BaseDocument._connection_pool.close(), config.db_connection_timeout.get())
    except asyncio.TimeoutError:
        BaseDocument._connection_pool.terminate()
        LOGGER.exception("A timeout occurred while closing the connection pool to the database")
        raise
    finally:
        BaseDocument.remove_connection_pool()


class ExternalInitAsyncPG(PGDialect_asyncpg):
    """
    Define our own postgres dialect to use in engine initialization. The parent dialect
    reconfigures json serialization/deserialization each time a connection is
    checked out from the pool.

    Overwriting the on_connect method here removes this redundant behaviour. The
    configuration for json serialization is set once when the asyncpg pool is
    created
    """

    def on_connect(self) -> None:
        return None


registry.impls["postgresql.asyncpgnoi"] = lambda: ExternalInitAsyncPG


async def asyncpg_on_connect(connection: asyncpg.Connection) -> None:
    """
    Helper method to configure json serialization/deserialization when
    initializing the database connection pool.
    """

    def _json_decoder(bin_value: bytes) -> object:
        return json.loads(bin_value.decode())

    await connection.set_type_codec(
        "json",
        encoder=str.encode,
        decoder=_json_decoder,
        schema="pg_catalog",
        format="binary",
    )

    def _jsonb_encoder(str_value: str) -> bytes:
        # \x01 is the prefix for jsonb used by PostgreSQL.
        # asyncpg requires it when format='binary'
        return b"\x01" + str_value.encode()

    def _jsonb_decoder(bin_value: bytes) -> object:
        # the byte is the \x01 prefix for jsonb used by PostgreSQL.
        # asyncpg returns it when format='binary'
        return json.loads(bin_value[1:].decode())

    await connection.set_type_codec(
        "jsonb",
        encoder=_jsonb_encoder,
        decoder=_jsonb_decoder,
        schema="pg_catalog",
        format="binary",
    )


async def start_engine(
    *,
    database_username: str,
    database_password: str,
    database_host: str,
    database_port: int,
    database_name: str,
    create_db_schema: bool = False,
    connection_pool_min_size: int = 10,
    connection_pool_max_size: int = 10,
    connection_timeout: float = 60.0,
) -> asyncpg.pool.Pool:
    """
    Start the SQL Alchemy engine for this process.

    We don't delegate pool creation to SQL alchemy (yet?) because at this stage
    we are still using the low level asyncpg connection object to interact with
    the DB in most of the code base.

    We create our own asyncpg pool and configure the SQL alchemy engine to use it.

    To this end, we pass the following arguments to `create_async_engine`:

        * async_creator: tell SQL alchemy how it can acquire new DB connections
            i.e. using pool.acquire()

        * poolclass: use a subclass of NullPool to disable SQL alchemy pool management.
            The _do_return_conn method will make sure the connection is returned back
            into the pool.
    """

    pool = await connect_pool(
        host=database_host,
        port=database_port,
        database=database_name,
        username=database_username,
        password=database_password,
        create_db_schema=create_db_schema,
        connection_pool_min_size=connection_pool_min_size,
        connection_pool_max_size=connection_pool_max_size,
        connection_timeout=connection_timeout,
    )

    url_object = URL.create(
        drivername="postgresql+asyncpgnoi",
        username=database_username,
        password=database_password,
        host=database_host,
        port=database_port,
        database=database_name,
    )

    async def bridge_creator() -> asyncpg.connection.Connection:
        return await pool.acquire()

    class NullerPool(NullPool):
        def _do_return_conn(self, record: ConnectionPoolEntry) -> None:
            assert record.dbapi_connection is not None
            assert isinstance(record.dbapi_connection, AdaptedConnection)
            record.dbapi_connection.run_async(pool.release)

    global ENGINE
    global SESSION_FACTORY

    if ENGINE is not None:
        raise Exception("Engine already running: cannot call start_engine twice.")

    LOGGER.debug("Creating engine...")
    try:
        ENGINE = create_async_engine(url=url_object, pool_pre_ping=True, poolclass=NullerPool, async_creator=bridge_creator)
        SESSION_FACTORY = async_sessionmaker(ENGINE)
    except Exception as e:
        await stop_engine()
        raise e

    return pool


async def stop_engine() -> None:
    """
    Stop the sql alchemy engine and the associated asyncpg connection pool.
    """

    global ENGINE
    global SESSION_FACTORY
    if ENGINE is not None:
        await ENGINE.dispose(close=True)
    ENGINE = None
    SESSION_FACTORY = None

    await disconnect_pool()


def get_engine() -> AsyncEngine:
    assert ENGINE is not None, "SQL Alchemy engine was not initialized"
    return ENGINE


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    assert SESSION_FACTORY is not None, "SQL Alchemy engine and session factory were not initialized"
    return SESSION_FACTORY


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    assert SESSION_FACTORY is not None, "SQL Alchemy engine and session factory were not initialized"
    async with SESSION_FACTORY() as session:
        yield session
