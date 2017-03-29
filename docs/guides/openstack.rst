OpenStack
=========

The openstack module provides support for managing various resources on OpenStack, including virtual
machines, networks, routers, ...

This guide explains how to start virtual machines on OpenStack.

Prerequisites
------------------

This tutorial requires you to have an account on an OpenStack. The example below loads the required
credentials from environment variables, just like the OpenStack command line tools. Additionally,
the following parameters are also required:

+---------------------+--------------------------------------------------------------------------+
| ssh_public_key      | Your public ssh key (the key itself, not the name of the file it is in)  |
+---------------------+--------------------------------------------------------------------------+
| network_name        | The name of the Openstack network to connect the VM to                   |
+---------------------+--------------------------------------------------------------------------+
| subnet_name         | The name of the Openstack subnet to connect the VM to                    |
+---------------------+--------------------------------------------------------------------------+
| network_address     | The network address of the subnet above                                  |
+---------------------+--------------------------------------------------------------------------+
| flavor_name         | The name of the Openstack flavor to create the VM from                   |
+---------------------+--------------------------------------------------------------------------+
| image_id            | The ID of the Openstack image to boot the VM from                        |
+---------------------+--------------------------------------------------------------------------+
| os                  | The OS of the image                                                      |
+---------------------+--------------------------------------------------------------------------+

The model below exposes these parameters at the top of the code snippet.

Creating machines
----------------------------------

.. literalinclude:: ../examples/openstack.snip
   :language: ruby


Getting the agent on the machine
----------------------------------

The user_data attribute of the openstack::Host entity can inject a shell script that is executed
at first boot of the virtual machine (through cloud-init). Below is an example script to install
the inmanta agent (from RPM) and let it connect back to the management server.

.. literalinclude:: ../examples/user_data.tmpl
   :language: bash


Pushing config to the machine
----------------------------------

To install config::

    #put a file on the machine
    std::ConfigFile(host = host1, path="/tmp/test", content="I did it!")


Actual usage
----------------------------------

Creating instances of ``openstack::Host``, as shown above requires many parameters and relations,
creating a model that is hard to read. Often, these parameters are all the same within a single
model. This means that Inmanta can encapsulate this complexity.

In a larger model, a new ``Host`` type can encapsulate all settings that are the same for all hosts.
Additionally, an entity that represents the `infrastructure` can hold shared configuration such as
the provider, monitoring, shared networks, global parameters,...)

For example (`full source here <https://github.com/inmanta/inmanta/tree/master/docs/examples/openstackclean>`_)

Applied to the example above the main file is reduced to:

.. literalinclude:: ../examples/openstackclean/main.cf
   :language: ruby

With the following module:

.. literalinclude:: ../examples/openstackclean/libs/mymodule/model/_init.cf
   :language: ruby

If this were not an example, we would make the following changes:

* hardcode the ``image_id`` and ``os`` (and perhaps ``flavor``) into the defintion of ``myhost``.
* the parameters on top would be moved to either a :doc:`form <forms>` or filled in directly into the constructor.
* use ``std::password`` to store passwords, to prevent accidential check-ins with passwords in the source


