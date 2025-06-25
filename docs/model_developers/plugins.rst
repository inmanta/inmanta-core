.. _module-plugins:

Developing Plugins
*********************

Plugins provide :ref:`functions<lang-plugins>` that can be called from the :term:`DSL`. This is the
primary mechanism to interface Python code with the orchestration model at compile time. For example,
this mechanism is also used for std::template and std::file. In addition to this, Inmanta also registers all
plugins with the template engine (Jinja2) to use as filters.

A simple plugin that accepts no arguments, prints out ``Hello world!`` and returns no value requires
the following code:

.. code-block:: python

    from inmanta.plugins import plugin

    @plugin
    def hello() -> None:
        print("Hello world!")


If the code above is placed in the plugins directory of the example module
(``inmanta_plugins/example/__init__.py``) the plugin can be invoked from the orchestration model as
follows:

.. code-block:: inmanta

    import example

    example::hello()


.. note::

    A module's Python code lives in the ``inmanta_plugins.<module_name>`` namespace.


A more complex plugin accepts arguments and returns a value. Compared to what `python supports as
function arguments <https://docs.python.org/3/glossary.html#term-parameter>`_, only positional-only
arguments are not supported.
The following example creates a plugin that converts a string to uppercase:

.. code-block:: python

    from inmanta.plugins import plugin

    @plugin
    def upper(value: str) -> str:
        return value.upper()


This plugin can be tested with:

.. code-block:: inmanta

    import example

    std::print(example::upper("hello world"))


If your plugin requires external libraries, add them as dependencies of the module. For more details on how to add dependencies
see :ref:`moddev-module`.


Passing entities into plugins
=============================

Entities can also be passed into plugins.
The python code of the plugin can navigate relations throughout the
orchestration model to access attributes of other entities.

This example searches for a specific subnet entity fo a specific IP in a list of subnet entities.

.. code-block:: python

    @plugin
    def find_subnet_for(
        the_ip: "std::ipv4_address",
        subnets: "Subnet[]",
    ) -> "Subnet":
        """find a network containing the ip"""
        ip = IPAddress(the_ip)
        for subnet in subnets:
            if ip in IPNetwork(subnet.ip_subnet):
                return subnet
        raise NoSubnetFoundForIpException(the_ip)

When passing entities into a plugin:

1. the actual python type of the object will be :py:class:`inmanta.execute.proxy.DynamicProxy`
2. the entities can not be modified
3. when traversing a relation or accessing an attribute, that has no value yet, we will raise an :py:class:`inmanta.ast.UnsetException`. The plugin will be re-executed when the value is known. This means that this exception must never be blocked and that code executing before the last attribute or relation access can be executed multiple times.



Raising Exception
====================

A base exception for plugins is provided in :py:class:`inmanta.plugins.PluginException`. Exceptions raised
from a plugin should be of a subtype of this base exception.

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin, PluginException

    @plugin
    def raise_exception(message: "string") -> None:
        raise PluginException(message)



Adding new plugins
========================

A plugin is a python function, registered with the platform with the :func:`~inmanta.plugins.plugin`
decorator. This plugin accepts arguments when called from the DSL and can return a value. Both the
arguments and the return value must be annotated with the allowed types from the orchestration model.

To provide this DSL typing information, you can use either:

-  python types (e.g. ``str``)
-  inmanta types (e.g. ``string``)


Type hinting using python types
-------------------------------

Pass the native python type that corresponds to the :term:`DSL` type at hand. e.g. the ``foo`` plugin
defined below can be used in a model, in a context where the following signature is expected ``string -> int[]``:


.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin
    from collections.abc import Sequence


    @plugin
    def foo(value: str) -> Sequence[int]:
        ...

This approach is the recommended way of adding type information to plugins as it allows you to use mypy when writing plugin code.

This approach also fully supports the use of ``Union`` types (e.g. ``Union[str, int]`` for an argument
or a return value, that can be of either type).


The table below shows correspondence between types from the Inmanta DSL and their respective python counterpart:


