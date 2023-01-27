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
import hashlib
import json
import logging
import re
import typing
import uuid
import warnings
from abc import ABC, abstractmethod
from collections import abc, defaultdict
from configparser import RawConfigParser
from contextlib import AbstractAsyncContextManager
from itertools import chain
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    NewType,
    Optional,
    Pattern,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)
from uuid import UUID

import asyncpg
import dateutil
import pydantic
import pydantic.tools
import typing_inspect
from asyncpg import Connection
from asyncpg.exceptions import SerializationError
from asyncpg.protocol import Record

import inmanta.const as const
import inmanta.db.versions
import inmanta.resources as resources
import inmanta.util as util
from crontab import CronTab
from inmanta.const import DONE_STATES, UNDEPLOYABLE_NAMES, AgentStatus, LogLevel, ResourceState
from inmanta.data import model as m
from inmanta.data import schema
from inmanta.data.model import PagingBoundaries, ResourceIdStr, api_boundary_datetime_normalizer
from inmanta.protocol.common import custom_json_encoder
from inmanta.protocol.exceptions import BadRequest, NotFound
from inmanta.server import config
from inmanta.stable_api import stable_api
from inmanta.types import JsonType, PrimitiveTypes

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
- Code -> ConfigurationModel
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
        super(InvalidQueryType, self).__init__(message)
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

    ROW_EXCLUSIVE: str = "ROW EXCLUSIVE"
    SHARE_UPDATE_EXCLUSIVE: str = "SHARE UPDATE EXCLUSIVE"
    SHARE: str = "SHARE"
    SHARE_ROW_EXCLUSIVE: str = "SHARE ROW EXCLUSIVE"


class RowLockMode(enum.Enum):
    """
    Row level locks as defined in the PostgreSQL docs: https://www.postgresql.org/docs/13/explicit-locking.html#LOCKING-ROWS.
    When acquiring a lock, make sure to use the same locking order accross transactions (as described at the top of this
    module) to prevent deadlocks and to otherwise respect the consistency docs:
    https://www.postgresql.org/docs/13/applevel-consistency.html#NON-SERIALIZABLE-CONSISTENCY.
    """

    FOR_UPDATE: str = "FOR UPDATE"
    FOR_NO_KEY_UPDATE: str = "FOR NO KEY UPDATE"
    FOR_SHARE: str = "FOR SHARE"
    FOR_KEY_SHARE: str = "FOR KEY SHARE"


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


RangeConstraint = list[tuple[RangeOperator, int]]
DateRangeConstraint = list[tuple[RangeOperator, datetime.datetime]]
QueryFilter = Tuple[QueryType, object]


class PagingCounts:
    def __init__(self, total: int, before: int, after: int) -> None:
        self.total = total
        self.before = before
        self.after = after


class InvalidQueryParameter(Exception):
    def __init__(self, message: str) -> None:
        super(InvalidQueryParameter, self).__init__(message)
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

    def __call__(self, entry: object) -> str:
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

    @property
    def db_form(self) -> OrderStr:
        if self == PagingOrder.ASC:
            return OrderStr("ASC NULLS FIRST")
        return OrderStr("DESC NULLS LAST")


class InvalidSort(Exception):
    def __init__(self, message: str, *args: object) -> None:
        super(InvalidSort, self).__init__(message, *args)
        self.message = message


class ColumnType:
    """
    Class encapsulating all handling of specific column types

    This implementation supports the PRIMITIVE_SQL_TYPES types, for more specific behavior, make a subclass.
    """

    def __init__(self, base_type: Type[PRIMITIVE_SQL_TYPES], nullable: bool):
        self.base_type = base_type
        self.nullable = nullable

    def as_basic_filter_elements(self, name: str, value: object) -> Sequence[Tuple[str, "ColumnType", object]]:
        """
        Break down this filter into more elementary filters

        :param name: column name, intended to be passed through get_accessor
        :param value: the value of this column
        :return: a list of (name, type, value) items
        """
        return [(name, self, self.get_value(value))]

    def as_basic_order_elements(self, name: str, order: PagingOrder) -> Sequence[Tuple[str, "ColumnType", PagingOrder]]:
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
            return pydantic.validators.bool_validator(value)
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
        table_prefix_value = "" if table_prefix is None else table_prefix + "."
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


class TablePrefixWrapper(ColumnType):
    def __init__(self, table_name: str, child: ColumnType) -> None:
        self.table_name = table_name
        self.child = child

    @property
    def nullable(self) -> bool:
        return self.child.nullable

    def get_value(self, value: object) -> Optional[PRIMITIVE_SQL_TYPES]:
        return self.child.get_value(value)

    def get_accessor(self, column_name: str, table_prefix: Optional[str] = None) -> str:
        if not table_prefix:
            table_prefix = self.table_name
        return self.child.get_accessor(column_name, table_prefix)

    def coalesce_to_min(self, value_reference: str) -> str:
        return self.child.coalesce_to_min(value_reference)


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


class ResourceVersionIdColumnType(ColumnType):
    def __init__(self) -> None:
        self.nullable = False

    def as_basic_filter_elements(self, name: str, value: object) -> Sequence[Tuple[str, "ColumnType", object]]:
        """
        Break down this filter into more elementary filters

        :param name: column name, intended to be passed through get_accessor
        :param value: the value of this column
        :return: a list of (name, type, value) items
        """
        assert isinstance(value, str)
        id = resources.Id.parse_resource_version_id(value)
        return [
            ("resource_id", StringColumn, StringColumn.get_value(id.resource_str())),
            ("model", PositiveIntColumn, PositiveIntColumn.get_value(id.version)),
        ]

    def as_basic_order_elements(self, name: str, order: PagingOrder) -> Sequence[Tuple[str, "ColumnType", PagingOrder]]:
        """
        Break down this filter into more elementary filters

        :param name: column name, intended to be passed through get_accessor
        :return: a list of (name, type, order) items
        """
        return [("resource_id", StringColumn, order), ("model", PositiveIntColumn, order)]

    def get_value(self, value: object) -> Optional[PRIMITIVE_SQL_TYPES]:
        """
        Prepare the actual value for use as an argument in a prepared statement for this type
        """
        raise NotImplementedError()

    def get_accessor(self, column_name: str, table_prefix: Optional[str] = None) -> str:
        """
        return the sql statement to get this column, as used in filter and other statements
        """
        raise NotImplementedError()

    def coalesce_to_min(self, value_reference: str) -> str:
        """If the order by column is nullable, coalesce the parameter value to the minimum value of the specific type
        This is required for the comparisons used for paging, because comparing a value to
        NULL always yields NULL.
        """
        raise NotImplementedError()


StringColumn = ColumnType(base_type=str, nullable=False)
OptionalStringColumn = ColumnType(base_type=str, nullable=True)

DateTimeColumn = ColumnType(base_type=datetime.datetime, nullable=False)
OptionalDateTimeColumn = ColumnType(base_type=datetime.datetime, nullable=True)

PositiveIntColumn = ColumnType(base_type=int, nullable=False)
# Negatives ints require updating coalesce_to_min

TextColumn = ForcedStringColumn("text")

UUIDColumn = ColumnType(base_type=uuid.UUID, nullable=False)
BoolColumn = ColumnType(base_type=bool, nullable=False)
ResourceVersionIdColumn = ResourceVersionIdColumnType()


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
    ) -> Tuple[List[str], List[object]]:
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
        pass

    @abstractmethod
    def get_order_by_statement(self, invert: bool = False, table: Optional[str] = None) -> str:
        """Get this order as an order_by statement"""
        pass

    @abstractmethod
    def get_order(self) -> PagingOrder:
        """Return the order of this paging request"""
        pass

    @abstractmethod
    def get_paging_boundaries(self, first: abc.Mapping[str, object], last: abc.Mapping[str, object]) -> PagingBoundaries:
        """Return the page boundaries, given the first and last record of the page"""
        pass


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
    def get_valid_sort_columns(cls) -> Dict[ColumnNameStr, ColumnType]:
        """Return all valid columns for lookup and their type"""
        raise NotImplementedError()

    #  Factory
    @classmethod
    def parse_from_string(
        cls: Type[T_SELF],
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
    ) -> Tuple[List[str], List[object]]:
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
            (f"{type.get_accessor(col, table)} {order.db_form}" for col, type, order in self.get_order_elements(invert))
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
    def id_column(self) -> Tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        pass

    # External API
    def as_filter(
        self,
        offset: int,
        column_value: Optional[PRIMITIVE_SQL_TYPES] = None,
        id_value: Optional[PRIMITIVE_SQL_TYPES] = None,
        start: bool = True,
    ) -> Tuple[List[str], List[object]]:
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
    def get_valid_sort_columns(cls) -> Dict[ColumnNameStr, ColumnType]:
        return {
            ColumnNameStr("resource_type"): StringColumn,
            ColumnNameStr("agent"): StringColumn,
            ColumnNameStr("resource_id_value"): StringColumn,
        }

    @property
    def id_column(self) -> Tuple[ColumnNameStr, ColumnType]:
        """Name of the id column of this database order"""
        return ColumnNameStr("resource_id"), StringColumn


class ResourceOrder(VersionedResourceOrder):
    """Represents the ordering by which resources should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[ColumnNameStr, ColumnType]:
        return {
            ColumnNameStr("resource_type"): StringColumn,
            ColumnNameStr("agent"): StringColumn,
            ColumnNameStr("resource_id"): StringColumn,
            ColumnNameStr("resource_id_value"): StringColumn,
            ColumnNameStr("status"): TextColumn,
        }

    @property
    def id_column(self) -> Tuple[ColumnNameStr, ColumnType]:
        """Name of the id column of this database order"""
        return ColumnNameStr("resource_version_id"), ResourceVersionIdColumn

    def get_paging_boundaries(self, first: abc.Mapping[str, object], last: abc.Mapping[str, object]) -> PagingBoundaries:
        if self.get_order() == PagingOrder.ASC:
            first, last = last, first

        order_column_name = self.order_by_column
        order_type: ColumnType = self.get_order_by_column_type()

        def make_id(record: abc.Mapping[str, object]) -> str:
            resource_id = record["resource_id"]
            assert isinstance(resource_id, str)
            model = record["model"]
            return resource_id + ",v=" + str(model)

        return PagingBoundaries(
            start=order_type.get_value(first[order_column_name]),
            first_id=make_id(first),
            end=order_type.get_value(last[order_column_name]),
            last_id=make_id(last),
        )


class ResourceHistoryOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which resource history should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[ColumnNameStr, ColumnType]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder"""
        return {ColumnNameStr("date"): DateTimeColumn}

    @property
    def id_column(self) -> Tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("attribute_hash"), StringColumn)


class ResourceLogOrder(SingleDatabaseOrder):
    """Represents the ordering by which resource logs should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[ColumnNameStr, ColumnType]:
        return {
            ColumnNameStr("timestamp"): DateTimeColumn,
        }


class CompileReportOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which compile reports should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[ColumnNameStr, ColumnType]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder"""
        return {ColumnNameStr("requested"): DateTimeColumn}

    @property
    def id_column(self) -> Tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("id"), UUIDColumn)


class AgentOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which agents should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[ColumnNameStr, ColumnType]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder"""
        return {
            ColumnNameStr("name"): TablePrefixWrapper("a", StringColumn),
            ColumnNameStr("process_name"): OptionalStringColumn,
            ColumnNameStr("paused"): BoolColumn,
            ColumnNameStr("last_failover"): OptionalDateTimeColumn,
            ColumnNameStr("status"): StringColumn,
        }

    @property
    def id_column(self) -> Tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("name"), TablePrefixWrapper("a", StringColumn))


class DesiredStateVersionOrder(SingleDatabaseOrder):
    """Represents the ordering by which desired state versions should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[ColumnNameStr, ColumnType]:
        return {
            ColumnNameStr("version"): PositiveIntColumn,
        }


class ParameterOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which parameters should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[ColumnNameStr, ColumnType]:
        return {
            ColumnNameStr("name"): StringColumn,
            ColumnNameStr("source"): StringColumn,
            ColumnNameStr("updated"): OptionalDateTimeColumn,
        }

    @property
    def id_column(self) -> Tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("id"), UUIDColumn)


class FactOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which facts should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[ColumnNameStr, ColumnType]:
        return {
            ColumnNameStr("name"): StringColumn,
            ColumnNameStr("resource_id"): StringColumn,
        }

    @property
    def id_column(self) -> Tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("id"), UUIDColumn)


