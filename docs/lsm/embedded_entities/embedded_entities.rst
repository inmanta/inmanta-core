*****************
Embedded entities
*****************

In some situations, the attributes of a ServiceEntity contain a lot of duplication. Consider the following example:

.. literalinclude:: embedded_entities_sources/example_with_duplication.cf
    :linenos:
    :language: inmanta
    :caption: main.cf

Specifying the router details multiple times, results in code that is hard to read and hard to maintain. Embedded entities
provide a mechanism to define a set of attributes in a separate entity. These attributes can be included
in a ServiceEntity or in another embedded entity via an entity
relationship. The code snippet below rewrite the above-mentioned example using the embedded entity Router:

.. literalinclude:: embedded_entities_sources/basic_example.cf
    :linenos:
    :language: inmanta
    :caption: main.cf

Note, that the Router entity also defines an index on the name attribute.

Modelling embedded entities
###########################

This section describes the different parts of the model that are relevant when modelling an embedded entity.

Strict modifier enforcement
***************************

Each entity binding (``lsm::ServiceEntityBinding`` and ``lsm::ServiceEntityBindingV2``) has a feature flag
called ``strict_modifier_enforcement``. This flag indicates whether attribute modifiers should be enforced recursively
on embedded entities or not. For new projects, it's recommended to enable this flag. Enabling it can be done in two
different ways:

* Create a service binding using the ``lsm::ServiceEntityBinding`` entity and set the value of the attribute
  ``strict_modifier_enforcement`` explicitly to true.
* Or, create a service binding using the ``lsm::ServiceEntityBindingV2`` entity (recommended approach). This entity
  has the ``strict_modifier_enforcement`` flag enabled by default.

The remainder of this section assumes the ``strict_modifier_enforcement`` flag is enabled. If your project has
``strict_modifier_enforcement`` disabled for legacy reasons, consult the Section
:ref:`Legacy: Embedded entities without strict_modifier_enforcement<legacy_no_strict_modifier_enforcement>` for more
information.


Defining an embedded entity
***************************

.. _constraints_on_embedded_entities:

The following constraints should be satisfied for each embedded entity defined in a model:

* The embedded entity must inherit from :inmanta:entity:`lsm::EmbeddedEntity`.
* When a bidirectional relationship is used between the embedding entity and the embedded entity, the variable name
  referencing the embedding entity should start with an underscore (See code snippet below).
* When a bidirectional relationship is used, the arity of the relationship towards the embedding entity should be 0 or 1.
* Relation attributes, where the other side is an embedded entity, should be prefixed with an underscore when the
  relation should not be included in the service definition.
* An index must be defined on an embedded entity if the relationship towards that embedded entity has an upper arity
  larger than one. This index is used to uniquely identify an embedded entity in a relationship. More information
  regarding this is available in section
  :ref:`Attribute modifiers on a relationship<attribute_modifiers_on_a_relationship>`.
* When an embedded entity is defined with the attribute modifier ``__r__``, all sub-attributes of that embedded
  entity need to have the attribute modifier set to read-only as well. More information regarding attribute modifiers
  on embedded entities is available in section :ref:`Attribute modifiers on a relationship<attribute_modifiers_on_a_relationship>`.


The following code snippet gives an example of a bidirectional relationship to an embedded entity. Note that the name
of the relationship to the embedding entity starts with an underscore as required by the above-mentioned constraints:

.. literalinclude:: embedded_entities_sources/example_bidirectional_relationship.cf
    :linenos:
    :language: inmanta
    :emphasize-lines: 16,17
    :caption: main.cf


.. _attribute_modifiers_on_a_relationship:

Attribute modifiers on a relationship
#####################################

Attribute modifiers can also be specified on relational attributes. The ``--`` part of the relationship definition can be
replaced with either ``lsm::__r__``, ``lsm::__rw__`` or ``lsm::__rwplus__``. These attribute modifiers have the following
semantics when set on a relationship:

* **__r__**: The embedded entity/entities can only be set by an allocator. If an embedded entity has this attribute
  modifier, all its sub-attributes should have the read-only modifier as well.
