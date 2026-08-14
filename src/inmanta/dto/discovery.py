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

import typing
import urllib
from typing import Optional

import pydantic.schema
from pydantic import computed_field

from inmanta import resources
from inmanta.types import BaseModel as BaseModel
from inmanta.types import ResourceIdStr as ResourceIdStr
from inmanta.types import ResourceType as ResourceType


def _check_resource_id_str(v: str) -> ResourceIdStr:
    if resources.Id.is_resource_id(v):
        return ResourceIdStr(v)
    raise ValueError("Invalid id for resource %s" % v)


ResourceId: typing.TypeAlias = typing.Annotated[ResourceIdStr, pydantic.AfterValidator(_check_resource_id_str)]


class DiscoveredResourceABC(BaseModel):
    """
    :param discovered_resource_id: The name of the resource
    :param values: The actual resource
    :param managed_resource_uri: URI of the resource with the same ID that is already
        managed by the orchestrator e.g. "/api/v2/resource/<rid>". Or None if the resource is not managed.
    :param discovery_resource_id: Resource id of the (managed) discovery resource that reported this
        discovered resource.
    """

    discovered_resource_id: ResourceId
    values: dict[str, object]
    managed_resource_uri: Optional[str] = None

    discovery_resource_id: ResourceId

    # computed_field turns this into a property itself. Stacking an explicit @property on top is what mypy rejects as a
    # decorated property, so do not add one back.
    @computed_field
    def discovery_resource_uri(self) -> str | None:
        return f"/api/v2/resource/{urllib.parse.quote(self.discovery_resource_id, safe='')}"


class DiscoveredResourceOutput(DiscoveredResourceABC):
    """
    Discovered resource for API returns. Contains additional (redundant) metadata to improve user experience.
    """

    resource_type: ResourceType
    agent: str
    resource_id_value: str


class DiscoveredResourceInput(DiscoveredResourceABC):
    """
    A discovered resource that is sent to the API.
    """
