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
import datetime
import enum
import itertools
import typing
import uuid
from collections import defaultdict
from collections.abc import Mapping, Set
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Self, cast

import asyncpg

import inmanta.types
from inmanta import const, resources
from inmanta.types import ResourceIdStr
from inmanta.util.collections import BidirectionalManyMapping


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


class Compliance(StrEnum):
    """
    Status of a resource's operational status with respect to its latest desired state, to the best of our knowledge.
    COMPLIANT: The operational state complies to latest resource intent as far as we know.
    HAS_UPDATE: The resource intent has been updated since latest deploy attempt (if any),
        meaning we are not yet managing the new intent.
    NON_COMPLIANT: The resource intent has not been updated since latest deploy attempt (if any)
        but we have reason to believe operational state might not comply with latest resource intent,
        based on a deploy attempt / compliance check for that intent.
    UNDEFINED: The resource status is undefined, because it has an unknown attribute. i.e. undefined status <=> undefined
        intent.
    """

    COMPLIANT = enum.auto()
    HAS_UPDATE = enum.auto()
    NON_COMPLIANT = enum.auto()
    UNDEFINED = enum.auto()

    def is_dirty(self) -> bool:
        """
        Return True iff the status indicates the resource is not up-to-date and is ready to be deployed.
        """
        return self in [Compliance.HAS_UPDATE, Compliance.NON_COMPLIANT]


