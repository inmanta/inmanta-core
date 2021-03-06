South Bound Integration
***********************

The inmanta orchestrator comes with a set of integrations with different platforms (see: :ref:`ref-modules`).
But it is also possible to develop your own south bound integrations.

To integrate a new platform into the orchestrator, you must take the following steps:

1. Create a new module to contain the integration (see: :ref:`moddev-module`).
2. Model the target platform as set of :term:`entities<entity>`.
3. Create :term:`resources<resource>` and :term:`handler<handler>`, as described below.

A :term:`resource<resource>` defines how to serialize an :term:`entity` so that it can be sent
over to the server and the agent. A :term:`handler<handler>` is the python code required by the
agent to enforce the :term:`desired state` expressed by a resource.


Resource
^^^^^^^^
A resource is represented by a Python class that is registered with Inmanta using the
:func:`@resource<inmanta.resources.resource>` decorator. This decorator decorates a class that inherits from
the :class:`~inmanta.resources.Resource` class.

The fields of the resource are indicated with a ``fields`` field in the class. This field is a tuple
or list of strings with the name of the desired fields of the resource. The orchestrator uses these
fields to determine which attributes of the matching entity need to be included in the resource.

Fields of a resource cannot refer to an instance in the orchestration model or fields of other
resources. The resource serializers allows to map field values. Instead of referring directly to an
attribute of the entity it serializes (path in std::File and path in the resource map one on one).
This mapping is done by adding a static method to the resource class with ``get_$(field_name)`` as
name. This static method has two arguments: a reference to the exporter and the instance of the
entity it is serializing.


.. code-block:: python
    :linenos:

    from inmanta.resources import resource, Resource

    @resource("std::File", agent="host.name", id_attribute="path")
    class File(Resource):
        fields = ("path", "owner", "hash", "group", "permissions", "purged", "reload")

        @staticmethod
        def get_hash(exporter, obj):
            hash_id = md5sum(obj.content)
            exporter.upload_file(hash_id, obj.content)
            return hash_id

        @staticmethod
        def get_permissions(_, obj):
            return int(x.mode)


Classes decorated with :func:`@resource<inmanta.resources.resource>` do not have to inherit directly from
:class:`~inmanta.resources.Resource`. The orchestrator already offers two additional base classes with fields and mappings
defined: :class:`~inmanta.resources.PurgeableResource` and
:class:`~inmanta.resources.ManagedResource`. This mechanism is useful for resources that have fields
in common.

A resource can also indicate that it has to be ignored by raising the
:class:`~inmanta.resources.IgnoreResourceException` exception.

Handler
^^^^^^^
Handlers interface the orchestrator with resources in the :term:`infrastructure`.
Handlers take care of changing the current state of a resource to the desired state expressed in the
orchestration model.

The compiler collects all python modules from Inmanta modules that provide handlers and uploads them
to the server. When a new orchestration model version is deployed, the handler code is pushed to all
agents and imported there.

Handlers should inherit the class :class:`~inmanta.agent.handler.ResourceHandler`. The
:func:`@provider<inmanta.agent.handler.provider>` decorator registers the class with the orchestrator. When the
agent needs a handler for a resource it will load all handler classes registered for that resource
and call the :meth:`~inmanta.agent.handler.ResourceHandler.available` method. This method should check
if all conditions are fulfilled to use this handler. The agent will select a handler, only when a
single handler is available, so the :meth:`~inmanta.agent.handler.ResourceHandler.available` method of all handlers of a resource need to be
mutually exclusive. If no handler is available, the resource will be marked unavailable.

:class:`~inmanta.agent.handler.ResourceHandler` is the handler base class.
:class:`~inmanta.agent.handler.CRUDHandler` provides a more recent base class that is better suited
for resources that are manipulated with Create, Delete or Update operations. These operations often
match managed APIs very well. The CRUDHandler is recommended for new handlers unless the resource
has special resource states that do not match CRUD operations.

Each handler basically needs to support two things: reading the current state and changing the state
of the resource to the desired state in the orchestration model. Reading the state is used for dry
runs and reporting. The CRUDHandler handler also uses the result to determine whether create, delete
or update needs to be invoked.

The context (See :class:`~inmanta.agent.handler.HandlerContext`) passed to most methods is used to
report results, changes and logs to the handler and the server.

Built-in Handler utilities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :term:`Inmanta Agent<agent>`, responsible for executing handlers has built-in utilities to help
handler development. This section describes the most important ones.

Logging
"""""""

The agent has a built-in logging facility, similar to the standard python logger. All logs written
to this logger will be sent to the server and are available via the dashboard and the API. 
Additionally, the logs go into the agent's logfile and into the resource-action log on the server. 

To use this logger, use one of the methods: :py:meth:`ctx.debug<inmanta.agent.handler.HandlerContext.debug>`,
:py:meth:`ctx.info<inmanta.agent.handler.HandlerContext.info>`,
:py:meth:`ctx.warning<inmanta.agent.handler.HandlerContext.warning>`,
:py:meth:`ctx.error<inmanta.agent.handler.HandlerContext.error>`,
:py:meth:`ctx.critical<inmanta.agent.handler.HandlerContext.critical>` or
:py:meth:`ctx.exception<inmanta.agent.handler.HandlerContext.exception>`.

This logger supports kwargs. The kwargs have to be json serializable. They will be available via the API in their json structured form.

For example:

.. code-block:: python

    def create_resource(self, ctx: HandlerContext, resource: ELB) -> None:
        # ...
        ctx.debug("Creating loadbalancer with security group %(sg)s", sg=sg_id)


Caching
"""""""

The agent maintains a cache, that is kept over handler invocations. It can, for example, be used to
cache a connection, so that multiple resources on the same device can share a connection.

The cache can be invalidated either based on a timeout or on version. A timeout based cache is kept
for a specific time. A version based cache is used for all resource in a specific version.
The cache will be dropped when the deployment for this version is ready.

The cache can be used through the :py:func:`@cache<inmanta.agent.handler.cache>` decorator. Any
method annotated with this annotation will be cached, similar to the way
`lru_cache <https://docs.python.org/3/library/functools.html#functools.lru_cache>`_ works. The arguments to
the method will form the cache key, the return value will be cached. When the method is called a
second time with the same arguments, it will not be executed again, but the cached result is
returned instead. To exclude specific arguments from the cache key, use the `ignore` parameter.


For example, to cache the connection to a specific device for 120 seconds:

.. code-block:: python

    @cache(timeout=120, ignore=["ctx"])
    def get_client_connection(self, ctx, device_id):
       # ...
       return connection

To do the same, but additionally also expire the cache when the next version is deployed, the method must have a parameter called `version`.
`for_version` is True by default, so when a version parameter is present, the cache is version bound by default.

.. code-block:: python

    @cache(timeout=120, ignore=["ctx"], for_version=True)
    def get_client_connection(self, ctx, device_id, version):
       # ...
       return connection

To also ensure the connection is properly closed, an `on_delete` function can be attached. This
function is called when the cache is expired. It gets the cached item as argument.


.. code-block:: python

    @cache(timeout=120, ignore=["ctx"], for_version=True,
       call_on_delete=lambda connection:connection.close())
    def get_client_connection(self, ctx, device_id, version):
       # ...
       return connection
