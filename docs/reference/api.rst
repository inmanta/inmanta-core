Inmanta API reference
=====================

Plugins
-------

.. autoclass:: inmanta.plugins.Context
    :members:
    :undoc-members:

.. autofunction:: inmanta.plugins.plugin

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
