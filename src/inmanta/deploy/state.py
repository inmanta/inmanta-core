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

import contextlib
import dataclasses
import enum
from collections import defaultdict
from collections.abc import Mapping, Set
from dataclasses import dataclass
from enum import StrEnum

from inmanta.data.model import ResourceIdStr, ResourceType
from inmanta.resources import Id
from inmanta.util.collections import BidirectionalManyMapping


class RequiresProvidesMapping(BidirectionalManyMapping[ResourceIdStr, ResourceIdStr]):
    def requires_view(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self

    def provides_view(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self.reverse_mapping()


@dataclass(frozen=True)
class ResourceDetails:
    resource_id: ResourceIdStr
    attribute_hash: str
    attributes: Mapping[str, object] = dataclasses.field(hash=False)

    id: Id = dataclasses.field(init=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        # use object.__setattr__ because this is a frozen dataclass, see dataclasses docs
        object.__setattr__(self, "id", Id.parse_id(self.resource_id))


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


class AgentStatus(StrEnum):
    """
    The status of the agent responsible of a given resource.

    STARTED: Agent has been started.
    STOPPED: Agent has been stopped (previously called PAUSED).
    """

    STARTED = enum.auto()
    STOPPED = enum.auto()


@dataclass
class ResourceState:
    """
    State of a resource. Consists of multiple independent (mostly) state vectors that make up the final state.
    """

    # FIXME: review / finalize resource state. Based on draft design in
    #   https://docs.google.com/presentation/d/1F3bFNy2BZtzZgAxQ3Vbvdw7BWI9dq0ty5c3EoLAtUUY/edit#slide=id.g292b508a90d_0_5
    status: ResourceStatus
    deployment_result: DeploymentResult
    agent_stauts: AgentStatus


@dataclass(kw_only=True)
class ModelState:
    """
    The state of the model, meaning both resource intent and resource state.

    Invariant: all resources in the current model, and only those, exist in the resources and resource_state mappings.
    """

    version: int
    resources: dict[ResourceIdStr, ResourceDetails] = dataclasses.field(default_factory=dict)
    requires: RequiresProvidesMapping = dataclasses.field(default_factory=RequiresProvidesMapping)
    resource_state: dict[ResourceIdStr, ResourceState] = dataclasses.field(default_factory=dict)
    # resources with a known or assumed difference between intent and actual state
    dirty: set[ResourceIdStr] = dataclasses.field(default_factory=set)
    # types per agent keeps track of which resource types live on which agent by doing a reference count
    # the dict is agent_name -> resource_type -> resource_count
    types_per_agent: dict[str, dict[ResourceType, int]] = dataclasses.field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: 0))
    )
    agent_status: dict[str, AgentStatus] = dataclasses.field(default_factory=dict)
    """
    Resources that have a new desired state (might be simply a change of its dependencies), which are still being processed by
    the resource scheduler. This is a shortlived transient state, used for internal concurrency control. Kept separate from
    ResourceStatus so that it lives outside of the scheduler lock's scope.
    """

    def reset(self) -> None:
        self.version = 0
        self.resources.clear()
        self.requires.clear()
        self.resource_state.clear()
        self.types_per_agent.clear()
        self.agent_status.clear()

    def update_desired_state(
        self,
        resource: ResourceIdStr,
        details: ResourceDetails,
    ) -> None:
        """
        Register a new desired state for a resource.
        """
        self.resources[resource] = details
        if resource in self.resource_state:
            self.resource_state[resource].status = ResourceStatus.HAS_UPDATE
        else:
            self.resource_state[resource] = ResourceState(
                status=ResourceStatus.HAS_UPDATE,
                deployment_result=DeploymentResult.NEW,
                agent_stauts=AgentStatus.STARTED,
            )
            self.types_per_agent[details.id.agent_name][details.id.entity_type] += 1
        self.dirty.add(resource)

    def update_requires(
        self,
        resource: ResourceIdStr,
        requires: Set[ResourceIdStr],
    ) -> None:
        """
        Update the requires relation for a resource. Updates the reverse relation accordingly.
        """
        self.requires[resource] = requires

    def drop(self, resource: ResourceIdStr) -> None:
        """
        Completely remove a resource from the resource state.
        """
        details: ResourceDetails = self.resources.pop(resource)
        del self.resource_state[resource]
        # stand-alone resources may not be in requires
        with contextlib.suppress(KeyError):
            del self.requires[resource]
        # top-level resources may not be in provides
        with contextlib.suppress(KeyError):
            del self.requires.reverse_mapping()[resource]

        self.types_per_agent[details.id.agent_name][details.id.entity_type] -= 1
        if self.types_per_agent[details.id.agent_name][details.id.entity_type] == 0:
            del self.types_per_agent[details.id.agent_name][details.id.entity_type]
        self.dirty.discard(resource)
