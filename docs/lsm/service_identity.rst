.. _service_identity:

Service Identity
****************

For each Service Entity, it's possible to define a ``Service Identity``. This is an attribute of the Service,
and it can be used to identify and query the instances belonging to this service,
in case using the default UUIDs is not desirable.

Specifying an identity
----------------------
In order to use a Service Identity, the ``service_identity`` field of a Service Entity should be set,
and point to an attribute of said Service.
It's also possible to define a display name for a service entity (using the ``service_identity_display_name`` field),
which can be used by the frontend to show these values.

There are certain rules concerning Service Identities.
The attribute, that is used as an identity:

- should have an ``rw`` modifier
- should not be optional
- its type should be either string or int (or their constrained variants)
- its values should be unique (with regards to the service entity and environment)

An example of how the identity can be defined in the model:

.. code-block:: inmanta

        entity TestService extends lsm::ServiceEntity:
            string service_id
        end

        implement TestService using std::none

        binding = lsm::ServiceEntityBinding(
            service_entity="__config__::TestService",
            lifecycle=lsm::fsm::simple,
            service_entity_name="{service_entity}",
            service_identity="service_id",
            service_identity_display_name="Service ID"
        )

Adding service identity to an existing entity
---------------------------------------------

Adding a Service Identity to an existing Service is possible, with certain constraints:

- It's not allowed to change or delete an existing identity
- If the values of a proposed identity are not unique with regards to the existing instances, the update will be rejected

Querying service instances using their service identity attribute
-----------------------------------------------------------------

To use the service identity for querying, it can be specified as the ``service_id`` parameter to for the
``GET`` instance endpoint according to the pattern ``<service_identity>=<identity_value>``, instead of a ``UUID``. For example:
``/service_inventory/test_entity/order_id=1234``
