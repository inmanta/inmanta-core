**************
Allocation
**************

In a service lifecycle, allocation is the lifecycle stage where identifiers are allocated for use by a specific service instance.

For example a customer orders a virtual wire between two ports on two routers.
The customer specifies router, port and vlan for both the A and Z side of the wire.
In the network, this virtual wire is implemented as a VXlan tunnel, tied to both endpoints.
Each such tunnel requires a "VXLAN Network Identifier (VNI)" that uniquely identifies the tunnel.
In the allocation phase, the orchestrator selects a VNI and ensures no other customer is assigned the same VNI.

Correct allocation is crucial for the correct functioning of automated services.
However, when serving multiple customers at once or when mediating between multiple inventories, correct allocation can be challenging, due to concurrency and distribution effects.

LSM offers a framework to perform allocation correctly and efficiently. The remainder of this document will explain how.


Types of Allocation
####################

We distinguish several types of allocation. The next sections will explain each type, from simplest to most advanced.
After the basic explanation, a more in-depth explanation is given for the different types.
When first learning about LSM allocation (or allocation in general), it is important to have a basic understanding of the different types, before diving into the details.


LSM internal allocation
------------------------

The easiest form of allocation is when no external inventory is involved.
A range of available identifiers is assigned to LSM to distribute as it sees fit.
For example, VNI range 50000-70000 is reserved to this service and can be used by LSM freely.
This requires no coordination with external systems and is supported out-of-the-box.

The VNI example, allocation would look like this

.. literalinclude:: allocation_sources/base_example.cf
    :linenos:
    :language: inmanta
    :lines: 2-27
    :emphasize-lines: 7,8,17
    :caption: main.cf

The main changes in the model are:

1. the attributes that have to be allocated are added to the service definition as `r` (read only) attributes.
2. the service binding refers to an allocation spec (defined in python code)

.. literalinclude:: allocation_sources/base_example.py
    :linenos:
    :language: python
    :caption: plugins/__init__.py

The allocation spec specifies how to allocate the attribute:

1. Use the pure LSM internal allocation mechanism for `vlan_id`
2. To select a new value, use the `AnyUniqueInt` strategy, which selects a random number in the specified range

Internally, this works by storing allocations in read-only attributes on the instance.
The lsm::all function ensures that if a value is already in the attribute, that value is used.
Otherwise, the allocator gets an appropriate, new value, that doesn't collide with any value in any attribute-set of any other service instance.

*In practice, this means that a value is allocated as long as it's in the active, candidate or rollback attribute sets of any non-terminated service instance.*
When a service instance is terminated, or clears one of its attribute sets, all identifiers are automatically deallocated.

Important note when designing custom lifecycles: allocation only happens during validating, and the result of the allocation is always written to the candidate attributes.

External lookup
---------------

Often, values received via the NorthBound API are not directly usable.
For example, a router can be identified in the API by its name, but what is required is its management IP.
The management IP can be obtained based on the name, through lookup in an inventory.

While lookup is not strictly allocation, it is in many ways similar.

The basic mechanism for external lookup is similar to internal allocation:
the resolved value is stored in a read-only parameter.
This is done to ensure that LSM remains stable, even if the inventory is down or corrupted.
This also implies that if the inventory wants to change the value (i.e. router management IP is suddenly changed),
it should notify LSM. LSM will not by itself pick up inventory changes.
This notification mechanism is currently not supported yet.

An example with router management IP looks like this:

.. literalinclude:: allocation_sources/lookup_example.cf
    :linenos:
    :language: inmanta
    :lines: 1-43
    :emphasize-lines: 12,13,41
    :caption: main.cf

While the allocation implementation could look like the following

.. literalinclude:: allocation_sources/pg_lookup_example.py
    :linenos:
    :language: python
    :caption: plugins/__init__.py

External inventory owns allocation
----------------------------------

When allocating is owned externally, synchronization between LSM and the external inventory is crucial.
If either LSM or the inventory fails, this should not lead to inconsistencies.
In other words, LSM doesn’t only have to maintain consistency between different service instances, but also between itself and the inventory.

The basic mechanism for external allocation is similar to external lookup. One important difference is that we also write our allocation to the inventory.

For example, consider that there is an external Postgres Database that contains the allocation table.
In the model, this will look exactly the same as in the case of internal allocation, in the code, it will look as follows

.. literalinclude:: allocation_sources/pg_id_example.py
    :linenos:
    :language: python
    :caption: plugins/__init__.py

What is important to notice is that the code first tries to see if an allocation has already happened.
This is important in case there was a failure before LSM could commit the allocation.
In general, LSM must be able to identify what has been allocated to it, in order to recover aborted operations.
This is done either by attaching an identifier when performing allocation by knowing where the value will be stored
in the inventory up front (e.g. the inventory contains a service model as well, LSM can find the VNI for a service by requesting the VNI for that service directly).

In the above example, the identifier is the same as the service instance id that LSM uses internally to identify an instance.
An attribute of the instance can also be used to identify it in the external inventory, as the `name` attribute in the the example below.

.. literalinclude:: allocation_sources/pg_attr_example.py
    :linenos:
    :language: python
    :caption: plugins/__init__.py

Second, it is required that the inventory has a procedure to safely obtain ownership of an identifier.
There must be some way LSM can definitely determine if it has correctly obtained an identifier.
In the example, the database transaction ensures this. Many other mechanisms exist, but the inventory has to support at least one.
Examples of possible transaction coordination mechanism are:

1. an API endpoint that atomically and consistently performs allocation,
2. database transaction
3. Compare-and-set style API  (when updating a value, the old  value is also passed along, ensuring no concurrent updates are possible)
4. API with version argument (like the LSM API itself, when updating a value, the version prior to update has to be passed along, preventing concurrent updates)
5. Locks and/or Leases (a value or part of the inventory can be locked or leased(locked for some time) prior to allocation, the lock ensures no concurrent modifications)

This scenario performs no de-allocation.


External inventory with deallocation
------------------------------------

To ensure de-allocation on an external inventory is properly executed, it is not executed during compilation, but by a
handler. This ensures that de-allocation is retried until it completes successfully.

The example below shows how allocation and de-allocation of a VLAN ID can be done using an external inventory. The handler of
the PGAllocation entity performs the de-allocation. An instance of this entity is only constructed when the service instance is
in the deallocating state.

.. literalinclude:: allocation_sources/deallocation.cf
    :linenos:
    :lines: 2-57
    :language: inmanta
    :caption: vlan_assignment/model/_init.cf

The handler associated with the PGAllocation handler is shown in the code snippet below. Note that the handler doesn't have an
implementation for the create_resource() and the update_resource() method since they can never be called. The only possible
operation is a delete operation.

.. literalinclude:: allocation_sources/deallocation.py
    :linenos:
    :language: python
    :caption: vlan_assignment/plugins/__init__.py
