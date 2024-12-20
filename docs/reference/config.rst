.. _config_reference:

Configuration Reference
============================

This document lists all configuration options for the inmanta application and extensions.

Setting a value for an option can be done via a config file or by setting the associated
environment variable following the ``INMANTA_<section_name>_<option_name>`` naming scheme
(In all caps and any hyphens replaced by underscores).

For example, setting the database connection timeout can be set either in a config file,
e.g. adding the following snippet inside ``/etc/inmanta/inmanta.cfg``:


.. code-block:: yaml

    [database]
    connection-timeout=60

Or, equivalently, by setting the environment variable associated with this configuration option prior
to starting the server:

.. code-block:: bash

    export INMANTA_DATABASE_CONNECTION_TIMEOUT=60

If an option is set both via a config file and via an environment variable,
the environment variable value will take precedence.

For more information about how to use the configuration framework and details
about precedence rules, please visit the administrator documentation configuration :ref:`page<configuration_framework>`.


The options are listed per config section

.. show-options::
    :namespace-files: ./config-namespaces/all.conf
