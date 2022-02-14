"""
    Copyright 2021 Inmanta

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
import datetime
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Tuple, Type, TypeVar

import dateutil
import more_itertools
from pydantic import BaseModel, ValidationError, validator

from inmanta import const
from inmanta.data import DateRangeConstraint, QueryFilter, QueryType, RangeConstraint, RangeOperator
from inmanta.data.model import ReleasedResourceState


class InvalidFilter(Exception):
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


def parse_single_value(v: object) -> object:
    """
    Transform list values to their single element value.
    """
    if isinstance(v, list):
        return more_itertools.one(
            v,
            too_short=ValueError("Empty filter provided"),
            too_long=ValueError(f"Multiple values provided for filter: {v}"),
        )

    return v


def parse_range_value_to_date(single_constraint: str, value: str) -> datetime.datetime:
    try:
        datetime_obj: datetime.datetime = dateutil.parser.isoparse(value)
    except ValueError:
        raise ValueError("Invalid range constraint %s: '%s' is not a valid datetime" % (single_constraint, value))
    else:
        return datetime_obj if datetime_obj.tzinfo is not None else datetime_obj.replace(tzinfo=datetime.timezone.utc)


def parse_range_value_to_int(single_constraint: str, value: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise ValueError("Invalid range constraint %s: '%s' is not an integer" % (single_constraint, value))


S = TypeVar("S", int, datetime.datetime)


def get_range_operator_parser(
    parse_value_to_type: Callable[[str, str], S]
) -> Callable[[object, object], Optional[List[Tuple[RangeOperator, S]]]]:
    def parse_range_operator(v: object) -> Optional[List[Tuple[RangeOperator, S]]]:
        """
        Transform list of "<lt|le|gt|ge>:<x>" constraint specifiers to typed objects.
        """

        def transform_single(single: str, parse_value_to_type: Callable[[str, str], S]) -> Tuple[RangeOperator, S]:
            split: List[str] = single.split(":", maxsplit=1)
            if len(split) != 2:
                raise ValueError("Invalid range constraint %s, expected '<lt|le|gt|ge>:<x>`" % single)
            operator: RangeOperator
            try:
                operator = RangeOperator.parse(split[0])
            except ValueError:
                raise ValueError(
                    "Invalid range operator %s in constraint %s, expected one of lt, le, gt, ge" % (split[0], single)
                )
            bound = parse_value_to_type(single, split[1])
            return (operator, bound)

        if v is None:
            return None

        if isinstance(v, str):
            return [transform_single(v, parse_value_to_type=parse_value_to_type)]

        if isinstance(v, list) and all(isinstance(x, str) for x in v):
            return [transform_single(x, parse_value_to_type=parse_value_to_type) for x in v]

        raise ValueError(f"value is not a valid list of range constraints: {str(v)}")

    return parse_range_operator


class Filter(ABC, BaseModel):
    """A pydantic model for a specific filter
    Subclasses are expected to have property named `field`, representing the value to be validated.
    The `to_query_type` method describes how to interpret this as filter in for a database query by providing the correct
    `QueryType`
    """

    # Pydantic doesn't support Generic BaseModels on python 3.6

    @abstractmethod
    def to_query_type(self) -> Optional[Tuple[QueryType, object]]:
        """Get the value of the filter with the correct query type"""
        pass


class BooleanEqualityFilter(Filter):
    """Represents a valid boolean which should be handled as an equality filter"""

    field: Optional[bool]
    validate_field: classmethod = validator("field", pre=True, allow_reuse=True)(parse_single_value)

    def to_query_type(self) -> Optional[Tuple[QueryType, object]]:
        if self.field is not None:
            return (QueryType.EQUALS, self.field)
        return None


class BooleanIsNotNullFilter(BooleanEqualityFilter, Filter):
    """Represents a valid boolean which should be handled as an IS_NOT_NULL filter"""

    def to_query_type(self) -> Optional[Tuple[QueryType, object]]:
        if self.field is not None:
            return (QueryType.IS_NOT_NULL, None) if self.field else (QueryType.EQUALS, None)
        return None


class DateRangeFilter(Filter):
    """Represents a valid date range constraint which should be handled as a range filter"""

    field: Optional[DateRangeConstraint]

    @validator("field", pre=True)
    @classmethod
    def parse_requested(cls, v: object) -> Optional[List[Tuple[RangeOperator, datetime.datetime]]]:
        return get_range_operator_parser(parse_range_value_to_date)(v)

    def to_query_type(self) -> Optional[Tuple[QueryType, object]]:
        if self.field:
            return (QueryType.RANGE, self.field)
        return None


class IntRangeFilter(Filter):
    field: Optional[RangeConstraint]

    @validator("field", pre=True)
    @classmethod
    def parse_field(cls, v: object) -> Optional[List[Tuple[RangeOperator, int]]]:
        return get_range_operator_parser(parse_range_value_to_int)(v)

    def to_query_type(self) -> Optional[Tuple[QueryType, object]]:
        if self.field:
            return (QueryType.RANGE, self.field)
        return None


class ContainsPartialFilter(Filter):
    """Represents a valid string list constraint which should be handled as a partial containment filter"""

    field: Optional[List[str]]

    def to_query_type(self) -> Optional[Tuple[QueryType, object]]:
        if self.field:
            return (QueryType.CONTAINS_PARTIAL, self.field)
        return None


class ContainsFilter(Filter):
    """Represents a valid string list constraint which should be handled as a containment filter"""

    field: Optional[List[str]]

    def to_query_type(self) -> Optional[Tuple[QueryType, object]]:
        if self.field:
            return (QueryType.CONTAINS, self.field)
        return None


class ContainsFilterResourceState(Filter):
    """Represents a valid ReleasedResourceState list constraint which should be handled as a containment filter"""

    # Pydantic doesn't support Generic models on python 3.6
    field: Optional[List[ReleasedResourceState]]

    def to_query_type(self) -> Optional[Tuple[QueryType, object]]:
        if self.field:
            return (QueryType.CONTAINS, self.field)
        return None


class ContainsFilterResourceAction(Filter):
    """Represents a valid ResourceAction list constraint which should be handled as a containment filter"""

    # Pydantic doesn't support Generic models on python 3.6
    field: Optional[List[const.ResourceAction]]

    def to_query_type(self) -> Optional[Tuple[QueryType, object]]:
        if self.field:
            return (QueryType.CONTAINS, self.field)
        return None


class LogLevelFilter(Filter):
    """Represents a valid LogLevel constraint which is considered to be the minimal log level"""

    field: Optional[const.LogLevel]

    @validator("field", pre=True)
    @classmethod
    def _field_single(cls, v: object) -> object:
        """
        Transform a list to a single log level
        """
        if isinstance(v, list):
            try:
                return const.LogLevel[
                    more_itertools.one(
                        v,
                        too_short=ValueError("Empty 'minimal_log_level' filter provided"),
                        too_long=ValueError(f"Multiple values provided for 'minimal_log_level' filter: {v}"),
                    ).upper()
                ]
            except KeyError:
                raise ValueError(f"{v} is not a valid log level")
        return v

    def to_query_type(self) -> Optional[Tuple[QueryType, object]]:
        if self.field is not None:
            return (QueryType.CONTAINS, self._get_log_levels_for_filter(self.field))
        return None

    def _get_log_levels_for_filter(self, minimal_log_level: const.LogLevel) -> List[str]:
        return [level.value for level in const.LogLevel if level.to_int >= minimal_log_level.to_int]


class FilterValidator(ABC):
    """
    This class provides methods to validate and process filters as received via the API.
    """

    @property
    @abstractmethod
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        """A dictionary that determines the mapping between the allowed filters and how they should be parsed and validated"""
        raise NotImplementedError()

    def process_filters(self, filter: Dict[str, List[str]]) -> Dict[str, QueryFilter]:
        """
        Processes filters and returns a structured query filter object.

        :raises InvalidFilter: The supplied filter is invalid.
        """

        query: Dict[str, QueryFilter] = {}
        for filter_name, filter_class in self.allowed_filters.items():
            try:
                # Validate the provided filter value with pydantic,
                # then determine how it should be handled according to its QueryType
                validated_query_type = filter_class(field=filter.get(filter_name)).to_query_type()
                if validated_query_type is not None:
                    query[filter_name] = validated_query_type
            except ValidationError as e:
                raise InvalidFilter(
                    f"Filter validation failed while parsing {filter_name}: {str(e)}, values provided: {str(filter)}"
                ) from e
        not_allowed_filters = set(filter.keys()) - set(self.allowed_filters.keys())
        if len(not_allowed_filters) > 0:
            raise InvalidFilter(f"The following filters are not supported: {not_allowed_filters}")
        return query


class ResourceFilterValidator(FilterValidator):
    @property
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "resource_type": ContainsPartialFilter,
            "agent": ContainsPartialFilter,
            "resource_id_value": ContainsPartialFilter,
            "status": ContainsFilterResourceState,
        }


class ResourceLogFilterValidator(FilterValidator):
    @property
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "minimal_log_level": LogLevelFilter,
            "timestamp": DateRangeFilter,
            "message": ContainsPartialFilter,
            "action": ContainsFilterResourceAction,
        }

    def process_filters(self, filter: Dict[str, List[str]]) -> Dict[str, QueryFilter]:
        # Change the api names of the filters to the names used internally in the database
        query = super().process_filters(filter)
        if query.get("minimal_log_level"):
            filter_value = query.pop("minimal_log_level")
            query["level"] = filter_value
        if query.get("message"):
            filter_value = query.pop("message")
            query["msg"] = filter_value
        return query


class CompileReportFilterValidator(FilterValidator):
    @property
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "requested": DateRangeFilter,
            "success": BooleanEqualityFilter,
            "started": BooleanIsNotNullFilter,
            "completed": BooleanIsNotNullFilter,
        }


class AgentFilterValidator(FilterValidator):
    @property
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "name": ContainsPartialFilter,
            "process_name": ContainsPartialFilter,
            "status": ContainsFilter,
        }


class DesiredStateVersionFilterValidator(FilterValidator):
    @property
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "version": IntRangeFilter,
            "date": DateRangeFilter,
            "status": ContainsFilter,
        }


class VersionedResourceFilterValidator(FilterValidator):
    @property
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "resource_type": ContainsPartialFilter,
            "agent": ContainsPartialFilter,
            "resource_id_value": ContainsPartialFilter,
        }


class ParameterFilterValidator(FilterValidator):
    @property
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "name": ContainsPartialFilter,
            "source": ContainsPartialFilter,
            "updated": DateRangeFilter,
        }


class FactsFilterValidator(FilterValidator):
    @property
    def allowed_filters(self) -> Dict[str, Type[Filter]]:
        return {
            "name": ContainsPartialFilter,
            "resource_id": ContainsPartialFilter,
        }
