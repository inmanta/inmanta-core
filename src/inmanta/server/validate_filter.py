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
from abc import ABC, abstractmethod
from typing import Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, Extra, ValidationError

from inmanta.const import ResourceState
from inmanta.data import QueryFilter, QueryType


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
    value: Optional[List[str]]
    status: Optional[List[ResourceState]]


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
        if validated_filter.value:
            query["value"] = (QueryType.CONTAINS_PARTIAL, validated_filter.value)
        if validated_filter.status:
            query["status"] = (QueryType.CONTAINS, validated_filter.status)

        return query
