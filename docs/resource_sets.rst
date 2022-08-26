**********************************
Resource sets and partial compile
**********************************
To reduce the time of a compile action, resource sets can be used. Without the use of those, each time a resource is added,
updated or removed, the entire model is recompiled.
By using resource sets, the resources that are usually updated together can be grouped in resource sets.
This way, the time to compile will depend on the size of the targeted resource set. When not using resource sets,
the time to compile will depend on the size of the entire model.
This allows to perform certain actions only on the resources of a specific resource set.
Compiling only some resource sets and not the entire model is called a partial compile.

While the rest of this document will consider the simple case of manually slimming down the model to allow for faster compiles,
the partial compile feature is really mostly useful in combination with additional tooling (e.g. a model generator based on a
yaml file) or an inmanta extension (e.g. LSM) that provides dynamic entity construction.

Resource sets
###########################
Resource sets are represented in the model by instances of the ``std::ResourceSet`` entity. This entity holds the name
of the resource set and a list of resources that belong to the resource set.
The default exporter discovers these ResourceSet instances to determine which resources are part of which resource set.

The example shown below creates 1000 networks of 5 routers each. Each router is part of its network's resource set.

.. literalinclude:: resource_sets/basic_example_full.cf
    :language: inmanta
    :caption: main.cf

Partial compiles
###########################
A partial compile compiles a model that only contains the entities/resources for the resource sets that should be
updated (and the dependencies of these resources to resources that don't belong to a resource set). It's the
responsibility of the server to compose a new version of the model using the resources in the previous version of the
model and the resources that are part of the partial compile.

When a partial export to the server is done, only those resource sets that are present in the partially compiled model will be
replaced. All resources that belong to other sets will remain unaffected. Resources that aren't part of any resource set are
considered shared and may always be added.

A partial export for the model below would update the resources from the previous example:

.. literalinclude:: resource_sets/basic_example_partial.cf
    :language: inmanta
    :caption: main.cf

as a result, network 0 would be updated to have only one router (the other resources are deleted), while all other networks
remain as previously defined (because their resource set was not present in the partial export). The equivalent full model
would look like this:

.. literalinclude:: resource_sets/basic_example_full_result.cf
    :language: inmanta
    :caption: main.cf

Note that each resource set encloses a set of independent resources. If e.g. Router had an index on the id alone, without
including the network, this could never be enforced in the partial compile (because at compile-time the router instances for
other sets do not exist). It is the model developer's responsibility to ensure that resource sets are always defined for a set
of resources that is independent from other sets (that are not part of the partial compile).

Constraints and rules
************************

To ensure partial compiles work correctly some constraints and rules where put in place:

* A resource cannot be part of multiple resource sets at the same time.
* A resource doesn't have to be assigned to a resource set.
* Resources cannot migrate to a different resource set using a partial compile. This operation requires a full compile.
* If a partial export contains a resource set, it must be complete, i.e. all its resources should be present in the partial export.
* A partial compile can never update/remove resources that were not assigned to a specific resource set (adding resources is allowed).
* The new version of the model that results from a partial compile, should have a dependency graph that is closed within the
  exported resource sets (i.e. doesn't have any dependencies in other resource sets).
* A partial compile can update multiple resource sets at the same time.

Exporting a partial model to the server
******************************************************
To export a partial model to the server, 2 options can be specified to the ``inmanta export`` command.

- A ``--partial`` option is added to indicate that the model being compiled, only contains the resources that should be updated with respect to the previous version of the model.

- A ``--delete-resource-set <resource-set-name>`` option is added. This option can be passed multiple times and indicates that the resource set with the given name should be removed from the model. This option can only be used in combination with the previous one. Note that it is also possible to implicitly delete resource sets in a partial compile by using an ``std::ResourceSet`` that doesn't contains any resources

Limitations
*************
* With partial compiles the compiler cannot verify all constraints that would be checked when a full compile is ran. For example, not all index constraints can be verified. It's the responsibility of the model developer to make sure that these constraints are satisfied.
* By only doing partial compile it can happen that a shared resource becomes obsolete: several resources that belong to a different resource set can depend on a specific shared resource (not associated with a specific resource set).
  When a partial compile deletes the last resource that was depending on the shared resource, the shared resource will become obsolete, but it is kept as a resource managed by the server because partial compiles cannot delete shared resources.
  To delete shared resources a full compile is needed. A solution to this is to perform scheduled full compiles to garbage-collect these shared resources.
  To schedule full compiles, the :inmanta.environment-settings:setting:`auto_full_compile` environment setting should be used.
