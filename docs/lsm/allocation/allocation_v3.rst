**************
Allocation V3
**************


Allocation V3 is a new framework that changes significantly compared to Allocation V2. The purpose is
the same as V2: filling up the read-only values of a service instance during the first validation compile
of the lifecycle. Allocation is now performed via a plugin call.

The advantage of this approach is that it simplifies greatly the process: you don't need anymore to write
allocator classes and all the required functions (``needs_allocation``, ``allocate``, etc.). You also don't need to instantiate many
``AllocationSpecV2`` with your allocators inside. Instead, you just need to write one plugin per attribute
you want to allocate and register it as an ``allocator``, it is less verbose and a much more straightforward approach.
LSM comes with build-in allocators that can be used out of the box, e.g. :func:`get_first_free_integer<lsm::allocators.get_first_free_integer>`.

Create an allocator
###################

In the allocation V3 framework, an allocator is a python function returning the value to be set
for a specific read-only attribute on a specific service instance. To register this function as
an allocator, use the ``allocation_helpers.allocator()`` decorator:


.. code-block:: python
    :linenos:

    from inmanta_plugins.lsm.allocation_helpers import allocator

    @allocator()
    def get_service_id(
        service: "lsm::ServiceEntity",
        attribute_path: "string",
    ) -> "int":
        return 5


An allocator must accept exactly two positional arguments:
    1. ``service``, the service instance for which the value is being allocated.
    2. ``attribute_path``, the attribute of the service instance in which the allocated
    value should be saved, as a :class:`~inmanta.util.dict_path.DictPath` expression. The decorated function can define a default value.

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
   :emphasize-lines: 62

On the plugin side, add an optional argument to enforce ordering:

.. literalinclude:: allocation_sources/allocation_v3/ordering_example/plugin.py
   :language: python
   :caption: __init__.py (Plugin call ordering)
   :linenos:
   :emphasize-lines: 29


V2 to V3 migration
##################

Moving from allocation V2 to allocation V3 boils down to the following steps:

In the plugins directory:

1. Create a specific allocator for each property of the service that requires allocation.
2. Make sure to register these allocators by decorating them with the ``@allocator()`` decorator.

In the model:

3. Call the relevant allocator plugin for each value requiring allocation in the ``lsm::all`` unwrapping.

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



When moving to V3, register an allocator in the plugin:

.. literalinclude:: allocation_sources/allocation_v3/basic_example/v3_plugin.py
   :language: python
   :caption: __init__.py (V3 allocation)
   :linenos:


Model
-----

Baseline V2 allocation in the model:

.. literalinclude:: allocation_sources/allocation_v3/basic_example/v2_main.cf
   :language: inmanta
   :caption: main.cf (V2 allocation)
   :linenos:


When moving to V3 allocation, on the model side, call the allocators for
the values requiring allocation:

.. literalinclude:: allocation_sources/allocation_v3/basic_example/v3_main.cf
   :language: inmanta
   :caption: main.cf (V3 allocation)
   :emphasize-lines: 75,80-88
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


This example will demonstrate how to use the :func:`get_first_free_integer<lsm::allocators.get_first_free_integer>`
allocator from the ``lsm`` module. Since we are using a plugin that is already defined, no extra plugin code
is required. We will simply call this plugin from the model with the appropriate arguments.


Model
-----

Baseline V2 allocation in the model:

.. literalinclude:: allocation_sources/allocation_v3/complex_example/v2_main.cf
   :language: inmanta
   :caption: main.cf (V2 allocation)
   :linenos:


When moving to V3 allocation, on the model side, call the allocators for
the values requiring allocation:

.. literalinclude:: allocation_sources/allocation_v3/complex_example/v3_main.cf
   :language: inmanta
   :caption: main.cf (V3 allocation)
   :linenos:
   :emphasize-lines: 46-54


