.. _unmanaged_resources:

*******************
Unmanaged Resources
*******************


Unmanaged resources are resources that are part of the network but are not yet managed
by the Inmanta orchestrator. Automatic discovery of such resources can be used to perform
on-boarding of existing services for which corresponding resources were found, or to publish
compliance reports when auditing the network.

Terminology
===========

Unmanaged resource
------------------

A resource that is not yet managed on a network. In many cases this will be an
existing :term:`resource` type without any modifications.

Discovery resource
------------------

A meta-resource responsible for discovering a specific type of unmanaged resources.
Its :term:`handler` does not deploy anything in the network like
more conventional handlers would. Instead it is responsible for resource discovery

Model side
==========

The example below shows how to declare a discovery resource in the model:


.. literalinclude:: unmanaged_resources/basic_example.cf
    :language: inmanta
    :caption: main.cf

Handler implementation
======================

The snippet below shows an example implementation of a handler responsible for
a discovery resource.

.. literalinclude:: unmanaged_resources/handler_implementation.py
    :language: python
    :caption: handler_implementation.py
