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
import uuid
import warnings
from abc import ABC, abstractmethod
from collections import defaultdict
from configparser import RawConfigParser
from itertools import chain
from typing import (
    Any,
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
)

import asyncpg
import dateutil
import pydantic
import typing_inspect
from asyncpg.protocol import Record

import inmanta.db.versions
from inmanta import const, resources, util
from inmanta.const import DONE_STATES, UNDEPLOYABLE_NAMES, AgentStatus, LogLevel, ResourceState
from inmanta.data import model as m
from inmanta.data import schema
from inmanta.server import config
from inmanta.stable_api import stable_api
from inmanta.types import JsonType, PrimitiveTypes

LOGGER = logging.getLogger(__name__)

DBLIMIT = 100000
APILIMIT = 1000


# TODO: disconnect
# TODO: difference between None and not set


@enum.unique
class QueryType(str, enum.Enum):
    def _generate_next_value_(name: str, start: int, count: int, last_values: List[object]) -> object:  # noqa: N805
        """
        Make enum.auto() return the name of the enum member in lower case.
        """
        return name.lower()

    EQUALS = enum.auto()
    CONTAINS = enum.auto()
    IS_NOT_NULL = enum.auto()
    CONTAINS_PARTIAL = enum.auto()
    RANGE = enum.auto()


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


RangeConstraint = List[Tuple[RangeOperator, int]]
DateRangeConstraint = List[Tuple[RangeOperator, datetime.datetime]]
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


