.. _partial_compile:

****************
Partial compiles
****************

.. warning::

    This is an advanced feature, targeted at mature models that have the need to scale beyond their current capabilities.
    Care should be taken to :ref:`implement this safely<partial-compiles-guidelines>`, and the user should be aware of
    :ref:`its limitations<partial-compiles-limitations>`.


.. only:: iso

    .. note::

        For partial compiles through LSM, see :ref:`its documentation<partial_compile_lsm>` on how to manage resource sets for an
        LSM service in addition to the documentation below.

Small updates to large models can be compiled quickly using partial compiles. We merely recompile a tiny, independent portion of the model, as opposed to doing it for the entire model.
A ``resource set`` is made up of the resources in a specific portion of the model.

The model's resources must be separated into resource sets in order to employ partial compilations. The model can then be shrunk to only include the entities for the resource sets that need to be modified.
The changes will be pushed to the server when this smaller model is recompiled and exported in partial mode, but all other resource sets won't be impacted.

While the remainder of this document will focus on the straightforward scenario of manually trimming down the model to facilitate quicker compilations,
the partial compile feature is actually most useful in conjunction with additional tooling (such as a model generator based on a YAML file) or an Inmanta extension (such as ``LSM``) that offers dynamic entity construction.


Resource sets
=============

Instances of the ``std::ResourceSet`` entity serve as the model's representation of resource sets. The name of the set and a list of its resources are held by this entity.
These ``ResourceSet`` instances are found by the default exporter to ascertain which resources belong to which set.

In the example below, 1000 networks of 5 hosts each are created. Each host is part of its network's resource set.

.. literalinclude:: resource_sets/basic_example_full.cf
    :language: inmanta
    :caption: main.cf


Partial compiles
================