+------------------+---------------------------------------+
| Inmanta DSL type | Python type                           |
+==================+=======================================+
| ``string``       | ``str``                               |
+------------------+---------------------------------------+
| ``int``          | ``int``                               |
+------------------+---------------------------------------+
| ``float``        | ``float``                             |
+------------------+---------------------------------------+
| ``int[]``        | ``collections.abc.Sequence[int]``     |
+------------------+---------------------------------------+
| ``dict[int]``    | ``collections.abc.Mapping[str, int]`` |
+------------------+---------------------------------------+
| ``string?``      | ``str | None``                        |
+------------------+---------------------------------------+
| ``any``          | ``typing.Any``                        |
+------------------+---------------------------------------+


``any`` is a special type that effectively disables type validation.

We also give some liberty to the user to define python types for Inmanta DSL types that are not present on this table.

This is done by combining ``typing.Annotated`` with ``inmanta.plugins.ModelType``. The first parameter of ``typing.Annotated``
will be the python type we want to assume for typechecking and the second will be the ``inmanta.plugins.ModelType``
with the Inmanta DSL type that we want the compiler to validate.

For example, if we want to pass a ``std::Entity`` to our plugins and have python validate its type as ``typing.Any``, we could do this:

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin, ModelType
    from typing import Annotated, Any

    type Entity = Annotated[Any, ModelType["std::Entity"]]

    @plugin
    def my_plugin(my_entity: Entity) -> None:
        ...


Our compiler will validate ``my_entity`` as ``std::Entity``, meaning that we will only be able to provide a ``std::Entity``
as an argument to this plugin, but for IDE and static typing purposes it will be treated as ``typing.Any``.



Type hinting using Inmanta DSL types
------------------------------------

Alternatively, the Inmanta :term:`DSL` type annotations can be provided as a string (Python3 style argument annotation)
that refers to Inmanta primitive types or to entities.

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin

    @plugin
    def foo(value: "string") -> "int[]":
        ...



Renaming plugins
================

The plugin decorator accepts an argument name. This can be used to change the name of the plugin in
the DSL. This can be used to create plugins that use python reserved names such as ``print`` for example:

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin

    @plugin("print")
    def printf() -> None:
        """
            Prints inmanta
        """
        print("inmanta")






Dataclasses
========================

When you want to construct entities in a plugin, you can use dataclasses.

An inmanta dataclass is an entity that has a python counterpart.
When used in a plugin, it is a normal python object, when used in the model, it is a normal Entity.

.. literalinclude:: examples/dataclass_1.py
   :language: python


.. literalinclude:: examples/dataclass_1.cf
   :language: inmanta

When using dataclasses, the object can be passed around freely into and out of plugins.

However, some restrictions apply:
The python class is expected to be:

* a frozen dataclass
* with the same name
* in the plugins package of this module
* in the corresponding submodule
* with the exact same fields

The Inmanta entity is expected to:

* have no relations
* have no indexes
* have only std::none as implementation
* extend std::Dataclass

.. note::

    When the inmanta entity and python class don't match, the compiler will print out a correction for both.
    This means you only ever have to write the Entity, because the compiler will print the python class for you to copy paste.

Dataclasses can also be passed into plugins.
When the type is a dataclass, it will always be converted to the python dataclass form.
When you want pass it in as a normal entity, you have to use annotated types and declare the python type to be 'DynamicProxy`.

.. literalinclude:: examples/dataclass_2.py
   :language: python


.. literalinclude:: examples/dataclass_2.cf
   :language: inmanta


Deprecate plugins
========================

To deprecate a plugin the :func:`~inmanta.plugins.deprecated` decorator can be used in combination with the :func:`~inmanta.plugins.plugin`
decorator. Using this decorator will log a warning message when the function is called. This decorator also accepts an
optional argument ``replaced_by`` which can be used to potentially improve the warning message by telling which other
plugin should be used in the place of the current one.

For example if the plugin below is called:

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin, deprecated

    @deprecated(replaced_by="my_new_plugin")
    @plugin
    def printf() -> None:
        """
            Prints inmanta
        """
        print("inmanta")


it will give following warning:

.. code-block::

    Plugin 'printf' in module 'inmanta_plugins.<module_name>' is deprecated. It should be replaced by 'my_new_plugin'

Should the replace_by argument be omitted, the warning would look like this:

.. code-block::

    Plugin 'printf' in module 'inmanta_plugins.<module_name>' is deprecated.

