Developing South Bound Integrations
**********************************************

The inmanta orchestrator comes with a set of integrations with different platforms (see: :ref:`ref-modules`).
But it is also possible to develop your own south bound integrations.

To integrate a new platform into the orchestrator, you must take the following steps:

1. Create a new module to contain the integration (see: :ref:`moddev-module`).
2. Model the target platform as set of :term:`entities<entity>`.
3. Create :term:`resources<resource>` and :term:`handler<handler>`, as described below.

Overview
^^^^^^^^
A South Bound integration always consists of three parts:
  * one or more :term:`entities<entity>` in the model
  * a :term:`resource<resource>` that serializes the entities and captures all information required to enforce the :term:`desired state`.
  * a :term:`handler<handler>`: the python code required to enforce the desired state.

.. image:: images/handler_flow.*

* In the *compiler*, a model is constructed that consists of entities. The entities can be related to each other.
* The *exporter* will search for all :term:`entities<entity>` that can be directly deployed by a :term:`handler<handler>`. These are the :term:`resources<resource>`. Resources are self-contained and can not refer to any other entity or resource.
* The :term:`resources<resource>` will be sent to the server in json serialized form.
* The :term:`resource scheduler` will spawn :term:`executors<executor>` that will load the :term:`handler<handler>` code in order to enforce the :term:`desired state` on the managed infrastructure.


.. _resources:

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

..
    This uses std::File, which is to be removed, but it re-constructs it, so that is OK

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

Handlers should inherit the class :class:`~inmanta.agent.handler.CRUDHandler`. The
:func:`@provider<inmanta.agent.handler.provider>` decorator registers the class with the orchestrator.

Each Handler should override 4 methods of the CRUDHandler:

1. :meth:`~inmanta.agent.handler.CRUDHandler.read_resource` to read the current state of the system.
2. :meth:`~inmanta.agent.handler.CRUDHandler.create_resource` to create the resource if it doesn't exist.
3. :meth:`~inmanta.agent.handler.CRUDHandler.update_resource` to update the resource when required.
4. :meth:`~inmanta.agent.handler.CRUDHandler.delete_resource` to delete the resource when required.

The context (See :class:`~inmanta.agent.handler.HandlerContext`) passed to most methods is used to
report results, changes and logs to the handler and the server.


.. _Using facts:

