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

from datetime import datetime

from inmanta_plugins.lsm.allocation_helpers import allocator


@allocator()
def ordered_allocation(
    service: "lsm::ServiceEntity",
    attribute_path: "string",
    *,
    requires: "list?" = None
) -> "string":
    """
    For demonstration purposes, this allocator returns the current time.

    :param service: The service instance for which the attribute value
        is being allocated.
    :param attribute_path: DictPath to the attribute of the service
        instance in which the allocated value will be stored.
    :param requires: Optional list containing the results of allocator calls
        that should happen before the current call.
    """
    return str(datetime.now())
