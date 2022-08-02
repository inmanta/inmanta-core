**********************************
Resource sets and partial compile
**********************************
To support constant scalability resource sets can be used. Without the use of those, each time a resource is added,
updated or removed, the entire model is recompiled.
By using resource sets, the resources that are usually updated together can be grouped in resource sets.
This allows to perform a certain action (e.g. dry-run, repair run) only on the resources of a specific resource sets.
Compiling only some resource sets and not the entire model is called a partial compile.

Resource sets
###########################
Resource sets are represented in the model by instances of the ``std::ResourceSet`` entity. This entity holds the name
of the resource set and a list of resources that belong to the resource set.
The default exporter discovers these ResourceSet instances to determine which resources are part of which resource set.

The example shown below defines an entity/resource Res. Instance a of Res is assigned to the resource set called test:

.. literalinclude:: resource_sets_sources/basic_example.cf
    :linenos:
    :language: inmanta
    :caption: main.cf

Partial compiles
###########################
A partial compile compiles a model that only contains the entities/resources for the resource sets that should be
updated (and the dependencies of these resources to resources that don't belong to a resource set). It's the
responsibility of the server to compose a new version of the model using the resources in the previous version of the
model and the resources that are part of the partial compile.

Constraints and rules
************************

To ensure partial compiles work correctly some constraints and rules where put in place:

* A resource cannot be part of multiple resource sets at the same time.
* A resource doesn't have to be assigned to a resource set.
* Resources cannot migrate to a different resource set using a partial compile. This operation requires a full compile.
* When a partial compile contains a resource that belongs to a certain resource set, the partial compile should contain all the resources for that specific resource set that should be present in the new version of the model.
* A partial compile can never update/remove resources that were not assigned to a specific resource set (adding resources is allowed).
* The new version of the model that results from a partial compile, should have a dependency graph that is closed (i.e. doesn't have any dangling dependencies). This constraint is check by the server.
* A partial compile can update multiple resource sets at the same time.

Exporting a partial model to the server
******************************************************
To export a partial model to the server, 2 options can be specified to the ``inmanta export`` command.
- A ``--partial`` option is added to indicate that the model being compiled, only contains the resources that should be
updated with respect to the previous version of the model.
- A ``--delete-resource-set <resource-set-name>`` option is added. This option can be passed multiple times and
indicates that the resource set with the given name should be removed from the model. This option can only be used in
combination with the previous one.

Limitations
*************
With partial compiles the compiler cannot verify all constraints that would be checked when a full compile is ran.
For example, not all index constraints can be verified. It's the responsibility of the model developer to make sure
that these constraints are satisfied.
