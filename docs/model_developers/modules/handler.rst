Resources and handlers
**********************

A module can add additional :term:`resources<resource>` and/or handlers for resources to Inmanta. A
resource defines a type that resembles an :term:`entity` but without any relations. This is required
for serializing resources for communication between the compiler, server and agents.

Resource
^^^^^^^^
A resource is represented by a Python class that is registered with Inmanta using the
:func:`~inmanta.resources.resource` decorator. This decorator decorates a class that inherits from
the :class:`~inmanta.resources.Resource` class.

The fields of the resource are indicated with a ``fields`` field in the class. This field is a tuple
or list of strings with the name of the desired fields of the resource. The orchestrator uses these
fields to determine which attributes of the matching entity need to be included in the resource.

Fields of a resource cannot refer to instance in the orchestration model or fields of other
resources. The resource serializers allows to map field values. Instead of referring directly to an
attribute of the entity is serializes (path in std::File and path in the resource map one on one).
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


Classes decorated with :func:`~inmanta.resources.resource` do not have to inherit directly from
Resource. The orchestrator already offers two additional base classes with fields and mappings
defined: :class:`~inmanta.resources.PurgeableResource` and
:class:`~inmanta.resources.ManagedResource`. This mechanism is useful for resources that have fields
in common.

A resource can also indicate that it has to be ignored by raising the
:class:`~inmanta.resources.IgnoreResourceException` exception.

Handler
^^^^^^^
Handlers interface the orchestrator with resources in the :term:`infrastructure` in the agents.
Handlers take care of changing the current state of a resource to the desired state expressed in the
orchestration model.

The compiler collects all python modules from Inmanta modules that provide handlers and uploads them
to the server. When a new orchestration module version is deployed, the handler code is pushed to all
agents and imported there.

Handlers should inherit the class :class:`~inmanta.agent.handler.ResourceHandler`. The
:func:`~inmanta.agent.handler.provider` decorator register the class with the orchestrator. When the
agent needs a handler for a resource it will load all handler classes registered for that resource
and call the :func:`~inmanta.agent.handler.ResourceHandler.available`. This method should check
if all conditions are fulfilled to use this handler. The agent will select a handler, only when a
single handler is available, so the is_available method of all handlers of a resource need to be
mutually exclusive. If no handler is available, the resource will be marked unavailable.

:class:`~inmanta.agent.handler.ResourceHandler` is the handler base class.
:class:`~inmanta.agent.handler.CRUDHandler` provides a more recent base class that is better suited
for resources that are manipulated with Create, Delete or Update operations. This operations often
match managed APIs very well. The CRUDHandler is recommended for new handlers unless the resource
has special resource states that do not match CRUD operations.

Each handler basically needs to support two things: reading the current state and changing the state
of the resource to the desired state in the orchestration model. Reading the state is used for dry
runs and reporting. The CRUDHandler handler also uses the result to determine whether create, delete
or update needs to be invoked.

The context (See :class:`~inmanta.agent.handler.HandlerContext`) passed to most methods is used to
report results, changes and logs to the handler and the server.
