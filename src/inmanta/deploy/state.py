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
import itertools
from collections import defaultdict
from collections.abc import Mapping, Set
from dataclasses import dataclass
from enum import StrEnum
from typing import AbstractSet, Tuple

from inmanta import const
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
    status: const.ResourceState

    id: Id = dataclasses.field(init=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        # use object.__setattr__ because this is a frozen dataclass, see dataclasses docs
        object.__setattr__(self, "id", Id.parse_id(self.resource_id))


class ComplianceStatus(StrEnum):
    """
    Status of a resource's operational status with respect to its latest desired state, to the best of our knowledge.
    COMPLIANT: The operational state complies to latest resource intent as far as we know.
    HAS_UPDATE: The resource intent has been updated since latest deploy attempt (if any),
        meaning we are not yet managing the new intent.
    NON_COMPLIANT: The resource intent has not been updated since latest deploy attempt (if any)
        but we have reason to believe operational state might not comply with latest resource intent,
        based on a deploy attempt / compliance check for that intent.
    UNDEFINED: The resource status is undefined, because it has an unknown attribute.
    """

    COMPLIANT = enum.auto()
    HAS_UPDATE = enum.auto()
    NON_COMPLIANT = enum.auto()
    UNDEFINED = enum.auto()


class DeploymentResult(StrEnum):
    """
    The result of a resource's last (finished) deploy. This result may be for an older version than the latest desired state.
    See ResourceStatus for a resource's operational status with respect to its latest desired state.

    NEW: Resource has never been deployed before.
    DEPLOYED: Last resource deployment was successful.
    FAILED: Last resource deployment was unsuccessful.
    SKIPPED: Resource skipped deployment.
    """

    NEW = enum.auto()
    DEPLOYED = enum.auto()
    FAILED = enum.auto()
    SKIPPED = enum.auto()


class AgentStatus(StrEnum):
    """
    The status of the agent responsible of a given resource.

    STARTED: Agent has been started.
    STOPPING: Agent is stopping.
    STOPPED: Agent has been stopped (previously called PAUSED).
    """

    STARTED = enum.auto()
    STOPPING = enum.auto()
    STOPPED = enum.auto()


class BlockedStatus(StrEnum):
    """
    YES: The resource will retain its blocked status within this model version. For example: A resource that has unknowns
         or depends on a resource with unknowns.
    NO: The resource is not blocked
    TRANSIENT: The resource is blocked but may recover within the same version.
        Concretely it is waiting for its dependencies to deploy successfully.
    """

    YES = enum.auto()
    NO = enum.auto()
    TRANSIENT = enum.auto()


@dataclass
class ResourceState:
    """
    State of a resource. Consists of multiple independent (mostly) state vectors that make up the final state.
    """

    # FIXME: review / finalize resource state. Based on draft design in
    #   https://docs.google.com/presentation/d/1F3bFNy2BZtzZgAxQ3Vbvdw7BWI9dq0ty5c3EoLAtUUY/edit#slide=id.g292b508a90d_0_5
    status: ComplianceStatus
    deployment_result: DeploymentResult
    blocked: BlockedStatus


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

    def reset(self) -> None:
        self.version = 0
        self.resources.clear()
        self.requires.clear()
        self.resource_state.clear()
        self.types_per_agent.clear()

    def add_up_to_date_resource(self, resource: ResourceIdStr, details: ResourceDetails) -> None:
        """
        Add a resource to this ModelState for which the desired state was successfully deployed before, has an up-to-date
        desired state and for which the deployment isn't blocked at the moment.
        """
        self.resources[resource] = details
        if resource in self.resource_state:
            self.resource_state[resource].status = ComplianceStatus.COMPLIANT
            self.resource_state[resource].deployment_result = DeploymentResult.DEPLOYED
            self.resource_state[resource].blocked = BlockedStatus.NO
        else:
            self.resource_state[resource] = ResourceState(
                status=ComplianceStatus.COMPLIANT, deployment_result=DeploymentResult.DEPLOYED, blocked=BlockedStatus.NO
            )
            self.types_per_agent[details.id.agent_name][details.id.entity_type] += 1
        self.dirty.discard(resource)

    def update_resource_to_undefined(self, resource: ResourceIdStr, details: ResourceDetails) -> None:
        """
        Mark the given resource as blocked, i.e. it's not deployable. This method updates the resource details
        and the resource_status.

        :param resource: The resource that should be blocked.
        :param details: The details of the resource that should be blocked.
        """
        self.resources[resource] = details
        if resource in self.resource_state:
            self.resource_state[resource].status = ComplianceStatus.UNDEFINED
            self.resource_state[resource].blocked = BlockedStatus.YES
        else:
            self.resource_state[resource] = ResourceState(
                status=ComplianceStatus.UNDEFINED,
                deployment_result=DeploymentResult.NEW,
                blocked=BlockedStatus.YES,
            )
            self.types_per_agent[details.id.agent_name][details.id.entity_type] += 1
        self.dirty.discard(resource)

    def _block_resource_transitive(self, resource: ResourceIdStr) -> None:
        """
        Mark the given resource as transitively blocked, i.e. it's not deployable.
        """

        self.resource_state[resource].blocked = BlockedStatus.YES
        self.dirty.discard(resource)

    def _unblock_resource(self, resource: ResourceIdStr) -> None:
        """
        Mark the given resource as unblocked
        """
        my_state = self.resource_state[resource]
        my_state.blocked = BlockedStatus.NO
        if my_state.status in [ComplianceStatus.HAS_UPDATE, ComplianceStatus.NON_COMPLIANT]:
            self.dirty.add(resource)

    def are_dependencies_compliant(self, resource: ResourceIdStr) -> bool:
        """
        Checks if a resource has all of its dependencies in a compliant state.

        :param resource: The id of the resource to find the dependencies for
        """
        requires_view: Mapping[ResourceIdStr, Set[ResourceIdStr]] = self.requires.requires_view()
        dependencies: Set[ResourceIdStr] = requires_view.get(resource, set())

        return all(self.resource_state[dep_id].status is ComplianceStatus.COMPLIANT for dep_id in dependencies)

    def update_transitive_state(
        self,
        new_undefined: AbstractSet[ResourceIdStr],
        verify_blocked: AbstractSet[ResourceIdStr],
        verify_unblocked: set[ResourceIdStr],
    ) -> Tuple[set[ResourceIdStr], set[ResourceIdStr]]:
        """

        Update transitive states

        :param new_undefined: resources that have become undefined
        :param verify_blocked: resources that have added requires
        :param verify_unblocked: resources that have lost requires relations

        returns: <unblocked, blocked> resources
        """
        # This algorithm moves the blocked/unblocked forward over the provides relation
        # 1. We start from the nodes passed in
        # 2. Resources that have become undefined are first marked over the requires relation.
        #   - This is easy as blocked state with a known root can safely be propagated froward
        # 3. Resource that added a requirement may have become blocked
        #   - We back check one step  (along requires)
        #   - We mark them as blocked if needed.
        #       - Nodes marked as blocked this way are not definitely blocked,
        #         as nodes deeper down the tree may become unblocked later on
        #       - Except if we find an undefined node on the path, in that case, they are definitely blocked
        #   - We forward propagate that
        # 4. Resources that removed a requirements or became defined may have become defined
        #    are checked one step along the requires relations to see if they are unblocked
        #    - We check back one step (along requires)
        #    - We mark them as unblocked if needed
        #       - Nodes marked as blocked this way are not definitely blocked,
        #         as nodes deeper down the tree may become unblocked later on
        #       - Except if we find an undefined node on the path, in that case, they are definitely blocked
        #    - We forward propagate that

        # To traverse efficiently, we maintain:
        #  - a worklist of definitely blocked nodes
        #  - a set of definitely blocked nodes
        #  - a worklist of potential unblocked nodes

        #  - a cache of blocker nodes. When we find a node B blocking a potentially unblocked node A, we cache this.
        #    If we hit node A again and we are not coming from B, we know it is still blocked.

        out_blocked: set[ResourceIdStr] = set()
        out_unblocked: set[ResourceIdStr] = set()

        # a set of definitely blocked nodes
        is_blocked: set[ResourceIdStr] = set(new_undefined)

        # forward graph
        provides_view: Mapping[ResourceIdStr, Set[ResourceIdStr]] = self.requires.provides_view()

        # 1. forward propagate blocked, start one provides step forward from the updated nodes
        propagate_blocked_work: list[ResourceIdStr] = list(
            itertools.chain.from_iterable(provides_view.get(r, set()) for r in is_blocked)
        )
        # We rely on the seen set to improve performance. Although the improvement might be rather small,
        # because we only save one check `self.resource_state[resource_id].blocked == BlockedStatus.YES`.
        while propagate_blocked_work:
            resource_id: ResourceIdStr = propagate_blocked_work.pop()
            if resource_id in is_blocked:
                continue
            is_blocked.add(resource_id)
            if self.resource_state[resource_id].blocked is BlockedStatus.YES:
                # Resource is already blocked. All provides will be blocked as well.
                continue
            else:
                # Block resource and its provides.
                self._block_resource_transitive(resource_id)
                out_blocked.add(resource_id)
                propagate_blocked_work.extend(provides_view.get(resource_id, set()))

        # 2. back check propagate potential blockers
        known_blockers_cache: dict[ResourceIdStr, ResourceIdStr] = {}
        # Cache used by the `update_blocked_status_*()` method to prevent the expensive check on the blocked
        # status of the requirements of a resource. If the dictionary contains key value pair (X, Y), it
        # indicates that resource Y is a requirement of resource X that was blocked, last we checked
        # This cache is a bit complicated in that
        #  - The unblock check on node A takes us up to n traversals (if A has n requires)
        #  - We may hit A up to n times
        #  - The chance of a cache miss is 1/n (i.e. we come from that edge) (roughly)
        #  - So we reduce from n*n to n time complexity
        # unclear if it is worth it, hard to tell/test

        def update_blocked_status_to_blocked(resource: ResourceIdStr) -> bool:
            """
            Check if the deployment of the given resource is still blocked and mark it as unblocked if it is.
            check one step over the requires relation, assume all states to hold.
            if they don't we will pass this node again

            :return: True iff the given resource changes state.
            """
            if resource in is_blocked:
                # Is blocked for a know root
                return False

            my_state = self.resource_state[resource]
            if my_state.blocked is BlockedStatus.YES:
                # The resource is already blocked.
                return False

            if my_state.status is ComplianceStatus.UNDEFINED:
                assert False  # TODO: remove, should not happen

            blocked_dependency: ResourceIdStr | None = None
            # one blocked requires, evidence we are blocked

            if resource in known_blockers_cache:
                # First check the blocked status of the cached known blocker for improved performance.
                known_blocker: ResourceIdStr = known_blockers_cache[resource]
                if self.resource_state[known_blocker].blocked is BlockedStatus.YES:
                    blocked_dependency = known_blocker
                else:
                    # Cache is out of date. Clear cache item.
                    del known_blockers_cache[resource]

            if blocked_dependency is None:
                # Perform more expensive call by traversing all requirements of resource.
                blocked_dependency = next(
                    (r for r in self.requires.get(resource, set()) if self.resource_state[r].blocked is BlockedStatus.YES), None
                )

            if blocked_dependency is None:
                return False

            if blocked_dependency:
                # Resource is blocked, because a dependency is blocked.
                known_blockers_cache[resource] = blocked_dependency

            if blocked_dependency in is_blocked:
                # We know the root is undefined, hard block
                is_blocked.add(resource)

            # Block resource
            self._block_resource_transitive(resource)
            out_blocked.add(resource)
            return True

        for resource_id in verify_blocked:
            # verify all potential blockers
            blocked = update_blocked_status_to_blocked(resource_id)
            # if we did block it, add it to the work
            if blocked:
                propagate_blocked_work.append(resource_id)

        # Propagate blockers once more
        # We iterate differently, because the parents blocked status is relevant
        while propagate_blocked_work:
            already_blocked: ResourceIdStr = propagate_blocked_work.pop()
            is_hard_block = already_blocked in is_blocked
            for to_be_blocked in provides_view.get(already_blocked, set()):
                if is_hard_block:
                    is_blocked.add(to_be_blocked)
                my_state = self.resource_state[to_be_blocked]
                if my_state.blocked is not BlockedStatus.YES:
                    continue
                else:
                    self._block_resource_transitive(to_be_blocked)
                    out_blocked.add(to_be_blocked)
                    propagate_blocked_work.append(to_be_blocked)

        # 2. forward propagate the unblocked
        def update_blocked_status(resource: ResourceIdStr) -> bool:
            """
            Check if the deployment of the given resource is still blocked and mark it as unblocked if it is.
            check one step over the requires relation, assume all states to hold.
            if they don't we will pass this node again

            :return: True iff the given resource was unblocked.
            """
            if resource in is_blocked:
                # Is blocked for a know root
                return False

            my_state = self.resource_state[resource]
            if my_state.blocked is not BlockedStatus.YES:
                # The resource is already unblocked.
                return False

            if my_state.status is ComplianceStatus.UNDEFINED:
                # The resource is undefined.
                # Root blocker
                is_blocked.add(resource)
                return False

            if resource in known_blockers_cache:
                # First check the blocked status of the cached known blocker for improved performance.
                known_blocker: ResourceIdStr = known_blockers_cache[resource]
                if self.resource_state[known_blocker].blocked is BlockedStatus.YES:
                    return False
                else:
                    # Cache is out of date. Clear cache item.
                    del known_blockers_cache[resource]

            # Perform more expensive call by traversing all requirements of resource.
            blocked_dependency: ResourceIdStr | None = next(
                (r for r in self.requires.get(resource, set()) if self.resource_state[r].blocked is BlockedStatus.YES), None
            )
            if blocked_dependency:
                # Resource is blocked, because a dependency is blocked.
                known_blockers_cache[resource] = blocked_dependency
                return False

            # Unblock resource
            self._unblock_resource(resource)
            out_unblocked.add(resource)
            return True

        to_verify_work: list[ResourceIdStr] = list(verify_unblocked)
        while to_verify_work:
            resource_id = to_verify_work.pop()
            resource_was_unblocked: bool = update_blocked_status(resource_id)
            if resource_was_unblocked:
                to_verify_work.extend(provides_view.get(resource_id, set()))

        return out_unblocked, out_blocked

    def update_desired_state(
        self,
        resource: ResourceIdStr,
        details: ResourceDetails,
    ) -> None:
        """
        Register a new desired state for a resource.

        The resource is not currently blocked

        For blocked resources, block_resource() should be called instead.
        """
        self.resources[resource] = details
        if resource in self.resource_state:
            self.resource_state[resource].status = ComplianceStatus.HAS_UPDATE
            # Blocked status is handled in update_transitive_state
        else:
            self.resource_state[resource] = ResourceState(
                status=ComplianceStatus.HAS_UPDATE,
                deployment_result=DeploymentResult.NEW,
                blocked=BlockedStatus.NO,  # Requires are not set yet, handled in update_transitive_state
            )
            self.types_per_agent[details.id.agent_name][details.id.entity_type] += 1
        self.dirty.add(resource)

    def update_requires(self, resource: ResourceIdStr, requires: Set[ResourceIdStr]) -> None:
        """
        Update the requires relation for a resource. Updates the reverse relation accordingly.
        """

        # TODO: verify this is correct and needed

        check_dependencies: bool = self.resource_state[resource].blocked is BlockedStatus.TRANSIENT and bool(
            self.requires[resource] - requires
        )
        self.requires[resource] = requires
        # If the resource is blocked transiently, and we drop at least one of its requirements
        # we check to see if the resource can now be unblocked
        # i.e. all of its dependencies are now compliant with the desired state.
        if check_dependencies and self.are_dependencies_compliant(resource):
            self.resource_state[resource].blocked = BlockedStatus.NO
            self.dirty.add(resource)

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
