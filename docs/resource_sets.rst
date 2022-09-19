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

In the example below, 1000 networks of 5 hosts each are created. Each host is part of its network's resource set.

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

As a result, network 0 would be changed to only have one host (the other resources are removed), but the other networks
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
************************

When using partial compiles, the following rules have to be followed:

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
This section will introduce some guidelines for developing models for use with the partial compilation feature.
Take extreme care when not following these guidelines and keep in mind the `Constraints and rules`_. The purpose of these
guidelines is to present a modelling approach to safely make use of partial compiles. In essence, this boils down to developing
the model so that a partial compile only succeeds if a full one would as well.

In this guide, we only cover models where each set of independent resources is defined by a single top-level
entity, which we will refer to as the "service" or "service entity" (as in ``LSM``).

When building an inmanta model all potential instances of a service entity must refine to compatible (low level) config.
In the model this config is represented by the resources. Therefore these guidelines will focus on creating valid and
compatible resources. With well-designed resources, valid and compatible config will follow.

To safely make use of partial compiles, each service must be the sole owner of its resources and any shared resources must be
identical across service instances. The graphs below picture respectively a valid and an invalid service for partial compiles.
Each arrow represents a refinement: one entity creating another in one of its implementations. The valid service results in
fully separate resource sets for each instance, while the invalid one has resources that overlap
between instances. Additionally, the shared resource for the valid service is consistent, but the invalid service attempts to
create a resource with the same id, yet a different value. The invalid service can thus not be allowed for partial compiles
because of the inconsistency of shared resources and the fact that no resource can be considered completely owned by a single
service instance.

.. digraph:: resource_sets_good
    :caption: A good service for partial compiles.

    subgraph cluster_service_good0 {
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
        color="green";
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
        color="green";
    }
    { "GoodService(id=0)" "GoodService(id=1)" } -> subgraph cluster_resources_good_shared {
        "SharedResource(id=0, value=0)";
        color="green";
        fontcolor="grey";
        label = "Shared and consistent among all service instances";
        labelloc = "bottom";
    }

    # force rendering on multiple ranks
    {"Resource(id=0)" "Resource(id=1)" "Resource(id=2)" "Resource(id=3)"} -> "SharedResource(id=0, value=0)" [style="invis"]


.. digraph:: resource_sets_generic_bad
    :caption: A bad service for partial compiles.

    subgraph cluster_services_bad {
        "BadService(id=0)" [shape=rectangle];
        "BadService(id=1)" [shape=rectangle];
        { "BadService(id=0)", "BadService(id=1)" } -> subgraph cluster_resources_bad {
            "Resource(id=4)";
            "Resource(id=5)";
            color = "grey";
            fontcolor = "grey";
            label = "Not a valid resource set";
            labelloc = "bottom";
        }
        label = "Services' \"owned\" resources overlap";
        labelloc = "top";
        color = "red";
    }
    subgraph cluster_resources_bad_shared {
        "SharedResource(id=1, value=0)";
        "SharedResource(id=1, value=1)";
        color = "red";
        fontcolor="grey";
        label = "Shared resources' values are not consistent"
        labelloc = "bottom";
    }
    "BadService(id=0)" -> "SharedResource(id=1, value=0)";
    "BadService(id=1)" -> "SharedResource(id=1, value=1)";

    # force rendering on multiple ranks
    {"Resource(id=4)" "Resource(id=5)"} -> {"SharedResource(id=1, value=0)" "SharedResource(id=1, value=1)"} [style="invis"]


TODO: clean up other graphs to look similar to this one


In conclusion, each service's refinements (through implementations) form a tree that may only intersect between service instances on
shared nodes. The whole subtree below such a shared node should be considered shared and any resources in it must not be part of
a resource set. All shared resources should be consistent between any two service instances that might create the object (see
`Constraints and rules`_). All other nodes should generally be considered owned by the service and all their resources be part
of the service's resource set. For more details on what it means to own a resource (or any child node in the tree) and how
to ensure two service instance's trees can not intersect on owned nodes, see the `Ownership`_ subsection.


Service instance uniqueness
***************************
With full compiles, indexes serve as the identity of a service instance in the model. The compiler then validates that no conflicting
service instances can exist. With partial compiles this validation is lost because only one service instance will be present
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
          routers:
            - id: 0
        - id: 1
          routers:
            - id: 0
            - id: 1
            - id: 2
            - id: 3
            - id: 4
        - id: 0
          routers:
            - id: 0
            - id: 1


