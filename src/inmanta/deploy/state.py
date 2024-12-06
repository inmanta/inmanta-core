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
import json
import uuid
from collections import defaultdict
from collections.abc import Mapping, Set
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

import asyncpg

from inmanta import const
from inmanta.util.collections import BidirectionalManyMapping

if TYPE_CHECKING:
    from inmanta import resources
    from inmanta.data.model import ResourceIdStr, ResourceType


class RequiresProvidesMapping(BidirectionalManyMapping["ResourceIdStr", "ResourceIdStr"]):
    def requires_view(self) -> Mapping["ResourceIdStr", Set["ResourceIdStr"]]:
        """
        Returns a view of the requires relationship of this RequiresProvidesMapping. This view will be updated
        whenever the RequiresProvidesMapping object is updated.
        """
        return self

    def provides_view(self) -> Mapping["ResourceIdStr", Set["ResourceIdStr"]]:
        """
        Returns a view of the provides relationship of this RequiresProvidesMapping. This view will be updated
        whenever the RequiresProvidesMapping object is updated.
        """
        return self.reverse_mapping()


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
    ORPHAN: The resource has become an orphan, i.e. it is no longer present in the latest released model version.
    """

    COMPLIANT = enum.auto()
    HAS_UPDATE = enum.auto()
    NON_COMPLIANT = enum.auto()
    UNDEFINED = enum.auto()
    ORPHAN = enum.auto()

    def is_dirty(self) -> bool:
        """
        Return True iff the status indicates the resource is not up-to-date and is ready to be deployed.
        """
        return self in [ComplianceStatus.HAS_UPDATE, ComplianceStatus.NON_COMPLIANT]

    def is_deployable(self) -> bool:
        """
        Return True iff the status indicates the resource is ready to be deployed.
        """
        return self not in [ComplianceStatus.UNDEFINED, ComplianceStatus.ORPHAN]


@dataclass(frozen=True)
class ResourceDetails:
    resource_id: "ResourceIdStr"
    attribute_hash: str
    attributes: Mapping[str, object] = dataclasses.field(hash=False)
    status: ComplianceStatus

    id: "resources.Id" = dataclasses.field(init=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        from inmanta import resources

        # use object.__setattr__ because this is a frozen dataclass, see dataclasses docs
        object.__setattr__(self, "id", resources.Id.parse_id(self.resource_id))


class DeploymentResult(StrEnum):
    """
    The result of a resource's last (finished) deploy. This result may be for an older version than the latest desired state.
    See ComplianceStatus for a resource's operational status with respect to its latest desired state.

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
    status: ComplianceStatus
    deployment_result: DeploymentResult
    blocked: BlockedStatus

    def is_dirty(self) -> bool:
        """
        Return True iff the status indicates the resource is not up-to-date and is ready to be deployed.
        """
        return self.status.is_dirty()

    def is_deployable(self) -> bool:
        """
        Return True iff the status indicates the resource is ready to be deployed.
        """
        return self.status.is_deployable() and not self.blocked.is_blocked()


