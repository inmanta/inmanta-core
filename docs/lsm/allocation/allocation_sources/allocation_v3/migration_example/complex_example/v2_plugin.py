allocation.AllocationSpec(
    "allocate_vlan",
    allocation.LSM_Allocator(
        attribute="vlan_id", strategy=allocation.AnyUniqueInt(lower=50000, upper=70000)
    ),
)
