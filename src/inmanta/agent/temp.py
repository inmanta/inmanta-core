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

import abc
import dataclasses
from collections.abc import Mapping, Set
from dataclasses import dataclass
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
class ModelState:
    attribute_hash: str
    attributes: Mapping[str, object]


@dataclass(kw_only=True)
class ModelState:
    version: int
    resources: dict[ResourceIdStr, ResourceDetails] = dataclasses.field(default_factory=dict)
    requires: RequiresProvidesMapping = dataclasses.field(default_factory=RequiresProvidesMapping)
    # TODO


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
class ScheduledWork:
    # TODO: in_progress?
    # TODO: list is not a good type?
    agent_queues: dict[str, list[Task]] = dataclasses.field(default_factory=dict)
    # TODO: this requires context about what each task is waiting for
    waiting: dict[ResourceIdStr, Task] = dataclasses.field(default_factory=dict)


# TODO: name
class Scheduler:
    def __init__(self) -> None:
        # TODO
        self._state: Optional[ModelState] = None
        self.work: ScheduledWork = ScheduledWork()

    def start(self) -> None:
        # TODO: read from DB instead
        self._state = ModelState(version=0)

    @property
    def state(self) -> ModelState:
        if self._state is None:
            # TODO
            raise Exception("Call start first")
        return self._state

    async def new_version(self) -> None:
        # TODO
        pass


# TODO: what needs to be refined before hand-off?
#   - where will this component go to start with?
#
# TODO: opportunities for work hand-off:
# - connection to DB
# - connection to agent
