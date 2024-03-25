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

from inmanta.util import dict_path
from inmanta_plugins.lsm.allocation import AllocationSpecV2
from inmanta_plugins.lsm.allocation_v2.framework import AllocatorV2, ContextV2, ForEach


class IntegerAllocator(AllocatorV2):
    """
    Custom allocator class to set an integer value for an attribute.
    """

    def __init__(self, value: int, attribute: str) -> None:
        """
        :param value: The value to store for this attribute of this service.
        :param attribute: Attribute of the service instance in which the
            value will be stored.
        """
        self.value = value
        self.attribute = dict_path.to_path(attribute)

    def needs_allocation(self, context: ContextV2) -> bool:
        """
        Determine if this allocator has any work to do or if all
        values have already been allocated correctly for the instance
        exposed through the context object.

        :param context: Interface with the current instance
        being unwrapped in an lsm::all call.
        """
        try:
            if not context.get_instance().get(self.attribute):
                # Attribute not present
                return True
        except IndexError:
            return True

        return False

    def allocate(self, context: ContextV2) -> None:
        """
        Allocate the value for the attribute via the context object.

        :param context: Interface with the current instance
            being unwrapped in an lsm::all call.
        """
        context.set_value(self.attribute, self.value)


# In the allocation V2 framework, AllocationSpecV2 objects
# are used to configure the allocation process:
AllocationSpecV2(
    "value_allocation",
    IntegerAllocator(value=1, attribute="top_level_value"),
    ForEach(
        item="item",
        in_list="embedded_services",
        identified_by="id",
        apply=[
            IntegerAllocator(
                value=3,
                attribute="embedded_value",
            ),
        ],
    ),
)
