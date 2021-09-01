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
from typing import Dict, Generic, List, Optional, Tuple, Type, TypeVar

import dateutil
import more_itertools
from pydantic import BaseModel, Extra, ValidationError, validator

from inmanta import const
from inmanta.data import DateRangeConstraint, QueryFilter, QueryType, RangeOperator
from inmanta.data.model import ReleasedResourceState


class InvalidFilter(Exception):
    def __init__(self, message: str, *args) -> None:
        super().__init__(message, *args)
        self.message = message


class FilterModel(BaseModel, extra=Extra.forbid):
    pass


T = TypeVar("T", bound=FilterModel)


class FilterValidator(ABC, Generic[T]):
    """
    This class provides methods to validate and process filters as received via the API.
    """

    @property
    @abstractmethod
    def model(self) -> Type[T]:
        raise NotImplementedError()

    def validate_filters(self, filter: Dict[str, List[str]]) -> T:
        """
        Validate filters as received via the API and return a corresponding pydantic structure.
        """
        try:
            return self.model(**filter)
        except ValidationError as e:
            raise InvalidFilter(f"Filter validation failed: {str(e)}, values provided: {str(filter)}") from e

    @abstractmethod
    def process_filters(self, filter: Dict[str, List[str]]) -> Dict[str, QueryFilter]:
        """
        Processes filters and returns a structured query filter object.

        :raises InvalidFilter: The supplied filter is invalid.
        """
        raise NotImplementedError()


class ResourceFilterModel(FilterModel):
    resource_type: Optional[List[str]]
    agent: Optional[List[str]]
    resource_id_value: Optional[List[str]]
    status: Optional[List[ReleasedResourceState]]


class ResourceFilterValidator(FilterValidator):
    @property
    def model(self) -> Type[ResourceFilterModel]:
        return ResourceFilterModel

    def process_filters(self, filter: Dict[str, List[str]]) -> Dict[str, QueryFilter]:
        validated_filter: ResourceFilterModel = self.validate_filters(filter)
        query: Dict[str, QueryFilter] = {}
        if validated_filter.resource_type:
            query["resource_type"] = (QueryType.CONTAINS_PARTIAL, validated_filter.resource_type)
        if validated_filter.agent:
            query["agent"] = (QueryType.CONTAINS_PARTIAL, validated_filter.agent)
        if validated_filter.resource_id_value:
            query["resource_id_value"] = (QueryType.CONTAINS_PARTIAL, validated_filter.resource_id_value)
        if validated_filter.status:
            query["status"] = (QueryType.CONTAINS, validated_filter.status)

        return query


def parse_range_value_to_date(single_constraint: str, value: str) -> datetime.datetime:
    try:
        datetime_obj: datetime.datetime = dateutil.parser.isoparse(value)
    except ValueError:
        raise ValueError("Invalid range constraint %s: '%s' is not a valid datetime" % (single_constraint, value))
    else:
        return datetime_obj if datetime_obj.tzinfo is not None else datetime_obj.replace(tzinfo=datetime.timezone.utc)


class ResourceLogFilterModel(FilterModel):
    minimal_log_level: Optional[const.LogLevel]
    timestamp: Optional[DateRangeConstraint]
    message: Optional[List[str]]
    action: Optional[List[const.ResourceAction]]

    @validator("minimal_log_level", pre=True)
    @classmethod
    def _deleted_single(cls, v: object) -> object:
        """
        Transform list values to their single element value.
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

    @validator("timestamp", pre=True)
    @classmethod
    def parse_range_operator(cls, v: object) -> List[Tuple[RangeOperator, datetime.datetime]]:
        """
        Transform list of "<lt|le|gt|ge>:<x>" constraint specifiers to typed objects.
        """

        def transform_single(single: str) -> Tuple[RangeOperator, datetime.datetime]:
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
            bound = parse_range_value_to_date(single, split[1])
            return (operator, bound)

        if isinstance(v, str):
            return [transform_single(v)]

        if isinstance(v, list) and all(isinstance(x, str) for x in v):
            return [transform_single(x) for x in v]

        raise ValueError(f"value is not a valid list of range constraints: {str(v)}")


def get_log_levels_for_filter(minimal_log_level: const.LogLevel) -> List[str]:
    return [level.value for level in const.LogLevel if level.to_int >= minimal_log_level.to_int]


class ResourceLogFilterValidator(FilterValidator):
    @property
    def model(self) -> Type[ResourceLogFilterModel]:
        return ResourceLogFilterModel

    def process_filters(self, filter: Dict[str, List[str]]) -> Dict[str, QueryFilter]:
        validated_filter: ResourceLogFilterModel = self.validate_filters(filter)
        query: Dict[str, QueryFilter] = {}
        if validated_filter.minimal_log_level:
            query["level"] = (QueryType.CONTAINS, get_log_levels_for_filter(validated_filter.minimal_log_level))
        if validated_filter.timestamp:
            query["timestamp"] = (QueryType.RANGE, validated_filter.timestamp)
        if validated_filter.message:
            query["msg"] = (QueryType.CONTAINS_PARTIAL, validated_filter.message)
        if validated_filter.action:
            query["action"] = (QueryType.CONTAINS, validated_filter.action)

        return query
