*****************************
Attribute and entity metadata
*****************************


This section describes the metadata fields that can be associated with service entities, embedded entities and its attributes and how these metadata fields can be set in the model.


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


------------

Annotations
~~~~~~~~~~~

Definition
##########

Annotations are key-value pairs that can be associated with an entity (service entity or embedded entity) or an attribute
(simple attribute or relational attribute). These annotations don't influence the behavior of LSM or the Inmanta Service
Orchestrator itself, but are intended to pass meta data to other components. For example, they can be used to pass on
visualization meta-data to the the web-console to improve the user-experience.

Annotations on entities
#######################

Annotations can be attached to an entity using the ``__annotations`` attribute. This attribute has the type ``dict`` and
requires a default value that defines the annotations. Each key-value pair in the dictionary contains respectively the name and
the value of the annotation. The value of an annotation can be any of the simple types (string, float, int, bool), lists and
dicts. Note: These values are the default values of an attribute, therefore they must be constants and cannot include varables,
attribute access or plugins.

Example
#######

The example below illustrates how the annotation ``annotation=value`` can be set on on a service entity.
Annotations can be set on embedded entities in the same way.

.. code-block:: inmanta

    entity Interface extends lsm::ServiceEntity:
        string interface_name
        dict __annotations = {"annotation": "value"}
    end


Annotations on simple attributes
################################

Annotations can be attached to simple (non-relational) attributes by defining an attribute of type dict, with a name
``<attribute>__annotations``, where ``<attribute>`` is the name of the attribute the annotations belong to. This
attribute needs a default value containing the attributes. The values of the elements in the dictionary must be
strings.

Example
#######

The example below shows how the annotation ``annotation=value`` is set on the attribute ``interface_name``.
Annotations can be set on simple attributes of embedded entities in the same way.

.. code-block:: inmanta

    entity Interface extends lsm::ServiceEntity:
        string interface_name
        dict interface_name__annotations = {"annotation": "value"}
    end

Annotations on relational attributes
####################################

Annotations can be attached to a relational attribute by replacing the ``--`` part of the relationship definition with
an instance of the ``lsm::RelationAnnotations`` entity. This entity has a dict attribute ``annotations`` that
represents the annotations that should be set on the relational attribute. The values of this dictionary must
be strings. By convention the name of the ``lsm::RelationAnnotations`` instance should be prefixed and suffixed with
two underscores. This improves the readability of the relationship definition.

Example
#######

The example below illustrates how the annotation ``annotation=value`` can be attached to the relational attribute
``ports``.

.. code-block:: inmanta

    entity Router extends lsm::ServiceEntity:
        string name
    end

    entity Port extends lsm::EmbeddedEntity:
        number id
    end

    __annotations__ = lsm::RelationAnnotations(
        annotations={"annotation": "value"}
    )
    Router.ports [0:] __annotations__ Port._router [1]
