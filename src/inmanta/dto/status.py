"""
Copyright 2019 Inmanta

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

from enum import StrEnum
from typing import Mapping, Optional, Union

from inmanta.types import ArgumentTypes
from inmanta.types import BaseModel as BaseModel
from inmanta.types import SimpleTypes


class ExtensionStatus(BaseModel):
    """
    Status response for extensions loaded in the server
    """

    name: str
    version: str
    package: str


class ReportedStatus(StrEnum):
    OK = "OK"
    Warning = "Warning"
    Error = "Error"

    def __gt__(self, other: str) -> bool:
        # Determines the order of severity of the reported status
        order: list[str] = [ReportedStatus.OK, ReportedStatus.Warning, ReportedStatus.Error]
        if self not in order or other not in order:
            raise ValueError
        return order.index(self) > order.index(other)


class SliceStatus(BaseModel):
    """
    Status response for slices loaded in the server
    """

    name: str
    status: Mapping[str, ArgumentTypes | Mapping[str, ArgumentTypes]]
    reported_status: ReportedStatus
    message: str | None = None


class FeatureStatus(BaseModel):
    """
    Status of the feature
    """

    slice: str
    name: str
    value: Optional[object] = None


class StatusResponse(BaseModel):
    """
    Response for the status method call

    :param product: The name of the product.
    :param edition: The edition of the product.
    :param version: The version of the product.
    :param license: The license used by the product.
    :param extensions: The status of the extensions of the server
    :param slices: The status of the slices of the server.
    :param features: The status of the features offered by the slices of the server.
    :param status: The overall status of the server
    :param python_version: The python version used by the server.
    :param postgresql_version: The postgresql version used by the database slice
        None if it is not initialized or an error occurred with the database slice.
    """

    product: str
    edition: str
    version: str
    license: Union[str, dict[str, SimpleTypes]]
    extensions: list[ExtensionStatus]
    slices: list[SliceStatus]
    features: list[FeatureStatus]
    status: ReportedStatus
    python_version: str
    postgresql_version: str | None