@dataclass(kw_only=True)
class ModelState:
    """
    The state of the model, meaning both resource intent and resource state.

    Invariant: all resources in the current model, and only those, exist in the resources (also undeployable resources)
               and resource_state mappings.
    """

    version: int
    resources: dict["ResourceIdStr", ResourceDetails] = dataclasses.field(default_factory=dict)
    requires: RequiresProvidesMapping = dataclasses.field(default_factory=RequiresProvidesMapping)
    resource_state: dict["ResourceIdStr", ResourceState] = dataclasses.field(default_factory=dict)
    # resources with a known or assumed difference between intent and actual state
    # (might be simply a change of its dependencies), which are still being processed by
    # the resource scheduler. This is a short-lived transient state, used for internal concurrency control. Kept separate from
    # ResourceStatus so that it lives outside the scheduler lock's scope.
    dirty: set["ResourceIdStr"] = dataclasses.field(default_factory=set)
    # types per agent keeps track of which resource types live on which agent by doing a reference count
    # the dict is agent_name -> resource_type -> resource_count
    types_per_agent: dict[str, dict["ResourceType", int]] = dataclasses.field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: 0))
    )

    @classmethod
    async def create_from_db(
        cls, environment: uuid.UUID, last_processed_model_version: int, *, connection: asyncpg.connection.Connection
    ) -> "ModelState":
        """
        Create a new instance of the ModelState object, by restoring the model state from the database.

        :param environment: The environment the model state belongs to.
        :param last_processed_model_version: The model version that was last processed by the scheduler, i.e. the version
                                             associated with the state in the persistent_resource_state table.
        """
        from inmanta import data, resources

        result = ModelState(version=last_processed_model_version)
        resource_records = await data.Resource.get_resources_for_version_raw_with_persistent_state(
            environment=environment,
            version=last_processed_model_version,
            projection=["resource_id", "attributes", "attribute_hash"],
            projection_persistent=[
                "is_orphan",
                "is_undefined",
                "current_intent_attribute_hash",
                "last_deployed_attribute_hash",
                "deployment_result",
                "blocked_status",
                "last_success",
                "last_produced_events",
            ],
            project_attributes=["requires", const.RESOURCE_ATTRIBUTE_SEND_EVENTS],
            connection=connection,
        )
        by_resource_id = {r["resource_id"]: r for r in resource_records}
        for res in resource_records:
            resource_id = res["resource_id"]

            # Populate resource_state
            compliance_status: ComplianceStatus
            if res["is_orphan"]:
                compliance_status = ComplianceStatus.ORPHAN
            elif res["is_undefined"]:
                compliance_status = ComplianceStatus.UNDEFINED
            elif res["current_intent_attribute_hash"] != res["last_deployed_attribute_hash"]:
                compliance_status = ComplianceStatus.HAS_UPDATE
            elif DeploymentResult[res["deployment_result"]] is DeploymentResult.DEPLOYED:
                compliance_status = ComplianceStatus.COMPLIANT
            else:
                compliance_status = ComplianceStatus.NON_COMPLIANT
            resource_state = ResourceState(
                status=compliance_status,
                deployment_result=DeploymentResult[res["deployment_result"]],
                blocked=BlockedStatus[res["blocked_status"]],
            )
            result.resource_state[resource_id] = resource_state

            # Populate resources details
            details = ResourceDetails(
                resource_id=resource_id,
                attribute_hash=res["attribute_hash"],
                attributes=json.loads(res["attributes"]),
                status=compliance_status,
            )
            result.resources[resource_id] = details

            # Populate types_per_agent
            result.types_per_agent[details.id.agent_name][details.id.entity_type] += 1

            # Populate requires
            requires = {resources.Id.parse_id(req).resource_str() for req in res["requires"]}
            result.requires[resource_id] = requires

            # Check whether resource is dirty
            if resource_state.is_deployable():
                if resource_state.is_dirty():
                    # Resource is dirty by itself.
                    result.dirty.add(details.id.resource_str())
                else:
                    # Check whether the resource should be deployed because of an outstanding event.
                    last_success = res["last_success"] or const.DATETIME_MIN_UTC
                    for req in requires:
                        req_res = by_resource_id[req]
                        assert req_res is not None
                        last_produced_events = req_res["last_produced_events"]
                        if (
                            last_produced_events is not None
                            and last_produced_events > last_success
                            and req_res[const.RESOURCE_ATTRIBUTE_SEND_EVENTS]
                        ):
                            result.dirty.add(details.id.resource_str())
                            break
        return result

    def reset(self) -> None:
        self.version = 0
        self.resources.clear()
        self.requires.clear()
        self.resource_state.clear()
        self.types_per_agent.clear()

    def add_up_to_date_resource(self, resource: "ResourceIdStr", details: ResourceDetails) -> None:
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

    def block_resource(self, resource: "ResourceIdStr", details: ResourceDetails, is_transitive: bool) -> None:
        """
        Mark the given resource as blocked, i.e. it's not deployable. This method updates the resource details
        and the resource_status.

        :param resource: The resource that should be blocked.
        :param details: The details of the resource that should be blocked.
        :param is_transitive: True iff the given resource is blocked transitively. It's blocked because one of its dependencies
                              is blocked. If False, the resource is blocked because it's undefined.
        """
        self.resources[resource] = details
        if resource in self.resource_state:
            if not is_transitive:
                self.resource_state[resource].status = ComplianceStatus.UNDEFINED
            self.resource_state[resource].blocked = BlockedStatus.YES
        else:
            resource_status = ComplianceStatus.UNDEFINED if not is_transitive else ComplianceStatus.HAS_UPDATE
            self.resource_state[resource] = ResourceState(
                status=resource_status,
                deployment_result=DeploymentResult.NEW,
                blocked=BlockedStatus.YES,
            )
            self.types_per_agent[details.id.agent_name][details.id.entity_type] += 1
        self.dirty.discard(resource)

    def block_provides(self, resources: Set["ResourceIdStr"]) -> Set["ResourceIdStr"]:
        """
        Marks the provides of the given resources as blocked.

        Must be called under the scheduler lock. This method assumes that all the resources of the model version
        are populated in the resources dictionary.

        :param resources: The set of resources for which the provides have to be blocked.
        :return: The set of dependent resources that were newly marked as blocked (transitively).
        """
        result: set[ResourceIdStr] = set()
        provides_view: Mapping[ResourceIdStr, Set[ResourceIdStr]] = self.requires.provides_view()
        todo: list[ResourceIdStr] = list(itertools.chain.from_iterable(provides_view.get(r, set()) for r in resources))
        # We rely on the seen set to improve performance. Although the improvement might be rather small,
        # because we only save one call to `self.resource_state[resource_id].blocked.is_blocked()`.
        seen: set[ResourceIdStr] = set()
        while todo:
            resource_id: ResourceIdStr = todo.pop()
            if resource_id in seen:
                continue
            seen.add(resource_id)
            if self.resource_state[resource_id].blocked.is_blocked():
                # Resource is already blocked. All provides will be blocked as well.
                continue
            else:
                # Block resource and its provides.
                self.block_resource(resource_id, self.resources[resource_id], is_transitive=True)
                result.add(resource_id)
                todo.extend(provides_view.get(resource_id, set()))
        return result

    def mark_as_defined(self, resource: "ResourceIdStr", details: ResourceDetails) -> Set["ResourceIdStr"]:
        """
        Mark the given resource as defined. If the given resource or any of its provides became unblocked, because of this,
        this method also updates the blocked status.

        Must be called under the scheduler lock. This method assumes that all the resources of the model version
        are populated in the resources dictionary.

        :param resource: The resource that became defined.
        :param details: The details of resource.
        :return: All the resources that were transitively unblocked because of the given resource being unblocked.
        """

        # Cache used by the `update_blocked_status()` method to prevent the expensive check on the blocked
        # status of the requirements of a resource. If the dictionary contains key value pair (X, Y), it
        # indicates that resource Y is a requirement of resource X that was blocked, last we checked
        known_blockers_cache: dict[ResourceIdStr, ResourceIdStr] = {}

        def update_blocked_status(resource: "ResourceIdStr") -> bool:
            """
            Check if the deployment of the given resource is still blocked and mark it as unblocked if it is.

            :return: True iff the given resource was unblocked.
            """
            if self.resource_state[resource].blocked is BlockedStatus.NO:
                # The resource is already unblocked.
                return False
            if self.resource_state[resource].status is ComplianceStatus.UNDEFINED:
                # The resource is undefined.
                return False
            if resource in known_blockers_cache:
                # First check the blocked status of the cached known blocker for improved performance.
                known_blocker: ResourceIdStr = known_blockers_cache[resource]
                if self.resource_state[known_blocker].blocked.is_blocked():
                    return False
                else:
                    # Cache is out of date. Clear cache item.
                    del known_blockers_cache[resource]
            # Perform more expensive call by traversing all requirements of resource.
            blocked_dependency: ResourceIdStr | None = next(
                (r for r in self.requires.get(resource, set()) if self.resource_state[r].blocked.is_blocked()), None
            )
            if blocked_dependency:
                # Resource is blocked, because a dependency is blocked.
                known_blockers_cache[resource] = blocked_dependency
                return False
            # Unblock resource
            self.resource_state[resource].blocked = BlockedStatus.NO
            if self.resource_state[resource].status in [ComplianceStatus.HAS_UPDATE, ComplianceStatus.NON_COMPLIANT]:
                self.dirty.add(resource)
            return True

        provides_view: Mapping[ResourceIdStr, Set[ResourceIdStr]] = self.requires.provides_view()
        self.resources[resource] = details
        self.resource_state[resource].status = ComplianceStatus.HAS_UPDATE
        todo: list[ResourceIdStr] = [resource]
        transitively_unblocked_resources = set()
        while todo:
            resource_id: ResourceIdStr = todo.pop()
            resource_was_unblocked: bool = update_blocked_status(resource_id)
            if resource_was_unblocked:
                if resource_id != resource:
                    transitively_unblocked_resources.add(resource_id)
                todo.extend(provides_view.get(resource_id, set()))
        return transitively_unblocked_resources

    def update_desired_state(
        self,
        resource: "ResourceIdStr",
        details: ResourceDetails,
    ) -> None:
        """
        Register a new desired state for a resource.

        For blocked resources, block_resource() should be called instead.
        """
        self.resources[resource] = details
        if resource in self.resource_state:
            self.resource_state[resource].status = ComplianceStatus.HAS_UPDATE
            self.resource_state[resource].blocked = BlockedStatus.NO
        else:
            self.resource_state[resource] = ResourceState(
                status=ComplianceStatus.HAS_UPDATE,
                deployment_result=DeploymentResult.NEW,
                blocked=BlockedStatus.NO,
            )
            self.types_per_agent[details.id.agent_name][details.id.entity_type] += 1
        self.dirty.add(resource)

    def update_requires(
        self,
        resource: "ResourceIdStr",
        requires: Set["ResourceIdStr"],
    ) -> None:
        """
        Update the requires relation for a resource. Updates the reverse relation accordingly.
        """
        self.requires[resource] = requires

    def drop(self, resource: "ResourceIdStr") -> None:
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
