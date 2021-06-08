Environment variables
=====================

Environment variables can be supplied to the Inmanta server and it's agents.


Supplying environment variables to the Inmanta server
-----------------------------------------------------

The Inmanta server loads the environment variables specified in ``/etc/sysconfig/inmanta-server`` at startup. The example
below defines three environment variables:

.. code-block:: sh

    OS_AUTH_URL=http://openstack.domain
    OS_USERNAME=admin
    OS_PASSWORD=sYOUZdhcgwctSmA

These environment variables are accessible in a configurationmodel via the ``std::get_env(name: "string", default_value:
"string"=None)`` plugin as shown in the following snippet:

.. code-block:: inmanta
    :linenos:

    import std
    import openstack

    provider = openstack::Provider(name="openstack",
                                   connection_url=std::get_env("OS_AUTH_URL"),
                                   username=std::get_env("OS_USERNAME"),
                                   password=std::get_env("OS_PASSWORD"),
                                   tenant="dev")


Supplying environment variables to an agent
-------------------------------------------

A manually started agent loads the environment variables specified in ``/etc/sysconfig/inmanta-agent`` at startup. This can
be useful when a handler relies on the value of a certain environment variable.
