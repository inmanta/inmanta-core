**********************************
Resource sets and partial compile
**********************************

Small updates to large models can be compiled quickly using partial compiles. We merely recompile a tiny, independent portion of the model, as opposed to doing it for the entire model.
A ``resource set`` is made up of the resources in a specific portion of the model.

The model's resources must be separated into resource sets in order to employ partial compilations. The model can then be shrunk to only include the entities for the resource sets that need to be modified.
The changes will be pushed to the server when this smaller model is recompiled and exported in partial mode, but all other resource sets won't be impacted.

While the remainder of this document will focus on the straightforward scenario of manually trimming down the model to facilitate quicker compilations,
the partial compile feature is actually most useful in conjunction with additional tooling (such as a model generator based on a YAML file) or an Inmanta extension (such as ``LSM``) that offers dynamic entity construction.


Resource sets
###########################

Instances of the ``std::ResourceSet`` entity serve as the model's representation of resource sets. The name of the set and a list of its resources are held by this entity.
These ``ResourceSet`` instances are found by the default exporter to ascertain which resources belong to which set.

In the example below, 1000 networks of 5 routers each are created. Each router is part of its network's resource set.

.. literalinclude:: resource_sets/basic_example_full.cf
    :language: inmanta
    :caption: main.cf


Partial compiles
###########################

When a model is partially compiled, it only includes the entities and resources for the resource sets that need to be changed (as well as their dependencies on additional resources that aren't part of a resource set).
It is the server's responsibility to create a new version of the desired state utilizing the resources from the old version and those from the partial compile.

Only the resource sets that are present in the partially compiled model will be replaced when a partial export
to the server is performed. Other sets' resources won't be impacted in any way.
Shared resources are those that aren't a part of any resource collection and can always be added.


The resources from the prior example would be updated by a partial export for the model below:

.. literalinclude:: resource_sets/basic_example_partial.cf
    :language: inmanta
    :caption: main.cf

As a result, network 0 would be changed to only have one router (the other resources are removed), but the other networks
would continue to function as they had before (because their resource set was not present in the partial export).
The comparable complete model would seem as follows:

.. literalinclude:: resource_sets/basic_example_full_result.cf
    :language: inmanta
    :caption: main.cf

Keep in mind that each resource set contains a collection of independent resources.
In this example scenario, since the router instances for other sets do not exist at compilation time, it would be impossible to enforce a router index that was based just on the id and excluded the network.

The model developer is accountable for the following: Each resource set in a partial compilation needs to be separate from and independent of the resource sets that aren't included in the partial model.
When performing partial compilations, this is a crucial assumption. If this condition is not satisfied, partial compilations may end up being incompatible with one another (a full compilation with the identical changes would fail),
as the index example shows. This can result in undefinable behavior.


Constraints and rules
************************

Some restrictions were implemented to guarantee that partial compilations function properly:

* A resource cannot be a part of more than one resource set at once.
* A resource does not have to be part of a resource set.
* Resources cannot be migrated using a partial compile to a different resource set. A full compile is necessary for this process.
* A resource set that is contained in a partial export must be complete, meaning that all of its resources must be present.
* Resources that weren't assigned to a specific resource set can never be updated or removed by a partial build. Although, adding resources is allowed.
* The new version of the model that emerges from a partial compilation should have a dependency graph that is closed within the resource sets that were exported.
  i.e., it should not depend on any resource sets other than those that were exported.
* Multiple resource sets may be updated simultaneously via a partial build.

TODO: link to new section


Exporting a partial model to the server
******************************************************

Two arguments can be passed to the ``inmanta export`` command in order to export a partial model to the server:

- ``--partial`` To specify that the model being compiled only contains the resources that need to be updated in relation to the previous version of the model.
- ``--delete-resource-set <resource-set-name>`` This option, which may be used more than once, instructs the model to remove the resource set with the specified name. Only in conjunction with the preceding choice may this option be utilized. Note that utilizing a ``std::ResourceSet`` that includes no resources allows resource sets to be implicitly deleted during a partial compilation.


Limitations
*************

* The compiler cannot verify all constraints that would be verified when a full build is run. Some index constraints, for instance, cannot be verified. The model creator is in charge of making sure that these constraints are met.
* If just a partial compile is performed, it is possible for a shared resource to become obsolete.
  The shared resource will become obsolete when a partial compile deletes the last resource that depended on it, but it is preserved as a server-managed resource because partial compiles cannot delete shared resources.
  A full compile is required to remove shared resources. Scheduled full compilations that ``garbage-collect`` these shared resources are one way to fix this.
  The :inmanta.environment-settings:setting:`auto_full_compile` environment setting is used to schedule full compilations.
  As an example, to plan a daily full compile for 01:00 UTC, use the ``auto_full_compile`` environment setting:  ``0 1 * * *``.


TODO: mention this in the document's introduction?

Modeling guidelines
###################
This section will introduce some guidelines for developing models for use with the partial compilation feature. These present
a generic method that is safe to use with partial compiles. While diverging from these guidelines where they are overly
restrictive for your use case does not guarantee an incompatible model, it should always be done conciously and with extreme
care to respect the `Constraints and rules`_.

For simplicity, we will assume a model where each set of independent resources is ultimately defined by a single top-level
entity, which we will refer to as the "service" or "service entity" (as in ``LSM``). While the same concepts apply to the
use case where a set of independent resources is defined by more than one service entity, the guidelines currently do not
cover that use case.

TODO: see how trivial it would be to extend to the multi-service use case
TODO: "On a high level" -> remove?
TODO: should I simplify and just talk about resources rather than generic nodes?

On a high level, to allow safe use of partial compiles, it is imperative that each service's refinements (through
implementations) form a tree that can only intersect between service instances on shared nodes. The whole subtree below such a
shared node should be considered shared and any resources in it must not be part of a resource set. All shared resources should
be consistent between any two service instances that might create the object (see `Constraints and rules`_). All other nodes
should generally be considered owned by the service and all their resources be part of the service's resource set. For more
details on what it means to own a a child node in the tree (e.g. a resource) and how to ensure two service instance's trees can
not intersect on owned nodes, see the `Ownership`_ section.

Ownership
*********
A resource can safely be considered owned by a service instance if it could never be created by another service instance. There
are two main mechanisms that can be used to provide this guarantee. One is the use of indexes on appropriate locations, the
other is the use of some external distributor of unique values (e.g. a plugin to generate a UUID or to allocate values in an
inventory).

TODO: indexes, do they even suffice now that we don't check on the API level yet? For core-only custom check is always required
TODO: when using inventory, responsibility for uniqueness is shifted to inventory
TODO: which values need to be unique?


TODO: section about ownership: indexes vs inventory
TODO: example model (running example? mention assumption that resource id is netid+rid) + trees + highlight tree if there would be an index on Router id + that's where inventory comes into play


TODO: can we be more concrete? Should the section introduction mention that we go from high level to concrete?

TODO: guideline on test setup to verify correctness. Run tests with both partial and non-partial, what sort of tests should definitely be included, ...?
