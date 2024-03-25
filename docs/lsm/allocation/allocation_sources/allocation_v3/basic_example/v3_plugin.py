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

from inmanta_plugins.lsm.allocation_helpers import allocator


@allocator()
def get_value(
    service: "lsm::ServiceEntity",
    attribute_path: "string",
    *,
    value: "any",
) -> "any":
    """
    Store a given value in the attributes of a service.

    :param service: The service instance for which the attribute value
        is being allocated.
    :param attribute_path: DictPath to the attribute of the service
        instance in which the allocated value will be stored.
    :param value: The value to store for this attribute of this service.
    """

    return value
