"""
    Inmanta LSM

    :copyright: 2020 Inmanta
    :contact: code@inmanta.com
    :license: Inmanta EULA
"""

import inmanta_plugins.lsm.allocation as lsm

lsm.AllocationSpec(
    "allocate_vlan",
    lsm.LSM_Allocator(
        attribute="vlan_id", strategy=lsm.AnyUniqueInt(lower=50000, upper=70000)
    ),
)
