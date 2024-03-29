**************
Allocation V2
**************

Allocation V2 is a new framework, similar to allocation (v1).  It happens in the same lifecycle stage
and serves the same purpose: filling up read-only values of a service instance.

It comes to fill some gaps in the functionalities of allocation (v1) and takes advantages of the
experience and learnings that using allocation (v1) taught us.  It is a more complete,
functional, and elegant framework.


Example
#######

The example below show you the use case where a single allocator is used the same way on both the
service instance and an embedded entity.

.. literalinclude:: allocation_sources/allocation_v2/allocation_v2_native.cf
    :linenos:
    :language: inmanta
    :lines: 1-53
    :caption: main.cf

.. literalinclude:: allocation_sources/allocation_v2/allocation_v2_native.py
    :linenos:
    :language: python
    :caption: plugins/__init__.py


Allocation V2 features
######################

The two main additions to allocation v2 when compared to v1 are:
 - The new ContextV2_ object (replacement for ``AllocationContext`` object), which goes in pair with AllocatorV2_ and AllocationSpecV2_
 - The support for allocating attributes in embedded entities.

Setting a read-only attribute on an embedded entity, like done in the above-mentioned example, is only possible when ``strict_modifier_enforcement`` is enabled. On legacy services, where ``strict_modifier_enforcement`` is not enabled, read-only attributes can be set on embedded entities using the workaround mentioned the Section :ref:`Legacy: Set attributes on embedded entities<legacy_set_attributes_on_embedded_entities>`.

.. warning::
   To use allocation safely, allocators should not keep any state between invocations, but pass all state via the `ContextV2`_ object.

ContextV2
---------

A context object that will be passed to each allocator and that should be used to set values.
This context always shows the attributes the allocator should have access to, based on its level
in the allocators tree. This means a top level allocator will see all the attributes, but an
allocator used on embedded entities will only see the attributes of such embedded entity (as if
it was a standalone entity).  The context object can also be used to store values at each "level
of allocation", reachable by all allocators at the same level.

.. autoclass:: inmanta_plugins.lsm.allocation_v2.framework.ContextV2
   :members:

In the example_ at the beginning of this page, the same allocator can be used to set a value on the service entity and an
embedded entity.  In ``needs_allocation``, when calling ``context.get_instance()``, we receive as dict
the full service entity when allocating ``first_value`` and the embedded entity when allocating
``third_value``.


AllocatorV2
-----------

A base class for all v2 allocators, they are provided with a ``ContextV2`` object for those two
methods: ``needs_allocation`` and ``allocate``. The main difference with v1, is that the allocate
method doesn't return any value to allocate, it sets them using the context object:
``context.set_value(name, value)``.

.. autoclass:: inmanta_plugins.lsm.allocation_v2.framework.AllocatorV2
   :members:


AllocationSpecV2
----------------

The collector for all ``AllocatorV2``.

.. autoclass:: inmanta_plugins.lsm.allocation.AllocationSpecV2
   :members:

   .. automethod:: __init__

.. _legacy_set_attributes_on_embedded_entities:

Legacy: Set attributes on embedded entities
###########################################

The server doesn't have support to set read-only attributes on embedded entities when ``strict_modifier_enforcement`` is disabled. Thanks to the allocator ``ContextV2Wrapper`` and the plugin ``lsm::context_v2_unwrapper`` a workaround exists to do allocation on an embedded entity's attributes with ``strict_modifier_enforcement`` disabled. This workaround saves all the allocated values in a dict, in an attribute of the service instance (added to the instance for this single purpose). That way, the server accepts the update.

.. autoclass:: inmanta_plugins.lsm.allocation_v2.framework.ContextV2Wrapper
   :members:

   .. automethod:: __init__

.. autofunction:: inmanta_plugins.lsm.context_v2_unwrapper

The ``ContextV2Wrapper``, which has to be used at the root of the allocation tree, will collect and save all the allocated value in a single dict.  And when getting all the service instances in your model, with ``lsm::all``, you can simply wrap the call
to ``lsm::all`` with a call to ``lsm::context_v2_unwrapper``, which will place all the allocated values
saved in the dict, directly where they belong, in the embedded entities.

When using the ``ContextV2Wrapper`` and the ``lsm::context_v2_unwrapper`` plugin, you will have to
specify in which attributes all the allocated values should be saved.



.. literalinclude:: allocation_sources/allocation_v2/allocation_v2_with_context_v2_wrapper.cf
    :linenos:
    :language: inmanta
    :lines: 1-55
    :emphasize-lines: 12,13,35,36,37,38
    :caption: main.cf

.. literalinclude:: allocation_sources/allocation_v2/allocation_v2_with_context_v2_wrapper.py
    :linenos:
    :language: python
    :emphasize-lines: 39,40,52
    :caption: plugins/__init__.py


To facilitate allocation on embedded entities, the ``ForEach`` allocator can be used.


.. autoclass:: inmanta_plugins.lsm.allocation_v2.framework.ForEach
   :members:

   .. automethod:: __init__


Deleting of Embedded entities
-----------------------------

When you want to support deletion of embedded entities during updates, a slightly different configuration is needed.
Because all allocated values are stored in a single attribute, the deleted entities will be recreated when unwrapping.

To prevent this, use ``track_deletes=true`` on both the the allocator ``ContextV2Wrapper`` and the plugin ``lsm::context_v2_unwrapper``

Additionally, to re-trigger allocation when an item is deleted, use ``SetSensitiveForEach`` instead of ``ForEach``.

.. literalinclude:: allocation_sources/allocation_v2/allocation_v2_track_delete.cf
    :linenos:
    :language: inmanta
    :lines: 1-61
    :emphasize-lines: 43
    :caption: main.cf

.. literalinclude:: allocation_sources/allocation_v2/allocation_v2_track_delete.py
    :linenos:
    :language: python
    :emphasize-lines: 42, 53
    :caption: plugins/__init__.py
