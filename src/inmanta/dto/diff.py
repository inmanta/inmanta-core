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

import datetime
from enum import Enum
from typing import Optional

from inmanta.deploy.state import Compliance, HandlerResult
from inmanta.dto.resource import AttributeStateChange
from inmanta.types import BaseModel as BaseModel
from inmanta.types import ResourceIdStr as ResourceIdStr


class ResourceDiffStatus(str, Enum):
    added = "added"
    modified = "modified"
    deleted = "deleted"
    unmodified = "unmodified"
    agent_down = "agent_down"
    undefined = "undefined"
    skipped_for_undefined = "skipped_for_undefined"


class AttributeDiff(BaseModel):
    """
    :param from_value: The value of the attribute in the earlier version
    :param to_value: The value of the attribute in the later version
    :param from_value_compare: A stringified, diff-friendly form of the 'from_value' field
    :param to_value_compare: A stringified, diff-friendly form of the 'to_value' field
    """

    from_value: Optional[object] = None
    to_value: Optional[object] = None
    from_value_compare: str
    to_value_compare: str


class ResourceDiff(BaseModel):
    """
    :param resource_id: The id of the resource the diff is about (without version)
    :param attributes: The diff between the attributes of two versions of the resource
    :param status: The kind of diff between the versions of the resource
    """

    resource_id: ResourceIdStr
    attributes: dict[str, AttributeDiff]
    status: ResourceDiffStatus


class ResourceComplianceDiff(BaseModel):
    """
    :param report_only: Is this resource in report only mode.
    :param compliance: The current compliance of this resource.
    :param last_handler_run: The handler result of the last run of this resource.
    :param last_handler_run_at: The timestamp of the last run of this resource.
    :param attribute_diff: The diff between the attributes of the current and desired state of a non_compliant resource.
    """

    report_only: bool
    compliance: Compliance
    last_handler_run: HandlerResult
    last_handler_run_at: datetime.datetime | None
    attribute_diff: dict[str, AttributeStateChange] | None
