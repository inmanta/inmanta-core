.. _config_reference:

Configuration Reference
============================

This document lists all configuration options for the inmanta application and extensions.

Setting a value for an option can be done via a config file or by setting the associated
environment variable following the ``INMANTA_<section_name>_<option_name>`` naming scheme
(In all caps and any hyphens replaced by underscores).

For example, setting the database connection timeout can be set either in a config file:


.. code-block:: yaml

    [database]
    connection-timeout=60

Or, equivalently, by passing this configuration option as an environment variable:

.. code-block:: bash

    export INMANTA_DATABASE_CONNECTION_TIMEOUT=60



If an option is set in multiple places, the following precedence rules apply:



The options are listed per config section

.. show-options::
    :namespace-files: ./config-namespaces/all.conf