When a model is partially compiled, it only includes the entities and resources for the resource sets that need to be changed (as well as their dependencies on additional resources that aren't part of a resource set).
It is the server's responsibility to create a new version of the desired state utilizing the resources from the old version and those from the partial compile.

Only the resource sets that are present in the partially compiled model will be replaced when a partial export
to the server is performed. Other sets' resources won't be impacted in any way.
Shared resources are those that aren't a part of any resource collection and can always be added.


The resources from the prior example would be updated by a partial export for the model below:

.. literalinclude:: resource_sets/basic_example_partial.cf
    :language: inmanta
    :caption: main.cf

As a result, network 0 would be changed to only have one host (the other four resources are removed), but the other networks
would continue to function as they had before (because their resource set was not present in the partial export).
The comparable complete model would seem as follows:

.. literalinclude:: resource_sets/basic_example_full_result.cf
    :language: inmanta
    :caption: main.cf

Keep in mind that each resource set contains a collection of independent resources.
In this example scenario, since the host instances for other sets do not exist at compilation time, it would be impossible to enforce a host index that was based just on the id and excluded the network.

The model developer is accountable for the following: Each resource set in a partial compilation needs to be separate from and independent of the resource sets that aren't included in the partial model.
When performing partial compilations, this is a crucial assumption. If this condition is not satisfied, partial compilations may end up being incompatible with one another (a full compilation with the identical changes would fail),
as the index example shows. This can result in undefinable behavior.


Constraints and rules
---------------------

When using partial compiles, the following rules have to be followed:

* A resource cannot be a part of more than one resource set at once.
* A resource does not have to be part of a resource set.
* Resources cannot be migrated using a partial compile to a different resource set. A full compile is necessary for this process.
* A resource set that is contained in a partial export must be complete, meaning that all of its resources must be present.
* Resources that weren't assigned to a specific resource set can never be updated or removed by a partial build. Although, adding resources is allowed.
* Resources within a resource set cannot depend on resources in another resource set. Dependencies on shared resources are allowed.
* Multiple resource sets may be updated simultaneously via a partial build.

For a guide on how to design a model in order to take these into account, see `Modeling guidelines`_.


Exporting a partial model to the server
---------------------------------------

Three arguments can be passed to the ``inmanta export`` command in order to export a partial model to the server:

- ``--partial`` To specify that the model being compiled only contains the resources that need to be updated in relation to the previous version of the model.
- ``--delete-resource-set <resource-set-name>`` This option, which may be used more than once, instructs the model to remove the resource set with the specified name. Only in conjunction with the preceding choice may this option be utilized. Note that utilizing a ``std::ResourceSet`` that includes no resources allows resource sets to be implicitly deleted during a partial compilation.
- ``--soft-delete`` To silently ignore deletion of resource sets specified through the ``--delete-resource-set`` option if the model is exporting resources that are part of these sets.

.. _partial-compiles-limitations:

Limitations
-----------

* The compiler cannot verify all constraints that would be verified when a full build is run. Some index constraints, for instance, cannot be verified. The model creator is in charge of making sure that these constraints are met.
    See `Modeling guidelines`_ on how to design your model.
* If just a partial compile is performed, it is possible for a shared resource to become obsolete.
  The shared resource will become obsolete when a partial compile deletes the last resource that depended on it, but it is preserved as a server-managed resource because partial compiles cannot delete shared resources.
  A full compile is required to remove shared resources. Scheduled full compilations that ``garbage-collect`` these shared resources are one way to fix this.
  The :inmanta.environment-settings:setting:`auto_full_compile` environment setting is used to schedule full compilations.
  As an example, to plan a daily full compile for 01:00 UTC, use the ``auto_full_compile`` environment setting:  ``0 1 * * *``.


.. _partial-compiles-guidelines:

Modeling guidelines
===================
This section will introduce some guidelines for developing models for use with the partial compilation feature.
Take extreme care when not following these guidelines and keep in mind the `Constraints and rules`_. The purpose of these
guidelines is to present a modelling approach to safely make use of partial compiles. In essence, this boils down to developing
the model so that a partial compile only succeeds if a full one would as well.

In this guide, we only cover models where each set of independent resources is defined by a single top-level entity, which we
will refer to as the "service" or "service entity" (as in ``LSM``). We will use the term "identity" to refer to any set of
attributes that uniquely identify an instance. In the model this usually corresponds to an index.

All potential instances of a service entity must be refined to compatible (low level) configuration when creating an Inmanta
model. In the model this config is represented by the resources. Therefore these guidelines will focus on creating valid and
compatible resources. With well-designed resources, valid and compatible config will follow.

To safely make use of partial compiles, each service must be the sole owner of its resources and any shared resources must be
identical across service instances. The graph below pictures a valid service for partial compiles. Each arrow represents a
refinement: one entity creating another in one of its implementations. The valid service results in fully separate resource
sets for each instance. Additionally, the one shared resource is created consistently between service instances. For each
entity type, the ``id`` attribute is assumed to be an identifying attribute for the instance (i.e. there is an index on the
attribute).

.. digraph:: resource_sets_generic_good
    :caption: A good service for partial compiles.

    subgraph cluster_services {
        "GoodService(id=0)" [shape=rectangle];
        "GoodService(id=0)" -> subgraph cluster_resources_good0 {
            "Resource(id=0)";
            "Resource(id=1)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set for GoodService(id=0)";
            labelloc = "bottom";
        }
        label = "Owned by GoodService(id=0)";
        labelloc = "top";
        color = "green";
    }
    subgraph cluster_service_good1 {
        "GoodService(id=1)" [shape=rectangle];
        "GoodService(id=1)" -> subgraph cluster_resources_good1 {
            "Resource(id=2)";
            "Resource(id=3)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set for GoodService(id=1)";
            labelloc = "bottom";
        }
        label = "Owned by GoodService(id=1)";
        labelloc = "top";
        color = "green";
    }
    { "GoodService(id=0)" "GoodService(id=1)" } -> subgraph cluster_resources_good_shared {
        "SharedResource(id=0, value=0)";
        color = "green";
        fontcolor = "grey";
        label = "Shared and consistent among all service instances";
        labelloc = "bottom";
    }

    # force rendering on multiple ranks
    {"Resource(id=0)" "Resource(id=1)" "Resource(id=2)" "Resource(id=3)"} -> "SharedResource(id=0, value=0)" [style="invis"];


In contrast, the graph below shows an invalid service definition. Its resources overlap between instances. The invalid service
can thus not be allowed for partial compiles because no resource can be considered completely owned by a single service
instance.


.. digraph:: resource_sets_generic_bad_owned
    :caption: A bad service for partial compiles: no owned resources

    subgraph cluster_services {
        "BadService(id=0)" [shape=rectangle];
        "BadService(id=1)" [shape=rectangle];
        { "BadService(id=0)", "BadService(id=1)" } -> subgraph cluster_resources_bad {
            "Resource(id=0)";
            "Resource(id=1)";
            color = "grey";
            fontcolor = "grey";
            label = "Not a valid resource set";
            labelloc = "bottom";
        }
        label = "Services' \"owned\" resources overlap";
        labelloc = "top";
        color = "red";
    }
    { "BadService(id=0)" "BadService(id=1)" } -> subgraph cluster_resources_good_shared {
        "SharedResource(id=0, value=0)";
        color = "green";
        fontcolor = "grey";
        label = "Shared and consistent among all service instances"
        labelloc = "bottom";
    }


Finally, the graph below shows another invalid model. Here, the resources are clearly divided into sets, but the shared
resource is created inconsistently: one instance sets its value to 0 while the other sets it to 1.


.. digraph:: resource_sets_generic_bad_shared
    :caption: A bad service for partial compiles: conflicting shared resources

    subgraph cluster_services {
        "BadService(id=0)" [shape=rectangle];
        "BadService(id=0)" -> subgraph cluster_resources_good0 {
            "Resource(id=0)";
            "Resource(id=1)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set for BadService(id=0)";
            labelloc = "bottom";
        }
        label = "Owned by BadService(id=0)";
        labelloc = "top";
        color = "green";
    }
    subgraph cluster_service_good1 {
        "BadService(id=1)" [shape=rectangle];
        "BadService(id=1)" -> subgraph cluster_resources_good1 {
            "Resource(id=2)";
            "Resource(id=3)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set for BadService(id=1)";
            labelloc = "bottom";
        }
        label = "Owned by BadService(id=1)";
        labelloc = "top";
        color = "green";
    }
    subgraph cluster_resources_bad_shared {
        "SharedResource(id=0, value=0)";
        "SharedResource(id=0, value=1)";
        color = "red";
        fontcolor = "grey";
        label = "Shared resources' values are not consistent"
        labelloc = "bottom";
    }
    "BadService(id=0)" -> "SharedResource(id=0, value=0)";
    "BadService(id=1)" -> "SharedResource(id=0, value=1)";

    # force rendering on multiple ranks
    {"Resource(id=0)" "Resource(id=1)" "Resource(id=2)" "Resource(id=3)"} -> "SharedResource(id=0, value=0)" [style="invis"];


In conclusion, each service's refinements (through implementations) form a tree that may only intersect between service instances on
shared nodes. The whole subtree below such a shared node should be considered shared and any resources in it must not be part of
a resource set. All shared resources should be consistent between any two service instances that might create the object (see
`Constraints and rules`_). All other nodes should generally be considered owned by the service and all their resources be part
of the service's resource set. For more details on what it means to own a resource (or any child node in the tree) and how
to ensure two service instance's trees can not intersect on owned nodes, see the `Ownership`_ subsection.


Service instance uniqueness
---------------------------
With full compiles, indexes serve as the identity of a service instance in the model. The compiler then validates that no conflicting
service instances exist. With partial compiles this validation is lost because only one service instance will be present
in the model. However, it is still crucial that such conflicts do not exist. Put simply, we need to make sure that a partial
compile succeeds only when a full compile would succeed as well. This subsection deals solely with the uniqueness of service
instances. The `Ownership`_ subsection then deals with safe refinements into resources.

To ensure service instance definitions are distinct, the model must make sure to do appropriate validation on the full set of
definitions. When doing a partial compile, the model must verify that the service instance it is compiling for has a different
identity from any of the previously defined service instances. This can be achieved by externally checking against some sort of
inventory that there are no matches for any set of input attributes that identify the instance.

The current implementation of partial compiles does not provide any helpers for this verification. It is the responsibility of
the model developer or the tool/extension that does the export to ensure that no two service instances can be created that are
considered to have the same identity by the model.

For example, suppose we modify the example model to take input from a simple yaml file:

.. code-block:: inmanta

    for network_def in mymodule::read_from_yaml():
        network = Network(id=network_def["id"])
        for host in network["hosts"]:
            network.hosts += Host(id=host["id"])
        end
    end


.. code-block:: yaml

    networks:
        - id: 0
          hosts:
            - id: 0
        - id: 1
          hosts:
            - id: 0
            - id: 1
            - id: 2
            - id: 3
            - id: 4
        - id: 0
          hosts:
            - id: 0
            - id: 1


The ``read_from_yaml()`` plugin would have to verify that no two networks with the same id are defined. After this validation,
if doing a partial, it may return a list with only the relevant network in it. For the yaml given above validation would fail
because two networks with the same id are defined.


Ownership
---------
A resource can safely be considered owned by a service instance if it could never be created by another service instance. There
are two main mechanisms that can be used to provide this guarantee, both of which will be described in their own subsection
below. One is the use of indexes on appropriate locations, the other is the use of some external allocator of unique values
(e.g. a plugin to generate a UUID or to allocate values in an inventory).

In either case, the goal is to make sure that any object that is marked as owned by a service instance, is unique to that
instance. In the index case we do so by making sure the object's identity is in fact completely and uniquely derived from the
identity of the service instance. In the case where unique values are externally produced/allocated, responsibility for
uniqueness falls to the plugin that produces the values.

Ownership through indexes
^^^^^^^^^^^^^^^^^^^^^^^^^
As stated above, during partial compiles indexes alone can not serve as a uniqueness guarantee because each compile only
contains a single service instance. And yet, indexes can still be used as a mechanism to guarantee ownership: e.g. if a value
for a resource's index is uniquely derived from the identity of its service instance, this in itself is a guarantee that no
other service instance could result in this same resource. In other words, rather than count on the stand-alone identity aspect
of the index, we will make sure the identity is fully defined by the service instance's identity (or an external inventory).
This, coupled with the `Service instance uniqueness`_ guarantee ensures that the refinement trees will not intersect. This in
turn allows us to conclude that the partial compile behavior will be the same as the full compile behavior.

Generally, for every index on a set of attributes of an owned resource, at least one of the fields must be either derived from
the identity of the service instance, or allocated in a safe manner by a plugin as described above. The same goes for every
pair of resource id and agent. If the first constraint is not met, a full compile might fail, while if the second is not met,
the export will be rejected because two services are trying to configure the same resources.

For example, consider the example model from before. If two networks with two hosts each would be created, they would result
in two disjunct resource sets, as pictured below.

.. digraph:: resource_sets_example
    :caption: Two valid service instances with their resource sets

    subgraph cluster_shared {
        AgentConfig;
        color = "green";
        fontcolor = "grey";
        label = "Shared resources";
        labelloc = "bottom";
    }

    subgraph cluster_service0 {
        "Network(id=0)" [shape=rectangle];
        "Network(id=0)" -> subgraph cluster_resources0 {
            "Host(nid=0, id=0)";
            "Host(nid=0, id=1)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set for Network 0";
            labelloc = "bottom";
        }
        color = "green";
        label = "service 0";
        labelloc = "top";
    }
    subgraph cluster_service1 {
        "Network(id=1)" [shape=rectangle];
        "Network(id=1)" -> subgraph cluster_resources1 {
            "Host(nid=1, id=0)";
            "Host(nid=1, id=1)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set for Network 1";
            labelloc = "bottom";
        }
        color = "green";
        label = "service 1";
        labelloc = "top";
    }

    # force rendering on multiple ranks
    {"Host(nid=0, id=0)" "Host(nid=0, id=1)" "Host(nid=1, id=0)" "Host(nid=1, id=1)"} -> "AgentConfig";

Now suppose the index on ``Host`` did not include the network instance. In that case the identity of a ``Host`` instance
would no longer be derived from the identity of its ``Network`` instance. It would then be possible to end up with two networks
that refine to the same host objects as shown below. The resource sets are clearly no longer disjunct.

.. digraph:: resource_sets_example_invalid
    :caption: Two invalid service instances with a resource set conflict

    subgraph cluster_shared {
        AgentConfig;
        color = "green";
        fontcolor = "grey";
        label = "Shared resources";
        labelloc = "bottom";
    }

    subgraph cluster_bad {
        "Network(id=0)" [shape=rectangle];
        "Network(id=1)" [shape=rectangle];
        { "Network(id=0)" "Network(id=1)" }-> subgraph cluster_resources0 {
            "Host(id=0)";
            "Host(id=1)";
            color = "grey"
            fontcolor = "grey"
            label = "Resource set 0/1?";
            labelloc = "bottom";
        }
        color = "red";
        label = "intersecting services";
        labelloc = "top";
    }
    { "Host(id=0)" "Host(id=1)" } -> AgentConfig;


Ownership through allocation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Instead of the index ``Host(network, id)`` we could also use an allocation plugin to determine the id of a host. Suppose
we add such a plugin that allocates a unique value in some external inventory, then the index is no longer required for correct
behavior because the allocator guarantees uniqueness for the host id:

.. digraph:: resource_sets_example_allocation
    :caption: Two valid services with their resource sets, using allocation

    subgraph cluster_shared {
        AgentConfig;
        color = "green";
        fontcolor = "grey";
        label = "Shared resources";
        labelloc = "bottom";
    }

    subgraph cluster_service0 {
        "Network(id=0)" [shape=rectangle];
        "Network(id=0)" -> subgraph cluster_resources0 {
            "Host(id=269)";
            "Host(id=694)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set 0";
            labelloc = "bottom";
        }
        color = "green";
        label = "service 0";
        labelloc = "top";
    }
    subgraph cluster_service1 {
        "Network(id=1)" [shape=rectangle];
        "Network(id=1)" -> subgraph cluster_resources1 {
            "Host(id=31)";
            "Host(id=712)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set 1";
            labelloc = "bottom";
        }
        color = "green";
        label = "service 1";
        labelloc = "top";
    }

    # force rendering on multiple ranks
    {"Host(id=694)" "Host(id=269)" "Host(id=712)" "Host(id=31)"} -> "AgentConfig";


Inter-resource set dependencies
-------------------------------

Resources within a resource set can only depend on resources within the same resource set or on shared resources.
Shared resources on the other hand can have dependencies on any resource in the model. The diagram below provides
an example where the resource dependency graph satisfies these requirements. The arrows in the diagram show the
requires relationship between entities/resources.

.. digraph:: resource_sets_example_valid_dependencies
    :caption: Two resource sets satisfying the dependency constraints

    subgraph cluster_shared {
        AgentConfig;
        color = "green";
        fontcolor = "grey";
        label = "Shared resources";
        labelloc = "bottom";
    }

    subgraph cluster_service0 {
        "Network(id=0)" [shape=rectangle];
        "Network(id=0)" -> subgraph cluster_resources0 {
            "Host(id=269)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set 0";
            labelloc = "bottom";
        }
        color = "green";
        label = "service 0";
        labelloc = "top";
    }
    subgraph cluster_service1 {
        "Network(id=1)" [shape=rectangle];
        "Network(id=1)" -> subgraph cluster_resources1 {
            "Host(id=31)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set 1";
            labelloc = "bottom";
        }
        color = "green";
        label = "service 1";
        labelloc = "top";
    }

    {"Host(id=269)" "Host(id=31)"} -> "AgentConfig";

In the diagram below, resource ``Host(id=269)`` that belongs to resource set 0 depends on resource ``Host(id=31)`` that belongs to resource set 1. This inter-resource set dependency is not allowed.

.. digraph:: resource_sets_example_invalid_dependencies
    :caption: Two resource sets violating the dependency constraints

    subgraph cluster_shared {
        AgentConfig;
        color = "green";
        fontcolor = "grey";
        label = "Shared resources";
        labelloc = "bottom";
    }

    subgraph cluster_service0 {
        "Network(id=0)" [shape=rectangle];
        "Network(id=0)" -> subgraph cluster_resources0 {
            "Host(id=269)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set 0";
            labelloc = "bottom";
        }
        color = "green";
        label = "service 0";
        labelloc = "top";
    }
    subgraph cluster_service1 {
        "Network(id=1)" [shape=rectangle];
        "Network(id=1)" -> subgraph cluster_resources1 {
            "Host(id=31)";
            color = "grey";
            fontcolor = "grey";
            label = "Resource set 1";
            labelloc = "bottom";
        }
        color = "green";
        label = "service 1";
        labelloc = "top";
    }

    {"Host(id=269)" "Host(id=31)"} -> "AgentConfig";
    {"Host(id=269)"} -> "Host(id=31)" [color=red];


Testing
-------
While the guidelines outlined above suffice for safe use of partial compiles, a modeling error is easily made. In addition
to the usual testing of behavior of both full and partial compiles, you should include tests that guard against incompatible
resource sets and/or shared resources. These tests would generally be full compile tests with multiple service instances. As
long as a full compile succeeds for any valid set of inputs, you can be confident the partial compile will behave the same.
If on the other hand a set of valid service instances exist for which the full compile fails, you most likely have a modeling
error that would allow sequential partial compiles for those same instances.