@dataclass(frozen=True)
class ResourceIntent:
    resource_id: "ResourceIdStr"
    attribute_hash: str
    attributes: Mapping[str, object] = dataclasses.field(hash=False)

    id: "resources.Id" = dataclasses.field(init=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        # use object.__setattr__ because this is a frozen dataclass, see dataclasses docs
        object.__setattr__(self, "id", resources.Id.parse_id(self.resource_id))


class HandlerResult(StrEnum):
    """
    The result that the handler reported when processing a given resource.
    This result may be for an older version than the latest desired state.
    See Compliance for a resource's operational status with respect to its latest desired state.

    NEW: Resource has never been processed by the handler before.
    SUCCESSFUL: Handler processed the resource successfully.
    FAILED: Handler failed when processing the resource.
    SKIPPED: Handler skipped processing this resource.
    """

    NEW = enum.auto()
    SUCCESSFUL = enum.auto()
    FAILED = enum.auto()
    SKIPPED = enum.auto()

    @classmethod
    def from_handler_resource_state(cls, handler_resource_state: const.HandlerResourceState) -> "HandlerResult":
        match handler_resource_state:
            case const.HandlerResourceState.deployed | const.HandlerResourceState.non_compliant:
                return HandlerResult.SUCCESSFUL
            case const.HandlerResourceState.skipped | const.HandlerResourceState.skipped_for_dependency:
                return HandlerResult.SKIPPED
            case const.HandlerResourceState.failed | const.HandlerResourceState.unavailable:
                return HandlerResult.FAILED
            case _ as resource_state:
                raise Exception(f"Unexpected handler_resource_state {resource_state.name}")


@typing.overload
def get_compliance_status(
    is_orphan: typing.Literal[False],
    is_undefined: bool,
    last_deployed_attribute_hash: str | None,
    current_intent_attribute_hash: str | None,
    last_handler_run_compliant: bool | None,
) -> Compliance: ...


@typing.overload
def get_compliance_status(
    is_orphan: typing.Literal[True],
    is_undefined: bool,
    last_deployed_attribute_hash: str | None,
    current_intent_attribute_hash: str | None,
    last_handler_run_compliant: bool | None,
) -> None: ...


@typing.overload
def get_compliance_status(
    is_orphan: bool,
    is_undefined: bool,
    last_deployed_attribute_hash: str | None,
    current_intent_attribute_hash: str | None,
    last_handler_run_compliant: bool | None,
) -> Compliance | None: ...


def get_compliance_status(
    is_orphan: bool,
    is_undefined: bool,
    last_deployed_attribute_hash: str | None,
    current_intent_attribute_hash: str | None,
    last_handler_run_compliant: bool | None,
) -> Compliance | None:
    if is_orphan:
        return None
    elif is_undefined:
        return Compliance.UNDEFINED
    elif last_deployed_attribute_hash is None or current_intent_attribute_hash != last_deployed_attribute_hash:
        return Compliance.HAS_UPDATE
    elif last_handler_run_compliant:
        return Compliance.COMPLIANT
    return Compliance.NON_COMPLIANT


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


class Blocked(StrEnum):
    """
    BLOCKED: The resource will retain its blocked status within this model version. For example: A resource that has unknowns
         or depends on a resource with unknowns.
    NOT_BLOCKED: The resource is not blocked
    TEMPORARILY_BLOCKED: The resource is blocked but may recover within the same version.
        Concretely it is waiting for its dependencies to deploy successfully.
    """

    BLOCKED = enum.auto()
    NOT_BLOCKED = enum.auto()
    TEMPORARILY_BLOCKED = enum.auto()

    def db_value(self: "Blocked") -> "Blocked":
        """
        Convert this blocked status to one appropriate for writing to the database.

        This method exists to work around #8541 until a proper solution can be devised.
        """
        # TODO[#8541]: also persist TEMPORARILY_BLOCKED in database
        if self is Blocked.TEMPORARILY_BLOCKED:
            return Blocked.NOT_BLOCKED
        return self


@dataclass
class ResourceState:
    """
    State of a resource. Consists of multiple independent (mostly) state vectors that make up the final state.

    :param last_deployed: when was this resource last deployed
    :param last_handler_run_compliant: Was the last deploy for this resource compliant.
        None for resources that have yet to be deployed
    """

    compliance: Compliance
    last_handler_run: HandlerResult
    blocked: Blocked
    last_deployed: datetime.datetime | None
    last_handler_run_compliant: bool | None

    def is_dirty(self) -> bool:
        """
        Return True iff the status indicates the resource is not up-to-date and is ready to be deployed.
        """
        return self.compliance.is_dirty()

    def copy(self: Self) -> Self:
        """
        Returns a copy of this resource state object.
        """
        return dataclasses.replace(self)

    def to_handler_state(self) -> const.ResourceState:
        match self:
            case ResourceState(compliance=Compliance.UNDEFINED):
                return const.ResourceState.undefined
            case ResourceState(blocked=Blocked.BLOCKED):
                return const.ResourceState.skipped_for_undefined
            case ResourceState(compliance=Compliance.HAS_UPDATE):
                return const.ResourceState.available
            case ResourceState(last_handler_run=HandlerResult.SKIPPED):
                return const.ResourceState.skipped
            case ResourceState(last_handler_run=HandlerResult.FAILED):
                return const.ResourceState.failed
            case ResourceState(compliance=Compliance.NON_COMPLIANT):
                return const.ResourceState.non_compliant
            case ResourceState(last_handler_run=HandlerResult.SUCCESSFUL):
                return const.ResourceState.deployed
            case _:
                raise Exception(f"Unable to deduce handler state: {self}")


@dataclass(kw_only=True)
class ModelState:
    """
    The state of the model, meaning both resource intent and resource state.

    Invariant: all resources in the current model, and only those, exist in the resources (also undeployable resources)
               and state mappings.
    """

    version: int
    intent: dict["ResourceIdStr", ResourceIntent] = dataclasses.field(default_factory=dict)
    resource_sets: dict[Optional[str], set["ResourceIdStr"]] = dataclasses.field(default_factory=dict)
    requires: RequiresProvidesMapping = dataclasses.field(default_factory=RequiresProvidesMapping)
    resource_state: dict["ResourceIdStr", ResourceState] = dataclasses.field(default_factory=dict)
    # resources with a known or assumed difference between intent and actual state
    dirty: set["ResourceIdStr"] = dataclasses.field(default_factory=set)
    # group resources by agent to allow efficient triggering of a deploy for a single agent
    resources_by_agent: dict[str, set["ResourceIdStr"]] = dataclasses.field(default_factory=lambda: defaultdict(set))

    @classmethod
    async def create_from_db(
        cls, environment: uuid.UUID, *, connection: asyncpg.connection.Connection
    ) -> Optional["ModelState"]:
        """
        Create a new instance of the ModelState object, by restoring the model state from the database.
        Returns None iff no such (released) version exists (e.g. the scheduler hasn't processed any
        versions in the past or its last seen version has been cleaned up).

        :param environment: The environment the model state belongs to.
        """
        from inmanta import data, resources

        scheduler: Optional[data.Scheduler] = await data.Scheduler.get_one(environment=environment, connection=connection)
        assert scheduler is not None
        last_processed_model_version: Optional[int] = scheduler.last_processed_model_version
        if last_processed_model_version is None:
            return None

        result = ModelState(version=last_processed_model_version)
        model: Optional[tuple[int, inmanta.types.ResourceSets[dict[str, object]]]] = (
            await data.Resource.get_resources_for_version_raw(
                environment=environment,
                version=last_processed_model_version,
                projection=("resource_id", "attributes", "attribute_hash"),
                projection_persistent=(
                    "is_orphan",
                    "is_undefined",
                    "current_intent_attribute_hash",
                    "last_deployed_attribute_hash",
                    "last_handler_run",
                    "last_handler_run_compliant",
                    "blocked",
                    "last_success",
                    "last_handler_run_at",
                    "last_produced_events",
                ),
                project_attributes=(
                    "requires",
                    const.RESOURCE_ATTRIBUTE_SEND_EVENTS,
                    const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS,
                ),
                connection=connection,
            )
        )
        if not model:
            # the version does not exist at all (anymore)
            return None

        # build intermediate lookup collection
        type ResourceSetStr = Optional[str]
        by_resource_id: Mapping[ResourceIdStr, tuple[ResourceSetStr, Mapping[str, object]]] = {
            ResourceIdStr(cast(str, r["resource_id"])): (rs, r)
            for rs, resource_records in model[1].items()
            for r in resource_records
        }

        for resource_id, (resource_set, res) in by_resource_id.items():
            # Populate state

            compliance_status: Compliance
            last_deployed = cast(datetime.datetime, res["last_handler_run_at"])
            if res["is_orphan"]:
                # it was marked as an orphan by the scheduler when (or sometime before) it read the version we're currently
                # processing => exclude it from the model
                continue
            elif res["is_undefined"]:
                # it was marked as undefined by the scheduler when it read the version we're currently processing
                # (scheduler is only writer)
                compliance_status = Compliance.UNDEFINED
            elif (
                HandlerResult[res["last_handler_run"]] is HandlerResult.NEW
                or res["last_deployed_attribute_hash"] is None
                or res["current_intent_attribute_hash"] != res["last_deployed_attribute_hash"]
            ):
                compliance_status = Compliance.HAS_UPDATE
            elif res["last_handler_run_compliant"]:
                compliance_status = Compliance.COMPLIANT
            else:
                compliance_status = Compliance.NON_COMPLIANT

            resource_state = ResourceState(
                compliance=compliance_status,
                last_handler_run=HandlerResult[res["last_handler_run"]],
                blocked=Blocked[res["blocked"]],
                last_deployed=last_deployed,
                last_handler_run_compliant=res["last_handler_run_compliant"],
            )
            result.resource_state[resource_id] = resource_state

            # Populate resources intent
            resource_intent = ResourceIntent(
                resource_id=resource_id,
                attribute_hash=res["attribute_hash"],
                attributes=res["attributes"],
            )
            result.intent[resource_id] = resource_intent

            # Populate resource sets
            result.resource_sets.setdefault(resource_set, set()).add(resource_id)

            # Populate resources_by_agent
            result.resources_by_agent[resource_intent.id.agent_name].add(resource_id)

            # Populate requires
            requires = {resources.Id.parse_id(req).resource_str() for req in res["requires"]}
            result.requires[resource_id] = requires

            # Check whether resource is dirty
            if resource_state.blocked is Blocked.NOT_BLOCKED:
                if resource_state.is_dirty():
                    # Resource is dirty by itself.
                    result.dirty.add(resource_intent.id.resource_str())
                elif res.get(const.RESOURCE_ATTRIBUTE_RECEIVE_EVENTS, True):
                    # Check whether the resource should be deployed because of an outstanding event.
                    last_success = res["last_success"] or const.DATETIME_MIN_UTC
                    for req in requires:
                        _, req_res = by_resource_id[req]
                        assert req_res is not None
                        last_produced_events = req_res["last_produced_events"]
                        if (
                            last_produced_events is not None
                            and last_produced_events > last_success
                            and req_res.get(const.RESOURCE_ATTRIBUTE_SEND_EVENTS, False)
                        ):
                            result.dirty.add(resource_intent.id.resource_str())
                            break
        return result

    def reset(self) -> None:
        self.version = 0
        self.intent.clear()
        self.requires.clear()
        self.resource_state.clear()
        self.resources_by_agent.clear()
        self.dirty = set()

    def update_resource(
        self,
        resource_intent: ResourceIntent,
        *,
        force_new: bool = False,
        undefined: bool = False,
        known_compliant: bool = False,
        last_deployed: datetime.datetime | None = None,
    ) -> None:
        """
        Register a change of intent for a resource. Registers the new resource intent, as well as its undefined status.
        Does not touch or take into account requires-provides. To update these, call update_requires().

        Sets blocked status for undefined resources, but not vice versa because this depends on transitive properties, which
        requires a full view, including fully updated requires. When you call this method, you must also call
        update_transitive_state() after all direct state and requires have been updated.

        :param force_new: Whether to consider this a new resource, even if we happen to know one with the same id
            (in which case the old one is dropped from the model before registering the new one).
        :param undefined: Whether this resource's intent is undefined, i.e. there's an unknown attribute. Mutually exclusive
            with known_compliant.
        :param known_compliant: Whether this resource is known to be in a good state (compliant and last deploy was successful).
            Useful for restoring previously known state when scheduler is started. Mutually exclusive with undefined.
        :param last_deployed: last deployed time. Only set when restoring previously known state when scheduler is started.
        """
        if undefined and known_compliant:
            raise ValueError("A resource can not be both undefined and compliant")

        resource: ResourceIdStr = resource_intent.resource_id
        compliance_status: Compliance = (
            Compliance.COMPLIANT if known_compliant else Compliance.UNDEFINED if undefined else Compliance.HAS_UPDATE
        )
        # Latest requires are not set yet, transitive blocked status are handled in update_transitive_state
        blocked: Blocked = Blocked.BLOCKED if undefined else Blocked.NOT_BLOCKED

        already_known: bool = resource_intent.resource_id in self.intent
        if force_new and already_known:
            # register this as a new resource, even if we happen to know one with the same id
            self.drop(resource_intent.resource_id)

        if not already_known or force_new:
            # we don't know the resource yet (/ anymore) => create it
            self.resource_state[resource] = ResourceState(
                compliance=compliance_status,
                last_handler_run=HandlerResult.SUCCESSFUL if known_compliant else HandlerResult.NEW,
                blocked=blocked,
                last_deployed=last_deployed,
                last_handler_run_compliant=True if compliance_status == Compliance.COMPLIANT else None,
            )
            if resource not in self.requires:
                self.requires[resource] = set()
            self.resources_by_agent[resource_intent.id.agent_name].add(resource)
        else:
            # we already know the resource => update relevant fields
            self.resource_state[resource].compliance = compliance_status
            # update deployment result only if we know it's compliant. Otherwise it is kept, representing latest result
            if known_compliant:
                self.resource_state[resource].last_handler_run = HandlerResult.SUCCESSFUL
            # Override blocked status except if it was marked as blocked before. We can't unset it yet because a resource might
            # still be transitively blocked, which we'll deal with later, see note in docstring.
            # We do however override TEMPORARILY_BLOCKED because we want to give it another chance when it gets an update
            # (in part to progress the resource state away from available).
            if self.resource_state[resource].blocked is not Blocked.BLOCKED:
                self.resource_state[resource].blocked = blocked

        self.intent[resource] = resource_intent
        if not known_compliant and self.resource_state[resource].blocked is Blocked.NOT_BLOCKED:
            self.dirty.add(resource)
        else:
            self.dirty.discard(resource)

    def update_requires(self, resource: "ResourceIdStr", requires: Set["ResourceIdStr"]) -> None:
        """
        Update the requires relation for a resource. Updates the reverse relation accordingly.

        When updating requires, also call update_transitive_state to ensure temporirly_blocked state is also updated
        """
        check_dependencies: bool = self.resource_state[resource].blocked is Blocked.TEMPORARILY_BLOCKED and bool(
            self.requires[resource] - requires
        )
        self.requires[resource] = requires
        # If the resource is blocked temporarily, and we drop at least one of its requirements
        # we check to see if the resource can now be unblocked
        # i.e. all of its dependencies are now compliant with the desired state.
        if check_dependencies and not self.should_skip_for_dependencies(resource):
            self.resource_state[resource].blocked = Blocked.NOT_BLOCKED
            self.dirty.add(resource)

    def drop(self, resource: "ResourceIdStr") -> None:
        """
        Completely remove a resource from the resource state.
        """
        resource_intent: ResourceIntent = self.intent.pop(resource)
        del self.resource_state[resource]
        # stand-alone resources may not be in requires
        with contextlib.suppress(KeyError):
            del self.requires[resource]
        # top-level resources may not be in provides
        with contextlib.suppress(KeyError):
            del self.requires.reverse_mapping()[resource]

        self.resources_by_agent[resource_intent.id.agent_name].discard(resource)
        if not self.resources_by_agent[resource_intent.id.agent_name]:
            del self.resources_by_agent[resource_intent.id.agent_name]
        self.dirty.discard(resource)

    def should_skip_for_dependencies(self, resource: "ResourceIdStr") -> bool:
        """
        Returns true if this resource satisfies the conditions to skip for dependencies, provided that its handler requested it.
        Concretely, checks if a resource has at least one dependency that was not successful in its last deploy, if any.

        :param resource: The id of the resource to find the dependencies for
        """
        dependencies: Set[ResourceIdStr] = self.requires.get(resource, set())
        return any(self.resource_state[dep_id].last_handler_run_compliant is False for dep_id in dependencies)

    def update_transitive_state(
        self,
        *,
        new_undefined: "Set[ResourceIdStr]",
        verify_blocked: "Set[ResourceIdStr]",
        verify_unblocked: "Set[ResourceIdStr]",
    ) -> "tuple[Set[ResourceIdStr], Set[ResourceIdStr]]":
        """

        Update transitive states.
         Assumes transitive states are consistently set, apart from those of the resources passed as parameters.
         In turn this method ensures transitive state consistency for the entire model.

        :param new_undefined: resources that have become undefined.
            These have already moved to the blocked state by update_resource
        :param verify_blocked: resources that may have gotten blocked, e.g. due to added requires.
            If blocked, will propagate the check to its provides even if not in this set.
        :param verify_unblocked: resources that may have gotten unblocked,
            e.g. due to a transition from undefined to defined or due to dropped requires.
            If unblocked, will propagate the check to its provides even if not in this set.

        returns: <unblocked, blocked> resources that have effectively been moved to this state by this method.
          note: this doesn't include the members of new_undefined, as they had already been updated
        """
        # This algorithm moves the blocked/unblocked forward over the provides relation
        # 1. We start from the nodes passed in
        # 2. Resources that have become undefined are first marked over the requires relation.
        #   - This is easy as blocked state with a known root can safely be propagated froward
        # 3. Resource that added a requirement may have become blocked
        #   - We back check one step  (along requires)
        #        (safe because of invariant that all transitive states not passed to this method are set consistently)
        #   - We mark them as blocked if needed.
        #       - Nodes marked as blocked this way are not definitely blocked,
        #         as nodes deeper down the tree may become unblocked later on
        #       - Except if we find an undefined node on the path, in that case, they are definitely blocked
        #   - We forward propagate that
        # 4. Resources that removed a requirements or became defined
        #    are checked one step along the requires relations to see if they are unblocked
        #    - We check back one step (along requires)
        #       (safe because of invariant that all transitive states not passed to this method are set consistently)
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

        # 2. forward propagate blocked, start one provides step forward from the updated nodes
        propagate_blocked_work: list[ResourceIdStr] = list(
            itertools.chain.from_iterable(provides_view.get(r, set()) for r in is_blocked)
        )
        while propagate_blocked_work:
            resource_id: ResourceIdStr = propagate_blocked_work.pop()
            if resource_id in is_blocked:
                continue
            # directly down the provides relation from an undefined: definitely blocked,
            # will not be unblocked by stage 4
            is_blocked.add(resource_id)
            if self.resource_state[resource_id].blocked is Blocked.BLOCKED:
                # Resource is already blocked. All provides will be blocked as well.
                continue
            else:
                # Block resource and its provides.
                self._block_resource_transitive(resource_id)
                out_blocked.add(resource_id)
                propagate_blocked_work.extend(provides_view.get(resource_id, set()))

        # 3. back check propagate potential blockers
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

        def update_blocked_status_to_blocked(resource: "ResourceIdStr") -> bool:
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
            if my_state.blocked is Blocked.BLOCKED:
                # The resource is already blocked.
                return False

            blocked_dependency: ResourceIdStr | None = None
            # one blocked requires, evidence we are blocked

            if resource in known_blockers_cache:
                # First check the blocked status of the cached known blocker for improved performance.
                known_blocker: ResourceIdStr = known_blockers_cache[resource]
                if self.resource_state[known_blocker].blocked is Blocked.BLOCKED:
                    blocked_dependency = known_blocker
                else:
                    # Cache is out of date. Clear cache item.
                    del known_blockers_cache[resource]

            if blocked_dependency is None:
                # Perform more expensive call by traversing all requirements of resource.
                blocked_dependency = next(
                    (r for r in self.requires.get(resource, set()) if self.resource_state[r].blocked is Blocked.BLOCKED), None
                )
                if blocked_dependency is not None:
                    # cache the resource that is blocking us
                    known_blockers_cache[resource] = blocked_dependency

            if blocked_dependency is None:
                return False

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
                if my_state.blocked is not Blocked.BLOCKED:
                    continue
                else:
                    self._block_resource_transitive(to_be_blocked)
                    out_blocked.add(to_be_blocked)
                    propagate_blocked_work.append(to_be_blocked)

        # 4. forward propagate the unblocked
        def update_blocked_status(resource: "ResourceIdStr") -> bool:
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
            if my_state.blocked is not Blocked.BLOCKED:
                # The resource is already unblocked.
                return False

            if my_state.compliance is Compliance.UNDEFINED:
                # The resource is undefined.
                # Root blocker
                is_blocked.add(resource)
                return False

            if resource in known_blockers_cache:
                # First check the blocked status of the cached known blocker for improved performance.
                known_blocker: "ResourceIdStr" = known_blockers_cache[resource]
                if self.resource_state[known_blocker].blocked is Blocked.BLOCKED:
                    return False
                else:
                    # Cache is out of date. Clear cache item.
                    del known_blockers_cache[resource]

            # Perform more expensive call by traversing all requirements of resource.
            blocked_dependency: "ResourceIdStr" | None = next(
                (r for r in self.requires.get(resource, set()) if self.resource_state[r].blocked is Blocked.BLOCKED), None
            )
            if blocked_dependency:
                # Resource is blocked, because a dependency is blocked.
                known_blockers_cache[resource] = blocked_dependency
                return False

            # Unblock resource
            self._unblock_resource(resource)
            out_unblocked.add(resource)
            return True

        to_verify_work: "list[ResourceIdStr]" = list(verify_unblocked)
        while to_verify_work:
            resource_id = to_verify_work.pop()
            resource_was_unblocked: bool = update_blocked_status(resource_id)
            if resource_was_unblocked:
                to_verify_work.extend(provides_view.get(resource_id, set()))

        return out_unblocked, out_blocked

    def _block_resource_transitive(self, resource: "ResourceIdStr") -> None:
        """
        Mark the given resource as blocked, it's not deployable.

        Only used internally, see update_transitive_state
        """

        self.resource_state[resource].blocked = Blocked.BLOCKED
        self.dirty.discard(resource)

    def _unblock_resource(self, resource: "ResourceIdStr") -> None:
        """
        Mark the given resource as unblocked

        Only used internally, see update_transitive_state
        """
        my_state = self.resource_state[resource]
        my_state.blocked = Blocked.NOT_BLOCKED
        if my_state.compliance in [Compliance.HAS_UPDATE, Compliance.NON_COMPLIANT]:
            self.dirty.add(resource)
