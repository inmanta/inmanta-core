@allocation_helpers.allocator()
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
    print("This will be called in the first validation compile only!", str(service), str(attribute_path), str(value))
    return value
