.. _inter_service_relations:

***********************
Inter-Service Relations
***********************

In some situations, it might be useful to specify relations between services.
In the model, an inter-service-relation is indicated using a relation with the  ``lsm::__service__`` annotation. One can also specify :ref:`attribute_modifiers_on_a_relationship`.
Consider the following example:

.. literalinclude:: inter_service_relations_sources/inter_service_relations.cf
    :linenos:
    :language: inmanta
    :lines: 1-41
    :emphasize-lines: 15
    :caption: main.cf


Here, an inter-service-relation is indicated for service ``Child`` in field ``parent_entity`` with arity ``1`` and modifier ``rw+``.

.. _delete_validating:


delete-validating state
#####################################
Using inter-service-relations can introduce some difficulties with deleting of instances. If we consider the previous example,
deleting an instance of a ``Parent`` can make the configuration invalid if the instance is part of an inter-service-relation with a ``Child`` instance.
The solution to deal with this, is to use an intermediate validation state. Some pre-constructed lifecycles also exist in the ``lsm`` module with additional validation states.
Those lifecycles are:

* ``service_with_delete_validate``
* ``service_with_deallocation_and_delete_validate``
* ``simple_with_delete_validate``
* ``simple_with_deallocation_v2_and_delete_validate``

and use following validation states:

* ``delete_validating_creating``
* ``delete_validating_failed``
* ``delete_validating_up``
* ``delete_validating_update_failed``

To create a custom validation state, create a ``State`` with the ``validate_self`` attribute set to ``null``.

If the compilation succeeds the deletion is accepted, if it fails, this means we are trying to delete an instance that is still in use in an inter-service relation.
Lsm can then accordingly move the state of the service back to the original state or proceed with the delete operation.
