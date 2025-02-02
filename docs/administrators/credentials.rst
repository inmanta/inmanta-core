.. _env_vars:

Environment variables
=====================

The Inmanta server, installed from RPM, loads the environment variables specified in ``/etc/sysconfig/inmanta-server`` at startup. The example
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