class NotificationOrder(AbstractDatabaseOrderV2):
    """Represents the ordering by which notifications should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[ColumnNameStr, ColumnType]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder"""
        return {
            ColumnNameStr("created"): DateTimeColumn,
        }

    @property
    def id_column(self) -> Tuple[ColumnNameStr, ColumnType]:
        """Name and type of the id column of this database order"""
        return (ColumnNameStr("id"), UUIDColumn)


class BaseQueryBuilder(ABC):
    """Provides a way to build up a sql query from its parts.
    Each method returns a new query builder instance, with the additional parameters processed"""

    def __init__(
        self,
        select_clause: Optional[str] = None,
        from_clause: Optional[str] = None,
        filter_statements: Optional[List[str]] = None,
        values: Optional[List[object]] = None,
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

    def _join_filter_statements(self, filter_statements: List[str]) -> str:
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
    def filter(self, filter_statements: List[str], values: List[object]) -> "BaseQueryBuilder":
        """Add filters to the query"""
        raise NotImplementedError()

    @abstractmethod
    def build(self) -> Tuple[str, List[object]]:
        """Builds up the full query string, and the parametrized value list, ready to be executed"""
        raise NotImplementedError()


class SimpleQueryBuilder(BaseQueryBuilder):
    """A query builder suitable for most queries"""

    def __init__(
        self,
        select_clause: Optional[str] = None,
        from_clause: Optional[str] = None,
        filter_statements: Optional[List[str]] = None,
        values: Optional[List[object]] = None,
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

    def filter(self, filter_statements: List[str], values: List[object]) -> "SimpleQueryBuilder":
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

    def build(self) -> Tuple[str, List[object]]:
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
        field_type: Type[T],
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

    def get_field_type(self) -> Type[T]:
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
        if not (value.__class__ is self.field_type or isinstance(value, self.field_type)):
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
            if not isinstance(value, List):
                TypeError("Field %s should be a list, but got %s" % (name, type(value).__name__))
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
            if not isinstance(value, List):
                TypeError("Field %s should be a list, but got %s" % (name, type(value).__name__))
            else:
                return [self._from_db_single(name, v) for v in value]
        return self._from_db_single(name, value)

    def _from_db_single(self, name: str, value: object) -> object:
        """Load a single database value. Converts database representation to appropriately typed object."""
        if value.__class__ is self.field_type or isinstance(value, self.field_type):
            return value

        # asyncpg does not convert a jsonb field to a dict
        if isinstance(value, str) and self.field_type is dict:
            return json.loads(value)
        # asyncpg does not convert an enum field to an enum type
        if isinstance(value, str) and issubclass(self.field_type, enum.Enum):
            return self.field_type[value]
        # decode typed json
        if isinstance(value, str) and issubclass(self.field_type, pydantic.BaseModel):
            jsv = json.loads(value)
            return self.field_type(**jsv)
        if self.field_type == pydantic.AnyHttpUrl:
            return pydantic.tools.parse_obj_as(pydantic.AnyHttpUrl, value)

        raise TypeError(
            "Field %s should have the correct type (%s instead of %s)" % (name, self.field_type.__name__, type(value).__name__)
        )


class DataDocument(object):
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
    def __new__(cls, class_name: str, bases: Tuple[type, ...], dct: Dict[str, object]) -> Type:
        dct["_fields_metadata"] = {}
        new_type: Type[BaseDocument] = type.__new__(cls, class_name, bases, dct)
        if class_name != "BaseDocument":
            new_type.load_fields()
        return new_type


TBaseDocument = TypeVar("TBaseDocument", bound="BaseDocument")  # Part of the stable API
TransactionResult = TypeVar("TransactionResult")


@stable_api
class BaseDocument(object, metaclass=DocumentMeta):
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
    _fields_metadata: Dict[str, Field]
    __primary_key__: Tuple[str, ...]
    __ignore_fields__: Tuple[str, ...]

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
        # Make pypi happy
        assert cls._connection_pool is not None
        return cls._connection_pool.acquire()

    @classmethod
    def table_name(cls) -> str:
        """
        Return the name of the collection
        """
        return cls.__name__.lower()

    @classmethod
    def get_field_metadata(cls) -> Dict[str, Field]:
        return cls._fields_metadata.copy()

    @staticmethod
    def _annotation_to_field(
        attribute: str,
        annotation: Type[object],
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
        field_type: Type[object] = annotation
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
            if orig in [typing.List, typing.Sequence, list, abc.Sequence]:
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

            elif orig in [typing.Mapping, typing.Dict, abc.Mapping, dict]:
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
        primary_key: Tuple[str, ...] = tuple()
        ignore: Tuple[str, ...] = tuple()
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

    def __process_kwargs(self, from_postgres: bool, kwargs: Dict[str, object]) -> None:
        """This helper method process the kwargs provided to the constructor and populates the fields of the object."""
        fields = self.get_field_metadata()

        if "id" in fields and "id" not in kwargs:
            kwargs["id"] = uuid.uuid4()

        for name, value in kwargs.items():
            if name not in fields:
                raise AttributeError("%s field is not defined for this document %s" % (name, type(self).__name__.lower()))

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
    def get_valid_field_names(cls) -> List[str]:
        return list(cls.get_field_names())

    @classmethod
    def _get_names_of_primary_key_fields(cls) -> List[str]:
        return [name for name, value in cls.get_field_metadata().items() if value.is_part_of_primary_key()]

    def _get_filter_on_primary_key_fields(self, offset: int = 1) -> Tuple[str, List[Any]]:
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
            raise Exception(f"Connection already set on {cls} ({cls._connection_pool}!")
        cls._connection_pool = pool

    @classmethod
    async def close_connection_pool(cls) -> None:
        if not cls._connection_pool:
            return
        try:
            await asyncio.wait_for(cls._connection_pool.close(), config.db_connection_timeout.get())
        except asyncio.TimeoutError:
            cls._connection_pool.terminate()
            # Don't propagate this exception but just write a log message. This way:
            #   * A timeout here still makes sure that the other server slices get stopped
            #   * The tests don't fail when this timeout occurs
            LOGGER.exception("A timeout occurred while closing the connection pool to the database")
        except asyncio.CancelledError:
            cls._connection_pool.terminate()
            # Propagate cancel
            raise
        except Exception:
            LOGGER.exception("An unexpected exception occurred while closing the connection pool to the database")
            raise
        finally:
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
    def _convert_field_names_to_db_column_names(cls, field_dict: Dict[str, Any]) -> Dict[str, Any]:
        return field_dict

    def get_value(self, name: str, default_value: Optional[object] = None) -> object:
        """Check if a value is set for a field. Fields that are declared but that do not have a value are only present
        in annotations but not as attribute (in __dict__)"""
        if hasattr(self, name):
            return getattr(self, name)
        return default_value

    def _get_column_names_and_values(self) -> Tuple[List[str], List[object]]:
        column_names: List[str] = []
        values: List[object] = []
        for name, metadata in self.get_field_metadata().items():
            if metadata.ignore:
                continue

            value = self.get_value(name)

            if metadata.required and value is None:
                raise TypeError("%s should have field '%s'" % (self.__name__, name))

            metadata.validate(name, value)
            column_names.append(name)
            values.append(self._get_value(value))

        return column_names, values

    async def insert(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Insert a new document based on the instance passed. Validation is done based on the defined fields.
        """
        (column_names, values) = self._get_column_names_and_values()
        column_names_as_sql_string = ",".join(column_names)
        values_as_parameterize_sql_string = ",".join(["$" + str(i) for i in range(1, len(values) + 1)])
        query = f"INSERT INTO {self.table_name()} ({column_names_as_sql_string}) VALUES ({values_as_parameterize_sql_string})"
        await self._execute_query(query, *values, connection=connection)

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
            await con.copy_records_to_table(table_name=cls.table_name(), columns=columns, records=records)

    def add_default_values_when_undefined(self, **kwargs: object) -> Dict[str, object]:
        result = dict(kwargs)
        for name, field in self._fields.items():
            if name not in kwargs:
                default_value = field.default_value
                result[name] = default_value
        return result

    async def update(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: Any) -> None:
        """
        Update this document in the database. It will update the fields in this object and send a full update to database.
        Use update_fields to only update specific fields.
        """
        kwargs = self._convert_field_names_to_db_column_names(kwargs)
        for name, value in kwargs.items():
            setattr(self, name, value)
        (column_names, values) = self._get_column_names_and_values()
        values_as_parameterize_sql_string = ",".join([column_names[i - 1] + "=$" + str(i) for i in range(1, len(values) + 1)])
        (filter_statement, values_for_filter) = self._get_filter_on_primary_key_fields(offset=len(column_names) + 1)
        values = values + values_for_filter
        query = "UPDATE " + self.table_name() + " SET " + values_as_parameterize_sql_string + " WHERE " + filter_statement
        await self._execute_query(query, *values, connection=connection)

    def _get_set_statement(self, **kwargs: object) -> Tuple[str, List[object]]:
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
        (set_statement, values_set_statement) = self._get_set_statement(**kwargs)
        (filter_statement, values_for_filter) = self._get_filter_on_primary_key_fields(offset=len(kwargs) + 1)
        values = values_set_statement + values_for_filter
        query = "UPDATE " + self.table_name() + " SET " + set_statement + " WHERE " + filter_statement
        await self._execute_query(query, *values, connection=connection)

    @classmethod
    async def get_by_id(
        cls: Type[TBaseDocument], doc_id: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None
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
        cls: Type[TBaseDocument],
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
    def _validate_order(cls, order_by_column: str, order: str) -> Tuple[ColumnNameStr, OrderStr]:
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
    def _validate_order_strict(cls, order_by_column: str, order: str) -> Tuple[ColumnNameStr, PagingOrder]:
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
        cls: Type[TBaseDocument],
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
    ) -> List[TBaseDocument]:
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
        cls: Type[TBaseDocument],
        *,
        order_by_column: Optional[str] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: Optional[bool] = None,
        lock: Optional[RowLockMode] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        columns: Optional[List[str]] = None,
        **query: object,
    ) -> List[TBaseDocument]:
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
        (filter_statement, values) = cls._get_composed_filter(**query)
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
        cls: Type[TBaseDocument],
        *,
        page_by_column: str,
        order_by_column: Optional[str] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        start: Optional[Any] = None,
        end: Optional[Any] = None,
        no_obj: Optional[bool] = None,
        lock: Optional[RowLockMode] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: object,
    ) -> List[TBaseDocument]:
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
        (filter_statement, values) = cls._get_composed_filter(**query)
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
        (filter_statement, values) = cls._get_composed_filter(**query)
        query = "DELETE FROM " + cls.table_name()
        if filter_statement:
            query += " WHERE " + filter_statement
        result = await cls._execute_query(query, *values, connection=connection)
        record_count = int(result.split(" ")[1])
        return record_count

    @classmethod
    def _get_composed_filter(
        cls, offset: int = 1, col_name_prefix: Optional[str] = None, **query: object
    ) -> Tuple[str, List[object]]:
        filter_statements = []
        values = []
        index_count = max(1, offset)
        for key, value in query.items():
            cls.validate_field_name(key)
            name = cls._add_column_name_prefix_if_needed(key, col_name_prefix)
            (filter_statement, value) = cls._get_filter(name, value, index_count)
            filter_statements.append(filter_statement)
            values.extend(value)
            index_count += len(value)
        filter_as_string = " AND ".join(filter_statements)
        return (filter_as_string, values)

    @classmethod
    def _get_filter(cls, name: str, value: Any, index: int) -> Tuple[str, List[object]]:
        if value is None:
            return (name + " IS NULL", [])
        filter_statement = name + "=$" + str(index)
        value = cls._get_value(value)
        return (filter_statement, [value])

    @classmethod
    def _get_value(cls, value: object) -> object:
        if isinstance(value, dict):
            return json_encode(value)

        if isinstance(value, DataDocument) or issubclass(value.__class__, DataDocument):
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
    ) -> Tuple[List[str], List[object]]:
        filter_statements = []
        values: List[object] = []
        index_count = max(1, offset)
        for key, value_with_query_type in query.items():
            query_type, value = value_with_query_type
            filter_statement: str
            filter_values: List[object]
            name = cls._add_column_name_prefix_if_needed(key, col_name_prefix)
            filter_statement, filter_values = cls.get_filter_for_query_type(query_type, name, value, index_count)
            filter_statements.append(filter_statement)
            values.extend(filter_values)
            index_count += len(filter_values)

        return (filter_statements, values)

    @classmethod
    def get_filter_for_query_type(
        cls, query_type: QueryType, key: str, value: object, index_count: int
    ) -> Tuple[str, List[object]]:
        if query_type == QueryType.EQUALS:
            (filter_statement, filter_values) = cls._get_filter(key, value, index_count)
        elif query_type == QueryType.IS_NOT_NULL:
            (filter_statement, filter_values) = cls.get_is_not_null_filter(key)
        elif query_type == QueryType.CONTAINS:
            (filter_statement, filter_values) = cls.get_contains_filter(key, value, index_count)
        elif query_type == QueryType.CONTAINS_PARTIAL:
            (filter_statement, filter_values) = cls.get_contains_partial_filter(key, value, index_count)
        elif query_type == QueryType.RANGE:
            (filter_statement, filter_values) = cls.get_range_filter(key, value, index_count)
        elif query_type == QueryType.NOT_CONTAINS:
            (filter_statement, filter_values) = cls.get_not_contains_filter(key, value, index_count)
        elif query_type == QueryType.COMBINED:
            (filter_statement, filter_values) = cls.get_filter_for_combined_query_type(
                key, cast(Dict[QueryType, object], value), index_count
            )
        else:
            raise InvalidQueryType(f"Query type should be one of {[query for query in QueryType]}")
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
    def get_is_not_null_filter(cls, name: str) -> Tuple[str, List[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that are not null.
        """
        filter_statement = f"{name} IS NOT NULL"
        return (filter_statement, [])

    @classmethod
    def get_contains_filter(cls, name: str, value: object, index: int) -> Tuple[str, List[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that are contained in a given
        collection.
        """
        filter_statement = f"{name} = ANY (${str(index)})"
        value = cls._get_value(value)
        return (filter_statement, [value])

    @classmethod
    def get_filter_for_combined_query_type(
        cls, name: str, combined_value: Dict[QueryType, object], index: int
    ) -> Tuple[str, List[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter a single column
        based on the defined query types
        """
        filters = []
        for query_type, value in combined_value.items():
            filter_statement, filter_values = cls.get_filter_for_query_type(query_type, name, value, index)
            filters.append((filter_statement, filter_values))
            index += len(filter_values)
        (filter_statement, values) = cls._combine_filter_statements(filters)

        return (filter_statement, values)

    @classmethod
    def get_not_contains_filter(cls, name: str, value: object, index: int) -> Tuple[str, List[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that are not contained in a given
        collection.
        """
        filter_statement = f"NOT ({name} = ANY (${str(index)}))"
        value = cls._get_value(value)
        return (filter_statement, [value])

    @classmethod
    def get_contains_partial_filter(cls, name: str, value: object, index: int) -> Tuple[str, List[object]]:
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
    ) -> Tuple[str, List[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that match a given range
        constraint.
        """
        filter_statement: str
        values: List[object]
        (filter_statement, values) = cls._combine_filter_statements(
            (
                f"{name} {operator.pg_value} ${str(index + i)}",
                [cls._get_value(bound)],
            )
            for i, (operator, bound) in enumerate(value)
        )
        return (filter_statement, [cls._get_value(v) for v in values])

    @staticmethod
    def _combine_filter_statements(statements_and_values: Iterable[Tuple[str, List[object]]]) -> Tuple[str, List[object]]:
        statements: Tuple[str]
        values: Tuple[List[object]]
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
        start: Optional[Any] = None,
        first_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> Tuple[List[str], List[object]]:
        filter_statements = []
        values: List[object] = []
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
        end: Optional[Any] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> Tuple[List[str], List[object]]:
        filter_statements = []
        values: List[object] = []
        if end is not None and last_id:
            filter_statements.append(f"({order_by_column}, {id_column}) < (${str(offset + 1)}, ${str(offset + 2)})")
            values.append(cls._get_value(end))
            values.append(cls._get_value(last_id))
        elif end is not None:
            filter_statements.append(f"{order_by_column} < ${str(offset + 1)}")
            values.append(cls._get_value(end))
        return filter_statements, values

    @classmethod
    def _join_filter_statements(cls, filter_statements: List[str]) -> str:
        if filter_statements:
            return "WHERE " + " AND ".join(filter_statements)
        return ""

    async def delete(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Delete this document
        """
        (filter_as_string, values) = self._get_filter_on_primary_key_fields()
        query = "DELETE FROM " + self.table_name() + " WHERE " + filter_as_string
        await self._execute_query(query, *values, connection=connection)

    async def delete_cascade(self) -> None:
        await self.delete()

    @classmethod
    @overload
    async def select_query(
        cls: Type[TBaseDocument], query: str, values: List[object], connection: Optional[asyncpg.connection.Connection] = None
    ) -> Sequence[TBaseDocument]:
        """Return a sequence of objects of cls type."""
        ...

    @classmethod
    @overload
    async def select_query(
        cls: Type[TBaseDocument],
        query: str,
        values: List[object],
        no_obj: bool,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> Sequence[Record]:
        """Return a sequence of records instances"""
        ...

    @classmethod
    async def select_query(
        cls: Type[TBaseDocument],
        query: str,
        values: List[object],
        no_obj: bool = False,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> Sequence[Union[Record, TBaseDocument]]:
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                result: List[Union[Record, TBaseDocument]] = []
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
                raise TypeError("%s should have field '%s'" % (self.__name__, name))

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


def convert_agent_map(value: Dict[str, str]) -> Dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("Agent map should be a dict")

    for key, v in value.items():
        if not isinstance(key, str):
            raise ValueError("The key of an agent map should be string")

        if not isinstance(v, str):
            raise ValueError("The value of an agent map should be string")

    if "internal" not in value:
        raise ValueError("The internal agent must be present in the autostart_agent_map")

    return value


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
        raise ValueError("%s is not a valid agent trigger method. Valid value: %s" % (value, ",".join(valid_values)))
    return value


def validate_cron(value: str) -> str:
    if not value:
        return ""
    try:
        CronTab(value)
    except ValueError as e:
        raise ValueError("'%s' is not a valid cron expression: %s" % (value, e))
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
PUSH_ON_AUTO_DEPLOY = "push_on_auto_deploy"
AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY = "agent_trigger_method_on_auto_deploy"
ENVIRONMENT_AGENT_TRIGGER_METHOD = "environment_agent_trigger_method"
AUTOSTART_SPLAY = "autostart_splay"
AUTOSTART_AGENT_DEPLOY_INTERVAL = "autostart_agent_deploy_interval"
AUTOSTART_AGENT_DEPLOY_SPLAY_TIME = "autostart_agent_deploy_splay_time"
AUTOSTART_AGENT_REPAIR_INTERVAL = "autostart_agent_repair_interval"
AUTOSTART_AGENT_REPAIR_SPLAY_TIME = "autostart_agent_repair_splay_time"
AUTOSTART_ON_START = "autostart_on_start"
AUTOSTART_AGENT_MAP = "autostart_agent_map"
AUTOSTART_AGENT_INTERVAL = "autostart_agent_interval"
AGENT_AUTH = "agent_auth"
SERVER_COMPILE = "server_compile"
AUTO_FULL_COMPILE = "auto_full_compile"
RESOURCE_ACTION_LOGS_RETENTION = "resource_action_logs_retention"
PURGE_ON_DELETE = "purge_on_delete"
PROTECTED_ENVIRONMENT = "protected_environment"
NOTIFICATION_RETENTION = "notification_retention"
AVAILABLE_VERSIONS_TO_KEEP = "available_versions_to_keep"
RECOMPILE_BACKOFF = "recompile_backoff"
ENVIRONMENT_METRICS_RETENTION = "environment_metrics_retention"


class Setting(object):
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
        allowed_values: Optional[List[m.EnvSettingType]] = None,
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
        """
        self.name: str = name
        self.typ: str = typ
        self.default = default
        self.doc = doc
        self.validator = validator
        self.recompile = recompile
        self.update = update_model
        self.agent_restart = agent_restart
        self.allowed_values = allowed_values

    def to_dict(self) -> JsonType:
        return {
            "type": self.typ,
            "default": self.default,
            "doc": self.doc,
            "recompile": self.recompile,
            "update": self.update,
            "agent_restart": self.agent_restart,
            "allowed_values": self.allowed_values,
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
        )


@stable_api
class Environment(BaseDocument):
    """
    A deployment environment of a project

    :param id: A unique, machine generated id
    :param name: The name of the deployment environment.
    :param project: The project this environment belongs to.
    :param repo_url: The repository url that contains the configuration model code for this environment
    :param repo_branch: The repository branch that contains the configuration model code for this environment
    :param settings: Key/value settings for this environment
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
    settings: Dict[str, m.EnvSettingType] = {}
    last_version: int = 0
    halted: bool = False
    description: str = ""
    icon: str = ""

    def to_dto(self) -> m.Environment:
        return m.Environment(
            id=self.id,
            name=self.name,
            project_id=self.project,
            repo_url=self.repo_url,
            repo_branch=self.repo_branch,
            settings=self.settings,
            halted=self.halted,
            description=self.description,
            icon=self.icon,
        )

    _settings: Dict[str, Setting] = {
        AUTO_DEPLOY: Setting(
            name=AUTO_DEPLOY,
            typ="bool",
            default=True,
            doc="When this boolean is set to true, the orchestrator will automatically release a new version "
            "that was compiled by the orchestrator itself.",
            validator=convert_boolean,
        ),
        PUSH_ON_AUTO_DEPLOY: Setting(
            name=PUSH_ON_AUTO_DEPLOY,
            typ="bool",
            default=True,
            doc="Push a new version when it has been autodeployed.",
            validator=convert_boolean,
        ),
        AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY: Setting(
            name=AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY,
            typ="enum",
            default=const.AgentTriggerMethod.push_incremental_deploy.name,
            validator=convert_agent_trigger_method,
            doc="The agent trigger method to use when " + PUSH_ON_AUTO_DEPLOY + " is enabled",
            allowed_values=[opt.name for opt in const.AgentTriggerMethod],
        ),
        ENVIRONMENT_AGENT_TRIGGER_METHOD: Setting(
            name=ENVIRONMENT_AGENT_TRIGGER_METHOD,
            typ="enum",
            default=const.AgentTriggerMethod.push_full_deploy.name,
            validator=convert_agent_trigger_method,
            doc="The agent trigger method to use. "
            f"If {PUSH_ON_AUTO_DEPLOY} is enabled, "
            f"{AGENT_TRIGGER_METHOD_ON_AUTO_DEPLOY} overrides this setting",
            allowed_values=[opt.name for opt in const.AgentTriggerMethod],
        ),
        AUTOSTART_SPLAY: Setting(
            name=AUTOSTART_SPLAY,
            typ="int",
            default=10,
            doc="[DEPRECATED] Splay time for autostarted agents.",
            validator=convert_int,
        ),
        AUTOSTART_AGENT_DEPLOY_INTERVAL: Setting(
            name=AUTOSTART_AGENT_DEPLOY_INTERVAL,
            typ="int",
            default=600,
            doc="The deployment interval of the autostarted agents."
            " See also: :inmanta.config:option:`config.agent-deploy-interval`",
            validator=convert_int,
            agent_restart=True,
        ),
        AUTOSTART_AGENT_DEPLOY_SPLAY_TIME: Setting(
            name=AUTOSTART_AGENT_DEPLOY_SPLAY_TIME,
            typ="int",
            default=10,
            doc="The splay time on the deployment interval of the autostarted agents."
            " See also: :inmanta.config:option:`config.agent-deploy-splay-time`",
            validator=convert_int,
            agent_restart=True,
        ),
        AUTOSTART_AGENT_REPAIR_INTERVAL: Setting(
            name=AUTOSTART_AGENT_REPAIR_INTERVAL,
            typ="int",
            default=86400,
            doc="The repair interval of the autostarted agents."
            " See also: :inmanta.config:option:`config.agent-repair-interval`",
            validator=convert_int,
            agent_restart=True,
        ),
        AUTOSTART_AGENT_REPAIR_SPLAY_TIME: Setting(
            name=AUTOSTART_AGENT_REPAIR_SPLAY_TIME,
            typ="int",
            default=600,
            doc="The splay time on the repair interval of the autostarted agents."
            " See also: :inmanta.config:option:`config.agent-repair-splay-time`",
            validator=convert_int,
            agent_restart=True,
        ),
        AUTOSTART_ON_START: Setting(
            name=AUTOSTART_ON_START,
            default=True,
            typ="bool",
            validator=convert_boolean,
            doc="Automatically start agents when the server starts instead of only just in time.",
        ),
        AUTOSTART_AGENT_MAP: Setting(
            name=AUTOSTART_AGENT_MAP,
            default={"internal": "local:"},
            typ="dict",
            validator=convert_agent_map,
            doc="A dict with key the name of agents that should be automatically started. The value "
            "is either an empty string or an agent map string. See also: :inmanta.config:option:`config.agent-map`",
            agent_restart=True,
        ),
        AUTOSTART_AGENT_INTERVAL: Setting(
            name=AUTOSTART_AGENT_INTERVAL,
            default=600,
            typ="int",
            validator=convert_int,
            doc="[DEPRECATED] Agent interval for autostarted agents in seconds",
            agent_restart=True,
        ),
        SERVER_COMPILE: Setting(
            name=SERVER_COMPILE,
            default=True,
            typ="bool",
            validator=convert_boolean,
            doc="Allow the server to compile the configuration model.",
        ),
        AUTO_FULL_COMPILE: Setting(
            name=AUTO_FULL_COMPILE,
            default="",
            typ="str",
            validator=validate_cron,
            doc=(
                "Periodically run a full compile following a cron-like time-to-run specification, interpreted in UTC"
                " (e.g. `min hour dom month dow`). A compile will be requested at the scheduled time. The actual"
                " compilation may have to wait in the compile queue for some time, depending on the size of the queue and the"
                " RECOMPILE_BACKOFF environment setting. This setting has no effect when server_compile is disabled."
            ),
        ),
        RESOURCE_ACTION_LOGS_RETENTION: Setting(
            name=RESOURCE_ACTION_LOGS_RETENTION,
            default=7,
            typ="int",
            validator=convert_int,
            doc="The number of days to retain resource-action logs",
        ),
        AVAILABLE_VERSIONS_TO_KEEP: Setting(
            name=AVAILABLE_VERSIONS_TO_KEEP,
            default=100,
            typ="int",
            validator=convert_int,
            doc="The number of versions to keep stored in the database",
        ),
        PURGE_ON_DELETE: Setting(
            name=PURGE_ON_DELETE,
            default=False,
            typ="bool",
            validator=convert_boolean,
            doc="Enable purge on delete. When set to true, the server will detect the absence of resources with purge_on_delete"
            " set to true and automatically purges them.",
        ),
        PROTECTED_ENVIRONMENT: Setting(
            name=PROTECTED_ENVIRONMENT,
            default=False,
            typ="bool",
            validator=convert_boolean,
            doc="When set to true, this environment cannot be cleared, deleted or decommissioned.",
        ),
        NOTIFICATION_RETENTION: Setting(
            name=NOTIFICATION_RETENTION,
            default=365,
            typ="int",
            validator=convert_int,
            doc="The number of days to retain notifications for",
        ),
        RECOMPILE_BACKOFF: Setting(
            name=RECOMPILE_BACKOFF,
            default=0.1,
            typ="positive_float",
            validator=convert_positive_float,
            doc="""The number of seconds to wait before the server may attempt to do a new recompile.
                    Recompiles are triggered after facts updates for example.""",
        ),
        ENVIRONMENT_METRICS_RETENTION: Setting(
            name=ENVIRONMENT_METRICS_RETENTION,
            typ="int",
            default=8760,
            doc="The number of hours that environment metrics have to be retained before they are cleaned up. "
            "Default=8760 hours (1 year). Set to 0 to disable automatic cleanups.",
            validator=convert_int,
        ),
    }

    _renamed_settings_map = {
        AUTOSTART_AGENT_DEPLOY_INTERVAL: AUTOSTART_AGENT_INTERVAL,
        AUTOSTART_AGENT_DEPLOY_SPLAY_TIME: AUTOSTART_SPLAY,
    }  # name new_option -> name deprecated_option

    @classmethod
    def get_setting_definition(cls, setting_name: str) -> Setting:
        """
        Return the definition of the setting with the given name.
        """
        if setting_name not in cls._settings:
            raise KeyError()
        return cls._settings[setting_name]

    async def get(self, key: str, connection: Optional[asyncpg.connection.Connection] = None) -> m.EnvSettingType:
        """
        Get a setting in this environment.

        :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
        """
        if key not in self._settings:
            raise KeyError()

        if key in self._renamed_settings_map:
            name_deprecated_setting = self._renamed_settings_map[key]
            if name_deprecated_setting in self.settings and key not in self.settings:
                warnings.warn(
                    "Config option %s is deprecated. Use %s instead." % (name_deprecated_setting, key),
                    category=DeprecationWarning,
                )
                return self.settings[name_deprecated_setting]

        if key in self.settings:
            return self.settings[key]

        if self._settings[key].default is None:
            raise KeyError()

        value = self._settings[key].default
        await self.set(key, value, connection=connection)
        return value

    async def set(self, key: str, value: m.EnvSettingType, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Set a new setting in this environment.

        :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
        :param value: The value of the settings. The value should be of type as defined in _settings
        """
        if key not in self._settings:
            raise KeyError()
        # TODO: convert this to a string
        if callable(self._settings[key].validator):
            value = self._settings[key].validator(value)

        type = translate_to_postgres_type(self._settings[key].typ)
        (filter_statement, values) = self._get_composed_filter(name=self.name, project=self.project, offset=3)
        query = (
            "UPDATE "
            + self.table_name()
            + " SET settings=jsonb_set(settings, $1::text[], to_jsonb($2::"
            + type
            + "), TRUE)"
            + " WHERE "
            + filter_statement
        )
        values = [self._get_value([key]), self._get_value(value)] + values
        await self._execute_query(query, *values, connection=connection)
        self.settings[key] = value

    async def unset(self, key: str) -> None:
        """
        Unset a setting in this environment. If a default value is provided, this value will replace the current value.

        :param key: The name/key of the setting. It should be defined in _settings otherwise a keyerror will be raised.
        """
        if key not in self._settings:
            raise KeyError()

        if self._settings[key].default is None:
            (filter_statement, values) = self._get_composed_filter(name=self.name, project=self.project, offset=2)
            query = "UPDATE " + self.table_name() + " SET settings=settings - $1" + " WHERE " + filter_statement
            values = [self._get_value(key)] + values
            await self._execute_query(query, *values)
            del self.settings[key]
        else:
            await self.set(key, self._settings[key].default)

    async def delete_cascade(self, only_content: bool = False) -> None:
        if only_content:
            await Agent.delete_all(environment=self.id)

            procs = await AgentProcess.get_list(environment=self.id)
            for proc in procs:
                await proc.delete_cascade()

            compile_list = await Compile.get_list(environment=self.id)
            for cl in compile_list:
                await cl.delete_cascade()

            for model in await ConfigurationModel.get_list(environment=self.id):
                await model.delete_cascade()

            await Parameter.delete_all(environment=self.id)
            await Resource.delete_all(environment=self.id)
            await ResourceAction.delete_all(environment=self.id)
            await Notification.delete_all(environment=self.id)
        else:
            # Cascade is done by PostgreSQL
            await self.delete()

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
        cls: Type[TBaseDocument],
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
    ) -> List[TBaseDocument]:
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
        cls: Type[TBaseDocument],
        *,
        order_by_column: Optional[str] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: Optional[bool] = None,
        lock: Optional[RowLockMode] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: object,
    ) -> List[TBaseDocument]:
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
        cls: Type[TBaseDocument],
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


class Parameter(BaseDocument):
    """
    A parameter that can be used in the configuration model

    :param name: The name of the parameter
    :param value: The value of the parameter
    :param environment: The environment this parameter belongs to
    :param source: The source of the parameter
    :param resource_id: An optional resource id
    :param updated: When was the parameter updated last

    :todo Add history
    """

    __primary_key__ = ("id", "name", "environment")

    id: uuid.UUID
    name: str
    value: str = ""
    environment: uuid.UUID
    source: str
    resource_id: m.ResourceIdStr = ""
    updated: Optional[datetime.datetime] = None
    metadata: Optional[JsonType] = None

    @classmethod
    async def get_updated_before(cls, updated_before: datetime.datetime) -> List["Parameter"]:
        query = "SELECT * FROM " + cls.table_name() + " WHERE updated < $1"
        values = [cls._get_value(updated_before)]
        result = await cls.select_query(query, values)
        return result

    @classmethod
    async def list_parameters(cls, env_id: uuid.UUID, **metadata_constraints: str) -> List["Parameter"]:
        query = "SELECT * FROM " + cls.table_name() + " WHERE environment=$1"
        values = [cls._get_value(env_id)]
        for key, value in metadata_constraints.items():
            query_param_index = len(values) + 1
            query += " AND metadata @> $" + str(query_param_index) + "::jsonb"
            dict_value = {key: value}
            values.append(cls._get_value(dict_value))
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
    resource_id: m.ResourceIdStr = ""
    version: int
    metadata: Optional[Dict[str, Any]]
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
    async def get_live(cls, environment: Optional[uuid.UUID] = None) -> List["AgentProcess"]:
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
            DELETE FROM {cls.table_name()} as a1
            WHERE a1.expired IS NOT NULL AND
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
                    FROM {cls.table_name()} as agentprocess INNER JOIN {AgentInstance.table_name()} as agentinstance
                         ON agentinstance.process = agentprocess.sid
                    WHERE agentprocess.sid = a1.sid and agentinstance.expired IS NULL
                  )
        """
        await cls._execute_query(query, cls._get_value(nr_expired_records_to_keep))

    def to_dict(self) -> JsonType:
        result = super(AgentProcess, self).to_dict()
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
        cls: Type[TAgentInstance],
        tid: uuid.UUID,
        endpoint: str,
        process: Optional[uuid.UUID] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> List[TAgentInstance]:
        if process is not None:
            objects = await cls.get_list(expired=None, tid=tid, name=endpoint, process=process, connection=connection)
        else:
            objects = await cls.get_list(expired=None, tid=tid, name=endpoint, connection=connection)
        return objects

    @classmethod
    async def active(cls: Type[TAgentInstance]) -> List[TAgentInstance]:
        objects = await cls.get_list(expired=None)
        return objects

    @classmethod
    async def log_instance_creation(
        cls: Type[TAgentInstance],
        tid: uuid.UUID,
        process: uuid.UUID,
        endpoints: Set[str],
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
        cls: Type[TAgentInstance],
        sid: uuid.UUID,
        endpoints: Set[str],
        now: datetime.datetime,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Expire specific instances for a given session id.
        """
        if not endpoints:
            return
        instances: List[TAgentInstance] = await cls.get_list(connection=connection, process=sid)
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
    :param primary: what is the current active instance (if none, state is down)
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
    def get_valid_field_names(cls) -> List[str]:
        # Allow the computed fields
        return super().get_valid_field_names() + ["process_name", "status"]

    @classmethod
    async def get_statuses(cls, env_id: uuid.UUID, agent_names: Set[str]) -> Dict[str, Optional[AgentStatus]]:
        result: Dict[str, Optional[AgentStatus]] = {}
        for agent_name in agent_names:
            agent = await cls.get_one(environment=env_id, name=agent_name)
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
    def _convert_field_names_to_db_column_names(cls, field_dict: Dict[str, str]) -> Dict[str, str]:
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
    async def persist_on_resume(cls, env: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None) -> List[str]:
        """
        Restores default halted state. Returns a list of agents that should be unpaused.
        """

        async with cls.get_connection(connection) as con:
            async with con.transaction():
                unpause_on_resume = await cls._fetch_query(
                    # lock FOR UPDATE to avoid deadlocks: next query in this transaction updates the row
                    f"SELECT name FROM {cls.table_name()} WHERE environment=$1 AND unpause_on_resume FOR UPDATE",
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
    ) -> List[str]:
        """
        Pause a specific agent or all agents in an environment when endpoint is set to None.

        :return A list of agent names that have been paused/unpaused by this method.
        """
        if endpoint is None:
            query = f"UPDATE {cls.table_name()} SET paused=$1 WHERE environment=$2 RETURNING name"
            values = [cls._get_value(paused), cls._get_value(env)]
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
        endpoints_with_new_primary: Sequence[Tuple[str, Optional[uuid.UUID]]],
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
        for (endpoint, sid) in endpoints_with_new_primary:
            # Lock mode is required because we will update in this transaction
            # Deadlocks with cleanup otherwise
            agent = await cls.get(env, endpoint, connection=connection, lock=RowLockMode.FOR_UPDATE)
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
    :param do_export: should this compiler perform an export
    :param force_update: should this compile definitely update
    :param metadata: exporter metadata to be passed to the compiler
    :param environment_variables: environment variables to be passed to the compiler
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
    environment_variables: Optional[JsonType] = {}

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

    @classmethod
    async def get_substitute_by_id(cls, compile_id: uuid.UUID) -> Optional["Compile"]:
        """
        Get a compile's substitute compile if it exists, otherwise get the compile by id.

        :param compile_id: The id of the compile for which to get the substitute compile.
        :return: The compile object for compile c2 that is the substitute of compile c1 with the given id. If c1 does not have
            a substitute, returns c1 itself.
        """
        result: Optional[Compile] = await cls.get_by_id(compile_id)
        if result is None:
            return None
        if result.substitute_compile_id is None:
            return result
        return await cls.get_substitute_by_id(result.substitute_compile_id)

    @classmethod
    # TODO: Use join
    async def get_report(cls, compile_id: uuid.UUID) -> Optional[Dict]:
        """
        Get the compile and the associated reports from the database
        """
        result: Optional[Compile] = await cls.get_substitute_by_id(compile_id)
        if result is None:
            return None

        dict_model = result.to_dict()
        reports = await Report.get_list(compile=result.id)
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
    async def get_next_run(cls, environment_id: uuid.UUID) -> Optional["Compile"]:
        """Get the next compile in the queue for the given environment"""
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} WHERE environment=$1 AND completed IS NULL ORDER BY requested ASC LIMIT 1",
            [cls._get_value(environment_id)],
        )
        if not results:
            return None
        return results[0]

    @classmethod
    async def get_next_run_all(cls) -> "Sequence[Compile]":
        """Get the next compile in the queue for each environment"""
        results = await cls.select_query(
            f"SELECT DISTINCT ON (environment) * FROM {cls.table_name()} WHERE completed IS NULL ORDER BY environment, "
            f"requested ASC",
            [],
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
    async def get_next_compiles_count(cls) -> int:
        """Get the number of compiles in the queue for ALL environments"""
        result = await cls._fetch_int(f"SELECT count(*) FROM {cls.table_name()} WHERE NOT handled AND completed IS NULL")
        return result

    @classmethod
    async def get_by_remote_id(cls, environment_id: uuid.UUID, remote_id: uuid.UUID) -> "Sequence[Compile]":
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} WHERE environment=$1 AND remote_id=$2",
            [cls._get_value(environment_id), cls._get_value(remote_id)],
        )
        return results

    @classmethod
    async def delete_older_than(
        cls, oldest_retained_date: datetime.datetime, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        query = "DELETE FROM " + cls.table_name() + " WHERE completed <= $1::timestamp with time zone"
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
                c.environment_variables,
                c.compile_data,
                c.substitute_compile_id,
                c.partial,
                c.removed_resource_sets,
                c.exporter_plugin,
                c.notify_failed_compile,
                c.failed_compile_message,
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
                    comp.environment_variables,
                    comp.compile_data,
                    comp.substitute_compile_id,
                    comp.partial,
                    comp.removed_resource_sets,
                    comp.exporter_plugin,
                    comp.notify_failed_compile,
                    comp.failed_compile_message,
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
        result = cast(List[Record], result)
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

        # Reports should be included from the substituted compile (as well)
        reports = [
            m.CompileRunReport(
                id=report["report_id"],
                started=report["report_started"],
                completed=report["report_completed"],
                command=report["command"],
                name=report["name"],
                errstream=report["errstream"],
                outstream=report["outstream"],
                returncode=report["returncode"],
            )
            for report in result
            if report.get("report_id")
        ]

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
            metadata=json.loads(requested_compile["metadata"]) if requested_compile["metadata"] else {},
            environment_variables=json.loads(requested_compile["environment_variables"])
            if requested_compile["environment_variables"]
            else {},
            partial=requested_compile["partial"],
            removed_resource_sets=requested_compile["removed_resource_sets"],
            exporter_plugin=requested_compile["exporter_plugin"],
            notify_failed_compile=requested_compile["notify_failed_compile"],
            failed_compile_message=requested_compile["failed_compile_message"],
            compile_data=json.loads(requested_compile["compile_data"]) if requested_compile["compile_data"] else None,
            reports=reports,
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
            environment_variables=self.environment_variables,
            compile_data=None if self.compile_data is None else m.CompileData(**self.compile_data),
            partial=self.partial,
            removed_resource_sets=self.removed_resource_sets,
            exporter_plugin=self.exporter_plugin,
            notify_failed_compile=self.notify_failed_compile,
            failed_compile_message=self.failed_compile_message,
        )


class LogLine(DataDocument):
    """
    LogLine data document.

    An instance of this class only has one attribute: _data.
    This unique attribute is a dict, with the following keys:
        - msg: the message to write to logs (value type: str)
        - args: the args that can be passed to the logger (value type: list)
        - level: the log level of the message (value type: str, example: "CRITICAL")
        - kwargs: the key-word args that where used to generated the log (value type: list)
        - timestamp: the time at which the LogLine was created (value type: datetime.datetime)
    """

    @property
    def msg(self) -> str:
        return self._data["msg"]

    @property
    def args(self) -> List:
        return self._data["args"]

    @property
    def log_level(self) -> LogLevel:
        level: str = self._data["level"]
        return LogLevel[level]

    def write_to_logger(self, logger: logging.Logger) -> None:
        logger.log(self.log_level.to_int, self.msg, *self.args)

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
    resource_version_ids: List[m.ResourceVersionIdStr]

    action_id: uuid.UUID
    action: const.ResourceAction

    started: datetime.datetime
    finished: Optional[datetime.datetime] = None

    messages: Optional[List[Dict[str, Any]]] = None
    status: Optional[const.ResourceState] = None
    changes: Optional[Dict[m.ResourceIdStr, Dict[str, object]]] = None
    change: Optional[const.Change] = None

    def __init__(self, from_postgres: bool = False, **kwargs: object) -> None:
        super().__init__(from_postgres, **kwargs)
        self._updates = {}

        # rewrite some data
        if self.changes == {}:
            self.changes = None

        # load message json correctly
        if from_postgres and self.messages:
            new_messages = []
            for message in self.messages:
                message = json.loads(message)
                if "timestamp" in message:
                    # use pydantic instead of datetime.strptime because strptime has trouble parsing isoformat timezone offset
                    message["timestamp"] = pydantic.parse_obj_as(datetime.datetime, message["timestamp"])
                    if message["timestamp"].tzinfo is None:
                        raise Exception("Found naive timestamp in the database, this should not be possible")
                new_messages.append(message)
            self.messages = new_messages

    @classmethod
    async def get_by_id(cls, doc_id: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None) -> "ResourceAction":
        return await cls.get_one(action_id=doc_id, connection=connection)

    @classmethod
    async def get_log(
        cls, environment: uuid.UUID, resource_version_id: m.ResourceVersionIdStr, action: Optional[str] = None, limit: int = 0
    ) -> List["ResourceAction"]:
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
        async with cls.get_connection() as con:
            async with con.transaction():
                return [cls(**dict(record), from_postgres=True) async for record in con.cursor(query, *values)]

    @classmethod
    async def get_logs_for_version(
        cls, environment: uuid.UUID, version: int, action: Optional[str] = None, limit: int = 0
    ) -> List["ResourceAction"]:
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
        async with cls.get_connection() as con:
            async with con.transaction():
                return [cls(**dict(record), from_postgres=True) async for record in con.cursor(query, *values)]

    @classmethod
    def get_valid_field_names(cls) -> List[str]:
        return super().get_valid_field_names() + ["timestamp", "level", "msg"]

    @classmethod
    async def get(cls, action_id: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None) -> "ResourceAction":
        return await cls.get_one(action_id=action_id, connection=connection)

    async def insert(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        async with self.get_connection(connection) as con:
            async with con.transaction():
                await super(ResourceAction, self).insert(con)

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

    def add_changes(self, changes: Dict[m.ResourceIdStr, Dict[str, object]]) -> None:
        for resource, values in changes.items():
            for field, change in values.items():
                if "changes" not in self._updates:
                    self._updates["changes"] = {}
                if resource not in self._updates["changes"]:
                    self._updates["changes"][resource] = {}
                self._updates["changes"][resource][field] = change

    async def set_and_save(
        self,
        messages: List[Dict[str, Any]],
        changes: Dict[str, Any],
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
        environments = await Environment.get_list()
        for env in environments:
            time_to_retain_logs = await env.get(RESOURCE_ACTION_LOGS_RETENTION)
            keep_logs_until = datetime.datetime.now().astimezone() - datetime.timedelta(days=time_to_retain_logs)
            query = "DELETE FROM " + cls.table_name() + " WHERE started < $1"
            value = cls._get_value(keep_logs_until)
            await cls._execute_query(query, value)

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
    ) -> List["ResourceAction"]:
        query = """SELECT DISTINCT ra.*
                    FROM public.resource as r
                    INNER JOIN public.resourceaction_resource as jt
                        ON r.environment = jt.environment
                        AND r.resource_id = jt.resource_id
                        AND r.model = jt.resource_version
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
    ) -> Dict[ResourceIdStr, List["ResourceAction"]]:
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

        # steps 1 and 2:
        # find the interval between the current deploy and the previous successful deploy
        # also check we are currently deploying
        # do all of this in one query
        resource_version_id_str = resource_id.resource_version_str()
        resource_id_str = resource_id.resource_str()

        # These two variables are actually of type datetime.datetime
        # but mypy doesn't know as they come from the DB
        # mypy also doesn't care, because they go back into the DB
        current_deploy_start: object
        last_deploy_start: Optional[object]

        end_query = """
        with
            base_ra as (
            SELECT ra.*
                FROM public.resourceaction_resource as jt
                    INNER JOIN public.resourceaction as ra
                        ON ra.action_id = jt.resource_action_id
                    WHERE jt.environment=$1 AND ra.environment=$1 AND jt.resource_id=$2::varchar AND ra.action='deploy'
                    ORDER BY ra.started DESC
            )
        SELECT
            (SELECT started from base_ra ORDER BY started DESC LIMIT 1) as begin_started,
            (SELECT status from base_ra ORDER BY started DESC LIMIT 1) as begin_status,
            COALESCE((SELECT started from base_ra where status='deployed' ORDER BY started DESC LIMIT 1), NULL) as started
        """

        async with cls.get_connection() as connection:
            result = await connection.fetchrow(end_query, env.id, resource_id_str)

            if not result or result["begin_status"] is None:
                raise BadRequest(
                    "Fetching resource events only makes sense when the resource is currently deploying. Resource"
                    f" {resource_version_id_str} has not started deploying yet."
                )
            if result["begin_status"] != const.ResourceState.deploying:
                raise BadRequest(
                    "Fetching resource events only makes sense when the resource is currently deploying. Current deploy state"
                    f" for resource {resource_version_id_str} is {result['begin_status']}."
                )
            current_deploy_start = result["begin_started"]
            last_deploy_start = result["started"]

            # Step3: Get the resource
            resource: Optional[Resource] = await Resource.get_one(
                environment=env.id, resource_id=resource_id_str, model=resource_id.version, connection=connection
            )
            if resource is None:
                raise NotFound(f"Resource with id {resource_version_id_str} was not found in environment {env.id}")

            # Step 4: get the relevant resource actions
            # Do it in one query for all dependencies

            # Construct the query
            arg = ArgumentCollector(offset=2)

            # First make the filter
            filter = f"AND ra.started<{arg(current_deploy_start)}"
            if last_deploy_start:
                filter += f" AND ra.started > {arg(last_deploy_start)}"
            if exclude_change:
                filter += f"AND ra.change <> {arg(exclude_change.value)}"

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
            collector: Dict[ResourceIdStr, List["ResourceAction"]] = {
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


@stable_api
class Resource(BaseDocument):
    """
    A specific version of a resource. This entity contains the desired state of a resource.

    :param environment: The environment this resource version is defined in
    :param rid: The id of the resource and its version
    :param resource: The resource for which this defines the state
    :param model: The configuration model (versioned) this resource state is associated with
    :param attributes: The state of this version of the resource
    :param attribute_hash: hash of the attributes, excluding requires, provides and version,
                           used to determine if a resource describes the same state across versions
    :param resource_id_value: The attribute value from the resource id
    :param last_non_deploying_status: The last status of this resource that is not the 'deploying' status.
    """

    __primary_key__ = ("environment", "model", "resource_id")

    environment: uuid.UUID
    model: int

    # ID related
    resource_id: m.ResourceIdStr
    resource_type: m.ResourceType
    resource_id_value: str

    agent: str

    # Field based on content from the resource actions
    last_deploy: Optional[datetime.datetime] = None

    # State related
    attributes: Dict[str, Any] = {}
    attribute_hash: Optional[str]
    status: const.ResourceState = const.ResourceState.available
    last_non_deploying_status: const.NonDeployingResourceState = const.NonDeployingResourceState.available
    resource_set: Optional[str] = None

    # internal field to handle cross agent dependencies
    # if this resource is updated, it must notify all RV's in this list
    # the list contains full rv id's
    provides: List[m.ResourceIdStr] = []

    # Methods for backward compatibility
    @property
    def resource_version_id(self):
        # This field was removed from the DB, this method keeps code compatibility
        return resources.Id.set_version_in_id(self.resource_id, self.model)

    @classmethod
    def __mangle_dict(cls, record: dict) -> None:
        """
        Transform the dict of attributes as it exists here/in the database to the backward compatible form
        Operates in-place
        """
        version = record["model"]
        parsed_id = resources.Id.parse_id(record["resource_id"])
        parsed_id.set_version(version)
        record["resource_version_id"] = parsed_id.resource_version_str()
        record["id"] = record["resource_version_id"]
        record["resource_type"] = parsed_id.entity_type
        if "requires" in record["attributes"]:
            record["attributes"]["requires"] = [
                resources.Id.set_version_in_id(id, version) for id in record["attributes"]["requires"]
            ]
        record["provides"] = [resources.Id.set_version_in_id(id, version) for id in record["provides"]]

    @classmethod
    async def get_last_non_deploying_state_for_dependencies(
        cls, environment: uuid.UUID, resource_version_id: "resources.Id", connection: Optional[Connection] = None
    ) -> Dict[m.ResourceVersionIdStr, ResourceState]:
        """
        Return the last state of each dependency of the given resource that was not 'deploying'.
        """
        if not resource_version_id.is_resource_version_id_obj():
            raise Exception("Argument resource_version_id is not a resource_version_id")
        query = """
            SELECT r1.resource_id, r1.model, r1.last_non_deploying_status
            FROM resource AS r1
            WHERE r1.environment=$1
                  AND r1.model=$2
                  AND (
                      SELECT (r2.attributes->'requires')::jsonb
                      FROM resource AS r2
                      WHERE r2.environment=$1 AND r2.model=$2 AND r2.resource_id=$3
                  ) ? r1.resource_id
        """
        values = [
            cls._get_value(environment),
            cls._get_value(resource_version_id.version),
            resource_version_id.resource_str(),
        ]
        result = await cls._fetch_query(query, *values, connection=connection)
        return {r["resource_id"] + ",v=" + str(r["model"]): const.ResourceState(r["last_non_deploying_status"]) for r in result}

    def make_hash(self) -> None:
        character = json.dumps(
            {k: v for k, v in self.attributes.items() if k not in ["requires", "provides", "version"]},
            default=custom_json_encoder,
            sort_keys=True,  # sort the keys for stable hashes when using dicts, see #5306
        )
        m = hashlib.md5()
        m.update(self.resource_id.encode("utf-8"))
        m.update(character.encode("utf-8"))
        self.attribute_hash = m.hexdigest()

    @classmethod
    async def get_resources(
        cls,
        environment: uuid.UUID,
        resource_version_ids: List[m.ResourceVersionIdStr],
        lock: Optional[RowLockMode] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> List["Resource"]:
        """
        Get all resources listed in resource_version_ids
        """
        if not resource_version_ids:
            return []
        query_lock: str = lock.value if lock is not None else ""

        def convert_or_ignore(rvid):
            """Method to retain backward compatibility, ignore bad ID's"""
            try:
                return resources.Id.parse_resource_version_id(rvid)
            except ValueError:
                return None

        parsed_rv = (convert_or_ignore(id) for id in resource_version_ids)
        effective_parsed_rv = [id for id in parsed_rv if id is not None]

        if not effective_parsed_rv:
            return []

        query = (
            f"SELECT r.* FROM {cls.table_name()} r"
            f" INNER JOIN unnest($2::resource_id_version_pair[]) requested(resource_id, model)"
            f" ON r.resource_id = requested.resource_id AND r.model = requested.model"
            f" WHERE environment=$1"
            f" {query_lock}"
        )
        out = await cls.select_query(
            query,
            [cls._get_value(environment), [(id.resource_str(), id.get_version()) for id in effective_parsed_rv]],
            connection=connection,
        )
        return out

    @classmethod
    async def get_undeployable(cls, environment: uuid.UUID, version: int) -> List["Resource"]:
        """
        Returns a list of resources with an undeployable state
        """
        (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version)
        undeployable_states = ", ".join(["$" + str(i + 3) for i in range(len(const.UNDEPLOYABLE_STATES))])
        values = values + [cls._get_value(s) for s in const.UNDEPLOYABLE_STATES]
        query = (
            "SELECT * FROM " + cls.table_name() + " WHERE " + filter_statement + " AND status IN (" + undeployable_states + ")"
        )
        resources = await cls.select_query(query, values)
        return resources

    @classmethod
    async def get_resources_in_latest_version(
        cls,
        environment: uuid.UUID,
        resource_type: Optional[m.ResourceType] = None,
        attributes: Dict[PrimitiveTypes, PrimitiveTypes] = {},
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> List["Resource"]:
        """
        Returns the resources in the latest version of the configuration model of the given environment, that satisfy the
        given constraints.

        :param environment: The resources should belong to this environment.
        :param resource_type: The environment should have this resource_type.
        :param attributes: The resource should contain these key-value pairs in its attributes list.
        """
        values = [cls._get_value(environment)]
        query = f"""
            SELECT *
            FROM {Resource.table_name()} AS r1
            WHERE r1.environment=$1 AND r1.model=(SELECT MAX(cm.version)
                                                  FROM {ConfigurationModel.table_name()} AS cm
                                                  WHERE cm.environment=$1)
        """
        if resource_type:
            query += " AND r1.resource_type=$2"
            values.append(cls._get_value(resource_type))

        result = []
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    resource = cls(from_postgres=True, **record)
                    # The constraints on the attributes field are checked in memory.
                    # This prevents injection attacks.
                    if util.is_sub_dict(attributes, resource.attributes):
                        result.append(resource)
        return result

    @classmethod
    async def get_resources_report(cls, environment: uuid.UUID) -> List[JsonType]:
        """
        This method generates a report of all resources in the given environment,
        with their latest version and when they are last deployed.
        """
        query_resource_ids = f"""
                SELECT DISTINCT resource_id
                FROM {Resource.table_name()}
                WHERE environment=$1
        """
        query_latest_version = f"""
                SELECT resource_id, model AS latest_version, agent AS latest_agent
                FROM {Resource.table_name()}
                WHERE environment=$1 AND
                      resource_id=r1.resource_id
                ORDER BY model DESC
                LIMIT 1
        """
        query_latest_deployed_version = f"""
                SELECT resource_id, model AS deployed_version, last_deploy AS last_deploy
                FROM {Resource.table_name()}
                WHERE environment=$1 AND
                      resource_id=r1.resource_id AND
                      status != $2
                ORDER BY model DESC
                LIMIT 1
        """
        query = f"""
                SELECT r1.resource_id, r2.latest_version, r2.latest_agent, r3.deployed_version, r3.last_deploy
                FROM ({query_resource_ids}) AS r1 INNER JOIN LATERAL ({query_latest_version}) AS r2
                      ON (r1.resource_id = r2.resource_id)
                      LEFT OUTER JOIN LATERAL ({query_latest_deployed_version}) AS r3
                      ON (r1.resource_id = r3.resource_id)
        """
        values = [cls._get_value(environment), cls._get_value(const.ResourceState.available)]
        result = []
        async with cls.get_connection() as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    resource_id = record["resource_id"]
                    parsed_id = resources.Id.parse_id(resource_id)
                    result.append(
                        {
                            "resource_id": resource_id,
                            "resource_type": parsed_id.entity_type,
                            "agent": record["latest_agent"],
                            "latest_version": record["latest_version"],
                            "deployed_version": record["deployed_version"] if "deployed_version" in record else None,
                            "last_deploy": record["last_deploy"] if "last_deploy" in record else None,
                        }
                    )
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
    ) -> List["Resource"]:
        if agent:
            (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version, agent=agent)
        else:
            (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version)

        query = f"SELECT * FROM {Resource.table_name()} WHERE {filter_statement}"
        resources_list: Union[List[Resource], List[Dict[str, object]]] = []
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    if no_obj:
                        record = dict(record)
                        record["attributes"] = json.loads(record["attributes"])
                        cls.__mangle_dict(record)
                        resources_list.append(record)
                    else:
                        resources_list.append(cls(from_postgres=True, **record))
        return resources_list

    @classmethod
    async def get_resources_for_version_raw(
        cls, environment: uuid.UUID, version: int, projection: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        if not projection:
            projection = "*"
        else:
            projection = ",".join(projection)
        (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version)
        query = "SELECT " + projection + " FROM " + cls.table_name() + " WHERE " + filter_statement
        resource_records = await cls._fetch_query(query, *values)
        resources = [dict(record) for record in resource_records]
        for res in resources:
            if "attributes" in res:
                res["attributes"] = json.loads(res["attributes"])
        return resources

    @classmethod
    async def get_latest_version(cls, environment: uuid.UUID, resource_id: m.ResourceIdStr) -> Optional["Resource"]:
        resources = await cls.get_list(
            order_by_column="model", order="DESC", limit=1, environment=environment, resource_id=resource_id
        )
        if len(resources) > 0:
            return resources[0]
        return None

    @staticmethod
    def get_details_from_resource_id(resource_id: m.ResourceIdStr) -> m.ResourceIdDetails:
        parsed_id = resources.Id.parse_id(resource_id)
        return m.ResourceIdDetails(
            resource_type=parsed_id.entity_type,
            agent=parsed_id.agent_name,
            attribute=parsed_id.attribute,
            resource_id_value=parsed_id.attribute_value,
        )

    @classmethod
    async def get(
        cls,
        environment: uuid.UUID,
        resource_version_id: m.ResourceVersionIdStr,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> Optional["Resource"]:
        """
        Get a resource with the given resource version id
        """
        parsed_id = resources.Id.parse_id(resource_version_id)
        value = await cls.get_one(
            environment=environment, resource_id=parsed_id.resource_str(), model=parsed_id.version, connection=connection
        )
        return value

    @classmethod
    def new(cls, environment: uuid.UUID, resource_version_id: m.ResourceVersionIdStr, **kwargs: Any) -> "Resource":
        vid = resources.Id.parse_id(resource_version_id)

        attr = dict(
            environment=environment,
            model=vid.version,
            resource_id=vid.resource_str(),
            resource_type=vid.entity_type,
            agent=vid.agent_name,
            resource_id_value=vid.attribute_value,
        )

        attr.update(kwargs)

        return cls(**attr)

    @classmethod
    async def get_deleted_resources(
        cls,
        environment: uuid.UUID,
        current_version: int,
        current_resources: Sequence[m.ResourceIdStr],
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> List["Resource"]:
        """
        This method returns all resources that have been deleted from the model and are not yet marked as purged. It returns
        the latest version of the resource from a released model.

        :param environment:
        :param current_version:
        :param current_resources: A Sequence of all resource ids in the current version.
        """
        LOGGER.debug("Starting purge_on_delete queries")

        # get all models that have been released
        query = (
            "SELECT version FROM "
            + ConfigurationModel.table_name()
            + " WHERE environment=$1 AND released=TRUE ORDER BY version DESC LIMIT "
            + str(DBLIMIT)
        )
        versions = set()
        latest_version = None
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                async for record in con.cursor(query, cls._get_value(environment)):
                    version = record["version"]
                    versions.add(version)
                    if latest_version is None:
                        latest_version = version

        LOGGER.debug("  All released versions: %s", versions)
        LOGGER.debug("  Latest released version: %s", latest_version)

        # find all resources in previous versions that have "purge_on_delete" set
        (filter_statement, values) = cls._get_composed_filter(environment=environment, model=latest_version)
        query = (
            "SELECT DISTINCT resource_id FROM "
            + cls.table_name()
            + " WHERE "
            + filter_statement
            + " AND attributes @> $"
            + str(len(values) + 1)
        )
        values.append(cls._get_value({"purge_on_delete": True}))
        resources_records = await cls._fetch_query(query, *values, connection=connection)
        resources = [r["resource_id"] for r in resources_records]

        LOGGER.debug("  Resource with purge_on_delete true: %s", resources)

        # all resources on current model
        LOGGER.debug("  All resource in current version (%s): %s", current_version, current_resources)

        # determined deleted resources

        deleted = set(resources) - set(current_resources)
        LOGGER.debug("  These resources are no longer present in current model: %s", deleted)

        # filter out resources that should not be purged:
        # 1- resources from versions that have not been deployed
        # 2- resources that are already recorded as purged (purged and deployed)
        should_purge = []
        for deleted_resource in deleted:
            # get the full resource history, and determine the purge status of this resource
            (filter_statement, values) = cls._get_composed_filter(environment=environment, resource_id=deleted_resource)
            query = (
                "SELECT *"
                + " FROM "
                + cls.table_name()
                + " WHERE "
                + filter_statement
                + " AND model < $"
                + str(len(values) + 1)
                + " ORDER BY model DESC"
            )
            values.append(cls._get_value(current_version))

            async with cls.get_connection(connection) as con:
                async with con.transaction():
                    async for obj in con.cursor(query, *values):
                        # if a resource is part of a released version and it is deployed (this last condition is actually enough
                        # at the moment), we have found the last status of the resource. If it was not purged in that version,
                        # add it to the should purge list.
                        if obj["model"] in versions and obj["status"] == const.ResourceState.deployed.name:
                            attributes = json.loads(str(obj["attributes"]))
                            if not attributes["purged"]:
                                should_purge.append(cls(from_postgres=True, **obj))
                            break

        return should_purge

    @classmethod
    async def get_resource_details(cls, env: uuid.UUID, resource_id: m.ResourceIdStr) -> Optional[m.ReleasedResourceDetails]:
        status_subquery = """
        (CASE WHEN
            (SELECT resource.model < MAX(configurationmodel.version)
            FROM configurationmodel
            WHERE configurationmodel.released=TRUE
            AND environment = $1)
        THEN 'orphaned'
        ELSE resource.status::text END
        ) as status
        """

        query = f"""
        SELECT DISTINCT ON (resource_id) first.resource_id, cm.date as first_generated_time,
        first.model as first_model, latest.resource_id as latest_resource_id, latest.resource_type,
        latest.agent, latest.resource_id_value, latest.last_deploy as latest_deploy, latest.attributes, latest.status
        FROM resource first
        INNER JOIN
            /* 'latest' is the latest released version of the resource */
            (SELECT distinct on (resource_id) resource_id, attribute_hash, model, last_deploy, attributes,
                resource_type, agent, resource_id_value, {status_subquery}
                FROM resource
                JOIN configurationmodel cm ON resource.model = cm.version AND resource.environment = cm.environment
                WHERE resource.environment = $1 AND resource_id = $2 AND cm.released = TRUE
                ORDER BY resource_id, model desc
            ) as latest
        /* The 'first' values correspond to the first time the attribute hash was the same as in
            the 'latest' released version */
        ON first.resource_id = latest.resource_id AND first.attribute_hash = latest.attribute_hash
        INNER JOIN configurationmodel cm ON first.model = cm.version AND first.environment = cm.environment
        WHERE first.environment = $1 AND first.resource_id = $2 AND cm.released = TRUE
        ORDER BY first.resource_id, first.model asc;
        """
        values = [cls._get_value(env), cls._get_value(resource_id)]
        result = await cls.select_query(query, values, no_obj=True)

        if not result:
            return None
        record = result[0]
        parsed_id = resources.Id.parse_id(record["latest_resource_id"])
        attributes = json.loads(record["attributes"])
        requires = [resources.Id.parse_id(req).resource_str() for req in attributes["requires"]]

        # fetch the status of each of the requires. This is not calculated in the database because the lack of joinable
        # fields requires to calculate the status for each resource record, before it is filtered
        status_query = f"""
        SELECT DISTINCT ON (resource_id) resource_id, {status_subquery}
        FROM resource
        INNER JOIN configurationmodel cm ON resource.model = cm.version AND resource.environment = cm.environment
        WHERE resource.environment = $1 AND cm.released = TRUE AND resource_id = ANY($2)
        ORDER BY resource_id, model DESC;
        """
        status_result = await cls.select_query(status_query, [cls._get_value(env), cls._get_value(requires)], no_obj=True)

        return m.ReleasedResourceDetails(
            resource_id=record["latest_resource_id"],
            resource_type=record["resource_type"],
            agent=record["agent"],
            id_attribute=parsed_id.attribute,
            id_attribute_value=record["resource_id_value"],
            last_deploy=record["latest_deploy"],
            first_generated_time=record["first_generated_time"],
            first_generated_version=record["first_model"],
            attributes=attributes,
            status=record["status"],
            requires_status={record["resource_id"]: record["status"] for record in status_result},
        )

    @classmethod
    async def get_versioned_resource_details(
        cls, environment: uuid.UUID, version: int, resource_id: m.ResourceIdStr
    ) -> Optional[m.VersionedResourceDetails]:
        resource = await cls.get_one(environment=environment, model=version, resource_id=resource_id)
        if not resource:
            return None
        parsed_id = resources.Id.parse_id(resource.resource_id)
        parsed_id.set_version(resource.model)
        return m.VersionedResourceDetails(
            resource_id=resource.resource_id,
            resource_version_id=parsed_id.resource_version_str(),
            resource_type=resource.resource_type,
            agent=resource.agent,
            id_attribute=parsed_id.attribute,
            id_attribute_value=resource.resource_id_value,
            version=resource.model,
            attributes=resource.attributes,
        )

    @classmethod
    async def get_resource_deploy_summary(cls, environment: uuid.UUID) -> m.ResourceDeploySummary:
        query = f"""
            SELECT COUNT(r.resource_id) as count, status
            FROM {cls.table_name()} as r
                WHERE r.environment=$1 AND r.model=(SELECT MAX(cm.version)
                                                  FROM public.configurationmodel AS cm
                                                  WHERE cm.environment=$1 AND cm.released=TRUE)
            GROUP BY r.status
        """
        raw_results = await cls._fetch_query(query, cls._get_value(environment))
        results = {}
        for row in raw_results:
            results[row["status"]] = row["count"]
        return m.ResourceDeploySummary.create_from_db_result(results)

    async def insert(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        self.make_hash()
        await super(Resource, self).insert(connection=connection)

    @classmethod
    async def insert_many(
        cls, documents: Sequence["Resource"], *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        for doc in documents:
            doc.make_hash()
        await super(Resource, cls).insert_many(documents, connection=connection)

    async def update(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: Any) -> None:
        self.make_hash()
        await super(Resource, self).update(connection=connection, **kwargs)

    async def update_fields(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: Any) -> None:
        self.make_hash()
        await super(Resource, self).update_fields(connection=connection, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        self.make_hash()
        dct = super(Resource, self).to_dict()
        self.__mangle_dict(dct)
        return dct

    def to_dto(self) -> m.Resource:
        attributes = self.attributes.copy()

        if "requires" in self.attributes:
            version = self.model
            attributes["requires"] = [resources.Id.set_version_in_id(id, version) for id in self.attributes["requires"]]

        return m.Resource(
            environment=self.environment,
            model=self.model,
            resource_id=self.resource_id,
            resource_type=self.resource_type,
            resource_version_id=resources.Id.set_version_in_id(self.resource_id, self.model),
            agent=self.agent,
            last_deploy=self.last_deploy,
            attributes=attributes,
            status=self.status,
            resource_id_value=self.resource_id_value,
            resource_set=self.resource_set,
        )


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
    """

    __primary_key__ = ("version", "environment")

    version: int
    environment: uuid.UUID
    date: Optional[datetime.datetime] = None
    partial_base: Optional[int] = None

    released: bool = False
    deployed: bool = False
    result: const.VersionState = const.VersionState.pending
    version_info: Optional[Dict[str, Any]] = None

    total: int = 0

    # cached state for release
    undeployable: List[m.ResourceIdStr] = []
    skipped_for_undeployable: List[m.ResourceIdStr] = []

    def __init__(self, **kwargs: object) -> None:
        super(ConfigurationModel, self).__init__(**kwargs)
        self._status = {}
        self._done = 0

    @classmethod
    def get_valid_field_names(cls) -> List[str]:
        return super().get_valid_field_names() + ["status", "model"]

    @property
    def done(self) -> int:
        # Keep resources which are deployed in done, even when a repair operation
        # changes its state to deploying again.
        if self.deployed:
            return self.total
        return self._done

    @classmethod
    async def _get_status_field(cls, environment: uuid.UUID, values: str) -> Dict[str, str]:
        """
        This field is required to ensure backward compatibility on the API.
        """
        result = {}
        values = json.loads(values)
        for value_entry in values:
            entry_uuid = str(uuid.uuid5(environment, value_entry["id"]))
            result[entry_uuid] = value_entry
        return result

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
        **query: Any,
    ) -> List["ConfigurationModel"]:
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

        transient_states = ",".join(["$" + str(i) for i in range(1, len(const.TRANSIENT_STATES) + 1)])
        transient_states_values = [cls._get_value(s) for s in const.TRANSIENT_STATES]
        (filterstr, values) = cls._get_composed_filter(col_name_prefix="c", offset=len(transient_states_values) + 1, **query)
        values = transient_states_values + values
        where_statement = f"WHERE {filterstr} " if filterstr else ""
        order_by_statement = f"ORDER BY {order_by_column} {order} " if order_by_column else ""
        limit_statement = f"LIMIT {limit} " if limit is not None and limit > 0 else ""
        offset_statement = f"OFFSET {offset} " if offset is not None and offset > 0 else ""
        lock_statement = f" {lock.value} " if lock is not None else ""
        query_string = f"""SELECT c.*,
                           SUM(CASE WHEN r.status NOT IN({transient_states}) THEN 1 ELSE 0 END) AS done,
                           to_json(array(SELECT jsonb_build_object('status', r2.status, 'id', r2.resource_id)
                                         FROM {Resource.table_name()} AS r2
                                         WHERE c.environment=r2.environment AND c.version=r2.model
                                        )
                           ) AS status
                    FROM {cls.table_name()} AS c LEFT OUTER JOIN {Resource.table_name()} AS r
                    ON c.environment = r.environment AND c.version = r.model
                    {where_statement}
                    GROUP BY c.environment, c.version
                    {order_by_statement}
                    {limit_statement}
                    {offset_statement}
                    {lock_statement}"""
        query_result = await cls._fetch_query(query_string, *values, connection=connection)
        result = []
        for record in query_result:
            record = dict(record)
            if no_obj:
                record["status"] = await cls._get_status_field(record["environment"], record["status"])
                result.append(record)
            else:
                done = record.pop("done")
                status = await cls._get_status_field(record["environment"], record.pop("status"))
                obj = cls(from_postgres=True, **record)
                obj._done = done
                obj._status = status
                result.append(obj)
        return result

    def to_dict(self) -> JsonType:
        dct = BaseDocument.to_dict(self)
        dct["status"] = dict(self._status)
        dct["done"] = self._done
        return dct

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
    ) -> Optional["ConfigurationModel"]:
        """
        Get a specific version
        """
        result = await cls.get_one(environment=environment, version=version, connection=connection)
        return result

    @classmethod
    async def get_latest_version(cls, environment: uuid.UUID) -> Optional["ConfigurationModel"]:
        """
        Get the latest released (most recent) version for the given environment
        """
        versions = await cls.get_list(order_by_column="version", order="DESC", limit=1, environment=environment, released=True)
        if len(versions) == 0:
            return None

        return versions[0]

    @classmethod
    async def get_version_nr_latest_version(cls, environment: uuid.UUID) -> Optional[int]:
        """
        Get the version number of the latest released version in the given environment.
        """
        query = f"""SELECT version
                    FROM {ConfigurationModel.table_name()}
                    WHERE environment=$1 AND released=true
                    ORDER BY version DESC
                    LIMIT 1
                    """
        result = await cls._fetchrow(query, cls._get_value(environment))
        if not result:
            return None
        return int(result["version"])

    @classmethod
    async def get_agents(
        cls, environment: uuid.UUID, version: int, *, connection: Optional[asyncpg.connection.Connection] = None
    ) -> List[str]:
        """
        Returns a list of all agents that have resources defined in this configuration model
        """
        (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version)
        query = "SELECT DISTINCT agent FROM " + Resource.table_name() + " WHERE " + filter_statement
        result = []
        async with cls.get_connection(connection) as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    result.append(record["agent"])
        return result

    @classmethod
    async def get_versions(cls, environment: uuid.UUID, start: int = 0, limit: int = DBLIMIT) -> List["ConfigurationModel"]:
        """
        Get all versions for an environment ordered descending
        """
        versions = await cls.get_list(
            order_by_column="version", order="DESC", limit=limit, offset=start, environment=environment
        )
        return versions

    async def delete_cascade(self) -> None:
        async with self.get_connection() as con:
            async with con.transaction():
                # Delete all code associated with this version
                await Code.delete_all(connection=con, environment=self.environment, version=self.version)

                # Delete ConfigurationModel and cascade delete on connected tables
                await self.delete(connection=con)

            # Delete facts when the resources in this version are the only
            await con.execute(
                f"""
                DELETE FROM {Parameter.table_name()} p
                WHERE(
                    environment=$1 AND
                    resource_id<>'' AND
                    NOT EXISTS(
                        SELECT 1
                        FROM {Resource.table_name()} r
                        WHERE p.resource_id=r.resource_id
                    )
                )
                """,
                self.environment,
            )

    async def get_undeployable(self) -> List[m.ResourceIdStr]:
        """
        Returns a list of resource ids (NOT resource version ids) of resources with an undeployable state
        """
        return self.undeployable

    async def get_skipped_for_undeployable(self) -> List[m.ResourceIdStr]:
        """
        Returns a list of resource ids (NOT resource version ids)
        of resources which should get a skipped_for_undeployable state
        """
        return self.skipped_for_undeployable

    async def mark_done(self, *, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """mark this deploy as done"""
        subquery = f"""(EXISTS(
                    SELECT 1
                    FROM {Resource.table_name()}
                    WHERE environment=$1 AND model=$2 AND status != $3
                ))::boolean
            """
        query = f"""UPDATE {self.table_name()}
                SET
                deployed=True, result=(CASE WHEN {subquery} THEN $4::versionstate ELSE $5::versionstate END)
                WHERE environment=$1 AND version=$2 RETURNING result
            """
        values = [
            self._get_value(self.environment),
            self._get_value(self.version),
            self._get_value(const.ResourceState.deployed),
            self._get_value(const.VersionState.failed),
            self._get_value(const.VersionState.success),
        ]
        result = await self._fetchval(query, *values, connection=connection)
        self.result = const.VersionState[result]
        self.deployed = True

    @classmethod
    async def mark_done_if_done(
        cls, environment: uuid.UUID, version: int, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        async with cls.get_connection(connection) as con:
            """
            Performs the query to mark done if done. Expects to be called outside of any transaction that writes resource state
            in order to prevent race conditions.
            """
            async with con.transaction():
                query = f"""UPDATE {ConfigurationModel.table_name()}
                                SET deployed=True,
                                    result=(CASE WHEN (
                                                 EXISTS(SELECT 1
                                                        FROM {Resource.table_name()}
                                                        WHERE environment=$1 AND model=$2 AND status != $3)
                                                 )::boolean
                                            THEN $4::versionstate
                                            ELSE $5::versionstate END
                                    )
                                WHERE environment=$1 AND version=$2 AND
                                      total=(SELECT COUNT(*)
                                             FROM {Resource.table_name()}
                                             WHERE environment=$1 AND model=$2 AND status = any($6::resourcestate[])
                            )"""
                values = [
                    cls._get_value(environment),
                    cls._get_value(version),
                    cls._get_value(ResourceState.deployed),
                    cls._get_value(const.VersionState.failed),
                    cls._get_value(const.VersionState.success),
                    cls._get_value(DONE_STATES),
                ]
                await cls._execute_query(query, *values, connection=con)

    @classmethod
    async def get_increment(cls, environment: uuid.UUID, version: int) -> tuple[set[m.ResourceIdStr], set[m.ResourceIdStr]]:
        """
        Find resources incremented by this version compared to deployment state transitions per resource

        available -> next version
        not present -> increment
        skipped -> increment
        unavailable -> increment
        error -> increment
        Deployed and same hash -> not increment
        deployed and different hash -> increment
        """
        projection_a = ["resource_id", "status", "attribute_hash", "attributes"]
        projection = ["resource_id", "status", "attribute_hash"]

        # get resources for agent
        resources = await Resource.get_resources_for_version_raw(environment, version, projection_a)

        # to increment
        increment: list[abc.Mapping[str, Any]] = []
        not_increment: list[abc.Mapping[str, Any]] = []
        # todo in this version
        work: list[abc.Mapping[str, object]] = [r for r in resources if r["status"] not in UNDEPLOYABLE_NAMES]

        # get versions
        query = f"SELECT version FROM {cls.table_name()} WHERE environment=$1 AND released=true ORDER BY version DESC"
        values = [cls._get_value(environment)]
        version_records = await cls._fetch_query(query, *values)

        versions = [record["version"] for record in version_records]

        for version in versions:
            # todo in next version
            next = []

            vresources = await Resource.get_resources_for_version_raw(environment, version, projection)
            id_to_resource = {r["resource_id"]: r for r in vresources}

            for res in work:
                # not present -> increment
                if res["resource_id"] not in id_to_resource:
                    increment.append(res)
                    continue

                ores = id_to_resource[res["resource_id"]]

                status = ores["status"]
                # available -> next version
                if status == ResourceState.available.name:
                    next.append(res)

                # deploying
                # same hash -> next version
                # different hash -> increment
                elif status == ResourceState.deploying.name:
                    if res["attribute_hash"] == ores["attribute_hash"]:
                        next.append(res)
                    else:
                        increment.append(res)

                # -> increment
                elif status in [
                    ResourceState.failed.name,
                    ResourceState.cancelled.name,
                    ResourceState.skipped_for_undefined.name,
                    ResourceState.undefined.name,
                    ResourceState.skipped.name,
                    ResourceState.unavailable.name,
                ]:
                    increment.append(res)

                elif status == ResourceState.deployed.name:
                    if res["attribute_hash"] == ores["attribute_hash"]:
                        #  Deployed and same hash -> not increment
                        not_increment.append(res)
                    else:
                        # Deployed and different hash -> increment
                        increment.append(res)
                else:
                    LOGGER.warning("Resource in unexpected state: %s, %s", ores["status"], ores["resource_version_id"])
                    increment.append(res)

            work = next
            if not work:
                break
        if work:
            increment.extend(work)

        negative: set[ResourceIdStr] = {res["resource_id"] for res in not_increment}

        # patch up the graph
        # 1-include stuff for send-events.
        # 2-adapt requires/provides to get closured set

        outset: set[ResourceIdStr] = {res["resource_id"] for res in increment}
        original_provides: dict[str, List[ResourceIdStr]] = defaultdict(lambda: [])
        send_events: list[ResourceIdStr] = []

        # build lookup tables
        for res in resources:
            for req in res["attributes"]["requires"]:
                original_provides[req].append(res["resource_id"])
            if "send_event" in res["attributes"] and res["attributes"]["send_event"]:
                send_events.append(res["resource_id"])

        # recursively include stuff potentially receiving events from nodes in the increment
        increment_work: list[ResourceIdStr] = list(outset)
        done: set[ResourceIdStr] = set()
        while increment_work:
            current: ResourceIdStr = increment_work.pop()
            if current not in send_events:
                # not sending events, so no receivers
                continue

            if current in done:
                continue
            done.add(current)

            provides = original_provides[current]
            increment_work.extend(provides)
            outset.update(provides)
            negative.difference_update(provides)

        return outset, negative

    @classmethod
    def active_version_subquery(cls, environment: uuid.UUID) -> Tuple[str, List[object]]:
        query_builder = SimpleQueryBuilder(
            select_clause="""
            SELECT max(version)
            """,
            from_clause=f" FROM {cls.table_name()} ",
            filter_statements=[" environment = $1 AND released = TRUE"],
            values=[cls._get_value(environment)],
        )
        return query_builder.build()

    @classmethod
    def desired_state_versions_subquery(cls, environment: uuid.UUID) -> Tuple[str, List[object]]:
        active_version, values = cls.active_version_subquery(environment)
        # Coalesce to 0 in case there is no active version
        active_version = f"(SELECT COALESCE(({active_version}), 0))"
        query_builder = SimpleQueryBuilder(
            select_clause=f"""SELECT cm.version, cm.date, cm.total,
                                     version_info -> 'export_metadata' ->> 'message' as message,
                                     version_info -> 'export_metadata' ->> 'type' as type,
                                        (CASE WHEN cm.version = {active_version} THEN 'active'
                                            WHEN cm.version > {active_version} THEN 'candidate'
                                            WHEN cm.version < {active_version} AND cm.released=TRUE THEN 'retired'
                                            ELSE 'skipped_candidate'
                                        END) as status""",
            from_clause=f" FROM {cls.table_name()} as cm",
            filter_statements=[" environment = $1 "],
            values=values,
        )
        return query_builder.build()


class Code(BaseDocument):
    """
    A code deployment

    :param environment: The environment this code belongs to
    :param version: The version of configuration model it belongs to
    :param resource: The resource type this code belongs to
    :param sources: The source code of plugins (phasing out)  form:
        {code_hash:(file_name, provider.__module__, source_code, [req])}
    :param requires: Python requires for the source code above
    :param source_refs: file hashes refering to files in the file store
        {code_hash:(file_name, provider.__module__, [req])}
    """

    __primary_key__ = ("environment", "resource", "version")

    environment: uuid.UUID
    resource: str
    version: int
    source_refs: Optional[Dict[str, Tuple[str, str, List[str]]]] = None

    @classmethod
    async def get_version(cls, environment: uuid.UUID, version: int, resource: str) -> Optional["Code"]:
        codes = await cls.get_list(environment=environment, version=version, resource=resource)
        if len(codes) == 0:
            return None

        return codes[0]

    @classmethod
    async def get_versions(cls, environment: uuid.UUID, version: int) -> List["Code"]:
        codes = await cls.get_list(environment=environment, version=version)
        return codes

    @classmethod
    async def copy_versions(
        cls,
        environment: uuid.UUID,
        old_version: int,
        new_version: int,
        *,
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> None:
        """
        Copy all code for one model version to another.
        """
        query: str = f"""
            INSERT INTO {cls.table_name()} (environment, resource, version, source_refs)
            SELECT environment, resource, $1, source_refs
            FROM {cls.table_name()}
            WHERE environment=$2 AND version=$3
        """
        await cls._execute_query(
            query, cls._get_value(new_version), cls._get_value(environment), cls._get_value(old_version), connection=connection
        )


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
    resources: Dict[str, Any] = {}

    @classmethod
    async def update_resource(cls, dryrun_id: uuid.UUID, resource_id: m.ResourceVersionIdStr, dryrun_data: JsonType) -> None:
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
    ) -> List[m.DryRun]:
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
    uri: str
    read: bool = False
    cleared: bool = False

    @classmethod
    async def clean_up_notifications(cls) -> None:
        environments = await Environment.get_list()
        for env in environments:
            time_to_retain_logs = await env.get(NOTIFICATION_RETENTION)
            keep_notifications_until = datetime.datetime.now().astimezone() - datetime.timedelta(days=time_to_retain_logs)
            LOGGER.info(
                "Cleaning up notifications in environment %s that are older than %s", env.name, keep_notifications_until
            )
            query = f"DELETE FROM {cls.table_name()} WHERE created < $1 AND environment = $2"
            await cls._execute_query(query, cls._get_value(keep_notifications_until), cls._get_value(env.id))

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


_classes = [
    Project,
    Environment,
    UnknownParameter,
    AgentProcess,
    AgentInstance,
    Agent,
    Resource,
    ResourceAction,
    ConfigurationModel,
    Code,
    Parameter,
    DryRun,
    Compile,
    Report,
    Notification,
    EnvironmentMetricsGauge,
    EnvironmentMetricsTimer,
]


def set_connection_pool(pool: asyncpg.pool.Pool) -> None:
    LOGGER.debug("Connecting data classes")
    for cls in _classes:
        cls.set_connection_pool(pool)


async def disconnect() -> None:
    LOGGER.debug("Disconnecting data classes")
    # Enable `return_exceptions` to make sure we wait until all close_connection_pool() calls are finished
    # or until the gather itself is cancelled.
    result = await asyncio.gather(*[cls.close_connection_pool() for cls in _classes], return_exceptions=True)
    exceptions = [r for r in result if r is not None and isinstance(r, Exception)]
    if exceptions:
        raise exceptions[0]


PACKAGE_WITH_UPDATE_FILES = inmanta.db.versions

# Name of core schema in the DB schema verions
# prevent import loop
CORE_SCHEMA_NAME = schema.CORE_SCHEMA_NAME


async def connect(
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
        await pool.close()
        await disconnect()
        raise e
