**************
Multi-version
**************

The goal of multi-version lsm is to have versioning as a way to introduce changes to service entities while
supporting the older behaviour and remaining backwards compatible.
Each service entity will now have versions, which can introduce breaking changes while maintaining support for older
versions.

Why do we want to use  multi-version LSM and not different services?
====================================================================
A service represents a high level desired state. With a new version we want to introduce some changes to a service
(i.e. add a new option, or change how some minor things are done), but overall, keep the same intent.
We want to be able to let a service evolve over time while maintaining backwards compatibility and be able to upgrade
from one version to another without drastically changing the intent of the service.

Backwards compatibility
=======================

In order to keep backwards compatibility with the v1 endpoints we introduced the concept of a default version.
When we use the v1 endpoints to make operations on a service (i.e. get, create, update), we always target the default
version of the service entity.
Every service entity now has a version. The existing service entities and each new one created with the
``lsm::ServiceEntityBinding`` or ``lsm::ServiceEntityBindingV2`` will have one version numbered 0 (which will be the
default version for this service).

Additionally we can provide a default version to ``lsm::ServiceBinding`` to change which version will be accessible
through the v1 endpoints.

Updating a service entity version is not supported for versioned entities. The new workflow is to create a new version
with the required changes. However, updates to a version 0 of a service entity are allowed, if it is the only version
of that service.


Migrating from an existing unversioned model
============================================

Using the :ref:`model to create InterfaceIPAssignments <intro_example>` as an example, we will see how we can turn this
entity into a versioned one.

We just need to change our existing ``lsm::ServiceEntityBinding`` into a ``lsm::ServiceBinding``. Set the
``default_version`` to 0 and create a ``lsm::ServiceBindingVersion`` with the information that we had on our previous
binding.

When unrolling using lsm::all, we use ``lsm::get_service_binding_version`` to fetch the correct entity binding version
for each instance.

.. literalinclude:: multi_version/multi_version_sources/single_version.cf
    :linenos:
    :language: inmanta
    :lines: 1-49

Adding or removing versions
====================

To add a new version of our service we can either create a new entity (if we want to modify the attributes of a
previously created version) or just use the same entity but with different binding attributes
(i.e. different lifecycle).

.. literalinclude:: multi_version/multi_version_sources/multiple_versions.cf
    :linenos:
    :language: inmanta
    :lines: 1-86

In this example we add two new versions. Version 1 links to the same entity model but has a different lifecycle while
Version 2 is a different entity altogether.
When unrolling using ``lsm::all`` we can separate into groups of versions and unroll them as we wish.
In this example, version 1 and 2 will be unrolled together into ``InterfaceIPAssignmentV2`` regardless of their original
version, but version 0 will be unrolled separately into ``InterfaceIPAssignment``).

To remove a version we can delete the corresponding ``lsm::ServiceBindingVersion`` from ``lsm::ServiceBinding.versions``
and recompile and export the new model.

NOTE: We cannot remove service entity versions that have active instances.



Migrating instances between service entity version
==================================================

With the introduction of versions to service entities we might want to migrate existing instances to newer versions.
This can only be done with the `http://<host>:<port>/lsm/v1/service_inventory/<service_entity>/<service_id>/update_entity_version` endpoint
or by calling the `lsm_services_update_entity_version` API method on the Inmanta client.

To do this we need to provide all 3 attribute sets that we want the instance to have on the new entity version.
These attribute sets are validated against the schema of the new version.
We also need to provide the target state that we want to set the instance to.

NOTE: This change is impossible to rollback since we override each attribute set. And each attribute set needs to be
compatible with the target entity version.


