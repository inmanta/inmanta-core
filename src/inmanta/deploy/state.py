"""
    Copyright 2024 Inmanta

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

import dataclasses
import enum
from collections.abc import Mapping, Set
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, TypeAlias

from inmanta.data.model import ResourceIdStr
from inmanta.util.collections import BidirectionalManyToManyMapping


class RequiresProvidesMapping(BidirectionalManyToManyMapping[ResourceIdStr, ResourceIdStr]):
    def requires(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self

    def provides(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self.reverse_mapping()


AttributeHash: TypeAlias = str


@dataclass(frozen=True)
class ResourceDetails:
    attribute_hash: AttributeHash
    attributes: Mapping[str, object]
    # TODO: consider adding a read-only view on the requires relation?


class ResourceStatus(StrEnum):
    """
    Status of a resource's operational status with respect to its latest desired state, to the best of our knowledge.

    UP_TO_DATE: Resource has had at least one successful deploy for the latest desired state, and no compliance check has
        reported a diff since. Is not affected by later deploy failures, i.e. the last known operational status is assumed to
        hold until observed otherwise.
    HAS_UPDATE: Resource's operational state does not match latest desired state, as far as we know. Either the resource
        has never been (successfully) deployed, or was deployed for a different desired state or a compliance check revealed a
        diff.
    """
    UP_TO_DATE = enum.auto()
    HAS_UPDATE = enum.auto()
    # TODO: undefined / orphan? Otherwise a simple boolean `has_update` or `dirty` might suffice


class DeploymentResult(StrEnum):
    """
    The result of a resource's last (finished) deploy. This result may be for an older version than the latest desired state.
    See ResourceStatus for a resource's operational status with respect to its latest desired state.

    NEW: Resource has never been deployed before.
    DEPLOYED: Last resource deployment was successful.
    FAILED: Last resource deployment was unsuccessful.
    """
    NEW = enum.auto()
    DEPLOYED = enum.auto()
    FAILED = enum.auto()
    # TODO: design also has SKIPPED, do we need it now or add it later?


# TODO: where to link here? directly from ModelState or from ResourceDetails? Probably ResourceDetails
@dataclass
class ResourceState:
    # TODO: remove link, replace with documentation
    # based on https://docs.google.com/presentation/d/1F3bFNy2BZtzZgAxQ3Vbvdw7BWI9dq0ty5c3EoLAtUUY/edit#slide=id.g292b508a90d_0_5
    status: ResourceStatus
    deployment_result: DeploymentResult
    # TODO: add other relevant state fields


@dataclass(kw_only=True)
class ModelState:
    # TODO: document (or refactor to make more clear) that resource_state should only be updated under lock, and all other
    #   fields are considered the domain of the scheduler (not the queue executor)
    version: int
    resources: dict[ResourceIdStr, ResourceDetails] = dataclasses.field(default_factory=dict)
    requires: RequiresProvidesMapping = dataclasses.field(default_factory=RequiresProvidesMapping)
    resource_state: dict[ResourceIdStr, ResourceState] = dataclasses.field(default_factory=dict)
    update_pending: set[ResourceIdStr] = dataclasses.field(default_factory=set)
    """
    Resources that have a new desired state (might be simply a change of its dependencies), which are still being processed by
    the resource scheduler. This is a shortlived transient state, used for internal concurrency control. Kept separate from
    ResourceStatus so that it lives outside of the scheduler lock's scope.
    """

    def update_desired_state(
        self,
        resource: ResourceIdStr,
        attributes: ResourceDetails,
    ) -> None:
        # TODO: raise KeyError if already lives in state?
        self.resources[resource] = attributes
        if resource in self.resource_state:
            self.resource_state[resource].status = ResourceStatus.HAS_UPDATE
        else:
            self.resource_state[resource] = ResourceState(status=ResourceStatus.HAS_UPDATE, deployment_result=DeploymentResult.NEW)

    def update_requires(
        self,
        resource: ResourceIdStr,
        requires: Set[ResourceIdStr],
    ) -> None:
        self.requires[resource] = requires