Using facts
"""""""""""

Facts are properties of the environment whose values are not managed by the orchestrator.
Facts are either used as input in a model, e.g. a virtual machine provider provides an ip and the model then uses this
ip to run a service, or used for reporting purposes.

Retrieving a fact in the model is done with the `std::getfact() <../reference/modules/std.html#std.getfact>`_
function.

Example taken from the `openstack Inmanta module <https://github.com/inmanta/openstack>`_:

.. code-block:: inmanta
    :linenos:

    implementation fipAddr for FloatingIP:
        self.address = std::getfact(self, "ip_address")
    end

Facts can be pushed or pulled through the handler.

---------


Pushing a fact is done in the handler with the :meth:`~inmanta.agent.handler.HandlerContext.set_fact`
method during resource deployment (in ``read_resource`` and/or ``create_resource``). e.g.:

.. code-block:: python
    :linenos:

    @provider("openstack::FloatingIP", name="openstack")
    class FloatingIPHandler(OpenStackHandler):
        def read_resource(
            self, ctx: handler.HandlerContext, resource: FloatingIP
        ) -> None: ...

        def create_resource(
            self, ctx: handler.HandlerContext, resource: FloatingIP
        ) -> None:
            ...
            # Setting fact manually
            for key, value in ...:
                ctx.set_fact(fact_id=key, value=value, expires=True)



By default, facts expire when they have not been refreshed or updated for a certain time, controlled by the
:inmanta.config:option:`server.fact-expire` config option. Querying for an expired fact will force the
agent to refresh it first.

When reporting a fact, setting the ``expires`` parameter to ``False`` will ensure that this fact never expires. This
is useful to take some load off the agent when working with facts whose values never change. On the other hand, when
working with facts whose values are subject to change, setting the ``expires`` parameter to ``True`` will ensure
they are periodically refreshed.

---------

Facts are automatically pulled periodically (this time interval is controlled by the
:inmanta.config:option:`server.fact-renew` config option) when they are about to expire or if a model requested them
and they were not present. The server periodically asks the agent to call into the
handler's :meth:`~inmanta.agent.handler.CRUDHandler.facts` method. e.g.:


.. code-block:: python
    :linenos:

    @provider("openstack::FloatingIP", name="openstack")
    class FloatingIPHandler(OpenStackHandler):
        ...

        def facts(self, ctx, resource):
            port_id = self.get_port_id(resource.port)
            fip = self._neutron.list_floatingips(port_id=port_id)["floatingips"]
            if len(fip) > 0:
                ctx.set_fact("ip_address", fip[0]["floating_ip_address"])



.. warning::
    If you ever push a fact that does expire, make sure it is also returned by the handler's ``facts()`` method.
    If you omit to do so, when the fact eventually expires, the agent will keep on trying to refresh it unsuccessfully.

.. note::
    Facts should not be used for things that change rapidly (e.g. cpu usage),
    as they are not intended to refresh very quickly.

Built-in Handler utilities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :term:`Inmanta Agent<agent>`, responsible for executing handlers has built-in utilities to help
handler development. This section describes the most important ones.

Logging
"""""""

The agent has a built-in logging facility, similar to the standard python logger. All logs written
to this logger will be sent to the server and are available via the web-console and the API.
Additionally, the logs go into the agent's logfile and into the resource-action log on the server.

To use this logger, use one of the methods: :py:meth:`ctx.debug<inmanta.agent.handler.HandlerContext.debug>`,
:py:meth:`ctx.info<inmanta.agent.handler.HandlerContext.info>`,
:py:meth:`ctx.warning<inmanta.agent.handler.HandlerContext.warning>`,
:py:meth:`ctx.error<inmanta.agent.handler.HandlerContext.error>`,
:py:meth:`ctx.critical<inmanta.agent.handler.HandlerContext.critical>` or
:py:meth:`ctx.exception<inmanta.agent.handler.HandlerContext.exception>`.

This logger implements the `~inmanta.agent.handler.LoggerABC` logging interface and supports kwargs.
The kwargs have to be json serializable. They will be available via the API in their json structured form.

For example:

.. code-block:: python

    def create_resource(self, ctx: HandlerContext, resource: ELB) -> None:
        # ...
        ctx.debug("Creating loadbalancer with security group %(sg)s", sg=sg_id)


An alternative implementation of the `~inmanta.agent.handler.LoggerABC` logging interface that just
logs to the Python logger is provided in `~inmanta.agent.handler.PythonLogger`. This logger is not
meant to be used in actual handlers but it can be used for the automated testing of helper methods
that accept a `~inmanta.agent.handler.LoggerABC` instance. In production, these helpers would receive
the actual :class:`~inmanta.agent.handler.HandlerContext` and log appropriately, while for testing the
`PythonLogger` can be passed.

Caching
"""""""

The agent maintains a cache, that is kept over handler invocations. It can, for example, be used to
cache a connection, so that multiple resources on the same device can share a connection.



The cache can be used through the :py:func:`@cache<inmanta.agent.handler.cache>` decorator. Any
method annotated with this annotation will be cached, similar to the way
`lru_cache <https://docs.python.org/3/library/functools.html#functools.lru_cache>`_ works. The arguments to
the method will form the cache key, the return value will be cached. When the method is called a
second time with the same arguments, it will not be executed again, but the cached result is
returned instead. To exclude specific arguments from the cache key, use the ``ignore`` parameter.

Cache entries will be dropped from the cache when they become stale. Use the following parameters to set the retention policy:
  * ``evict_after_creation``: mark entries as stale after this amount of time (in seconds) has elapsed since they entered the cache.
  * ``evict_after_last_access``: mark entries as stale after this amount of time (in seconds) has elapsed since they were last accessed (60 by default).


.. note::

    If both ``evict_after_creation=True`` and ``evict_after_last_access=True`` are set,
    the entry will become stale when the shortest of the two timers is up.


For example, to cache the connection to a specific device for 120 seconds:

.. code-block:: python

    @cache(ignore=["ctx"], evict_after_creation=120)
    def get_client_connection(self, ctx, device_id):
        # ...
        return connection


Setting ``evict_after_last_access=60`` (or omitting the parameter) will evict
the connection from the cache 60s after it was last read from the cache.

.. code-block:: python

    @cache(ignore=["ctx"])
    def get_client_connection(self, ctx, device_id, version):
        # ...
        return connection

To also ensure the connection is properly closed, an ``on_delete`` function can be passed
via the ``call_on_delete`` parameter. This function is called when the cache entry is removed
from the cache. It gets the cached item as argument.


.. code-block:: python

    @cache(
        ignore=["ctx"],
        evict_after_last_access=60,
        call_on_delete=lambda connection: connection.close(),
    )
    def get_client_connection(self, ctx, device_id, version):
        # ...
        return connection