* **__rw__**: The embedded entities, part of the relationship, should be set on service instantiation. After creation,
  no embedded entities can be added or removed from the relationship anymore. Note that this doesn't mean that the
  attributes of the embedded entity cannot be updated. The latter is determined by the attribute modifiers defined on
  the attributes of the embedded entity.
* **__rwplus__**: After service instantiation, embedded entities can be added or removed from the relationship.

When the relationship definition contains a ``--`` instead of one of the above-mentioned keywords, the default attribute
modifier ``__rw__`` is applied on the relationship. The code snippet below gives an example on the usage of attribute
modifiers on relationships:

.. literalinclude:: embedded_entities_sources/example_attribute_modifiers_on_relations.cf
    :linenos:
    :emphasize-lines: 16,17
    :language: inmanta
    :caption: main.cf

In order to enforce the above-mentioned attribute modifiers, the inmanta server needs to be able to determine whether
the embedded entities, provided in an attribute update, are an update of an existing embedded entity or a new
embedded entity is being created. For that reason, each embedded entity needs to define the set of attributes that
uniquely identify the embedded entity if the upper arity of the relationship is larger than one. This set of
attributes is defined via an index on the embedded entity. The index should satisfy the following constraints:

* At least one non-relational attribute should be included in the index.
* Each non-relational attribute, part of the index, is exposed via the north-bound API (i.e. the name of the attribute
  doesn't start with an underscore).
* The index can include no other relational attributes except for the relation to the embedding entity.

The attributes that uniquely identify an embedded entity can never be updated. As such, they cannot have the
attribute modifier ``__rwplus__``.

If multiple indices are defined on the embedded entity that satisfy the above-mentioned constraints, one index needs
to be selected explicitly by defining the ``string[]? __lsm_key_attributes`` attribute in the embedded entity. The
default value of this attribute should contain all the attributes of the index that should be used to uniquely identify
the embedded entity.

The example below defines an embedded entity ``SubService`` with two indices that satisfy the above-mentioned
constraints. The ``__lsm_key_attributes`` attribute is used to indicate that the ``name`` attribute should be used
to uniquely identify the embedded entity.

.. literalinclude:: embedded_entities_sources/example_key_attributes.cf
    :linenos:
    :emphasize-lines: 26,29,30
    :language: inmanta
    :caption: main.cf

If the upper arity of the relationship towards an embedded entity is one, it's not required to define an
index on the embedded entity. In that case, the embedded entity will always have the same identity, no matter what the
values of its attributes are. This means that there will be no difference in behavior whether the attribute modifier is
set to ``rw`` or ``rw+``. If an index is defined on the embedded entity, the attribute modifiers will be enforced in
the same way as for relationships with an upper arity larger than one.


.. _legacy_no_strict_modifier_enforcement:

Legacy: Embedded entities without strict modifier enforcement
#############################################################

When the ``strict_modifier_enforcement`` flag is disabled on a service entity binding, the attribute modifiers defined
on embedded entities are not enforced recursively. In that case, only the attribute modifiers defined on top-level
service attributes are enforced. The following meaning applies to attribute modifiers associated with top-level
relational attributes to embedded entities:

* **__r__**: The embedded entity/entities can only be set by an allocator.
* **__rw__**: The embedded entity/entities should be set on service instantiation. Afterwards the relationship object
  cannot be altered anymore. This means it will be impossible to add/remove entities from the relationship as well as modify any
  of the attributes of the embedded entity in the relationship.
* **__rwplus__**: After service instantiation, embedded entities can be updated and embedded entities can be added/removed from
  the relationship.

The modelling rules that apply when the ``strict_modifier_enforcement`` flag is disabled are less strict compared to the
rules defined in :ref:`Defining an embedded entity<constraints_on_embedded_entities>`. The following changes apply:

* No index should be defined on an embedded entity to indicate the set of attributes that uniquely identify that
  embedded entity. There is also no need to set the ``__lsm_key_attributes`` attribute either.
* When the attribute modifier on an embedded entity is set to ``__r__``, it's not required to set the attribute
  modifiers of all sub-attribute to read-only as well.
