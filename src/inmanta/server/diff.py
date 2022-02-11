"""
    Copyright 2022 Inmanta

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

import json
from typing import Dict, List, Optional, Set

from inmanta import resources
from inmanta.data.model import AttributeDiff, ResourceDiff, ResourceDiffStatus, ResourceIdStr


class Attribute:
    def __init__(self, name: str, value: object) -> None:
        self._name = name
        self._value = value

        if self._name == "requires":
            # Sort the requires list
            self._value = sorted([resources.Id.parse_id(req).resource_str() for req in self._value])

        self._compare_value: Optional[str] = None

    @property
    def value(self) -> object:
        """The value of the attribute"""
        return self._value

    @property
    def compare_value(self) -> str:
        """The string representation of the value, which can be used for comparison"""
        self._generate_compare_value()

        return self._compare_value

    def _generate_compare_value(self) -> None:
        """Generate a value that can be used for comparison"""
        if self._compare_value is not None:
            return

        if self.value is None:
            self._compare_value = ""
        elif isinstance(self.value, (dict, list)):
            self._compare_value = json.dumps(self.value, indent=4, sort_keys=True)
        else:
            self._compare_value = str(self.value)

    def compare(self, other: "Attribute") -> Optional[AttributeDiff]:
        """Compare this value with other. Other is considered the original value"""
        if self.compare_value == other.compare_value:
            return None

        diff = AttributeDiff(
            from_value=other.value,
            to_value=self.value,
            from_value_compare=other.compare_value,
            to_value_compare=self.compare_value,
        )
        return diff

    def added(self) -> AttributeDiff:
        """Return an attribute diff as if this attribute is newly added"""
        return AttributeDiff(
            from_value=None,
            to_value=self.value,
            from_value_compare="",
            to_value_compare=self.compare_value,
        )

    def removed(self) -> AttributeDiff:
        """Return an attribute diff as if this attribute is removed in a later version"""
        return AttributeDiff(
            from_value=self.value,
            to_value=None,
            from_value_compare=self.compare_value,
            to_value_compare="",
        )


class Resource:
    def __init__(self, resource_id: ResourceIdStr, attributes: Dict[str, object]) -> None:
        self.resource_id = resource_id
        self._attributes = {name: Attribute(name, value) for name, value in attributes.items() if name != "version"}

    def compare(self, other: "Resource") -> Optional[ResourceDiff]:
        """Compare this resource with another: check which attributes are added, modified and removed.
        The other resource is considered to be the original"""
        other_attributes = set(other._attributes.keys())
        our_attributes = set(self._attributes.keys())

        diff = {}
        # Generate the diff for each attribute
        for added in our_attributes - other_attributes:
            diff[added] = self._attributes[added].added()

        for removed in other_attributes - our_attributes:
            diff[removed] = other._attributes[removed].removed()

        for name in other_attributes.intersection(our_attributes):
            attr_diff = self._attributes[name].compare(other._attributes[name])
            if attr_diff is not None:
                diff[name] = attr_diff

        if diff:
            return ResourceDiff(resource_id=self.resource_id, attributes=diff, status=ResourceDiffStatus.modified)

        return None

    def added(self) -> ResourceDiff:
        """Return a diff as if this resource is newly added"""
        return ResourceDiff(
            resource_id=self.resource_id,
            attributes={name: attr.added() for name, attr in self._attributes.items()},
            status=ResourceDiffStatus.added,
        )

    def removed(self) -> ResourceDiff:
        """Return a diff as if this resource is removed"""
        return ResourceDiff(
            resource_id=self.resource_id,
            attributes={name: attr.removed() for name, attr in self._attributes.items()},
            status=ResourceDiffStatus.deleted,
        )

    def unmodified(self) -> ResourceDiff:
        """Return a diff as if this resource is not modified"""
        return ResourceDiff(
            resource_id=self.resource_id,
            attributes={},
            status=ResourceDiffStatus.unmodified,
        )


class Version:
    def __init__(self, resources: Dict[ResourceIdStr, Resource]) -> None:
        self._resources = resources

    def get_resource_set(self) -> Set[ResourceIdStr]:
        """The names of the resources in this version"""
        return set(self._resources.keys())

    def generate_diff(self, other: "Version", include_unmodified: bool = False) -> List[ResourceDiff]:
        """Compare this version with another: check which resources are added, removed and modified.
        The other version is considered to be the original."""
        our_set = self.get_resource_set()
        other_set = other.get_resource_set()
        result: List[ResourceDiff] = []

        added = list(our_set - other_set)
        removed = list(other_set - our_set)
        result.extend(self._resources[x].added() for x in added)
        result.extend(other._resources[x].removed() for x in removed)

        intersect = our_set.intersection(other_set)
        for res in intersect:
            # generate diff for each resource
            cmp = self._resources[res].compare(other._resources[res])
            if cmp:
                result.append(cmp)
            elif include_unmodified:
                result.append(self._resources[res].unmodified())

        return sorted(result, key=lambda r: r.resource_id)


def generate_diff(
    from_version_resources: Dict[ResourceIdStr, Resource],
    to_version_resources: Dict[ResourceIdStr, Resource],
    include_unmodified: bool = False,
) -> List[ResourceDiff]:
    """Generate a diff of two sets of resources, describing what has changed between them

    :param from_version_resources: The resources that are considered the starting point for comparison
    :param to_version_resources: The resources that are considered the target for comparison
    :param include_unmodified: If set to true,
    resources that haven't changed between the versions will be included in the results
    """
    from_state = Version(from_version_resources)
    to_state = Version(to_version_resources)

    return to_state.generate_diff(from_state, include_unmodified)
