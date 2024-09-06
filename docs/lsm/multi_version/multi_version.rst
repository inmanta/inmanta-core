*****************
Multi-version LSM
*****************

Multi-version lsm allows you to have multiple api versions for the same service.

Why use multi-version LSM?
===========================

You should use multi-version LSM when you want to:

* Offer multiple api schema versions to the same service
* Upgrade a service in a way that is not supported by the :ref:`automated upgrade mechanism <operational_procedures_upgrade>`

Using multi-version LSM
========================

Using the :ref:`model to create InterfaceIPAssignments <intro_example>` as an example, we will see how we can turn this
entity into a versioned one. We just need to:

* Change our existing ``lsm::ServiceEntityBinding`` into a ``lsm::ServiceBinding``.
* Set the ``default_version`` to 0.
* Create a ``lsm::ServiceBindingVersion`` with the information that we had on our previous binding.

When unrolling using lsm::all, we use ``lsm::get_service_binding_version`` to fetch the correct entity binding version
for each instance.

.. literalinclude:: multi_version_sources/single_version.cf
    :linenos:
    :language: inmanta
    :lines: 1-49

Adding or removing versions
===========================

To add a new version of our service we can either create a new entity (if we want to modify the attributes of a
previously created version) or just use the same entity but with different binding attributes
(i.e. different lifecycle).

.. literalinclude:: multi_version_sources/multiple_versions.cf
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

.. note::
    We cannot remove service entity versions that have active instances.

API endpoints
=============
The following API endpoints were added in order to manage versioned services:

* ``GET lsm/v2/service_catalog`` : List all service entity versions of each defined services entity type in the service catalog
* ``GET lsm/v2/service_catalog/<service_entity>/<version>/schema``: Get the json schema for a service entity version.
* ``GET lsm/v2/service_catalog/<service_entity>``: Get all versions of the service entity type from the service catalog.
* ``GET lsm/v2/service_catalog/<service_entity>/<version>``: Get one service entity version from the service catalog.
* ``DELETE lsm/v2/service_catalog/<service_entity>/<version>``: Delete an existing service entity version from the service catalog.
* ``GET lsm/v2/service_catalog/<service_entity>/<version>/config``: Get the config settings for a service entity version.
* ``POST lsm/v2/service_catalog/<service_entity>/<version>/config``: Set the config for a service entity version.
* ``PATCH lsm/v1/service_inventory/<service_entity>/<service_id>/update_entity_version``: Migrate a service instance from one service entity version to another.

The  v1 endpoints are still supported.
When we use the v1 endpoints to make operations on a service (i.e. get, create, update), we always target the default
version of the service entity. (i.e. ``GET lsm/v1/service_catalog/<service_entity>`` will return the default version of this service entity).

Updating a service entity version is not supported for versioned entities. The new workflow is to create a new version
with the required changes. However, updates to a version 0 of a service entity are allowed, if it is the only version
of that service.

The endpoint to create a new service instance (``POST lsm/v1/service_inventory/<service_entity>``) now has an optional
``service_entity_version`` argument. If left empty, the service instance will be created using the default version of the
service entity. Most of the other endpoints that manage service instances remain unchanged, the only exception being
the endpoint to list the service instances of a given service entity (``GET lsm/v1/service_inventory/<service_entity>``)
which received an update to the ``filter`` argument to make it possible to filter by service entity version
(i.e. ``GET lsm/v1/service_inventory/<service_entity>?filter.service_entity_version=ge:2`` to filter for instances
with service entity version greater than or equal to 2).

Migrating instances between service entity version
==================================================

With the introduction of versions to service entities we might want to migrate existing instances to newer versions.
This can only be done with the ``PATCH /lsm/v1/service_inventory/<service_entity>/<service_id>/update_entity_version`` endpoint
or by calling the ``lsm_services_update_entity_version`` API method on the Inmanta client.

To do this we need to provide at least 1 of the 3 attribute sets that we want the instance to have on the new entity version.
These attribute sets are validated against the schema of the new version.
We also need to provide the target state that we want to set the instance to.

.. note::
    This change is impossible to rollback since we override each attribute set. And each attribute set needs to be
    compatible with the target entity version.

Below is a simple script that migrates existing instances of our service that have ``service_entity_version`` 0 or 1
and that are on the up or failed states.

We modify the existing active attribute set of each instance that qualifies for migration to add a generic description
field. We only need to set the candidate set on this example because we are moving each instance to the start state
where this set will be validated and eventually promoted.

.. literalinclude:: multi_version_sources/service_entity_version_migration.py
    :linenos:
    :language: python
    :lines: 1-94

Multi-version Inter-Service Relations
=====================================

Previously, an entity in the model corresponded to a service, with the introduction of multi-version lsm, that is no
longer the case, a service can have multiple version and each version can have the same, or different entities.
So what does this mean for :ref:`inter-service relations<inter_service_relations>`?

An inter-service relation still is a relation between 2 services, meaning that one service is related to another,
regardless of version and the entity that each version uses in the model. It is up to the developer to make sure that
the model remains functional and coherent.

Here is an example of an inter-service relation using multi-version lsm. In this example we have a service with 2 versions
each with a different entity in the model (``Service`` and ``ChildService``) and another service (``RefService``) that refers to them.

Both services are still supported, but, when unrolling the referred services we only create ``ChildService`` instances
(although we could realistically support both).

.. literalinclude:: multi_version_sources/2_versioned_isr.cf
    :linenos:
    :language: inmanta
    :lines: 1-70

In this example we create a new version that uses the ``DifferentService`` entity in the model. This entity does not
inherit from ``Service`` so we also changed ``RefService.ref`` to expect ``DifferentService`` instead.

Now when we unroll the services that ``RefService`` refers to, we have to create instances of ``DifferentService``,
otherwise the model will not compile. Another alternative would be to create a super class that all of the entities
that our service uses would inherit from.

.. literalinclude:: multi_version_sources/3_isr_with_multiple_versions.cf
    :linenos:
    :language: inmanta
    :lines: 1-85

Our migration script is also a bit different. We can't just set the state to ``start`` because it is a non-exporting
state, which means that our child entities would not be unrolled and the index lookup on the ``main_service`` unrolling
would fail, causing the compilation to fail.

.. literalinclude:: multi_version_sources/isr_service_entity_version_migration.py
    :linenos:
    :language: python
    :lines: 1-91
