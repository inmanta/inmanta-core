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
    :emphasize-lines: 15
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
    :emphasize-lines: 15,16
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
    :emphasize-lines: 25,28,29
    :language: inmanta
    :caption: main.cf


If the upper arity of the relationship towards an embedded entity is one, it's not required to define an
index on the embedded entity. In that case, the embedded entity will always have the same identity, no matter what the
values of its attributes are. This means that there will be no difference in behavior whether the attribute modifier is
set to ``rw`` or ``rw+``. If an index is defined on the embedded entity, the attribute modifiers will be enforced in
the same way as for relationships with an upper arity larger than one.

.. _tracking_embedded_entities_across_updates:

Tracking embedded entities across updates
#########################################


Depending on what the embedded entities are modeling, you might want to keep track of which embedded entities
were added or removed during an update, in order to apply custom logic to them. This section describes how to track
embedded entities during the update flow of a service.

When using the "simple" lifecycle, this is supported out of the box by passing ``include_purged_embedded_entities=true``
to the ``lsm::all()`` plugin call.

During each step of the update, two sets of attributes (the "current" set and the "previous" set) will be compared to
determine which embedded entities were added or removed. The plugin will accordingly set the following boolean
attributes on the relevant embedded entities: ``_removed`` and ``_added``. These values can
then be used in the model to implement custom logic.

.. note::
    The "simple" lifecycle defines out-of-the-box which pair of sets should be compared at each step of the update.
    Please refer to the :ref:`Tracking embedded entities when using a custom lifecycle<using_custom_lifecycle>` section
    below for more information on how to define which pairs should be compared when using a custom lifecycle.

.. note::
    To set a different naming scheme for these tracking attributes, use the ``removed_attribute`` and
    ``added_attribute`` parameters of the ``lsm::all()`` plugin.




The following sections describe 3 flavours of update flows through examples.



Update flow with implicit deletion
**********************************

In this update flow, the embedded entities are side-effect free
and fully under control of the parent entity. The following model
demonstrate this case:

- The parent entity is a file on a file system
- The embedded entities represent individual lines in this file

In this example, the deployed resources (i.e. the deployed files) will mirror exactly the embedded entities
present in the model since the content of the file is derived from the set of embedded entities.
If an embedded entity is removed during an update, the file content will reflect this accordingly.


.. literalinclude:: embedded_entities_sources/example_lines_in_file.cf
    :linenos:
    :language: inmanta
    :caption: main.cf


Update flow with explicit deletion
**********************************


In this update flow, the embedded entities are not side-effect free
or not fully under control of the parent entity. The following model
demonstrate this case:

- The parent entity is a directory on a file system
- The embedded entities represent individual files in this directory

In this example, we have to take extra steps to make sure the deployed resources (i.e. the deployed directories and files
below them) match the embedded entities present in the model.
The content of the directories is derived from the set of embedded entities. If an embedded entity is removed during an
update, we have to make sure to remove it from disk explicitly.

.. literalinclude:: embedded_entities_sources/example_files_in_folder.cf
    :linenos:
    :language: inmanta
    :caption: main.cf


Update flow with mutually explicit desired state
************************************************

The last possible update scenario is one with mutually exclusive desired state throughout the update, e.g. a database
migration from cluster A to cluster B:

1. Initial desired state: data lives in cluster A
2. Intermediate desired state:  data is replicated in cluster A and cluster B
3. Final desired state: data lives in cluster B


For these more involved update scenarios we recommend updating the lifecycle specifically for this update.

.. _using_custom_lifecycle:


Tracking embedded entities when using a custom lifecycle
********************************************************

To be able to track added and removed embedded entities across the update, all the
relevant lifecycle states (i.e. all states traversed during an update) need to be
provided with the following attributes:

* previous_attr_set_on_validate
* previous_attr_set_on_export

The domain of valid values for these attributes is [``"candidate"``, ``"active"``, ``"rollback"``, ``null``].



1. During a validation compile:
    * Current set
        - if the current instance is being validated:
             - The current set is the set defined by the ``validate_self`` parameter.

        - if another instance is being validated:
             - The current set is the set defined by the ``validate_others`` parameter.

    * Previous set
        - The previous set is the set defined by the ``previous_attr_set_on_validate`` parameter.

2. During an exporting compile:
    * Current set
        - The current set is the active attributes set

    * Previous set
        - The previous set is the set defined by the ``previous_attr_set_on_export`` parameter.


We recommend to manually go through all the states that are part of the update, think about which
two sets should be compared at each step and set the parameters accordingly.


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
