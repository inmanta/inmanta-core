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
from queue import SimpleQueue

from inmanta import const
from inmanta.data.model import ResourceIdStr, ResourceType
from inmanta.resources import Id
from inmanta.util.collections import BidirectionalManyMapping


class RequiresProvidesMapping(BidirectionalManyMapping[ResourceIdStr, ResourceIdStr]):
    def requires_view(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self

    def provides_view(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self.reverse_mapping()

    def get_all_provides_transitively(self, resource: ResourceIdStr | Set[ResourceIdStr]) -> list[ResourceIdStr]:
        """
        This method returns all the provides (transitively) of the given resource. The returned list will be sorted as such
        that all the requires of an elements in the list appear before that element in the list. The result will not include
        any resource ids from the input, even if there exists a provides edge between them.

        :param resource: The resource or set of resources for which the provides have to be resolved transitively.
        """
        # Use a dict here to not lose the order of the elements.
        result: dict[ResourceIdStr, None] = {}

        def append_to_result(res: ResourceIdStr) -> None:
            """
            Add `res` to the `result` dictionary. If `res` already exists in `result`, make sure that `res` appears
            last when executing `result.keys()`.
            """
            result.pop(res, None)
            result[res] = None

        input_set = {resource} if isinstance(resource, str) else set(resource)
        work: SimpleQueue[ResourceIdStr] = SimpleQueue()
        for elem in input_set:
            work.put_nowait(elem)
        provides_mapping = self.provides_view()
        while not work.empty():
            current_resource = work.get()
            append_to_result(current_resource)
            provides = provides_mapping.get(current_resource, set())
            for elem in provides:
                # We may queue an element multiple times here. This is required to properly sort the result.
                work.put_nowait(elem)
        for elem in input_set:
            result.pop(elem, None)
        return list(result.keys())


@dataclass(frozen=True)
class ResourceDetails:
    resource_id: ResourceIdStr
    attribute_hash: str
    attributes: Mapping[str, object] = dataclasses.field(hash=False)
    status: const.ResourceState

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
    UNDEFINED: The resource status is undefined, because it has an unknown attribute.
    """

    UP_TO_DATE = enum.auto()
    HAS_UPDATE = enum.auto()
    UNDEFINED = enum.auto()


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


class BlockedStatus(StrEnum):
    """
    YES: The resource will retain its blocked status within this model version. For example: A resource that has unknowns
         or depends on a resource with unknowns.
    NO: The resource is not blocked
    """

    YES = enum.auto()
    NO = enum.auto()

    def is_blocked(self) -> bool:
        """
        Return True iff the resource is currently blocked.
        """
        return self is not BlockedStatus.NO


@dataclass
class ResourceState:
    """
    State of a resource. Consists of multiple independent (mostly) state vectors that make up the final state.
    """

    # FIXME: review / finalize resource state. Based on draft design in
    #   https://docs.google.com/presentation/d/1F3bFNy2BZtzZgAxQ3Vbvdw7BWI9dq0ty5c3EoLAtUUY/edit#slide=id.g292b508a90d_0_5
    status: ResourceStatus
    deployment_result: DeploymentResult
    blocked: BlockedStatus
    agent_status: AgentStatus


@dataclass(kw_only=True)
class ModelState:
    """
    The state of the model, meaning both resource intent and resource state.

    Invariant: all resources in the current model, and only those, exist in the resources (also undeployable resources)
               and resource_state mappings.
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

    def block_resource(self, resource: ResourceIdStr, details: ResourceDetails, transient: bool) -> None:
        """
        Mark the given resource as blocked, i.e. it's not deployable. This method updates the resource details
        and the resource_status.

        :param resource: The resource that should be blocked.
        :param details: The details of the resource that should be blocked.
        :param transient: True iff the given resource is blocked transitively. It's blocked because one of its dependencies
                          is blocked.
        """
        self.resources[resource] = details
        if resource in self.resource_state:
            if not transient:
                self.resource_state[resource].status = ResourceStatus.UNDEFINED
            self.resource_state[resource].blocked = BlockedStatus.YES
        else:
            resource_status = ResourceStatus.UNDEFINED if not transient else ResourceStatus.HAS_UPDATE
            self.resource_state[resource] = ResourceState(
                status=resource_status,
                deployment_result=DeploymentResult.NEW,
                blocked=BlockedStatus.YES,
                agent_status=AgentStatus.STARTED,
            )
            self.types_per_agent[details.id.agent_name][details.id.entity_type] += 1
        self.dirty.discard(resource)

    def block_provides(self, resources: Set[ResourceIdStr]) -> set[ResourceIdStr]:
        """
        Marks the provides of the given resources as blocked.

        Must be called under the scheduler lock. This method assumes that all the resources of the model version
        are populated in the resources dictionary.

        :param resources: The set of resources for which the provides have to be blocked.
        :return: The set of dependent resources that were marked as blocked (transitively).
        """
        result = set()
        for dependent_resource in self.requires.get_all_provides_transitively(resources):
            self.block_resource(dependent_resource, self.resources[dependent_resource], transient=True)
            result.add(dependent_resource)
        return result

    def unblock_resource(self, resource: ResourceIdStr) -> None:
        """
        Mark the given resource no longer as blocked. Also mark the provides of the given resource as unblocked (transitively)
        if they become unblocked because of this.

        Must be called under the scheduler lock. This method assumes that all the resources of the model version
        are populated in the resources dictionary.

        :param resource: The resource that has to be unblocked and potentially any of its provides as a consequence of
                         `resource` being unblocked.
        """

        def _unblock(resource: ResourceIdStr) -> None:
            self.resource_state[resource].blocked = BlockedStatus.NO
            if self.resource_state[resource].status is ResourceStatus.UNDEFINED:
                self.resource_state[resource].status = ResourceStatus.HAS_UPDATE
            if self.resource_state[resource].status is ResourceStatus.HAS_UPDATE:
                self.dirty.add(resource)

        _unblock(resource)
        for res in self.requires.get_all_provides_transitively(resource):
            is_blocked = self.resource_state[res].status is ResourceStatus.UNDEFINED or any(
                self.resource_state[r].blocked.is_blocked() for r in self.requires.get(res, set())
            )
            if not is_blocked:
                _unblock(res)

    def update_desired_state(
        self,
        resource: ResourceIdStr,
        details: ResourceDetails,
    ) -> None:
        """
        Register a new desired state for a resource.

        For blocked resources, block_resource() should be called instead.
        """
        self.resources[resource] = details
        if resource in self.resource_state:
            self.resource_state[resource].status = ResourceStatus.HAS_UPDATE
            self.resource_state[resource].blocked = BlockedStatus.NO
        else:
            self.resource_state[resource] = ResourceState(
                status=ResourceStatus.HAS_UPDATE,
                deployment_result=DeploymentResult.NEW,
                blocked=BlockedStatus.NO,
                agent_status=AgentStatus.STARTED,
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
