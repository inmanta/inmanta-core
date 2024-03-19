**************
Allocation V3
**************


Allocation V3 is a new framework that changes significantly compared to Allocation V2. The purpose is
the same as V2: filling up the read-only values of a service instance during the first validation compile
of the lifecycle. The difference is that allocated attributes are not set in the LSM unwrapping anymore,
but instead in an implementation of the service, using plugins.

The advantage of this approach is that it simplifies greatly the process: you don't need anymore to write
allocator classes and all the required functions (``needs_allocation``, ``allocate``, etc.). You also don't need to instantiate many
``AllocationSpecV2`` with your allocators inside. Instead, you just need to write one plugin per attribute
you want to allocate, it is less verbose and a much more straightforward approach.

Create an allocator
###################

In the allocation V3 framework, an allocator is a python function returning the value to be set
for a specific read-only attribute on a specific service instance. To register this function as
an allocator, use the ``allocation_helpers.allocator()`` decorator:


.. code-block:: python
    :linenos:

    @allocation_helpers.allocator()
    def get_service_id(
        service: "lsm::ServiceEntity",
        attribute_path: "string",
    ) -> "int":
        return 5


An allocator must accept exactly two positional arguments:
    1. ``service``, the service instance for which the value is being allocated (usually ``self`` in the model).
    2. ``attribute_path``, the attribute of the service instance in which the allocated
    value should be saved, as a dict_path expression. The decorated function can define a default value.

After those two positional arguments, the function is free of accepting any keyword
argument it needs from the model and they will be passed transparently. The function
can also define default values, that will be passed transparently as well.


Once an allocator is registered, it can be reused for other instances and attributes that require the same type of
allocation by passing the appropriate parameters to the plugin call.

It is also possible to enforce an order in the allocators call by passing values that are returned by other plugins in
the model:


.. literalinclude:: allocation_sources/allocation_v3/ordering_example/main.cf
   :language: inmanta
   :caption: main.cf (Plugin call ordering)
   :linenos:
   :emphasize-lines: 20



V2 to V3 migration
##################

Moving from allocation V2 to allocation V3 boils down to the following steps:

In the plugins directory:

1. Create a specific allocator for each property of the service that requires allocation.
2. Make sure to register these allocators by decorating them with the ``@allocator()`` decorator.

In the model:

3. Add a new implementation for the service to set the values of the properties
requiring allocation by calling the relevant allocator plugin.

Basic example
=============


Here is an example of a V2 to V3 migration. For both the model and the plugin, first the
old V2 version is shown and then the new version using V3 framework:

Plugin
------

Baseline V2 allocation in the plugins directory:

.. literalinclude:: allocation_sources/allocation_v3/basic_example/v2_plugin.py
   :language: python
   :caption: __init__.py (V2 allocation)
   :linenos:



When moving to V3, register one allocator for each property:

.. literalinclude:: allocation_sources/allocation_v3/basic_example/v3_plugin.py
   :language: python
   :caption: __init__.py (V3 allocation)
   :emphasize-lines: 1-2,8-9
   :linenos:


Model
-----

Baseline V2 allocation in the model:

.. literalinclude:: allocation_sources/allocation_v3/basic_example/v2_main.cf
   :language: inmanta
   :caption: main.cf (V2 allocation)
   :linenos:


When moving to V3 allocation, on the model side, add a new implementation
that calls the allocators defined in the plugin:

.. literalinclude:: allocation_sources/allocation_v3/basic_example/v3_main.cf
   :language: inmanta
   :caption: main.cf (V3 allocation)
   :emphasize-lines: 12,14
   :linenos:


In-depth example
================

This is a more complex example ensuring uniqueness for an attribute across instances within a given range of values:


Plugin
------

Baseline V2 allocation in the plugins directory:

.. literalinclude:: allocation_sources/allocation_v3/complex_example/v2_plugin.py
   :language: python
   :caption: __init__.py (V2 allocation)
   :linenos:
   :emphasize-lines: 4


When moving to V3, register one allocator for each property:

.. literalinclude:: allocation_sources/allocation_v3/complex_example/v3_plugin.py
   :language: python
   :caption: __init__.py (V3 allocation)
   :linenos:


In the example above, the plugin takes extra arguments required to make the allocation: ``lower: "int"`` and
``upper: "int"``.



Model
-----

Baseline V2 allocation in the model:

.. literalinclude:: allocation_sources/allocation_v3/complex_example/v2_main.cf
   :language: inmanta
   :caption: main.cf (V2 allocation)
   :linenos:


When moving to V3 allocation, on the model side, add a new implementation
that calls the allocators defined in the plugin:

.. literalinclude:: allocation_sources/allocation_v3/complex_example/v3_main.cf
   :language: inmanta
   :caption: main.cf (V3 allocation)
   :linenos:
   :emphasize-lines: 8


