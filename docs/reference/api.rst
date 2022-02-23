Programmatic API reference
==========================

This page describes parts of inmanta code base that provide a stable API that could be used from modules or extensions.

.. warning::
    Only those parts explicitly mentioned here are part of the API. They provide a stable
    interface. Other parts of the containing modules provide no such guarantees.


Constants
---------

.. autoclass:: inmanta.const.LogLevel
    :show-inheritance:
    :members:
    :undoc-members:
.. autoclass:: inmanta.const.ResourceAction
    :show-inheritance:
    :members:
    :undoc-members:


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

.. autoclass:: inmanta.plugins.PluginMeta
    :show-inheritance:
    :members: add_function, clear, get_functions
    :undoc-members:

Resources
---------

.. autofunction:: inmanta.resources.resource
.. autoclass:: inmanta.resources.Resource
    :members: clone

.. autoclass:: inmanta.resources.PurgeableResource
.. autoclass:: inmanta.resources.ManagedResource
.. autoclass:: inmanta.resources.IgnoreResourceException
.. autoclass:: inmanta.resources.Id
    :members: parse_id, resource_str
    :undoc-members:

.. autoclass:: inmanta.execute.util.Unknown

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


Export
------

.. autodecorator:: inmanta.export.dependency_manager


Attributes
----------

.. autoclass:: inmanta.ast.attribute.Attribute
    :members: validate, get_type, type
    :undoc-members:

.. autoclass:: inmanta.ast.attribute.RelationAttribute
    :show-inheritance:


Modules
-------

.. autoclass:: inmanta.module.InstallMode
    :members:
    :undoc-members:
    :show-inheritance:

.. autodata:: inmanta.module.INSTALL_OPTS

.. autoclass:: inmanta.module.InvalidModuleException

.. autoclass:: inmanta.module.InvalidMetadata

.. autoclass:: inmanta.module.ModuleLike
    :show-inheritance:
    :members: metadata, from_path
    :undoc-members:

.. autoclass:: inmanta.module.Module
    :show-inheritance:
    :members: from_path, get_plugin_files, unload
    :undoc-members:

.. autodata:: inmanta.module.ModuleName

.. autoclass:: inmanta.module.ModuleV1
    :show-inheritance:
    :members: from_path
    :undoc-members:

.. autoclass:: inmanta.module.ModuleV2
    :show-inheritance:
    :members: is_editable, from_path
    :undoc-members:

.. autoclass:: inmanta.module.ModuleSource
    :show-inheritance:
    :members: get_installed_module
    :undoc-members:

.. autoclass:: inmanta.module.ModuleV2Source
    :show-inheritance:

.. autodata:: inmanta.module.Path

.. autoclass:: inmanta.loader.PluginModuleFinder
    :show-inheritance:
    :members: reset
    :undoc-members:

.. autofunction:: inmanta.loader.unload_inmanta_plugins


Project
-------

.. autoclass:: inmanta.module.Project
    :members: get, load, set, install_modules
    :undoc-members:
    :show-inheritance:

.. autoclass:: inmanta.module.ProjectNotFoundException
    :undoc-members:
    :show-inheritance:


Python Environment
------------------


.. autofunction:: inmanta.env.mock_process_env


.. autoclass:: inmanta.env.VirtualEnv
    :members: init_env, use_virtual_env
    :undoc-members:

Variables
------
.. autoclass:: inmanta.ast.variables.Reference
    :members: name
    :undoc-members:

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


Protocol
--------

.. autoclass:: inmanta.protocol.common.Result
    :members: code, result
    :undoc-members:


Data
----

.. warning::
    In contrast to the rest of this section, the data API interface is subject to change. It is documented here because it is
    currently the only available API to interact with the data framework. A restructure of the data framework is expected at
    some point. Until then, this API should be considered unstable.

.. data:: inmanta.data.TBaseDocument
    :annotation: : typing.TypeVar

    TypeVar with BaseDocument bound.

.. autoclass:: inmanta.data.BaseDocument
    :members: get_by_id, get_list
    :undoc-members:

.. autoclass:: inmanta.data.Compile
    :members: get_substitute_by_id, to_dto
    :undoc-members:
    :show-inheritance:

.. autoclass:: inmanta.data.ConfigurationModel
    :members: get_versions
    :undoc-members:
    :show-inheritance:

.. autoclass:: inmanta.data.Environment
    :show-inheritance:

.. autoclass:: inmanta.data.Report
    :show-inheritance:

.. autoclass:: inmanta.data.Resource
    :members: get_resources_for_version
    :undoc-members:
    :show-inheritance:

.. autoclass:: inmanta.data.ResourceAction
    :members: get_logs_for_version
    :undoc-members:
    :show-inheritance:

.. autoclass:: inmanta.data.model.BaseModel
    :show-inheritance:

    .. autoclass:: inmanta.data.model::BaseModel.Config
        :members:
        :undoc-members:

.. autodata:: inmanta.data.model.ResourceIdStr

.. autodata:: inmanta.data.model.ResourceVersionIdStr


Domain conversion
-----------------

This section describes methods for converting values between the plugin domain and the internal domain.
This conversion is performed automatically for plugin arguments and return values so it is only required
when bypassing the usual plugin workflow by calling internal methods directly.

.. autoclass:: inmanta.execute.proxy.DynamicProxy()
    :members: return_value, unwrap
    :undoc-members:

Rest API
---------

The rest API is also available as a `swagger spec <openapi.html#http://>`_

The (v2) API endpoints that offer paging, sorting and filtering follow a convention.
They share the following parameters:

limit
    specifies the page size, so the maximum number of items returned from the query
start and first_id
    These parameters define the lower limit for the page,
end and last_id
    These parameters define the upper limit for the page
    (only one of the (`start`, `first_id`), (`end`, `last_id`) pairs should be specified at the same time).

.. note:: The return value of these methods contain a `links` tag, with the urls of the `next` and `prev` pages, so for simply going through the pages a client only needs to follow these links.

filter
    The `filter` parameter is used for filtering the result set.

    Filters should be specified with the syntax `?filter.<filter_key>=value`.

    It's also possible to provide multiple values for the same filter, in this case results are returned,
    if they match any of these filter values: `?filter.<filter_key>=value&filter.<filter_key>=value2`

    Multiple different filters narrow the results however (they are treated as an 'AND' operator).
    For example `?filter.<filter_key>=value&filter.<filter_key2>=value2` returns results that match both filters.

    The documentation of each method describes the supported filters.

sort
    The sort parameter describes how the result set should be sorted.

    It should follow the pattern `?<attribute_to_sort_by>.<order>`, for example `?value.desc` (case insensitive).

    The documentation of each method describes the supported attributes to sort by.

.. automodule:: inmanta.protocol.methods
    :members:

.. automodule:: inmanta.protocol.methods_v2
    :members:
