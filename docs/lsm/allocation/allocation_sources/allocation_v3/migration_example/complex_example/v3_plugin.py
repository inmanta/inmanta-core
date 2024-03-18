@allocation_helpers.allocator()
def get_free_value_in_range(
    service: "lsm::ServiceEntity",
    attribute_path: "string",
    *,
    lower: "int",
    upper: "int",
) -> "int":
    # Find all allocated values
    instances=allocation_helpers.get_service_instances(service.entity_binding)
    attribute_path = dict_path.to_path(attribute_path)
    taken = set()
    for instance in instances:
        for attributes_set in (
            "active_attributes",
            "candidate_attributes",
            "rollback_attributes",
        ):
            values = attribute_path.get_elements(attributes_set)
            if len(values) > 0:
                taken.add(values[0])

    return allocation.AnyUniqueInt(lower=lower, upper=upper).select(None, taken)

allocation.AllocationSpecV2("allocate_vlan")
