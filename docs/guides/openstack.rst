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




Pushing config to the machine
----------------------------------


config::
    #put a file on the machine
    std::ConfigFile(hosts = host1, path="/tmp/test", content="I did it!")


Actual usage
----------------------------------

In practice, creating instances of `vm::Host` is not practical: it takes too many parameters and they are often the same.

Models using an IaaS are usually build around two user defined types: a custom infrastructure object and a custom host object.
The infrastructure object collects all system wide config (such as the ``vm::IaaS`` object, monitoring cluster, networks, global parameters,...)
The host object contains all seeting that are the same for all hosts.

For example

.. literalinclude:: ../examples/openstackClean.snip
   :language: ruby

