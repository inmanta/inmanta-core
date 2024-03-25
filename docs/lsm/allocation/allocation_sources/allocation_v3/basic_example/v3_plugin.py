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

    :param service: The service instance for which the attribute value
        is being allocated.
    :param attribute_path: DictPath to the attribute of the service
        instance in which the allocated value will be stored.
    :param value: The value to store for this attribute of this service.
    """

    return value

