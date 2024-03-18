@allocation_helpers.allocator()
def get_top_level_value(
    service: "lsm::ServiceEntity",
    attribute_path: "string",
) -> "int":
    return 1

@allocation_helpers.allocator()
def get_embedded_value(
    service: "lsm::ServiceEntity",
    attribute_path: "string",
) -> "int":
    return 3

allocation.AllocationSpecV2("value_allocation")
