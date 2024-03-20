"""
    Inmanta LSM
    :copyright: 2024 Inmanta
    :contact: code@inmanta.com
    :license: Inmanta EULA
"""


from datetime import datetime
from inmanta_plugins.lsm.allocation_helpers import allocator


def clock_time() -> str:
    return str(datetime.now())

@allocator()
def ordered_allocation(
    service: "lsm::ServiceEntity",
    attribute_path: "string",
    *,
    requires: "list?" = None
) -> "string":
    """
    For demonstration purposes, this allocator returns the current time.

    :param requires: Optional list containing the results of allocator calls
        that should happen before the current call.

    """
    return clock_time()
