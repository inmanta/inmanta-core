@allocation_helpers.allocator()
def get_first_value(
    service: "lsm::ServiceEntity",
    attribute_path: "string",
) -> "int":
    return 1

@allocation_helpers.allocator()
def get_third_value(
    service: "lsm::ServiceEntity",
    attribute_path: "string",
) -> "int":
    return 3

allocation.AllocationSpecV2("value_allocation_v3")