class DatabaseOrder:
    """Represents an ordering for database queries"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[str, Union[Type[datetime.datetime], Type[int], Type[str]]]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder """
        return {}

    @classmethod
    def validator_dataclass(cls) -> Type["BaseDocument"]:
        """ The class used for checking whether the ordering is valid for a table"""
        return BaseDocument

    @classmethod
    def parse_from_string(
        cls,
        sort: str,
    ) -> "DatabaseOrder":
        valid_sort_pattern: Pattern[str] = re.compile(
            f"^({'|'.join(cls.get_valid_sort_columns())})\\.(asc|desc)$", re.IGNORECASE
        )
        match = valid_sort_pattern.match(sort)
        if match and len(match.groups()) == 2:
            order_by_column = match.groups()[0].lower()
            validated_order_by_column, validated_order = cls.validator_dataclass()._validate_order_strict(
                order_by_column=order_by_column, order=match.groups()[1].upper()
            )
            return cls(order_by_column=validated_order_by_column, order=validated_order)
        raise InvalidSort(f"Sort parameter invalid: {sort}")

    def __init__(
        self,
        order_by_column: ColumnNameStr,
        order: PagingOrder,
    ) -> None:
        """The order_by_column and order parameters should be validated"""
        self.order_by_column = order_by_column
        self.order = order

    def get_order_by_column_db_name(self) -> ColumnNameStr:
        """The validated column name string as it should be used in the database queries"""
        return self.order_by_column

    def get_order(self) -> PagingOrder:
        """ The order string representing the direction the results should be sorted by"""
        return self.order

    def is_nullable_column(self) -> bool:
        """Is the current order by column type nullable (optional) or not"""
        column_type = self.get_order_by_column_type()
        return typing_inspect.is_optional_type(column_type)

    def coalesce_to_min(self, value_reference: str) -> ColumnNameStr:
        """If the order by column is nullable, coalesce the parameter value to the minimum value of the specific type
        This is required for the comparisons used for paging, for example, because comparing a value to
        NULL always yields NULL.
        """
        if self.is_nullable_column():
            column_type = self.get_order_by_column_type()
            if typing_inspect.get_args(column_type)[0] == datetime.datetime:
                return ColumnNameStr(f"COALESCE({value_reference}, to_timestamp(0))")
            elif typing_inspect.get_args(column_type)[0] == bool:
                return ColumnNameStr(f"COALESCE({value_reference}, FALSE)")
            else:
                return ColumnNameStr(f"COALESCE({value_reference}, '')")
        return ColumnNameStr(value_reference)

    def __str__(self) -> str:
        return f"{self.order_by_column}.{self.order}"

    def get_order_by_column_type(self) -> Union[Type[datetime.datetime], Type[int], Type[str]]:
        """ The type of the order by column"""
        return self.get_valid_sort_columns()[self.order_by_column]

    def get_order_by_column_api_name(self) -> str:
        """ The name of the column that the results should be ordered by """
        return self.order_by_column

    def get_min_time(self) -> Optional[datetime.datetime]:
        if self.get_order_by_column_type() == datetime.datetime:
            return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        else:
            return None

    def get_max_time(self) -> Optional[datetime.datetime]:
        if self.get_order_by_column_type() == datetime.datetime:
            return datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
        else:
            return None

    def ensure_boundary_type(
        self, order_by_column_value: Union[datetime.datetime, int, bool, str]
    ) -> Union[datetime.datetime, int, bool, str]:
        """Converts a value to the type of the order by column,
        can be used to make sure a boundary (start or end) is the correct type"""
        column_type = self.get_order_by_column_type()
        if isinstance(order_by_column_value, str):
            if column_type == datetime.datetime:
                return dateutil.parser.isoparse(order_by_column_value)
            elif column_type == int:
                return int(order_by_column_value)
            elif column_type == bool:
                return order_by_column_value.lower() == "true"
        return order_by_column_value

    @property
    def id_column(self) -> ColumnNameStr:
        """Name of the id column of this database order"""
        return ColumnNameStr("id")

    def as_filter(
        self,
        offset: int,
        column_value: Optional[object] = None,
        id_value: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[bool] = True,
    ) -> Tuple[List[str], List[object]]:
        """ Get the column and id values as filters"""
        filter_statements = []
        values: List[object] = []
        relation = ">" if start else "<"
        if (column_value is not None or self.is_nullable_column()) and id_value:
            filter_statements.append(
                f"""({self.get_order_by_column_db_name()}, {self.id_column}) {relation}
                    ({self.coalesce_to_min(f"${str(offset)}")}, ${str(offset + 1)})"""
            )
            values.append(BaseDocument._get_value(column_value))
            values.append(BaseDocument._get_value(id_value))
        elif column_value is not None:
            filter_statements.append(f"{self.get_order_by_column_db_name()} {relation} ${str(offset)}")
            values.append(BaseDocument._get_value(column_value))
        return filter_statements, values

    def as_start_filter(
        self,
        offset: int,
        start: Optional[object] = None,
        first_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> Tuple[List[str], List[object]]:
        """ Get the start and first_id values as start filters"""
        return self.as_filter(offset, column_value=start, id_value=first_id, start=True)

    def as_end_filter(
        self,
        offset: int,
        end: Optional[object] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> Tuple[List[str], List[object]]:
        """ Get the end and last_id values as end filters"""
        return self.as_filter(offset, column_value=end, id_value=last_id, start=False)


class VersionedResourceOrder(DatabaseOrder):
    """Represents the ordering by which resources should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[str, Union[Type[datetime.datetime], Type[int], Type[str]]]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder """
        return {"resource_type": str, "agent": str, "resource_id_value": str}

    @classmethod
    def validator_dataclass(cls) -> Type["BaseDocument"]:
        return Resource

    @property
    def id_column(self) -> ColumnNameStr:
        """Name of the id column of this database order"""
        return ColumnNameStr("resource_version_id")


class ResourceOrder(VersionedResourceOrder):
    """Represents the ordering by which resources should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[str, Union[Type[datetime.datetime], Type[int], Type[str]]]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder """
        return {**super().get_valid_sort_columns(), "status": str}

    def get_order_by_column_db_name(self) -> ColumnNameStr:
        return ColumnNameStr(
            f"{super().get_order_by_column_db_name()}{'::text' if self._should_be_treated_as_string() else ''}"
        )

    def _should_be_treated_as_string(self) -> bool:
        """Ensure that records are sorted alphabetically by status instead of the enum order"""
        return self.order_by_column == "status"


class ResourceHistoryOrder(DatabaseOrder):
    """Represents the ordering by which resource history should be sorted """

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[str, Union[Type[datetime.datetime], Type[int], Type[str]]]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder """
        return {"date": datetime.datetime}

    @classmethod
    def validator_dataclass(cls) -> Type["BaseDocument"]:
        # Sorting based on the date of the configuration model
        return ConfigurationModel


class ResourceLogOrder(DatabaseOrder):
    """Represents the ordering by which resource logs should be sorted """

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[str, Union[Type[datetime.datetime], Type[int], Type[str]]]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder """
        return {"timestamp": datetime.datetime}

    @classmethod
    def validator_dataclass(cls) -> Type["BaseDocument"]:
        return ResourceAction


class CompileReportOrder(DatabaseOrder):
    """Represents the ordering by which compile reports should be sorted """

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[str, Union[Type[datetime.datetime], Type[int], Type[str]]]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder """
        return {"requested": datetime.datetime}

    @classmethod
    def validator_dataclass(cls) -> Type["BaseDocument"]:
        return Compile


class AgentOrder(DatabaseOrder):
    """Represents the ordering by which agents should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[str, Union[Type[datetime.datetime], Type[int], Type[str]]]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder """
        return {
            "name": str,
            "process_name": Optional[str],
            "paused": bool,
            "last_failover": Optional[datetime.datetime],
            "status": str,
        }

    @classmethod
    def validator_dataclass(cls) -> Type["BaseDocument"]:
        return Agent

    @property
    def id_column(self) -> ColumnNameStr:
        """Name of the id column of this database order"""
        return ColumnNameStr("name")

    def get_order_by_column_db_name(self) -> ColumnNameStr:
        # This ordering is valid on nullable columns, which should be coalesced to the minimum value of the specific type
        return self.coalesce_to_min(self.order_by_column)


class DesiredStateVersionOrder(DatabaseOrder):
    """Represents the ordering by which desired state versions should be sorted"""

    @classmethod
    def get_valid_sort_columns(cls) -> Dict[str, Union[Type[datetime.datetime], Type[int], Type[str]]]:
        """Describes the names and types of the columns that are valid for this DatabaseOrder """
        return {
            "version": int,
        }

    @classmethod
    def validator_dataclass(cls) -> Type["BaseDocument"]:
        return ConfigurationModel

    @property
    def id_column(self) -> ColumnNameStr:
        """Name of the id column of this database order"""
        return ColumnNameStr("version")


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
        """ Join multiple filter statements """
        if filter_statements:
            return "WHERE " + " AND ".join(filter_statements)
        return ""

    @abstractmethod
    def from_clause(self, from_clause: str) -> "BaseQueryBuilder":
        """ Set the from clause of the query"""
        raise NotImplementedError()

    @property
    def offset(self) -> int:
        """ The current offset of the values to be used for filter statements"""
        return len(self.values) + 1

    @abstractmethod
    def filter(self, filter_statements: List[str], values: List[object]) -> "BaseQueryBuilder":
        """ Add filters to the query """
        raise NotImplementedError()

    @abstractmethod
    def build(self) -> Tuple[str, List[object]]:
        """ Builds up the full query string, and the parametrized value list, ready to be executed """
        raise NotImplementedError()


class SimpleQueryBuilder(BaseQueryBuilder):
    """ A query builder suitable for most queries """

    def __init__(
        self,
        select_clause: Optional[str] = None,
        from_clause: Optional[str] = None,
        filter_statements: Optional[List[str]] = None,
        values: Optional[List[object]] = None,
        db_order: Optional[DatabaseOrder] = None,
        limit: Optional[int] = None,
        backward_paging: Optional[bool] = False,
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
        """
        super().__init__(select_clause, from_clause, filter_statements, values)
        self.db_order = db_order
        self.limit = limit
        self.backward_paging = backward_paging

    def select(self, select_clause: str) -> "SimpleQueryBuilder":
        """ Set the select clause of the query """
        return SimpleQueryBuilder(
            select_clause,
            self._from_clause,
            self.filter_statements,
            self.values,
            self.db_order,
            self.limit,
            self.backward_paging,
        )

    def from_clause(self, from_clause: str) -> "SimpleQueryBuilder":
        """ Set the from clause of the query"""
        return SimpleQueryBuilder(
            self.select_clause,
            from_clause,
            self.filter_statements,
            self.values,
            self.db_order,
            self.limit,
            self.backward_paging,
        )

    def order_and_limit(
        self, db_order: DatabaseOrder, limit: Optional[int] = None, backward_paging: Optional[bool] = False
    ) -> "SimpleQueryBuilder":
        """ Set the order and limit of the query """
        return SimpleQueryBuilder(
            self.select_clause, self._from_clause, self.filter_statements, self.values, db_order, limit, backward_paging
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
        )

    def build(self) -> Tuple[str, List[object]]:
        if not self.select_clause or not self._from_clause:
            raise InvalidQueryParameter("A valid query must have a SELECT and a FROM clause")
        full_query = f"""{self.select_clause}
                         {self._from_clause}
                         {self._join_filter_statements(self.filter_statements)}
                         """
        if self.db_order:
            order = self.db_order.get_order()
            order_by_column = self.db_order.get_order_by_column_db_name()
            if self.backward_paging:
                backward_paging_order = order.invert().db_form
                full_query += (
                    f" ORDER BY {order_by_column} {backward_paging_order}, {self.db_order.id_column} {backward_paging_order}"
                )
            else:
                full_query += f" ORDER BY {order_by_column} {order.db_form}, {self.db_order.id_column}  {order.db_form}"
        if self.limit is not None:
            if self.limit > DBLIMIT:
                raise InvalidQueryParameter(f"Limit cannot be bigger than {DBLIMIT}, got {self.limit}")
            elif self.limit > 0:
                full_query += " LIMIT " + str(self.limit)
        if self.db_order and self.backward_paging:
            full_query = f"""SELECT * FROM ({full_query}) AS matching_records
                            ORDER BY {self.db_order.get_order_by_column_db_name()} {self.db_order.get_order().db_form},
                                     {self.db_order.id_column} {self.db_order.get_order().db_form}"""

        return full_query, self.values


class PageCountQueryBuilder(BaseQueryBuilder):
    """A specific query builder for counting records before and after
    the current page returned by a select query, as well as the total number of records"""

    def __init__(
        self,
        select_clause: Optional[str] = None,
        from_clause: Optional[str] = None,
        filter_statements: Optional[List[str]] = None,
        values: Optional[List[object]] = None,
    ) -> None:
        """
        :param select_clause: The select clause of the query, optional, `page_count()` can be used to provide a query builder
                              with a specific select clause
        :param from_clause: The from clause of the query
        :param filter_statements: A list of filters for the query
        :param values: The values to be used for the filter statements
        """
        super().__init__(select_clause, from_clause, filter_statements, values)

    def page_count(
        self,
        db_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
    ) -> "PageCountQueryBuilder":
        """ Determine the filters and select clause for a page count query"""
        order = db_order.get_order()
        values = []
        if "ASC" in order:
            before_filter_statements, before_values = db_order.as_end_filter(self.offset, end, last_id)
            values.extend(before_values)
            after_filter_statements, after_values = db_order.as_start_filter(self.offset + len(before_values), start, first_id)
            values.extend(after_values)
        else:
            before_filter_statements, before_values = db_order.as_start_filter(self.offset, start, first_id)
            values.extend(before_values)
            after_filter_statements, after_values = db_order.as_end_filter(self.offset + len(before_values), end, last_id)
            values.extend(after_values)
        before_filter = self._join_filter_statements(before_filter_statements)
        after_filter = self._join_filter_statements(after_filter_statements)
        id_column_name = db_order.id_column
        select_clause = (
            f"SELECT COUNT({id_column_name}) as count_total, "
            f"COUNT({id_column_name}) filter ({before_filter}) as count_before, "
            f"COUNT({id_column_name}) filter ({after_filter}) as count_after "
        )
        return PageCountQueryBuilder(select_clause, self._from_clause, self.filter_statements, self.values + values)

    def from_clause(self, from_clause: str) -> "PageCountQueryBuilder":
        """ Set the from clause of the query"""
        return PageCountQueryBuilder(self.select_clause, from_clause, self.filter_statements, self.values)

    def filter(self, filter_statements: List[str], values: List[object]) -> "PageCountQueryBuilder":
        return PageCountQueryBuilder(
            self.select_clause, self._from_clause, self.filter_statements + filter_statements, self.values + values
        )

    def build(self) -> Tuple[str, List[object]]:
        if not self.select_clause or not self._from_clause:
            raise InvalidQueryParameter("A valid query must have a SELECT and a FROM clause")
        full_query = f"""{self.select_clause}
                         {self._from_clause}
                         {self._join_filter_statements(self.filter_statements)}
                        """
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
        unique: bool = False,
        reference: bool = False,
        part_of_primary_key: bool = False,
        **kwargs: object,
    ) -> None:

        self._field_type = field_type
        self._required = required
        self._reference = reference
        self._part_of_primary_key = part_of_primary_key

        if "default" in kwargs:
            self._default = True
            self._default_value = kwargs["default"]
        else:
            self._default = False
            self._default_value = None

        self._unique = unique

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

    def is_unique(self) -> bool:
        return self._unique

    unique = property(is_unique)

    def is_reference(self) -> bool:
        return self._reference

    reference = property(is_reference)

    def is_part_of_primary_key(self) -> bool:
        return self._part_of_primary_key

    part_of_primary_key = property(is_part_of_primary_key)


class DataDocument(object):
    """
    A baseclass for objects that represent data in inmanta. The main purpose of this baseclass is to group dict creation
    logic. These documents are not stored in the database
    (use BaseDocument for this purpose). It provides a to_dict method that the inmanta rpc can serialize. You can store
    DataDocument childeren in BaseDocument fields, they will be serialized to dict. However, on retrieval this is not
    performed.
    """

    def __init__(self, **kwargs: object) -> None:
        self._data = kwargs

    def to_dict(self) -> JsonType:
        """
        Return a dict representation of this object.
        """
        return self._data


class DocumentMeta(type):
    def __new__(cls, class_name: str, bases: Tuple[type, ...], dct: Dict[str, object]) -> Type:
        dct["_fields"] = {}
        for name, field in dct.items():
            if isinstance(field, Field):
                dct["_fields"][name] = field

        for base in bases:
            if hasattr(base, "_fields"):
                dct["_fields"].update(base._fields)

        return type.__new__(cls, class_name, bases, dct)


TBaseDocument = TypeVar("TBaseDocument", bound="BaseDocument")  # Part of the stable API


@stable_api
class BaseDocument(object, metaclass=DocumentMeta):
    """
    A base document in the database. Subclasses of this document determine collections names. This type is mainly used to
    bundle query methods and generate validate and query methods for optimized DB access. This is not a full ODM.
    """

    _connection_pool: Optional[asyncpg.pool.Pool] = None

    @classmethod
    def get_connection(cls) -> asyncpg.pool.PoolAcquireContext:
        """
        Returns a PoolAcquireContext that can be either awaited or used in an async with statement to receive a Connection.
        """
        # Make pypi happy
        assert cls._connection_pool is not None
        return cls._connection_pool.acquire()

    @classmethod
    def table_name(cls) -> str:
        """
        Return the name of the collection
        """
        return cls.__name__.lower()

    def __init__(self, from_postgres: bool = False, **kwargs: object) -> None:
        self.__fields = self._create_dict_wrapper(from_postgres, kwargs)

    @classmethod
    def get_valid_field_names(cls) -> List[str]:
        return list(cls._fields.keys())

    @classmethod
    def _create_dict(cls, from_postgres: bool, kwargs: Dict[str, object]) -> JsonType:
        result = {}
        fields = cls._fields.copy()

        if "id" in fields and "id" not in kwargs:
            kwargs["id"] = cls._new_id()

        for name, value in kwargs.items():
            if name not in fields:
                raise AttributeError("%s field is not defined for this document %s" % (name, cls.table_name()))

            if value is None and fields[name].required:
                raise TypeError("%s field is required" % name)

            if (
                not fields[name].reference
                and value is not None
                and not (value.__class__ is fields[name].field_type or isinstance(value, fields[name].field_type))
            ):
                # pgasync does not convert a jsonb field to a dict
                if from_postgres and isinstance(value, str) and fields[name].field_type is dict:
                    value = json.loads(value)
                # pgasync does not convert a enum field to a enum type
                elif from_postgres and isinstance(value, str) and issubclass(fields[name].field_type, enum.Enum):
                    value = fields[name].field_type[value]
                else:
                    raise TypeError(
                        "Field %s should have the correct type (%s instead of %s)"
                        % (name, fields[name].field_type.__name__, type(value).__name__)
                    )

            if from_postgres or value is not None:
                result[name] = value
            elif fields[name].default:
                result[name] = fields[name].default_value

            del fields[name]

        for name in list(fields.keys()):
            if fields[name].default:
                result[name] = fields[name].default_value
                del fields[name]

            elif not fields[name].required:
                del fields[name]

        if len(fields) > 0:
            raise AttributeError("%s fields are required." % ", ".join(fields.keys()))

        return result

    @classmethod
    def _get_names_of_primary_key_fields(cls) -> List[str]:
        fields = cls._fields.copy()
        return [name for name, value in fields.items() if value.is_part_of_primary_key()]

    def _get_filter_on_primary_key_fields(self, offset: int = 1) -> Tuple[str, List[Any]]:
        names_primary_key_fields = self._get_names_of_primary_key_fields()
        query = {field_name: self.__getattribute__(field_name) for field_name in names_primary_key_fields}
        return self._get_composed_filter(offset=offset, **query)

    @classmethod
    def _create_dict_wrapper(cls, from_postgres: bool, kwargs: Dict[str, object]) -> JsonType:
        return cls._create_dict(from_postgres, kwargs)

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
        except (asyncio.TimeoutError, asyncio.CancelledError):
            cls._connection_pool.terminate()
        finally:
            cls._connection_pool = None

    def _get_field(self, name: str) -> Optional[Field]:
        if hasattr(self.__class__, name):
            field = getattr(self.__class__, name)
            if isinstance(field, Field):
                return field

        return None

    def __getattribute__(self, name: str) -> object:
        if name[0] == "_":
            return object.__getattribute__(self, name)

        field = self._get_field(name)
        if field is not None:
            if name in self.__fields:
                return self.__fields[name]
            else:
                return None

        return object.__getattribute__(self, name)

    def __setattr__(self, name: str, value: object) -> None:
        if name[0] == "_":
            return object.__setattr__(self, name, value)

        field = self._get_field(name)
        if field is not None:
            # validate
            if value is not None and not isinstance(value, field.field_type):
                raise TypeError("Field %s should be of type %s" % (name, field.field_type))

            self.__fields[name] = value
            return

        raise AttributeError(name)

    @classmethod
    def _convert_field_names_to_db_column_names(cls, field_dict: Dict[str, Any]) -> Dict[str, Any]:
        return field_dict

    def _get_column_names_and_values(self) -> Tuple[List[str], List[str]]:
        column_names: List[str] = []
        values: List[str] = []
        for name, typing in self._fields.items():
            if self._fields[name].reference:
                continue
            value = None
            if name in self.__fields:
                value = self.__fields[name]

            if typing.required and value is None:
                raise TypeError("%s should have field '%s'" % (self.__name__, name))

            if value is not None:
                if not isinstance(value, typing.field_type):
                    raise TypeError("Value of field %s does not have the correct type" % name)
            column_names.append(name)
            values.append(self._get_value(value))

        return (column_names, values)

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
    async def _fetchval(cls, query: str, *values: object) -> object:
        async with cls.get_connection() as con:
            return await con.fetchval(query, *values)

    @classmethod
    async def _fetchrow(cls, query: str, *values: object) -> Record:
        async with cls.get_connection() as con:
            return await con.fetchrow(query, *values)

    @classmethod
    async def _fetch_query(
        cls, query: str, *values: object, connection: Optional[asyncpg.connection.Connection] = None
    ) -> List[Record]:
        if connection is None:
            async with cls.get_connection() as con:
                return await con.fetch(query, *values)
        return await connection.fetch(query, *values)

    @classmethod
    async def _execute_query(
        cls, query: str, *values: object, connection: Optional[asyncpg.connection.Connection] = None
    ) -> str:
        if connection:
            return await connection.execute(query, *values)
        async with cls.get_connection() as con:
            return await con.execute(query, *values)

    @classmethod
    async def insert_many(cls, documents: Sequence["BaseDocument"]) -> None:
        """
        Insert multiple objects at once
        """
        if not documents:
            return

        columns = list(cls._fields.copy().keys())
        records = []
        for doc in documents:
            current_record = []
            for col in columns:
                current_record.append(cls._get_value(doc.__getattribute__(col)))
            current_record = tuple(current_record)
            records.append(current_record)

        async with cls.get_connection() as con:
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

    async def update_fields(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: Any) -> None:
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
        cls: Type[TBaseDocument], connection: Optional[asyncpg.connection.Connection] = None, **query: object
    ) -> Optional[TBaseDocument]:
        results = await cls.get_list(connection=connection, **query)
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

        if order_by_column not in cls._fields:
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
        order_by_column: Optional[str] = None,
        order: str = "ASC",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: bool = False,
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
            connection=connection,
            columns=None,
            **query,
        )

    @classmethod
    async def get_list_with_columns(
        cls: Type[TBaseDocument],
        order_by_column: Optional[str] = None,
        order: str = "ASC",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: bool = False,
        connection: Optional[asyncpg.connection.Connection] = None,
        columns: Optional[List[str]] = None,
        **query: object,
    ) -> List[TBaseDocument]:
        """
        Get a list of documents matching the filter args
        """
        if order_by_column:
            cls._validate_order(order_by_column, order)

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
        result = await cls.select_query(sql_query, values, no_obj=no_obj, connection=connection)
        return result

    @classmethod
    async def get_list_paged(
        cls: Type[TBaseDocument],
        page_by_column: str,
        order_by_column: Optional[str] = None,
        order: str = "ASC",
        limit: Optional[int] = None,
        start: Optional[Any] = None,
        end: Optional[Any] = None,
        no_obj: bool = False,
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
        if order_by_column:
            cls._validate_order(order_by_column, order)

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
            (filter_statement, value) = cls._get_filter(key, value, index_count, col_name_prefix=col_name_prefix)
            filter_statements.append(filter_statement)
            values.extend(value)
            index_count += len(value)
        filter_as_string = " AND ".join(filter_statements)
        return (filter_as_string, values)

    @classmethod
    def _get_filter(cls, name: str, value: Any, index: int, col_name_prefix: Optional[str] = None) -> Tuple[str, List[object]]:
        if value is None:
            return (name + " IS NULL", [])
        filter_statement = name + "=$" + str(index)
        if col_name_prefix is not None:
            filter_statement = col_name_prefix + "." + filter_statement
        value = cls._get_value(value)
        return (filter_statement, [value])

    @classmethod
    def _get_value(cls, value: Any) -> Any:
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
            if query_type == QueryType.EQUALS:
                (filter_statement, filter_values) = cls._get_filter(key, value, index_count, col_name_prefix=col_name_prefix)
            elif query_type == QueryType.IS_NOT_NULL:
                (filter_statement, filter_values) = cls.get_is_not_null_filter(key, col_name_prefix=col_name_prefix)
            elif query_type == QueryType.CONTAINS:
                (filter_statement, filter_values) = cls.get_contains_filter(
                    key, value, index_count, col_name_prefix=col_name_prefix
                )
            elif query_type == QueryType.CONTAINS_PARTIAL:
                (filter_statement, filter_values) = cls.get_contains_partial_filter(
                    key, value, index_count, col_name_prefix=col_name_prefix
                )
            elif query_type == QueryType.RANGE:
                (filter_statement, filter_values) = cls.get_range_filter(
                    key, value, index_count, col_name_prefix=col_name_prefix
                )

            filter_statements.append(filter_statement)
            values.extend(filter_values)
            index_count += len(filter_values)

        return (filter_statements, values)

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
    def get_is_not_null_filter(cls, name: str, col_name_prefix: Optional[str] = None) -> Tuple[str, List[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that are not null.
        """
        cls.validate_field_name(name)
        filter_statement = f"{name} IS NOT NULL"
        filter_statement = cls._add_column_name_prefix_if_needed(filter_statement, col_name_prefix)
        return (filter_statement, [])

    @classmethod
    def get_contains_filter(
        cls, name: str, value: object, index: int, col_name_prefix: Optional[str] = None
    ) -> Tuple[str, List[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that are contained in a given
        collection.
        """
        cls.validate_field_name(name)
        filter_statement = f"{name} = ANY (${str(index)})"
        filter_statement = cls._add_column_name_prefix_if_needed(filter_statement, col_name_prefix)
        value = cls._get_value(value)
        return (filter_statement, [value])

    @classmethod
    def get_contains_partial_filter(
        cls, name: str, value: object, index: int, col_name_prefix: Optional[str] = None
    ) -> Tuple[str, List[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that are contained in a given
        collection.
        """
        cls.validate_field_name(name)
        filter_statement = f"{name} ILIKE ANY (${str(index)})"
        filter_statement = cls._add_column_name_prefix_if_needed(filter_statement, col_name_prefix)
        value = cls._get_value(value)
        value = [f"%{v}%" for v in value]
        return (filter_statement, [value])

    @classmethod
    def get_range_filter(
        cls, name: str, value: Union[DateRangeConstraint, RangeConstraint], index: int, col_name_prefix: Optional[str] = None
    ) -> Tuple[str, List[object]]:
        """
        Returns a tuple of a PostgresQL statement and any query arguments to filter on values that match a given range
        constraint.
        """
        filter_statement: str
        values: List[object]
        (filter_statement, values) = cls._combine_filter_statements(
            (
                cls._add_column_name_prefix_if_needed(
                    f"{name} {operator.pg_value} ${str(index + i)}",
                    col_name_prefix,
                ),
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

    @classmethod
    def _get_list_query_pagination_parameters(
        cls,
        database_order: DatabaseOrder,
        id_column: ColumnNameStr,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[Any] = None,
        end: Optional[Any] = None,
        **query: QueryFilter,
    ) -> Tuple[List[str], List[object]]:
        cls._validate_paging_parameters(start, end, first_id, last_id)
        (filter_statements, values) = cls.get_composed_filter_with_query_types(offset=1, col_name_prefix=None, **query)

        start_filter_statements, start_values = cls._add_start_filter(
            len(values),
            database_order.get_order_by_column_db_name(),
            id_column,
            start,
            first_id,
        )
        filter_statements.extend(start_filter_statements)
        values.extend(start_values)
        end_filter_statements, end_values = cls._add_end_filter(
            len(values),
            database_order.get_order_by_column_db_name(),
            id_column,
            end,
            last_id,
        )
        filter_statements.extend(end_filter_statements)
        values.extend(end_values)

        return filter_statements, values

    @classmethod
    def _validate_paging_parameters(
        cls,
        start: Optional[Any],
        end: Optional[Any],
        first_id: Optional[Union[uuid.UUID, str]],
        last_id: Optional[Union[uuid.UUID, str]],
    ) -> None:
        if start and end:
            raise InvalidQueryParameter(
                f"Only one of start and end parameters is allowed at the same time. Received start: {start}, end: {end}"
            )
        if first_id and last_id:
            raise InvalidQueryParameter(
                f"Only one of first_id and last_id parameters is allowed at the same time. "
                f"Received first_id: {first_id}, last_id: {last_id}"
            )
        if (first_id and not start) or (first_id and end):
            raise InvalidQueryParameter(
                f"The first_id parameter should be used in combination with the start parameter. "
                f"Received first_id: {first_id}, start: {start}, end: {end}"
            )
        if (last_id and not end) or (last_id and start):
            raise InvalidQueryParameter(
                f"The last_id parameter should be used in combination with the end parameter. "
                f"Received last_id: {last_id}, start: {start}, end: {end}"
            )

    @classmethod
    def _get_item_count_query_conditions(
        cls,
        database_order: DatabaseOrder,
        id_column_name: ColumnNameStr,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[Any] = None,
        end: Optional[Any] = None,
        **query: Tuple[QueryType, object],
    ) -> Tuple[str, List[object], List[str]]:
        order_by_column = database_order.get_order_by_column_db_name()
        order = database_order.get_order()
        (common_filter_statements, values) = cls.get_composed_filter_with_query_types(offset=1, col_name_prefix=None, **query)

        if "ASC" in order:
            before_filter_statements, before_values = cls._add_end_filter(
                len(values), order_by_column, id_column_name, end, last_id
            )
            values.extend(before_values)
            after_filter_statements, after_values = cls._add_start_filter(
                len(values), order_by_column, id_column_name, start, first_id
            )
            values.extend(after_values)
        else:
            before_filter_statements, before_values = cls._add_start_filter(
                len(values), order_by_column, id_column_name, start, first_id
            )
            values.extend(before_values)
            after_filter_statements, after_values = cls._add_end_filter(
                len(values), order_by_column, id_column_name, end, last_id
            )
            values.extend(after_values)
        before_filter = cls._join_filter_statements(before_filter_statements)
        after_filter = cls._join_filter_statements(after_filter_statements)

        select_clause = (
            f"SELECT COUNT({id_column_name}) as count_total, "
            f"COUNT({id_column_name}) filter ({before_filter}) as count_before, "
            f"COUNT({id_column_name}) filter ({after_filter}) as count_after "
        )

        return select_clause, values, common_filter_statements

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
    async def select_query(
        cls, query: str, values: List[object], no_obj: bool = False, connection: Optional[asyncpg.connection.Connection] = None
    ) -> "BaseDocument":
        async def perform_query(con: asyncpg.connection.Connection) -> object:
            async with con.transaction():
                result = []
                async for record in con.cursor(query, *values):
                    if no_obj:
                        result.append(record)
                    else:
                        result.append(cls(from_postgres=True, **record))
                return result

        if connection is None:
            async with cls.get_connection() as con:
                return await perform_query(con)
        return await perform_query(connection)

    def to_dict(self) -> JsonType:
        """
        Return a dict representing the document
        """
        result = {}
        for name, typing in self._fields.items():
            value = None
            if name in self.__fields:
                value = self.__fields[name]

            if typing.required and value is None:
                raise TypeError("%s should have field '%s'" % (self.__name__, name))

            if value is not None:
                if not isinstance(value, typing.field_type):
                    raise TypeError("Value of field %s does not have the correct type" % name)

                result[name] = value

            elif typing.default:
                result[name] = typing.default_value

        return result


class Project(BaseDocument):
    """
    An inmanta configuration project

    :param name: The name of the configuration project.
    """

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    name: str = Field(field_type=str, required=True, unique=True)

    def to_dto(self) -> m.Project:
        return m.Project(id=self.id, name=self.name, environments=[])


def convert_boolean(value: object) -> bool:
    if isinstance(value, bool):
        return value

    if value.lower() not in RawConfigParser.BOOLEAN_STATES:
        raise ValueError("Not a boolean: %s" % value)
    return RawConfigParser.BOOLEAN_STATES[value.lower()]


def convert_int(value: object) -> Union[int, float]:
    if isinstance(value, (int, float)):
        return value

    f_value = float(value)
    i_value = int(value)

    if i_value == f_value:
        return i_value
    return f_value


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


TYPE_MAP = {"int": "integer", "bool": "boolean", "dict": "jsonb", "str": "varchar", "enum": "varchar"}

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
RESOURCE_ACTION_LOGS_RETENTION = "resource_action_logs_retention"
PURGE_ON_DELETE = "purge_on_delete"
PROTECTED_ENVIRONMENT = "protected_environment"


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
        :param validator: A validation and casting function for input settings.
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

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    name: str = Field(field_type=str, required=True)
    project: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    repo_url: str = Field(field_type=str, default="")
    repo_branch: str = Field(field_type=str, default="")
    settings: Dict[str, m.EnvSettingType] = Field(field_type=dict, default={})
    last_version: int = Field(field_type=int, default=0)
    halted: bool = Field(field_type=bool, default=False)
    description: str = Field(field_type=str, default="")
    icon: str = Field(field_type=str, default="")

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
        RESOURCE_ACTION_LOGS_RETENTION: Setting(
            name=RESOURCE_ACTION_LOGS_RETENTION,
            default=7,
            typ="int",
            validator=convert_int,
            doc="The number of days to retain resource-action logs",
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
    }

    _renamed_settings_map = {
        AUTOSTART_AGENT_DEPLOY_INTERVAL: AUTOSTART_AGENT_INTERVAL,
        AUTOSTART_AGENT_DEPLOY_SPLAY_TIME: AUTOSTART_SPLAY,
    }  # name new_option -> name deprecated_option

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
        else:
            # Cascade is done by PostgreSQL
            await self.delete()

    async def get_next_version(self) -> int:
        record = await self._fetchrow(
            f"""
UPDATE {self.table_name()}
SET last_version = last_version + 1
WHERE id = $1
RETURNING last_version;
""",
            self.id,
        )
        version = cast(int, record[0])
        self.last_version = version
        return version

    @classmethod
    async def get_list(
        cls,
        order_by_column: Optional[str] = None,
        order: str = "ASC",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: bool = False,
        connection: Optional[asyncpg.connection.Connection] = None,
        details: bool = True,
        **query: object,
    ) -> List["BaseDocument"]:
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
                connection=connection,
                **query,
            )
        return await cls.get_list_without_details(
            order_by_column=order_by_column,
            order=order,
            limit=limit,
            offset=offset,
            no_obj=no_obj,
            connection=connection,
            **query,
        )

    @classmethod
    async def get_list_without_details(
        cls,
        order_by_column: Optional[str] = None,
        order: str = "ASC",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: bool = False,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: object,
    ) -> List["BaseDocument"]:
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
            connection=connection,
            columns=columns,
            **query,
        )

    @classmethod
    async def get_by_id(
        cls,
        doc_id: uuid.UUID,
        connection: Optional[asyncpg.connection.Connection] = None,
        details: bool = True,
    ) -> Optional["BaseDocument"]:
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
    Any transactions that update Parameter should adhere to the locking order described in
    :py:class:`inmanta.data.ConfigurationModel`.

    :param name: The name of the parameter
    :param value: The value of the parameter
    :param environment: The environment this parameter belongs to
    :param source: The source of the parameter
    :param resource_id: An optional resource id
    :param updated: When was the parameter updated last

    :todo Add history
    """

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    name: str = Field(field_type=str, required=True, part_of_primary_key=True)
    value: str = Field(field_type=str, default="", required=True)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    source: str = Field(field_type=str, required=True)
    resource_id: m.ResourceIdStr = Field(field_type=str, default="")
    updated: datetime.datetime = Field(field_type=datetime.datetime)
    metadata: Dict[str, Any] = Field(field_type=dict)

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

    def to_dto(self) -> m.Parameter:
        return m.Parameter(
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

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    name: str = Field(field_type=str, required=True)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    source: str = Field(field_type=str, required=True)
    resource_id: m.ResourceIdStr = Field(field_type=str, default="")
    version: int = Field(field_type=int, required=True)
    metadata: Dict[str, Any] = Field(field_type=dict)
    resolved: bool = Field(field_type=bool, default=False)


class AgentProcess(BaseDocument):
    """
    A process in the infrastructure that has (had) a session as an agent.

    :param hostname: The hostname of the device.
    :param environment: To what environment is this process bound
    :param last_seen: When did the server receive data from the node for the last time.
    """

    hostname: str = Field(field_type=str, required=True)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    first_seen: datetime.datetime = Field(field_type=datetime.datetime, default=None)
    last_seen: datetime.datetime = Field(field_type=datetime.datetime, default=None)
    expired: datetime.datetime = Field(field_type=datetime.datetime, default=None)
    sid: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)

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

    # TODO: add env to speed up cleanup
    id = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    process = Field(field_type=uuid.UUID, required=True)
    name = Field(field_type=str, required=True)
    expired = Field(field_type=datetime.datetime)
    tid = Field(field_type=uuid.UUID, required=True)

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

        async def _execute_query(con: asyncpg.connection.Connection) -> None:
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

        if connection:
            await _execute_query(connection)
        else:
            async with cls.get_connection() as con:
                await _execute_query(con)

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

    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    name: str = Field(field_type=str, required=True, part_of_primary_key=True)
    last_failover: datetime.datetime = Field(field_type=datetime.datetime)
    paused: bool = Field(field_type=bool, default=False)
    id_primary: Optional[uuid.UUID] = Field(field_type=uuid.UUID)  # AgentInstance
    unpause_on_resume: Optional[bool] = Field(field_type=bool)

    def set_primary(self, primary: uuid.UUID) -> None:
        self.id_primary = primary

    def get_primary(self) -> Optional[uuid.UUID]:
        return self.id_primary

    def del_primary(self) -> None:
        del self.id_primary

    primary = property(get_primary, set_primary, del_primary)

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
    def _create_dict_wrapper(cls, from_postgres: bool, kwargs: Dict[str, object]) -> JsonType:
        kwargs = cls._convert_field_names_to_db_column_names(kwargs)
        return cls._create_dict(from_postgres, kwargs)

    @classmethod
    async def get(cls, env: uuid.UUID, endpoint: str, connection: Optional[asyncpg.connection.Connection] = None) -> "Agent":
        obj = await cls.get_one(environment=env, name=endpoint, connection=connection)
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

        async def query_with_connection(connection: asyncpg.connection.Connection) -> List[str]:
            async with connection.transaction():
                unpause_on_resume = await cls._fetch_query(
                    f"SELECT name FROM {cls.table_name()} WHERE environment=$1 AND unpause_on_resume",
                    cls._get_value(env),
                    connection=connection,
                )
                await cls._execute_query(
                    f"UPDATE {cls.table_name()} SET unpause_on_resume=NULL WHERE environment=$1",
                    cls._get_value(env),
                    connection=connection,
                )
                return sorted([r["name"] for r in unpause_on_resume])

        if connection is not None:
            return await query_with_connection(connection)

        async with cls.get_connection() as con:
            return await query_with_connection(con)

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
            agent = await cls.get(env, endpoint, connection=connection)
            if agent is None:
                continue

            if sid is None:
                await agent.update_fields(last_failover=now, primary=None, connection=connection)
            else:
                instances = await AgentInstance.active_for(tid=env, endpoint=agent.name, process=sid, connection=connection)
                if instances:
                    await agent.update_fields(last_failover=now, primary=instances[0].id, connection=connection)
                else:
                    await agent.update_fields(last_failover=now, primary=None, connection=connection)

    @classmethod
    async def mark_all_as_non_primary(cls, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        query = f"""
                UPDATE {cls.table_name()}
                SET id_primary=NULL
                WHERE id_primary IS NOT NULL
        """
        await cls._execute_query(query, connection=connection)

    @classmethod
    def agent_list_subquery(cls, environment: uuid.UUID) -> Tuple[str, List[object]]:
        query_builder = SimpleQueryBuilder(
            select_clause="""SELECT a.name, a.environment, last_failover, paused, unpause_on_resume,
                                    ai.name as process_name, ai.process as process_id,
                                    (CASE WHEN paused THEN 'paused'
                                        WHEN id_primary IS NOT NULL THEN 'up'
                                        ELSE 'down'
                                    END) as status""",
            from_clause=f" FROM {cls.table_name()} as a LEFT JOIN public.agentinstance ai ON a.id_primary=ai.id",
            filter_statements=[" environment = $1 "],
            values=[cls._get_value(environment)],
        )
        return query_builder.build()

    @classmethod
    async def count_items_for_paging(
        cls,
        environment: uuid.UUID,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        subquery, subquery_values = cls.agent_list_subquery(environment)
        base_query = PageCountQueryBuilder(
            from_clause=f"FROM ({subquery}) as result",
            values=subquery_values,
        )
        paging_query = base_query.page_count(database_order, first_id, last_id, start, end)
        filtered_query = paging_query.filter(
            *cls.get_composed_filter_with_query_types(offset=paging_query.offset, col_name_prefix=None, **query)
        )
        sql_query, values = filtered_query.build()
        result = await cls.select_query(sql_query, values, no_obj=True)
        result = cast(List[Record], result)
        if not result:
            raise InvalidQueryParameter(f"Environment {environment} doesn't exist")
        return PagingCounts(total=result[0]["count_total"], before=result[0]["count_before"], after=result[0]["count_after"])

    @classmethod
    async def get_agents(
        cls,
        database_order: DatabaseOrder,
        limit: int,
        environment: uuid.UUID,
        first_id: Optional[str] = None,
        last_id: Optional[str] = None,
        start: Optional[Union[datetime.datetime, bool, str]] = None,
        end: Optional[Union[datetime.datetime, bool, str]] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: Tuple[QueryType, object],
    ) -> List[m.Agent]:
        subquery, subquery_values = cls.agent_list_subquery(environment)

        query_builder = SimpleQueryBuilder(
            select_clause="""SELECT * """,
            from_clause=f" FROM ({subquery}) as result",
            values=subquery_values,
        )
        filtered_query = query_builder.filter(
            *cls.get_composed_filter_with_query_types(offset=query_builder.offset, col_name_prefix=None, **query)
        )
        paged_query = filtered_query.filter(*database_order.as_start_filter(filtered_query.offset, start, first_id)).filter(
            *database_order.as_end_filter(filtered_query.offset, end, last_id)
        )
        order = database_order.get_order()
        backward_paging: bool = (order == PagingOrder.ASC and (end is not None or last_id)) or (
            order == PagingOrder.DESC and (start is not None or first_id)
        )
        ordered_query = paged_query.order_and_limit(database_order, limit, backward_paging)
        sql_query, values = ordered_query.build()

        agent_records = await cls.select_query(sql_query, values, no_obj=True, connection=connection)
        agent_records = cast(Iterable[Record], agent_records)

        dtos = [
            m.Agent(
                name=agent["name"],
                environment=agent["environment"],
                last_failover=agent["last_failover"],
                paused=agent["paused"],
                unpause_on_resume=agent["unpause_on_resume"],
                process_id=agent["process_id"],
                process_name=agent["process_name"],
                status=agent["status"],
            )
            for agent in agent_records
        ]
        return dtos


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

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    started: datetime.datetime = Field(field_type=datetime.datetime, required=True)
    completed: Optional[datetime.datetime] = Field(field_type=datetime.datetime)
    command: str = Field(field_type=str, required=True)
    name: str = Field(field_type=str, required=True)
    errstream: str = Field(field_type=str, default="")
    outstream: str = Field(field_type=str, default="")
    returncode: Optional[int] = Field(field_type=int)
    compile: uuid.UUID = Field(field_type=uuid.UUID, required=True)

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
    :param succes: was the compile successful
    :param handled: were all registered handlers executed?
    :param version: version exported by this compile
    :param remote_id: id as given by the requestor, used by the requestor to distinguish between different requests
    :param compile_data: json data as exported by compiling with the --export-compile-data parameter
    :param substitute_compile_id: id of this compile's substitute compile, i.e. the compile request that is similar
        to this one that actually got compiled.
    """

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    remote_id: Optional[uuid.UUID] = Field(field_type=uuid.UUID)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    requested: Optional[datetime.datetime] = Field(field_type=datetime.datetime)
    started: Optional[datetime.datetime] = Field(field_type=datetime.datetime)
    completed: Optional[datetime.datetime] = Field(field_type=datetime.datetime)

    do_export: bool = Field(field_type=bool, default=False)
    force_update: bool = Field(field_type=bool, default=False)
    metadata: dict = Field(field_type=dict, default={})
    environment_variables: dict = Field(field_type=dict)

    success: Optional[bool] = Field(field_type=bool)
    handled: bool = Field(field_type=bool, default=False)
    version: Optional[int] = Field(field_type=int)

    # Compile queue might be collapsed if it contains similar compile requests.
    # In that case, substitute_compile_id will reference the actually compiled request.
    substitute_compile_id: Optional[uuid.UUID] = Field(field_type=uuid.UUID)

    compile_data: Optional[dict] = Field(field_type=dict)

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
    async def get_next_run_all(cls) -> "List[Compile]":
        """Get the next compile in the queue for each environment"""
        results = await cls.select_query(
            f"SELECT DISTINCT ON (environment) * FROM {cls.table_name()} WHERE completed IS NULL ORDER BY environment, "
            f"requested ASC",
            [],
        )
        return results

    @classmethod
    async def get_unhandled_compiles(cls) -> "List[Compile]":
        """Get all compiles that have completed but for which listeners have not been notified yet."""
        results = await cls.select_query(
            f"SELECT * FROM {cls.table_name()} WHERE NOT handled and completed IS NOT NULL ORDER BY requested ASC", []
        )
        return results

    @classmethod
    async def get_next_compiles_for_environment(cls, environment_id: uuid.UUID) -> "List[Compile]":
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
        result = await cls._fetchval(f"SELECT count(*) FROM {cls.table_name()} WHERE NOT handled and completed IS NOT NULL")
        return result

    @classmethod
    async def get_by_remote_id(cls, environment_id: uuid.UUID, remote_id: uuid.UUID) -> "List[Compile]":
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
    async def count_items_for_paging(
        cls,
        environment: uuid.UUID,
        database_order: DatabaseOrder,
        first_id: Optional[uuid.UUID] = None,
        last_id: Optional[uuid.UUID] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        base_query = PageCountQueryBuilder(
            from_clause=f"FROM {cls.table_name()}",
            filter_statements=[" environment = $1 "],
            values=[cls._get_value(environment)],
        )
        paging_query = base_query.page_count(database_order, first_id, last_id, start, end)
        filtered_query = paging_query.filter(
            *cls.get_composed_filter_with_query_types(offset=paging_query.offset, col_name_prefix=None, **query)
        )
        sql_query, values = filtered_query.build()
        result = await cls.select_query(sql_query, values, no_obj=True)
        if not result:
            raise InvalidQueryParameter(f"Environment {environment} doesn't exist")
        return PagingCounts(total=result[0]["count_total"], before=result[0]["count_before"], after=result[0]["count_after"])

    @classmethod
    async def get_compile_reports(
        cls,
        database_order: DatabaseOrder,
        limit: int,
        environment: uuid.UUID,
        first_id: Optional[uuid.UUID] = None,
        last_id: Optional[uuid.UUID] = None,
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: Tuple[QueryType, object],
    ) -> List[m.CompileReport]:
        cls._validate_paging_parameters(start, end, first_id, last_id)

        query_builder = SimpleQueryBuilder(
            select_clause="""SELECT id, remote_id, environment, requested,
                    started, completed, do_export, force_update,
                    metadata, environment_variables, success, version """,
            from_clause=f" FROM {cls.table_name()}",
            filter_statements=[" environment = $1 "],
            values=[cls._get_value(environment)],
        )
        filtered_query = query_builder.filter(
            *cls.get_composed_filter_with_query_types(offset=query_builder.offset, col_name_prefix=None, **query)
        )
        paged_query = filtered_query.filter(*database_order.as_start_filter(filtered_query.offset, start, first_id)).filter(
            *database_order.as_end_filter(filtered_query.offset, end, last_id)
        )
        order = database_order.get_order()
        backward_paging: bool = (order == PagingOrder.ASC and end) or (order == PagingOrder.DESC and start)
        ordered_query = paged_query.order_and_limit(database_order, limit, backward_paging)
        sql_query, values = ordered_query.build()

        compile_records = await cls.select_query(sql_query, values, no_obj=True, connection=connection)
        compile_records = cast(Iterable[Record], compile_records)

        dtos = [
            m.CompileReport(
                id=compile["id"],
                remote_id=compile["remote_id"],
                environment=compile["environment"],
                requested=compile["requested"],
                started=compile["started"],
                completed=compile["completed"],
                success=compile["success"],
                version=compile["version"],
                do_export=compile["do_export"],
                force_update=compile["force_update"],
                metadata=json.loads(compile["metadata"]) if compile["metadata"] else {},
                environment_variables=json.loads(compile["environment_variables"]) if compile["environment_variables"] else {},
            )
            for compile in compile_records
        ]
        return dtos

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
        ) SELECT * FROM compiledetails;
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
    Any transactions that update ResourceAction should adhere to the locking order described in
    :py:class:`inmanta.data.ConfigurationModel`

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

    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    version: int = Field(field_type=int, required=True)
    resource_version_ids: List[m.ResourceVersionIdStr] = Field(field_type=list, required=True)

    action_id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    action: const.ResourceAction = Field(field_type=const.ResourceAction, required=True)

    started: datetime.datetime = Field(field_type=datetime.datetime, required=True)
    finished: datetime.datetime = Field(field_type=datetime.datetime)

    messages: List = Field(field_type=list)
    status = Field(field_type=const.ResourceState)
    changes = Field(field_type=dict)
    change = Field(field_type=const.Change)
    send_event = Field(field_type=bool)

    def __init__(self, from_postgres: bool = False, **kwargs: object) -> None:
        super().__init__(from_postgres, **kwargs)
        self._updates = {}

    @classmethod
    async def get_by_id(cls, doc_id: uuid.UUID) -> "ResourceAction":
        return await cls.get_one(action_id=doc_id)

    @classmethod
    def _create_dict_wrapper(cls, from_postgres: bool, kwargs: Dict[str, object]) -> JsonType:
        result = cls._create_dict(from_postgres, kwargs)
        new_messages = []
        if from_postgres and result.get("messages"):
            for message in result["messages"]:
                message = json.loads(message)
                if "timestamp" in message:
                    # use pydantic instead of datetime.strptime because strptime has trouble parsing isoformat timezone offset
                    message["timestamp"] = pydantic.parse_obj_as(datetime.datetime, message["timestamp"])
                    if message["timestamp"].tzinfo is None:
                        raise Exception("Found naive timestamp in the database, this should not be possible")
                new_messages.append(message)
            result["messages"] = new_messages
        if "changes" in result and result["changes"] == {}:
            result["changes"] = None
        return result

    @classmethod
    async def get_log(
        cls, environment: uuid.UUID, resource_version_id: m.ResourceVersionIdStr, action: Optional[str] = None, limit: int = 0
    ) -> List["ResourceAction"]:
        # The @> operator is required to use the GIN index on the resource_version_ids column
        query = f"""SELECT *
                    FROM {cls.table_name()}
                    WHERE environment=$1 AND resource_version_ids::varchar[] @> ARRAY[$2]::varchar[]
                 """
        values = [cls._get_value(environment), cls._get_value(resource_version_id)]
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
    def validate_field_name(cls, name: str) -> ColumnNameStr:
        """Check if the name is a valid database column name for the current type"""
        valid_field_names = list(cls._fields.keys())
        valid_field_names.extend(["timestamp", "level", "msg"])
        if name not in valid_field_names:
            raise InvalidFieldNameException(f"{name} is not valid for a query on {cls.table_name()}")
        return ColumnNameStr(name)

    @classmethod
    def _validate_order_strict(cls, order_by_column: str, order: str) -> Tuple[ColumnNameStr, PagingOrder]:
        """Validate the correct values for order ('ASC' or 'DESC') and if the order column is an existing column name
        :param order_by_column: The name of the column to order by
        :param order: The sorting order.
        :return:
        """
        for o in order.split(" "):
            possible = ["ASC", "DESC"]
            if o not in possible:
                raise RuntimeError(f"The following order can not be applied: {order}, {o} should be one of {possible}")

        valid_field_names = list(cls._fields.keys())
        valid_field_names.extend(["timestamp", "level", "msg"])
        if order_by_column not in valid_field_names:
            raise RuntimeError(f"{order_by_column} is not a valid field name.")

        return ColumnNameStr(order_by_column), PagingOrder[order]

    @classmethod
    def _get_resource_logs_base_query(
        cls,
        select_clause: str,
        environment: uuid.UUID,
        resource_id: m.ResourceIdStr,
        offset: int,
    ) -> Tuple[str, List[object]]:
        query = f"""{select_clause}
                    FROM
                    (SELECT action_id, action, (unnested_message ->> 'timestamp')::timestamptz as timestamp,
                    unnested_message ->> 'level' as level,
                    unnested_message ->> 'msg' as msg,
                    unnested_message
                    FROM {cls.table_name()}, unnest(resource_version_ids) rvid, unnest(messages) unnested_message
                    WHERE environment = ${offset} AND rvid LIKE ${offset + 1}) unnested
                    """
        values = [cls._get_value(environment), cls._get_value(f"{resource_id}%")]
        return query, values

    @classmethod
    async def get_logs_paged(
        cls,
        database_order: DatabaseOrder,
        limit: int,
        environment: uuid.UUID,
        resource_id: m.ResourceIdStr,
        start: Optional[Any] = None,
        end: Optional[Any] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: Tuple[QueryType, object],
    ) -> List["m.ResourceLog"]:
        order_by_column = database_order.get_order_by_column_db_name()
        order = database_order.get_order()
        filter_statements, values = cls._get_list_query_pagination_parameters(
            database_order=database_order,
            id_column=ColumnNameStr("resource_version_id"),
            first_id=None,
            last_id=None,
            start=start,
            end=end,
            **query,
        )
        db_query, base_query_values = cls._get_resource_logs_base_query(
            select_clause="SELECT action_id, action, timestamp, unnested_message ",
            environment=environment,
            resource_id=resource_id,
            offset=len(values) + 1,
        )
        values.extend(base_query_values)
        if len(filter_statements) > 0:
            db_query += cls._join_filter_statements(filter_statements)
        backward_paging = (order == PagingOrder.ASC and end) or (order == PagingOrder.DESC and start)
        if backward_paging:
            backward_paging_order = order.invert().name

            db_query += f" ORDER BY {order_by_column} {backward_paging_order}"
        else:
            db_query += f" ORDER BY {order_by_column} {order}"
        if limit is not None:
            if limit > DBLIMIT:
                raise InvalidQueryParameter(f"Limit cannot be bigger than {DBLIMIT}, got {limit}")
            elif limit > 0:
                db_query += " LIMIT " + str(limit)

        if backward_paging:
            db_query = f"""SELECT * FROM ({db_query}) AS matching_records
                                ORDER BY matching_records.{order_by_column} {order}"""

        records = cast(Iterable[Record], await cls.select_query(db_query, values, no_obj=True, connection=connection))
        logs = []
        for record in records:
            message = json.loads(record["unnested_message"])
            logs.append(
                m.ResourceLog(
                    action_id=record["action_id"],
                    action=record["action"],
                    timestamp=record["timestamp"],
                    level=message.get("level"),
                    msg=message.get("msg"),
                    args=message.get("args", []),
                    kwargs=message.get("kwargs", {}),
                )
            )
        return logs

    @classmethod
    def _get_paging_resource_log_item_count_query(
        cls,
        environment: uuid.UUID,
        resource_id: m.ResourceIdStr,
        database_order: DatabaseOrder,
        id_column_name: ColumnNameStr,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[Any] = None,
        end: Optional[Any] = None,
        **query: Tuple[QueryType, object],
    ) -> Tuple[str, List[object]]:
        select_clause, values, common_filter_statements = cls._get_item_count_query_conditions(
            database_order, id_column_name, first_id, last_id, start, end, **query
        )

        sql_query, base_query_values = cls._get_resource_logs_base_query(
            select_clause=select_clause,
            environment=environment,
            resource_id=resource_id,
            offset=len(values) + 1,
        )
        values.extend(base_query_values)

        if len(common_filter_statements) > 0:
            sql_query += cls._join_filter_statements(common_filter_statements)

        return sql_query, values

    @classmethod
    async def get(cls, action_id: uuid.UUID, connection: Optional[asyncpg.connection.Connection] = None) -> "ResourceAction":
        return await cls.get_one(action_id=action_id, connection=connection)

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

    async def save(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        """
        Save the changes
        """
        if len(self._updates) == 0:
            return
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
        log_severity: Optional[str] = None,
        limit: int = 0,
        action_id: Optional[uuid.UUID] = None,
        first_timestamp: Optional[datetime.datetime] = None,
        last_timestamp: Optional[datetime.datetime] = None,
    ) -> List["ResourceAction"]:

        query = f"""SELECT DISTINCT ra.*
                        FROM {cls.table_name()} ra
                        INNER JOIN
                        {Resource.table_name()} r on  r.resource_version_id = ANY(ra.resource_version_ids)
                        WHERE r.environment=$1
                     """
        values = [cls._get_value(environment)]

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
            query += f" AND attributes->>${parameter_index} LIKE ${parameter_index + 1}::varchar"
            values.append(cls._get_value(attribute))
            values.append(cls._get_value(attribute_value))
            parameter_index += 2
        if log_severity:
            # <@ Is contained by
            query += f" AND ${parameter_index} <@ ANY(messages)"
            values.append(cls._get_value({"level": log_severity.upper()}))
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
                return [cls(**dict(record), from_postgres=True) async for record in con.cursor(query, *values)]

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
            send_event=self.send_event,
        )


@stable_api
class Resource(BaseDocument):
    """
    A specific version of a resource. This entity contains the desired state of a resource.
    Any transactions that update Resource should adhere to the locking order described in
    :py:class:`inmanta.data.ConfigurationModel`.

    :param environment: The environment this resource version is defined in
    :param rid: The id of the resource and its version
    :param resource: The resource for which this defines the state
    :param model: The configuration model (versioned) this resource state is associated with
    :param attributes: The state of this version of the resource
    :param attribute_hash: hash of the attributes, excluding requires, provides and version,
                           used to determine if a resource describes the same state across versions
    :param resource_id_value: The attribute value from the resource id
    """

    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    model: int = Field(field_type=int, required=True)

    # ID related
    resource_id: m.ResourceVersionIdStr = Field(field_type=str, required=True)
    resource_type: m.ResourceType = Field(field_type=str, required=True)
    resource_version_id: m.ResourceVersionIdStr = Field(field_type=str, required=True, part_of_primary_key=True)
    resource_id_value: str = Field(field_type=str, required=True)

    agent: str = Field(field_type=str, required=True)

    # Field based on content from the resource actions
    last_deploy: datetime.datetime = Field(field_type=datetime.datetime)

    # State related
    attributes: Dict[str, Any] = Field(field_type=dict)
    attribute_hash: str = Field(field_type=str)
    status: const.ResourceState = Field(field_type=const.ResourceState, default=const.ResourceState.available)

    # internal field to handle cross agent dependencies
    # if this resource is updated, it must notify all RV's in this list
    # the list contains full rv id's
    provides: List[m.ResourceVersionIdStr] = Field(field_type=list, default=[])  # List of resource versions

    def make_hash(self):
        character = "|".join(
            sorted([str(k) + "||" + str(v) for k, v in self.attributes.items() if k not in ["requires", "provides", "version"]])
        )
        m = hashlib.md5()
        m.update(self.resource_id.encode())
        m.update(character.encode())
        self.attribute_hash = m.hexdigest()

    @classmethod
    async def get_resources(
        cls,
        environment: uuid.UUID,
        resource_version_ids: List[m.ResourceVersionIdStr],
        connection: Optional[asyncpg.connection.Connection] = None,
    ) -> List["Resource"]:
        """
        Get all resources listed in resource_version_ids
        """
        if not resource_version_ids:
            return []
        resource_version_ids_statement = ", ".join(["$" + str(i) for i in range(2, len(resource_version_ids) + 2)])
        (filter_statement, values) = cls._get_composed_filter(environment=environment)
        values = values + cls._get_value(resource_version_ids)
        query = (
            f"SELECT * FROM {cls.table_name()} "
            f"WHERE {filter_statement} AND resource_version_id IN ({resource_version_ids_statement})"
        )
        resources = await cls.select_query(query, values, connection=connection)
        return resources

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
            WHERE r1.environment=$1 AND r1.model=(SELECT MAX(r2.model)
                                                  FROM {Resource.table_name()} AS r2
                                                  WHERE r2.environment=$1)
        """
        if resource_type:
            query += " AND r1.resource_type=$2"
            values.append(cls._get_value(resource_type))

        result = []
        async with cls.get_connection() as con:
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
        cls, environment: uuid.UUID, version: int, agent: Optional[str] = None, no_obj: bool = False
    ) -> List["Resource"]:
        if agent:
            (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version, agent=agent)
        else:
            (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version)

        query = f"SELECT * FROM {Resource.table_name()} WHERE {filter_statement}"
        resources_list = []
        async with cls.get_connection() as con:
            async with con.transaction():
                async for record in con.cursor(query, *values):
                    if no_obj:
                        record = dict(record)
                        record["attributes"] = json.loads(record["attributes"])
                        record["id"] = record["resource_version_id"]
                        parsed_id = resources.Id.parse_id(record["resource_version_id"])
                        record["resource_type"] = parsed_id.entity_type
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

    @classmethod
    def _get_released_resources_base_query(
        cls, select_clause: str, environment: uuid.UUID, offset: int
    ) -> Tuple[str, List[object]]:
        """A partial query describing the conditions for selecting the latest released resources,
        according to the model version number."""
        environment_db_value = cls._get_value(environment)
        # Emulate a loose index scan with a recursive common table expression (CTE),
        # Based on https://stackoverflow.com/a/25536748 and https://wiki.postgresql.org/wiki/Loose_indexscan
        # A loose index scan is "an operation that finds the distinct values of the leading columns of a
        # btree index efficiently; rather than scanning all equal values of a key,
        # as soon as a new value is found, restart the search by looking for a larger value"
        # In this case we don't scan all equal values of a resource_id
        # we just look for the first one that satisfies the conditions (in descending order according to the version number)
        # and move on to the next resource_id
        return (
            f"""
            /* the recursive CTE is the second one, but it has to be specified after 'WITH' if any of them are recursive */
            /* The cm_version CTE finds the maximum released version number in the environment  */
            WITH RECURSIVE cm_version AS (
                  SELECT
                    MAX(public.configurationmodel.version) as max_version
                    FROM public.configurationmodel
                WHERE public.configurationmodel.released=TRUE
                AND environment=${offset}
                ),
            /* emulate a loose (or skip) index scan */
            cte AS (
               (
               /* specify the necessary columns */
               SELECT r.resource_id, r.attributes, r.resource_version_id, r.resource_type,
                    r.agent, r.resource_id_value, r.model, r.environment, (CASE WHEN
                            (SELECT r.model < cm_version.max_version
                            FROM cm_version)
                        THEN 'orphaned' -- use the CTE to check the status
                    ELSE r.status::text END) as status
               FROM   resource r
               JOIN configurationmodel cm ON r.model = cm.version AND r.environment = cm.environment
               WHERE  r.environment = ${offset} AND cm.released = TRUE
               ORDER  BY resource_id, model DESC
               LIMIT  1
               )
               UNION ALL
               SELECT r.*
               FROM   cte c
               CROSS JOIN LATERAL
               /* specify the same columns in the recursive part */
                (SELECT r.resource_id, r.attributes, r.resource_version_id, r.resource_type,
                    r.agent, r.resource_id_value, r.model, r.environment, (CASE WHEN
                            (SELECT r.model < cm_version.max_version
                            FROM cm_version)
                        THEN 'orphaned'
                    ELSE r.status::text END) as status
               FROM   resource r JOIN configurationmodel cm on r.model = cm.version AND r.environment = cm.environment
               /* One result from the recursive call is the latest released version of one specific resource.
                  We always start looking for this based on the previous resource_id. */
               WHERE  r.resource_id > c.resource_id AND r.environment = ${offset} AND cm.released = TRUE
               ORDER  BY r.resource_id, r.model DESC
               LIMIT  1) r
               )
            {select_clause}
            FROM   cte
            """,
            environment_db_value,
        )

    @classmethod
    async def get_released_resources(
        cls,
        database_order: DatabaseOrder,
        limit: int,
        environment: uuid.UUID,
        first_id: Optional[str] = None,
        last_id: Optional[str] = None,
        start: Optional[Any] = None,
        end: Optional[Any] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: Tuple[QueryType, object],
    ) -> List[m.LatestReleasedResource]:
        """
        Get all resources that are in a released version, sorted, paged and filtered
        """
        order_by_column = database_order.get_order_by_column_db_name()
        order = database_order.get_order()
        filter_statements, values = cls._get_list_query_pagination_parameters(
            database_order=database_order,
            id_column=ColumnNameStr("resource_version_id"),
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
            **query,
        )
        db_query, base_query_values = cls._get_released_resources_base_query(
            select_clause="SELECT * ", environment=environment, offset=len(values) + 1
        )
        values.append(base_query_values)
        if len(filter_statements) > 0:
            db_query += cls._join_filter_statements(filter_statements)
        backward_paging = (order == PagingOrder.ASC and end) or (order == PagingOrder.DESC and start)
        if backward_paging:
            backward_paging_order = order.invert().name

            db_query += f" ORDER BY {order_by_column} {backward_paging_order}, resource_version_id {backward_paging_order}"
        else:
            db_query += f" ORDER BY {order_by_column} {order}, resource_version_id {order}"
        if limit is not None:
            if limit > DBLIMIT:
                raise InvalidQueryParameter(f"Limit cannot be bigger than {DBLIMIT}, got {limit}")
            elif limit > 0:
                db_query += " LIMIT " + str(limit)

        if backward_paging:
            db_query = f"""SELECT * FROM ({db_query}) AS matching_records
                        ORDER BY matching_records.{order_by_column} {order}, matching_records.resource_version_id {order}"""

        resource_records = await cls.select_query(db_query, values, no_obj=True, connection=connection)
        resource_records = cast(Iterable[Record], resource_records)

        dtos = [
            m.LatestReleasedResource(
                resource_id=resource["resource_id"],
                resource_version_id=resource["resource_version_id"],
                id_details=cls.get_details_from_resource_id(resource["resource_id"]),
                status=resource["status"],
                requires=json.loads(resource["attributes"]).get("requires", []),
            )
            for resource in resource_records
        ]
        return dtos

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
    def _get_paging_item_count_query(
        cls,
        environment: uuid.UUID,
        database_order: DatabaseOrder,
        id_column_name: ColumnNameStr,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[Any] = None,
        end: Optional[Any] = None,
        **query: Tuple[QueryType, object],
    ) -> Tuple[str, List[object]]:
        select_clause, values, common_filter_statements = cls._get_item_count_query_conditions(
            database_order, id_column_name, first_id, last_id, start, end, **query
        )

        sql_query, base_query_values = cls._get_released_resources_base_query(
            select_clause=select_clause,
            environment=environment,
            offset=len(values) + 1,
        )
        values.append(base_query_values)

        if len(common_filter_statements) > 0:
            sql_query += cls._join_filter_statements(common_filter_statements)

        return sql_query, values

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
        value = await cls.get_one(environment=environment, resource_version_id=resource_version_id, connection=connection)
        return value

    @classmethod
    def new(cls, environment: uuid.UUID, resource_version_id: m.ResourceVersionIdStr, **kwargs: Any) -> "Resource":
        vid = resources.Id.parse_id(resource_version_id)

        attr = dict(
            environment=environment,
            model=vid.version,
            resource_id=vid.resource_str(),
            resource_type=vid.entity_type,
            resource_version_id=resource_version_id,
            agent=vid.agent_name,
            resource_id_value=vid.attribute_value,
        )

        attr.update(kwargs)

        return cls(**attr)

    @classmethod
    async def get_deleted_resources(
        cls, environment: uuid.UUID, current_version: int, current_resources: Sequence[m.ResourceVersionIdStr]
    ) -> List["Resource"]:
        """
        This method returns all resources that have been deleted from the model and are not yet marked as purged. It returns
        the latest version of the resource from a released model.

        :param environment:
        :param current_version:
        :param current_resources: A set of all resource ids in the current version.
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
        async with cls.get_connection() as con:
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
        resources = await cls._fetch_query(query, *values)
        resources = [r["resource_id"] for r in resources]

        LOGGER.debug("  Resource with purge_on_delete true: %s", resources)

        # all resources on current model
        LOGGER.debug("  All resource in current version (%s): %s", current_version, current_resources)

        # determined deleted resources

        deleted = set(resources) - current_resources
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

            async with cls.get_connection() as con:
                async with con.transaction():
                    async for obj in con.cursor(query, *values):
                        # if a resource is part of a released version and it is deployed (this last condition is actually enough
                        # at the moment), we have found the last status of the resource. If it was not purged in that version,
                        # add it to the should purge list.
                        if obj["model"] in versions and obj["status"] == const.ResourceState.deployed.name:
                            attributes = json.loads(obj["attributes"])
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
        latest.agent, latest.resource_id_value, latest.last_deploy as latest_deploy, latest.attributes, latest.status,
        /* Split up the requires array to its elements and find the latest released version of
            the resources to get their status, and build a single json object from them */
        (SELECT JSON_OBJECT_AGG(substring(req.requires from '(.*),v='), s.status) as requires_status
            FROM
                (SELECT JSONB_ARRAY_ELEMENTS_TEXT(resource.attributes->'requires') as requires
                    FROM resource
                    WHERE resource_id = latest.resource_id and model = latest.model)
                    as req
                    INNER JOIN
                        (SELECT DISTINCT ON (resource_id) resource_id, resource.environment, {status_subquery}
                        FROM resource
                        INNER JOIN configurationmodel cm
                        ON resource.model = cm.version AND resource.environment = cm.environment
                        WHERE resource.environment = $1 AND cm.released = TRUE
                        ORDER BY resource_id, model desc
                        ) as s
                    ON substring(req.requires from '(.*),v=') = s.resource_id AND s.environment = $1
                )
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
        result = cast(List[Record], result)

        if not result:
            return None
        record = result[0]
        parsed_id = resources.Id.parse_id(record["latest_resource_id"])
        return m.ReleasedResourceDetails(
            resource_id=record["latest_resource_id"],
            resource_type=record["resource_type"],
            agent=record["agent"],
            id_attribute=parsed_id.attribute,
            id_attribute_value=record["resource_id_value"],
            last_deploy=record["latest_deploy"],
            first_generated_time=record["first_generated_time"],
            first_generated_version=record["first_model"],
            attributes=json.loads(record["attributes"]),
            status=record["status"],
            requires_status=json.loads(record["requires_status"]) if record["requires_status"] else {},
        )

    @classmethod
    async def get_versioned_resource_details(
        cls, environment: uuid.UUID, version: int, resource_id: m.ResourceIdStr
    ) -> Optional[m.VersionedResourceDetails]:
        resource = await cls.get_one(environment=environment, model=version, resource_id=resource_id)
        if not resource:
            return None
        parsed_id = resources.Id.parse_id(resource.resource_id)
        return m.VersionedResourceDetails(
            resource_id=resource.resource_id,
            resource_version_id=resource.resource_version_id,
            resource_type=resource.resource_type,
            agent=resource.agent,
            id_attribute=parsed_id.attribute,
            id_attribute_value=resource.resource_id_value,
            version=resource.model,
            attributes=resource.attributes,
        )

    @classmethod
    def get_history_base_query(
        cls,
        select_clause: str,
        environment: uuid.UUID,
        resource_id: m.ResourceIdStr,
        offset: int,
    ) -> Tuple[str, List[object]]:
        query = f"""
                /* Assign a sequence id to the rows, which is used for grouping consecutive ones with the same hash */
                WITH resourcewithsequenceids AS (
                  SELECT
                    attribute_hash,
                    model,
                    attributes,
                    date,
                    ROW_NUMBER() OVER (ORDER BY date) - ROW_NUMBER() OVER (
                      PARTITION BY attribute_hash
                      ORDER BY date
                    ) AS seqid
                  FROM resource JOIN configurationmodel cm
                    ON resource.model = cm.version AND resource.environment = cm.environment
                  WHERE resource.environment = ${offset} AND resource_id = ${offset + 1} AND cm.released = TRUE
                )
                   {select_clause}
                    FROM
                    (SELECT
                        attribute_hash,
                        min(date) as date,
                        (SELECT distinct on (attribute_hash) attributes
                            FROM resourcewithsequenceids
                            WHERE resourcewithsequenceids.attribute_hash = rs.attribute_hash
                            AND resourcewithsequenceids.seqid = rs.seqid
                            ORDER BY attribute_hash, model
                        ) as attributes
                    FROM resourcewithsequenceids rs
                    GROUP BY attribute_hash,  seqID) as sub
                    """
        values = [cls._get_value(environment), cls._get_value(resource_id)]
        return query, values

    @classmethod
    async def get_resource_history(
        cls,
        env: uuid.UUID,
        resource_id: m.ResourceIdStr,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
        limit: Optional[int] = None,
    ) -> List[m.ResourceHistory]:
        order_by_column = database_order.get_order_by_column_db_name()
        order = database_order.get_order()

        select_clause = """
        SELECT
        attribute_hash,
        date,
        attributes """

        filter_statements, values = cls._get_list_query_pagination_parameters(
            database_order=database_order,
            id_column=ColumnNameStr("attribute_hash"),
            first_id=first_id,
            last_id=last_id,
            start=start,
            end=end,
        )
        query, base_query_values = cls.get_history_base_query(
            select_clause=select_clause, environment=env, resource_id=resource_id, offset=len(values) + 1
        )
        if len(filter_statements) > 0:
            query += cls._join_filter_statements(filter_statements)
        values.extend(base_query_values)
        backward_paging = (order == PagingOrder.ASC and end) or (order == PagingOrder.DESC and start)
        if backward_paging:
            backward_paging_order = order.invert().name

            query += f" ORDER BY {order_by_column} {backward_paging_order}, attribute_hash {backward_paging_order}"
        else:
            query += f" ORDER BY {order_by_column} {order}, attribute_hash {order}"
        if limit is not None:
            if limit > DBLIMIT:
                raise InvalidQueryParameter(f"Limit cannot be bigger than {DBLIMIT}, got {limit}")
            elif limit > 0:
                query += " LIMIT " + str(limit)
        else:
            query += f" LIMIT {DBLIMIT} "

        if backward_paging:
            query = f"""SELECT * FROM ({query}) AS matching_records
                        ORDER BY matching_records.{order_by_column} {order}, matching_records.attribute_hash {order}"""
        result = await cls.select_query(query, values, no_obj=True)
        result = cast(List[Record], result)

        return [
            m.ResourceHistory(
                resource_id=resource_id,
                attribute_hash=record["attribute_hash"],
                attributes=json.loads(record["attributes"]),
                date=record["date"],
                requires=[
                    resources.Id.parse_id(rvid).resource_str() for rvid in json.loads(record["attributes"]).get("requires", [])
                ],
            )
            for record in result
        ]

    @classmethod
    def _get_paging_history_item_count_query(
        cls,
        environment: uuid.UUID,
        resource_id: m.ResourceIdStr,
        database_order: DatabaseOrder,
        id_column_name: ColumnNameStr,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[Any] = None,
        end: Optional[Any] = None,
        **query: Tuple[QueryType, object],
    ) -> Tuple[str, List[object]]:
        select_clause, values, common_filter_statements = cls._get_item_count_query_conditions(
            database_order, id_column_name, first_id, last_id, start, end, **query
        )

        sql_query, base_query_values = cls.get_history_base_query(
            select_clause=select_clause,
            environment=environment,
            resource_id=resource_id,
            offset=len(values) + 1,
        )
        values.extend(base_query_values)

        if len(common_filter_statements) > 0:
            sql_query += cls._join_filter_statements(common_filter_statements)

        return sql_query, values

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

    @classmethod
    def versioned_resources_subquery(cls, environment: uuid.UUID, version: int) -> Tuple[str, List[object]]:
        query_builder = SimpleQueryBuilder(
            select_clause="""SELECT r.resource_id, r.attributes, r.resource_version_id, r.resource_type,
                                    r.agent, r.resource_id_value, r.environment""",
            from_clause=f" FROM {cls.table_name()} as r",
            filter_statements=[" environment = $1 ", " model = $2"],
            values=[cls._get_value(environment), cls._get_value(version)],
        )
        return query_builder.build()

    @classmethod
    async def count_versioned_resources_for_paging(
        cls,
        environment: uuid.UUID,
        version: int,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        subquery, subquery_values = cls.versioned_resources_subquery(environment, version)
        base_query = PageCountQueryBuilder(
            from_clause=f"FROM ({subquery}) as result",
            values=subquery_values,
        )
        paging_query = base_query.page_count(database_order, first_id, last_id, start, end)
        filtered_query = paging_query.filter(
            *cls.get_composed_filter_with_query_types(offset=paging_query.offset, col_name_prefix=None, **query)
        )
        sql_query, values = filtered_query.build()
        result = await cls.select_query(sql_query, values, no_obj=True)
        result = cast(List[Record], result)
        if not result:
            raise InvalidQueryParameter(f"Environment {environment} doesn't exist")
        return PagingCounts(total=result[0]["count_total"], before=result[0]["count_before"], after=result[0]["count_after"])

    @classmethod
    async def get_versioned_resources(
        cls,
        version: int,
        database_order: DatabaseOrder,
        limit: int,
        environment: uuid.UUID,
        first_id: Optional[str] = None,
        last_id: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: Tuple[QueryType, object],
    ) -> List[m.VersionedResource]:
        subquery, subquery_values = cls.versioned_resources_subquery(environment, version)

        query_builder = SimpleQueryBuilder(
            select_clause="""SELECT * """,
            from_clause=f" FROM ({subquery}) as result",
            values=subquery_values,
        )
        filtered_query = query_builder.filter(
            *cls.get_composed_filter_with_query_types(offset=query_builder.offset, col_name_prefix=None, **query)
        )
        paged_query = filtered_query.filter(*database_order.as_start_filter(filtered_query.offset, start, first_id)).filter(
            *database_order.as_end_filter(filtered_query.offset, end, last_id)
        )
        order = database_order.get_order()
        backward_paging: bool = (order == PagingOrder.ASC and end is not None) or (
            order == PagingOrder.DESC and start is not None
        )
        ordered_query = paged_query.order_and_limit(database_order, limit, backward_paging)
        sql_query, values = ordered_query.build()

        versioned_resource_records = await cls.select_query(sql_query, values, no_obj=True, connection=connection)
        versioned_resource_records = cast(Iterable[Record], versioned_resource_records)

        dtos = [
            m.VersionedResource(
                resource_id=versioned_resource["resource_id"],
                resource_version_id=versioned_resource["resource_version_id"],
                id_details=cls.get_details_from_resource_id(versioned_resource["resource_id"]),
                requires=json.loads(versioned_resource["attributes"]).get("requires", []),
            )
            for versioned_resource in versioned_resource_records
        ]
        return dtos

    async def insert(self, connection: Optional[asyncpg.connection.Connection] = None) -> None:
        self.make_hash()
        await super(Resource, self).insert(connection=connection)

    @classmethod
    async def insert_many(cls, documents: Iterable["Resource"]) -> None:
        for doc in documents:
            doc.make_hash()
        await super(Resource, cls).insert_many(documents)

    async def update(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: Any) -> None:
        self.make_hash()
        await super(Resource, self).update(connection=connection, **kwargs)

    async def update_fields(self, connection: Optional[asyncpg.connection.Connection] = None, **kwargs: Any) -> None:
        self.make_hash()
        await super(Resource, self).update_fields(connection=connection, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        self.make_hash()
        dct = super(Resource, self).to_dict()
        dct["id"] = dct["resource_version_id"]
        return dct

    def to_dto(self) -> m.Resource:
        return m.Resource(
            environment=self.environment,
            model=self.model,
            resource_id=self.resource_id,
            resource_type=self.resource_type,
            resource_version_id=self.resource_version_id,
            agent=self.agent,
            last_deploy=self.last_deploy,
            attributes=self.attributes,
            status=self.status,
            resource_id_value=self.resource_id_value,
        )


@stable_api
class ConfigurationModel(BaseDocument):
    """
    A specific version of the configuration model.
    Any transactions that update ResourceAction, Resource, Parameter and/or ConfigurationModel
    should acquire their locks in that order.

    :param version: The version of the configuration model, represented by a unix timestamp.
    :param environment: The environment this configuration model is defined in
    :param date: The date this configuration model was created
    :param released: Is this model released and available for deployment?
    :param deployed: Is this model deployed?
    :param result: The result of the deployment. Success or error.
    :param version_info: Version metadata
    :param total: The total number of resources
    """

    version: int = Field(field_type=int, required=True, part_of_primary_key=True)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    date: datetime.datetime = Field(field_type=datetime.datetime)

    released: bool = Field(field_type=bool, default=False)
    deployed: bool = Field(field_type=bool, default=False)
    result: const.VersionState = Field(field_type=const.VersionState, default=const.VersionState.pending)
    version_info: Dict[str, Any] = Field(field_type=dict)

    total: int = Field(field_type=int, default=0)

    # cached state for release
    undeployable: List[m.ResourceIdStr] = Field(field_type=list, required=False)
    skipped_for_undeployable: List[m.ResourceIdStr] = Field(field_type=list, required=False)

    def __init__(self, **kwargs: object) -> None:
        super(ConfigurationModel, self).__init__(**kwargs)
        self._status = {}
        self._done = 0

    @classmethod
    def get_valid_field_names(cls) -> List[str]:
        return super().get_valid_field_names() + ["status"]

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
        order_by_column: Optional[str] = None,
        order: str = "ASC",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        no_obj: bool = False,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: Any,
    ) -> List["ConfigurationModel"]:
        # sanitize and validate order parameters
        if order_by_column:
            cls._validate_order(order_by_column, order)

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
        query = f"""SELECT c.*,
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
                    {offset_statement}"""
        query_result = await cls._fetch_query(query, *values, connection=connection)
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
    async def get_version(cls, environment: uuid.UUID, version: int) -> "ConfigurationModel":
        """
        Get a specific version
        """
        result = await cls.get_one(environment=environment, version=version)
        return result

    @classmethod
    async def get_latest_version(cls, environment: uuid.UUID) -> "ConfigurationModel":
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
    async def get_agents(cls, environment: uuid.UUID, version: int) -> List[str]:
        """
        Returns a list of all agents that have resources defined in this configuration model
        """
        (filter_statement, values) = cls._get_composed_filter(environment=environment, model=version)
        query = "SELECT DISTINCT agent FROM " + Resource.table_name() + " WHERE " + filter_statement
        result = []
        async with cls.get_connection() as con:
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

                # Acquire explicit lock to avoid deadlock. See ConfigurationModel docstring
                await self._execute_query(f"LOCK TABLE {ResourceAction.table_name()} IN SHARE MODE", connection=con)
                await Resource.delete_all(connection=con, environment=self.environment, model=self.version)

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

                # Delete ConfigurationModel and cascade delete on connected tables
                await self.delete(connection=con)

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

    async def mark_done(self) -> None:
        """ mark this deploy as done """
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
        result = await self._fetchval(query, *values)
        self.result = const.VersionState[result]
        self.deployed = True

    @classmethod
    async def mark_done_if_done(
        cls, environment: uuid.UUID, version: int, connection: Optional[asyncpg.connection.Connection] = None
    ) -> None:
        async def do_query_exclusive(con: asyncpg.connection.Connection) -> None:
            """
            Performs the query to mark done if done. Acquires a lock that blocks execution until other transactions holding
            this lock have committed. This makes sure that once a transaction performs this query, it needs to commit before
            another transaction is able to perform it. This way no race condition is possible where the deployed state is
            not set: when a transaction A is in this part of its lifecycle, either all other related (possibly conflicting)
            transactions have committed already, or they will only start this part of their lifecycle when A has committed
            itself.
            """
            async with con.transaction():
                # SHARE UPDATE EXCLUSIVE is self-conflicting
                # and does not conflict with the ROW EXCLUSIVE lock acquired by UPDATE
                await cls._execute_query(f"LOCK TABLE {Resource.table_name()} IN SHARE UPDATE EXCLUSIVE MODE", connection=con)
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

        if connection is None:
            async with cls.get_connection() as con:
                await do_query_exclusive(con)
        else:
            await do_query_exclusive(connection)

    @classmethod
    async def get_increment(
        cls, environment: uuid.UUID, version: int
    ) -> Tuple[Set[m.ResourceVersionIdStr], List[m.ResourceVersionIdStr]]:
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
        projection_a = ["resource_version_id", "resource_id", "status", "attribute_hash", "attributes"]
        projection = ["resource_version_id", "resource_id", "status", "attribute_hash"]

        # get resources for agent
        resources = await Resource.get_resources_for_version_raw(environment, version, projection_a)

        # to increment
        increment = []
        not_increment = []
        # todo in this version
        work = [r for r in resources if r["status"] not in UNDEPLOYABLE_NAMES]

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
                if status in [ResourceState.available.name]:
                    next.append(res)

                # -> increment
                elif status in [
                    ResourceState.failed.name,
                    ResourceState.cancelled.name,
                    ResourceState.deploying.name,
                    ResourceState.processing_events.name,
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

        negative = [res["resource_version_id"] for res in not_increment]

        # patch up the graph
        # 1-include stuff for send-events.
        # 2-adapt requires/provides to get closured set

        outset = set((res["resource_version_id"] for res in increment))  # type: Set[str]
        original_provides = defaultdict(lambda: [])  # type: Dict[str,List[str]]
        send_events = []  # type: List[str]

        # build lookup tables
        for res in resources:
            for req in res["attributes"]["requires"]:
                original_provides[req].append(res["resource_version_id"])
            if "send_event" in res["attributes"] and res["attributes"]["send_event"]:
                send_events.append(res["resource_version_id"])

        # recursively include stuff potentially receiving events from nodes in the increment
        work = list(outset)
        done = set()
        while work:
            current = work.pop()
            if current not in send_events:
                # not sending events, so no receivers
                continue

            if current in done:
                continue
            done.add(current)

            provides = original_provides[current]
            work.extend(provides)
            outset.update(provides)

        return set(outset), negative

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

    @classmethod
    async def count_items_for_paging(
        cls,
        environment: uuid.UUID,
        database_order: DatabaseOrder,
        first_id: Optional[Union[uuid.UUID, str]] = None,
        last_id: Optional[Union[uuid.UUID, str]] = None,
        start: Optional[object] = None,
        end: Optional[object] = None,
        **query: Tuple[QueryType, object],
    ) -> PagingCounts:
        subquery, subquery_values = cls.desired_state_versions_subquery(environment)
        base_query = PageCountQueryBuilder(
            from_clause=f"FROM ({subquery}) as result",
            values=subquery_values,
        )
        paging_query = base_query.page_count(database_order, first_id, last_id, start, end)
        filtered_query = paging_query.filter(
            *cls.get_composed_filter_with_query_types(offset=paging_query.offset, col_name_prefix=None, **query)
        )
        sql_query, values = filtered_query.build()
        result = await cls.select_query(sql_query, values, no_obj=True)
        result = cast(List[Record], result)
        if not result:
            raise InvalidQueryParameter(f"Environment {environment} doesn't exist")
        return PagingCounts(total=result[0]["count_total"], before=result[0]["count_before"], after=result[0]["count_after"])

    @classmethod
    async def get_desired_state_versions(
        cls,
        database_order: DatabaseOrder,
        limit: int,
        environment: uuid.UUID,
        start: Optional[int] = None,
        end: Optional[int] = None,
        connection: Optional[asyncpg.connection.Connection] = None,
        **query: Tuple[QueryType, object],
    ) -> List[m.DesiredStateVersion]:
        subquery, subquery_values = cls.desired_state_versions_subquery(environment)

        query_builder = SimpleQueryBuilder(
            select_clause="""SELECT * """,
            from_clause=f" FROM ({subquery}) as result",
            values=subquery_values,
        )
        filtered_query = query_builder.filter(
            *cls.get_composed_filter_with_query_types(offset=query_builder.offset, col_name_prefix=None, **query)
        )
        paged_query = filtered_query.filter(*database_order.as_start_filter(filtered_query.offset, start)).filter(
            *database_order.as_end_filter(filtered_query.offset, end)
        )
        order = database_order.get_order()
        backward_paging: bool = (order == PagingOrder.ASC and end is not None) or (
            order == PagingOrder.DESC and start is not None
        )
        ordered_query = paged_query.order_and_limit(database_order, limit, backward_paging)
        sql_query, values = ordered_query.build()

        desired_state_version_records = await cls.select_query(sql_query, values, no_obj=True, connection=connection)
        desired_state_version_records = cast(Iterable[Record], desired_state_version_records)

        dtos = [
            m.DesiredStateVersion(
                version=desired_state["version"],
                date=desired_state["date"],
                total=desired_state["total"],
                labels=[m.DesiredStateLabel(name=desired_state["type"], message=desired_state["message"])]
                if desired_state["type"] and desired_state["message"]
                else [],
                status=desired_state["status"],
            )
            for desired_state in desired_state_version_records
        ]
        return dtos


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

    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    resource: str = Field(field_type=str, required=True, part_of_primary_key=True)
    version: int = Field(field_type=int, required=True, part_of_primary_key=True)
    source_refs: Dict[str, Tuple[str, str, List[str]]] = Field(field_type=dict)

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

    id: uuid.UUID = Field(field_type=uuid.UUID, required=True, part_of_primary_key=True)
    environment: uuid.UUID = Field(field_type=uuid.UUID, required=True)
    model: int = Field(field_type=int, required=True)
    date: datetime.datetime = Field(field_type=datetime.datetime)
    total: int = Field(field_type=int, default=0)
    todo: int = Field(field_type=int, default=0)
    resources: Dict[str, Any] = Field(field_type=dict, default={})

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

    def to_dict(self) -> JsonType:
        dict_result = BaseDocument.to_dict(self)
        resources = {r["id"]: r for r in dict_result["resources"].values()}
        dict_result["resources"] = resources
        return dict_result


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
]


def set_connection_pool(pool: asyncpg.pool.Pool) -> None:
    LOGGER.debug("Connecting data classes")
    for cls in _classes:
        cls.set_connection_pool(pool)


async def disconnect() -> None:
    LOGGER.debug("Disconnecting data classes")
    await asyncio.gather(*[cls.close_connection_pool() for cls in _classes])


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
