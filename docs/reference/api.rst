Inmanta API reference
=====================

This page describes parts of the compiler that provide a stable API that could be used from modules.

.. warning::
    Only those parts explicitly mentioned here are part of the API. They provide a stable
    interface. Other parts of the containing modules provide no such guarantees.

.. _compiler-exceptions:

Compiler exceptions
-------------------

.. autoclass:: inmanta.ast.CompilerException
    :show-inheritance:

.. autoclass:: inmanta.parser.ParserException
    :show-inheritance:

.. autoclass:: inmanta.ast.RuntimeException
    :show-inheritance:

.. autoclass:: inmanta.ast.ExternalException
    :show-inheritance:

.. autoclass:: inmanta.ast.ExplicitPluginException
    :show-inheritance:

Plugins
-------

.. autoclass:: inmanta.plugins.Context
    :members:
    :undoc-members:

.. autofunction:: inmanta.plugins.plugin

.. autoclass:: inmanta.plugins.PluginException

Resources
---------

.. autofunction:: inmanta.resources.resource
.. autoclass:: inmanta.resources.Resource
    :members: clone

.. autoclass:: inmanta.resources.PurgeableResource
.. autoclass:: inmanta.resources.ManagedResource
.. autoclass:: inmanta.resources.IgnoreResourceException

Handlers
--------

.. autofunction:: inmanta.agent.handler.cache
.. autofunction:: inmanta.agent.handler.provider
.. autoclass:: inmanta.agent.handler.SkipResource
    :show-inheritance:
    :members:
.. autoclass:: inmanta.agent.handler.ResourcePurged
    :members:
.. autoclass:: inmanta.agent.handler.HandlerContext
    :members:
.. autoclass:: inmanta.agent.handler.ResourceHandler
    :members:
    :undoc-members:
    :private-members:

.. autoclass:: inmanta.agent.handler.CRUDHandler
    :members:
    :inherited-members:
    :undoc-members:
.. autoclass:: inmanta.agent.io.local.LocalIO
    :members:
    :inherited-members:
    :undoc-members:


Attributes
----------

.. autoclass:: inmanta.ast.attribute.Attribute
    :members: validate, get_type, type
    :undoc-members:


Modules
-------

.. autoclass:: inmanta.module.ModuleLike
    :members: name
    :undoc-members:

.. autoclass:: inmanta.module.Module
    :show-inheritance:
    :members: get_plugin_files
    :undoc-members:

.. autodata:: inmanta.module.ModuleName

.. autodata:: inmanta.module.Path


Typing
------

The `inmanta.ast.type` module contains a representation of inmanta types, as well as validation logic for
those types.

.. autoclass:: inmanta.ast.type.Type
    :members: validate, type_string, is_primitive, get_base_type, with_base_type
    :undoc-members:

.. autoclass:: inmanta.ast.type.NullableType
    :show-inheritance:

.. autoclass:: inmanta.ast.type.Primitive
    :members: cast
    :undoc-members:
    :show-inheritance:

.. autoclass:: inmanta.ast.type.Number
    :show-inheritance:

.. autoclass:: inmanta.ast.type.Integer
    :show-inheritance:

.. autoclass:: inmanta.ast.type.Bool
    :show-inheritance:

.. autoclass:: inmanta.ast.type.String
    :show-inheritance:

.. autoclass:: inmanta.ast.type.Union
    :show-inheritance:

.. autoclass:: inmanta.ast.type.Literal
    :show-inheritance:

.. autoclass:: inmanta.ast.type.List
    :show-inheritance:

.. autoclass:: inmanta.ast.type.TypedList
    :show-inheritance:

.. autoclass:: inmanta.ast.type.LiteralList
    :show-inheritance:

.. autoclass:: inmanta.ast.type.Dict
    :show-inheritance:

.. autoclass:: inmanta.ast.type.TypedDict
    :show-inheritance:

.. autoclass:: inmanta.ast.type.LiteralDict
    :show-inheritance:

.. autoclass:: inmanta.ast.type.ConstraintType
    :show-inheritance:

.. autodata:: inmanta.ast.type.TYPES
    :annotation:

.. note::
    The type classes themselves do not represent inmanta types, their instances do. For example, the
    type representation for the inmanta type `number` is `Number()`, not `Number`.


Domain conversion
-----------------

This section describes methods for converting values between the plugin domain and the internal domain.
This conversion is performed automatically for plugin arguments and return values so it is only required
when bypassing the usual plugin workflow by calling internal methods directly.

.. autoclass:: inmanta.execute.proxy.DynamicProxy()
    :members: return_value, unwrap
    :undoc-members:
