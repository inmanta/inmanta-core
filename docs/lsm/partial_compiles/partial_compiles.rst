.. _partial_compile_lsm_sec:

Partial Compiles
****************


Partial compilation is an approach to speed up compilation when the Service Inventory contains many instances.

Ordinarily, LSM re-compiles all instances on every update. This means that as the inventory grows, the compiles become slower. Partial compiles allow LSM to re-compile only those instances that are relevant to the current service instance, avoiding any slowdown.

Implementation guidelines
-------------------------

1. for every :inmanta:entity:`lsm::ServiceEntity`,

    1. make sure to collect all resources it contains in the relation :inmanta:relation:`owned_resources<lsm::ServiceBase.owned_resources>`
    2. make sure to always select the ``parent`` implementations (`implement ... using parents`)
2. for every :ref:`Inter Service Relation<inter_service_relations>`

    1. indicate if this is the relation to the owner by setting :inmanta:attribute:`lsm::ServiceEntityBinding.relation_to_owner` and :inmanta:relation:`lsm::ServiceEntityBinding.owner`.


Supported scenarios
-------------------

Partial compiles are possible when

1. Service Instances are unrelated: service instances don't share any resources and don't depend on each other in any way. This only requires correctly setting :inmanta:relation:`owned_resources<lsm::ServiceBase.owned_resources>`.
2. Services form groups under a common owner.

   - Instances within the group can freely depend on each other and share resources, but nothing is shared across groups.
   - One specific instance is designated as the common owner of the group.
   - Instances can not be moved to another group. The model should prevent this type of update.
   - This additionally requires indicating what the owner of any service is, by setting :inmanta:relation:`lsm::ServiceEntityBinding.owner` and :inmanta:attribute:`lsm::ServiceEntityBinding.relation_to_owner`.
     This does not immediately have to be the root owner, the ownership hierarchy is allowed to form a tree with intermediate owners below the root owner.

3. Service instances and groups can depend on shared resources, that are identical for all service instances and groups.
4. Any combination of the above

How it works for unrelated services
---------------------------------------

For unrelated services, LSM expands on the normal :ref:`resources set based partial compiles<partial_compile>` by automatically creating a single
resource set for each service instance.

To add resources to the instance's resource set, simply add them to its :inmanta:relation:`lsm::ServiceBase.owned_resources` relation and make sure to select the ``parents`` implementation for your service entities. LSM will then
make sure to populate the resource set and to correctly trigger related compiles and exports.


Example with Inter Service Relations
-------------------------------------

As an example, consider the following model for managing ports and routers.
Both are independent services, but a port can only be managed in combination with its router and all its siblings.
(This is not in general true, we often manage ports without managing the entire router, but we use it as an example.)

This model is not much different from normal :ref:`Inter Service Relations<inter_service_relations>`, except for lines 29, 38, 58-59.

.. literalinclude:: partial.cf
    :linenos:
    :language: inmanta
    :emphasize-lines: 29,38,58-59
    :caption: main.cf


How it works
-------------------

To better understand how this works, there are two things to consider:

1. how to divide the resources into resource sets
2. how to get the correct instances into the model

Resource sets
+++++++++++++
The key mechanism behind partial compiles are ``ResourceSets``: all resources in the desired state are divided into groups.
When building a new desired state, instead of replacing the entire desired state, we only replace a specific ``ResourceSet``.
Resources in a ``ResourceSet`` can not depend on Resources in other ``ResourceSets``.

To make this work, we have to assign every Service Instance to a ``ResourceSet``, such that the set has no relations to any other ``ResourceSet``.

In practice, we do this by putting all ``Resources`` in the ``ResourceSet`` of the owning entity.

.. digraph:: resource_sets_generic_good
    :caption: Resource Sets for the Router example with 2 Routers with each 1 port. Arrows represent the requires relation.

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
These ``Resources`` can be shared by multiple services, with the limitation that any compile that produces them, has to produce them exactly the same.
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

For more details, see :ref:`limitation section in the core documentation<partial-compiles-limitations>`

Further Reading
-------------------

- :ref:`Partial Compiles<partial_compile>`
