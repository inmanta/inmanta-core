"""
    Inmanta LSM
    :copyright: 2024 Inmanta
    :contact: code@inmanta.com
    :license: Inmanta EULA
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