The ``read_from_yaml()`` plugin would have to verify that no two networks with the same id are defined. After this validation,
if doing a partial, it may return a list with only the relevant network. TODO


Ownership
*********
A resource can safely be considered owned by a service instance if it could never be created by another service instance. There
are two main mechanisms that can be used to provide this guarantee. One is the use of indexes on appropriate locations, the
other is the use of some external distributor of unique values (e.g. a plugin to generate a UUID or to allocate values in an
inventory).

In either case, the goal is to make sure that any object that is marked as owned by a service instance, is unique to that
instance. In the index case we do so by making sure the object's identity is in fact completely derived from the identity of
the service instance. In the case where unique values are externally produced/allocated, responsibility for uniqueness falls
to the plugin that produces the values.

Generally, for every index on a set of attributes of an owned resource, at least one of the fields must be either derived from
the identity of the service instance, or allocated in a safe manner by a plugin as described above. The same goes for every
pair of resource id and agent. If the first constraint is not met, a full compile might fail, while if the second is not met,
the export will be rejected because two services are trying to configure the same resources.

For example, consider the example model from before. If two networks with two hosts each would be created, they would result
in two disjunct resource sets, as pictured below.

TODO: in all these graphs, the edge is actually from Host -> AgentConfig rather than Network -> AgentConfig

.. digraph:: resource_sets_example
    :caption: Two valid services with their resource sets

    subgraph cluster_shared {
        AgentConfig;
        label = "Shared resources";
        labelloc = "bottom";
    }

    subgraph cluster_service0 {
        "Network(id=0)" [shape=rectangle];
        "Network(id=0)" -> subgraph cluster_resources0 {
            "Host(nid=0, id=0)";
            "Host(nid=0, id=1)";
            label = "Resource set 0";
            labelloc = "bottom";
        }
        "Network(id=0)" -> AgentConfig;
        color = "lightgrey";
        label = "service 0";
        labelloc = "top";
    }
    subgraph cluster_service1 {
        "Network(id=1)" [shape=rectangle];
        "Network(id=1)" -> subgraph cluster_resources1 {
            "Host(nid=1, id=0)";
            "Host(nid=1, id=1)";
            label = "Resource set 1";
            labelloc = "bottom";
        }
        "Network(id=1)" -> AgentConfig;
        color = "lightgrey";
        label = "service 1";
        labelloc = "top";
    }

Now suppose the index on ``Host`` did not include the network instance. In that case the identity of a ``Host`` instance
would no longer be derived from the identity of its ``Network`` instance. It would then be possible to end up with two networks
that refine to the same host objects as shown below. The resource sets are clearly no longer disjunct.

.. digraph:: resource_sets_example_invalid
    :caption: Two invalid services with a resource set conflict

    subgraph cluster_shared {
        AgentConfig;
        label = "Shared resources";
        labelloc = "bottom";
    }

    "Network(id=0)" [shape=rectangle];
    "Network(id=1)" [shape=rectangle];
    { "Network(id=0)" "Network(id=1)" }-> subgraph cluster_resources0 {
        "Host(id=0)";
        "Host(id=1)";
        label = "Resource set 0/1?";
        labelloc = "bottom";
    }
    { "Network(id=0)" "Network(id=1)" } -> AgentConfig;

Instead of the index ``Host(network, id)`` we could also use an allocation plugin to determine the id of a host. Suppose
we add such a plugin that allocates a unique value in some external inventory, then the index is no longer required for correct
behavior:

.. digraph:: resource_sets_example_allocation
    :caption: Two valid services with their resource sets, using allocation

    subgraph cluster_shared {
        AgentConfig;
        label = "Shared resources";
        labelloc = "bottom";
    }

    subgraph cluster_service0 {
        "Network(id=0)" [shape=rectangle];
        "Network(id=0)" -> subgraph cluster_resources0 {
            "Host(id=269)";
            "Host(id=694)";
            label = "Resource set 0";
            labelloc = "bottom";
        }
        "Network(id=0)" -> AgentConfig;
        color = "lightgrey";
        label = "service 0";
        labelloc = "top";
    }
    subgraph cluster_service1 {
        "Network(id=1)" [shape=rectangle];
        "Network(id=1)" -> subgraph cluster_resources1 {
            "Host(id=31)";
            "Host(id=712)";
            label = "Resource set 1";
            labelloc = "bottom";
        }
        "Network(id=1)" -> AgentConfig;
        color = "lightgrey";
        label = "service 1";
        labelloc = "top";
    }

TODO: guideline on test setup to verify correctness. Run tests with both partial and non-partial, what sort of tests should definitely be included, ...?
