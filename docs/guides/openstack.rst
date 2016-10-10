OpenStack
=========

This guide explains how to start virtual machines on OpenStack.

Prerequisites
------------------

This tutorial requires you to have an account on an OpenStack. The following parameters are required:

+---------------------+--------------------------------------------------------------------------+
| connection_url      | The Openstack connection URL                                             |
+---------------------+--------------------------------------------------------------------------+
| tenant              | Openstack tenant for your account                                        |
+---------------------+--------------------------------------------------------------------------+
| username            | Openstack username for your account                                      |
+---------------------+--------------------------------------------------------------------------+
| password            | Openstack password for your account                                      |
+---------------------+--------------------------------------------------------------------------+
| ssh_public_key      | Your public ssh key (the key ittself, not the name of the file it is in) |
+---------------------+--------------------------------------------------------------------------+
| network_name        | The name of the Openstack network to connect the VM to                   |
+---------------------+--------------------------------------------------------------------------+
| machine_flavor_name | The name of the Openstack machine flavor to create the VM from           |
+---------------------+--------------------------------------------------------------------------+
| image_id            | The ID of the Openstack image to boot the VM from                        |
+---------------------+--------------------------------------------------------------------------+
| os                  | The OS of the image (fedora, centos, rhel and ubuntu are supported)      |
+---------------------+--------------------------------------------------------------------------+

You can fill the parameter into the model below.

Creating machines
----------------------------------

.. literalinclude:: ../examples/openstack.snip
   :language: ruby

Getting the agent on the machine
----------------------------------

Once the machines are created, we want to inject the inmanta agent into them, and configure it to connect back to the management server. 
Do do this, we use the cloud-init facility of OpenStack. 

To inject the agent into fedora machines, you can use the following script:

.. literalinclude:: ../examples/user_data.tmpl
   :language: bash



Pushing config to the machine
----------------------------------

To install config::

    #put a file on the machine
    std::ConfigFile(hosts = host1, path="/tmp/test", content="I did it!")


Actual usage
----------------------------------

Creating instances of ``vm::Host``, as shown above is not practival: it takes too many parameters and polutes the model.
Instead, we use the capabilities of Inmanta to encapsulate this complexity.

When building larger models, it is best to create your own ``Host`` type. This type encapsulates all settings that are the same for all hosts.
Addtionally, if there is some shared infrastructure (such as the ``vm::IaaS`` object, monitoring clusters, shared networks, global parameters,...) it is best to make an infrastructure object. 

For example (full source is at https://github.com/inmanta/inmanta/tree/master/docs/examples/openstackclean)

We can reduce the main file to:

.. literalinclude:: ../examples/openstackclean/main.cf
   :language: ruby

With the following module:

.. literalinclude:: ../examples/openstackclean/libs/mymodule/model/_init.cf
   :language: ruby
   
If this were not an example, we would make the following changes:

* hardcode the ``image_id`` and ``os`` (and perhaps ``flavor``) into the defintion of ``myhost``. 
* the parameters on top would be moved to either a :doc:`form <forms>` or filled in directly into the constructor.
* use ``std::password`` to store passwords, to prevent accidential check-ins with passwords in the source

 
