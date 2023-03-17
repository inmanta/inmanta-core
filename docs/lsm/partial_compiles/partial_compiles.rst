Partial Compiles
****************


Partial compilation is an approach to speed up compilation when the Service Inventory contains many instances.

Ordinarily, LSM re-compiles all instances on every update. This means that as the inventory grows, the compiles become slower. Partial compiles allow LSM to re-compile only those instances that are relevant to the current service instance, avoiding any slowdown. 

Supported scenarios
-------------------

Partial compiles are possible when

1. Service Instances are unrelated: service instances don't share any resources and don't depend on each other in any way. This requires no modifications to the model.
2. Services form groups under a common owner. 
    Instances within the group can freely depend on each other and share resources, but nothing is shared across group. 
    One specific instance is designated as the owner of the group.
    This requires indicating what the parent of any service is, by setting :inmanta:relation:`lsm::ServiceEntityBinding.owner` and :inmanta:attribute:`lsm::ServiceEntityBinding.relation_to_owner`.

3. Service instances and groups can depend on shared resources, that are identical for all service instances and groups. This requires no modifications to the model.
4. Any combination of the above

Example
-------------------

As an example, consider the following model for managing ports and routers.
Both are independent services, but a port can only be managed in combination with its router and all its sibling. 
(This is not in general true, we often managed port without managing the entire router, but we use it as an example.)

This model is not much different from normal :ref:`Inter Service Relations<inter_service_relations>`, except for lines 55-56.

.. literalinclude:: partial.cf
    :linenos:
    :language: inmanta
    :emphasize-lines: 55-56
    :caption: main.cf


How it works
-------------------

There are two things to consider:
1. how to divide the resources into resource sets
2. how to get the correct instances into the model

Resource sets
+++++++++++++
The key mechanism behind partial compiles are ``ResourceSet``: all resources in the desired state are divided into groups.
When building a new desired state, instead of replacing the entire desired state, we only replace specific ``ResourceSet``.
Resources in ``ResourceSet`` can not depend on Resources in other ``ResourceSets``.

To make this work, we have assign every Service Instance to a ``ResourceSet``, such that the set has no relations to any other ``ResourceSet``.

In practice, we do this by putting all ``Resources`` in the ``ResourceSet`` of the parent entity.

.. digraph:: resource_sets_generic_good
    :caption: Resource Sets for Router example with 2 Routers with each 2 ports.

    subgraph cluster_services {
        "NullResource(name=r1)" [shape=rectangle];
        "LifecycleTransfer(id=0)";
        "LifecycleTransfer(id=0)" ->  "NullResource(name=r1)" 

        "NullResource(name=r1-eth0)" [shape=rectangle];
        "NullResource(name=r1-eth0)" -> "NullResource(name=r1)"
        "LifecycleTransfer(id=2)" -> "NullResource(name=r1-eth0)"

        label = "ResourceSet for Router r1(id=0)";
        labelloc = "top";
        color = "green";
    }
    subgraph cluster_services_2 {
        "NullResource(name=r2)" [shape=rectangle];
        "LifecycleTransfer(id=3)";
        "LifecycleTransfer(id=3)" ->  "NullResource(name=r2)" 

        "NullResource(name=r2-eth0)" [shape=rectangle];
        "NullResource(name=r2-eth0)" -> "NullResource(name=r2)"
        "LifecycleTransfer(id=4)" -> "NullResource(name=r2-eth0)"

        label = "ResourceSet for Router r2(id=3)";
        labelloc = "top";
        color = "green";
    }


In addition to the ``ResourceSets`` used by individual services, there are also ``Resources`` that are not in any set.
There ``Resources`` can be shared by multiple services, with the limitation that any compile that produces them, has to produce them exactly the same. 
For more information see :ref:`Partial Compiles<partial_compile>`.

Service Instance Selection
++++++++++++++++++++++++++

To have efficiency gains when recompiling, it is important to only build the model for all Service Instances that are in the ``ResourceSet`` we want to update and nothing else. 

This selection is done automatically within ``lsm::all``, based on the relations set between the service bindings as explained above. 

The underlying mechanism is that when we recompile for a state change on any Service Instance, we first search its owner by traversing :inmanta:attribute:`lsm::ServiceEntityBinding.relation_to_owner` until we reach a single owner. 
Then we traverse back down the :inmanta:attribute:`lsm::ServiceEntityBinding.relation_to_owner` until we have all children.
``lsm::all`` will only return these children and nothing else.

Limitations
-------------------

1. When doing normal compiles, the model can very effectively find conflicts between services (e.g. using indexes), because it has an overview of all instances. 
When using partial compile, conflicts between groups can not be detected, because the compiler never sees them together. 
This means that the model must be designed to be conflict free or rely on an (external) inventory to avoid conflicts. 
*This is why we always advice to run models in full compile mode until performance becomes an issue*: it gives the model time to mature and to detect subtle conflicts.
2. Complex topologies (with multiple parents or cross-relations) are currently not supported out of the box. 
However, complex interdependencies between service instances are often an operation risk as well. 
Overly entangled services are hard to reason about, debug and fix. 
While it is possible to develop more complex topologies using the guidelines set out in :ref:`Partial Compiles<partial_compile>`, it may be preferable to simplify the service design for less interdependence. 

Further Reading
-------------------

- :ref:`Partial Compiles<partial_compile>` 