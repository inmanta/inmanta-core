"""
    Inmanta LSM
    :copyright: 2024 Inmanta
    :contact: code@inmanta.com
    :license: Inmanta EULA
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

    :param value: The value to store on the service.
    """

    return value
