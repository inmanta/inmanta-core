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

# TODO: file name and location

import abc
import dataclasses
import enum
from collections.abc import Mapping, Set
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, TypeAlias

from inmanta.data.model import ResourceIdStr
from inmanta.util.collections import BidirectionalManyToManyMapping


class RequiresProvidesMapping(BidirectionalManyToManyMapping[ResourceIdStr, ResourceIdStr]):
    def get_requires(self, resource: ResourceIdStr) -> Optional[Set[ResourceIdStr]]:
        return self.get_primary(resource)

    def get_provides(self, resource: ResourceIdStr) -> Optional[Set[ResourceIdStr]]:
        return self.get_secondary(resource)

    # TODO: methods for updating requires-provides

    def requires(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self

    def provides(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self.reverse_mapping()


@dataclass(frozen=True)
class ResourceDetails:
    attribute_hash: str
    attributes: Mapping[str, object]
    # TODO: consider adding a read-only view on the requires relation?


class ResourceStatus(StrEnum):
    """
    Status of a resource's operational status with respect to its latest desired state, to the best of our knowledge.

    UP_TO_DATE: Resource has had at least one successful deploy for the latest desired state, and no compliance check has
        reported a diff since. Is not affected by later deploy failures, i.e. the last known operational status is assumed to
        hold until observed otherwise.
    HAS_UPDATE: Resource's operational state does not match latest desired state, as far as we know. Either the resource
        has never been deployed, or was deployed for a different desired state or a compliance check revealed a diff.
    """
    UP_TO_DATE: str = enum.auto()
    HAS_UPDATE: str = enum.auto()
    # TODO: undefined / orphan? Otherwise a simple boolean `has_update` or `dirty` might suffice


class DeploymentResult(StrEnum):
    """
    The result of a resource's last (finished) deploy. This result may be for an older version than the latest desired state.
    See ResourceStatus for a resource's operational status with respect to its latest desired state.

    NEW: Resource has never been deployed before.
    DEPLOYED: Last resource deployment was successful.
    FAILED: Last resource deployment was unsuccessful.
    """
    NEW: str = enum.auto()
    DEPLOYED: str = enum.auto()
    FAILED: str = enum.auto()
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
        self.resources[rid] = attributes
        if resource in self.resource_state:
            self.resource_state[resource].status = ResourceStatus.HAS_UPDATE
        else:
            self.resource_state[resource] = ResourceState(status=ResourceStatus.HAS_UPDATE, deployment_result=DeploymentResult.NEW)

    def update_requires(
        self,
        resource: ResourceIdStr,
        requires: Set[ResourceIdStr],
    ) -> None:
        self.requires[rid] = requires


@dataclass(frozen=True, kw_only=True)
class _Task(abc.ABC):
    agent: str
    resource: ResourceIdStr
    priority: int


class Deploy(_Task): pass


@dataclass(frozen=True, kw_only=True)
class DryRun(_Task):
    # TODO: requires more attributes
    pass


class RefreshFact(_Task): pass


Task: TypeAlias = Deploy | DryRun | RefreshFact
"""
Type alias for the union of all task types. Allows exhaustive case matches.
"""

@dataclass
class BlockedDeploy:
    # TODO: docstring: deploy blocked on requires -> blocked_on is subset of requires or None when not yet calculated
    #   + mention that only deploys are ever blocked
    task: Deploy
    blocked_on: Optional[Set[ResourceIdStr]] = None


@dataclass
class ScheduledWork:
    # TODO: in_progress?
    # TODO: make this a data type with bidirectional read+remove access (ResourceIdStr -> list[Task]), so reset_requires can access it
    agent_queues: dict[str, list[Task]] = dataclasses.field(default_factory=dict)
    waiting: dict[ResourceIdStr, BlockedDeploy] = dataclasses.field(default_factory=dict)

    # TODO: task runner for the agent queues + when done:
    #   - update model state
    #   - follow provides edge to notify waiting tasks and move them to agent_queues

    def delete_resource(self, resource: ResourceIdStr) -> None:
        """
        Drop tasks for a given resource when it's deleted from the model. Does not affect dry-run tasks because they
        do not act on the latest desired state.
        """
        # TODO: delete from agent_queues if in there
        if resource in self.waiting:
            del self.waiting[resource]

    def reset_requires(self, resource: ResourceIdStr) -> None:
        """
        Resets metadata calculated from a resource's requires, i.e. when its requires changes.
        """
        # TODO: need to move out of agent_queues to waiting iff it's in there
        if resource in self.waiting:
            self.waiting[resource].blocked_on = None


# TODO: name
class Scheduler:
    def __init__(self) -> None:
        # TODO
        self._state: Optional[ModelState] = None
        self.work: ScheduledWork = ScheduledWork()

    def start(self) -> None:
        # TODO (ticket): read from DB instead
        self._state = ModelState(version=0)

    @property
    def state(self) -> ModelState:
        if self._state is None:
            # TODO
            raise Exception("Call start first")
        return self._state

    # TODO: name
    # TODO (ticket): design step 2: read new state from DB instead of accepting as parameter (method should be notification only, i.e. 0 parameters)
    async def new_version(
        self,
        version: int,
        resources: Mapping[ResourceIdStr, ResourceDetails],
        requires: Mapping[ResourceIdStr, Set[ResourceIdStr]],
    ) -> None:
        # TODO: make sure it doesn't block queue until lock is acquired: either run on thread or make sure to regularly pass
        #   control to IO loop (preferred)
        # TODO: design step 1: acquire update lock
        # TODO: what to do when an export changes handler code without changing attributes? Consider in deployed state? What
        #   does current implementation do?
        deleted_resources: Set[ResourceIdStr] = self.state.resources.keys() - resources.keys()
        # TODO: drop deleted resources from scheduled work

        new_desired_state: list[ResourceIdStr] = []
        changed_requires: list[ResourceIdStr] = []
        for resource, details in resources.items():
            if resource not in self.state.resources or details.attribute_hash != self.state.resources[resource].attribute_hash:
                self.state.update_pending.add(resource)
                new_desired_state.append(resource)
            if requires.get(resource, set()) != self.state.requires.get(resource, set()):
                self.state.update_pending.add(resource)
                changed_requires.append(resource)
        # TODO: design step 4: acquire scheduler lock
        self.state.version = version
        for resource in new_desired_state:
            self.state.update_desired_state(resource, resources[resource])
        for resource in changed_requires:
            self.state.update_requires(resource, requires[resource])
            self.work.update_requires(resource)

        # TODO: design step 6: release scheduler lock
        # TODO: design step 7: drop update_pending
        # TODO: design step 8: release update lock
        # TODO: design step 9: call into normal deploy flow's part after the lock (step 4)
        # TODO: design step 10: Once more, drop all resources that do not exist in this version from the scheduled work, in case they got added again by a deploy trigger


# TODO: what needs to be refined before hand-off?
#   - where will this component go to start with?
#
# TODO: opportunities for work hand-off:
# - connection to DB
# - connection to agent
