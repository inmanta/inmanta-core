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
from collections.abc import Mapping, Set
from dataclasses import dataclass
from typing import Optional

from inmanta.data.model import ResourceIdStr
from inmanta.util.collections import BidirectionalManyToManyMapping


class RequiresProvidesMapping(BidirectionalManyToManyMapping[ResourceIdStr, ResourceIdStr]):
    def get_requires(self, resource: ResourceIdStr) -> Optional[Set[ResourceIdStr]]:
        return self.get_primary(resource)

    def get_provides(self, resource: ResourceIdStr) -> Optional[Set[ResourceIdStr]]:
        return self.get_secondary(resource)

    # TODO: write methods

    def requires(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self

    def provides(self) -> Mapping[ResourceIdStr, Set[ResourceIdStr]]:
        return self.reverse_mapping()


@dataclass
class ModelState:
    version: int
    requires: RequiresProvidesMapping = dataclasses.field(default_factory=RequiresProvidesMapping)
    # TODO


# TODO: name
class Scheduler:
    def __init__(self) -> None:
        # TODO
        self.state: Optional[ModelState] = None
