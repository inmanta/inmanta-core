*******************
Attributes metadata
*******************


This section describes the metadata fields that can be associated with the attributes of a service entity or an embedded entity and how these metadata fields can be set in the model.


Attribute description
~~~~~~~~~~~~~~~~~~~~~

Definition
##########

The attribute description metadata is useful to provide textual information about attributes.
This text will be displayed in the service catalog view of the web console.

Usage
#####

To add a description to an attribute, create a metadata attribute with type string and whose name is the attribute's name extended with the suffix "__description".


Example
#######

.. code-block:: inmanta

    entity Interface :
        string interface_name
        string interface_name__description="The name of the interface"
    end


A detailed example can be found :ref:`here<quickstart_orchestration_model>`.

.. _attributes_metadata_attribute_modifiers:


------------

Attribute modifier
~~~~~~~~~~~~~~~~~~

Definition
##########

Adding the attribute modifier metadata lets the compiler know if:

* This attribute should be provided by an end-user or set by the orchestrator.
* This attribute's value is allowed to change after creation.


Usage
#####


The modifier itself is defined like a regular attribute, with a few caveats:

* it should be of type lsm::attribute_modifier.
* its name should extend the decorated attribute's name with the suffix "__modifier".
* its value should be one of the :ref:`supported values<supported_values>`.


Example
#######

.. code-block:: inmanta

    entity Interface :
        string interface_name
        lsm::attribute_modifier interface_name__modifier="rw+"
    end

A detailed example can be found :ref:`here<quickstart_orchestration_model>`.

.. _supported_values:

Supported values
################

* **r**: This attribute can only be set by an allocator.
* **rw**: This attribute can be set on service instantiation. It cannot be altered anymore afterwards.
* **rw+**: This attribute can be set freely during any phase of the lifecycle.


Attributes modifiers can also be specified on :ref:`relational attributes<attribute_modifiers_on_a_relationship>`.
