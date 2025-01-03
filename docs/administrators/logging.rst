.. _administrators_doc_logging:


*******
Logging
*******

This page describes the different logs files produced by the Inmanta server and its agents and explains what can be
configured regarding to logging.


Overview different log files
============================

By default log files are collected in the directory ``/var/log/inmanta/``.  The following files are expected:


1. ``server.log`` is the main log file of the server. It shows general information about actions performed by the Inmanta server (renewing parameters, purging resource action logs, etc.), and the access log of the API.
2. ``resource-actions-<environment-id>.log`` contains all actions performed by all resources. Each environment has one resource action log file. This file mirrors the actions logged on resources in the database.
3. ``agent-<environment-id>.log`` is the main log of the scheduler and executors. It contains information about when any executor started a deployment, which trigger caused that deployment, whether heartbeat messages are received from the server, etc.
4. ``agent-<environment-id>.out``: This log file contains all the messages written to the standard output stream of the scheduler and executors. Expected to be empty.
5. ``agent-<environment-id>.err``: This log file contains all the messages written to the standard error stream of the scheduler and executors. Expected to be empty.

For reasons of backward compatibility, the scheduler files are called 'agent' and not 'scheduler'


Configure logging
=================

Logging can be configured in two main ways:

- coarse grained configuration using configuration and command line options. This is sufficient in most cases.
- fine grained configuration using a config file. Here the logging config is fully user controlled.



Coarse grained configuration
----------------------------

The following log-related options can be set in an Inmanta config file:

* :inmanta.config:option:`config.log-dir`: determines the folder that will contain the log files

:ref:`As command line options,<reference_commands_inmanta>` the following are available:

* ``--timed-logs``: Add timestamps to logs
* ``--log-file``: Path to the logfile, enables logging to file, disables logging to console
* ``--log-file-level``: Log level for messages going to the logfile, options  `ERROR`, `WARNING`, `INFO`, `DEBUG` and `TRACE`
* ``-v``: Log level for messages going to the console. Default is warnings only. -v warning, -vv info, -vvv debug and -vvvv trace.
* ``-X``: When exiting with an error, show full stack trace.
* ``--keep-logger-names``: When using the compiler, don't shorten logger names.

To update the server startup config when using the RPM based install, copy the inmanta-server service
file at ``/usr/lib/systemd/system/inmanta-server.service`` to ``/etc/systemd/system/inmanta-server.service`` and edit it.

.. code-block:: text

  [Unit]
  Description=The server of the Inmanta platform
  After=network.target

  [Service]
  Type=simple
  User=inmanta
  Group=inmanta
  ExecStart=/usr/bin/inmanta --log-file /var/log/inmanta/server.log --log-file-level INFO --timed-logs server
  Restart=on-failure

  [Install]
  WantedBy=multi-user.target


.. code-block:: sh

  sudo systemctl daemon-reload
  sudo systemctl restart inmanta-server


Fine grained configuration
----------------------------
For fine grained configuration, `a standard python dict config file <https://docs.python.org/3/library/logging.config.html#logging-config-dictschema>`_ can be passed in via the config file for each component individually:

.. code-block:: ini

    [logging]
    server = server_log.yml
    scheduler = scheduler.log.tmpl
    compiler = compiler.yml

or via a cli option:

.. code-block:: sh

    inmanta --logging-config server_log.yml server


The log config has to be either a ``yaml`` file, containing a `python dict config <https://docs.python.org/3/library/logging.config.html#logging-config-dictschema>`_ or a template of a ``yaml`` file. In this case, the file name has to end with ``tmpl``.

The following log-related options can be set in an Inmanta config file:

* :inmanta.config:option:`logging.compiler`: determines the log config for the compiler.
* :inmanta.config:option:`logging.server`: determines the log config for the server
* :inmanta.config:option:`logging.scheduler`: determines the log config for the scheduler. This is always a template.

Each of the above-mentioned configurations can also be provided directly into an environment variable in the
following way:

* :inmanta.config:option:`config.logging-config`: ``INMANTA_CONFIG_LOGGING_CONFIG_CONTENT`` or ``INMANTA_CONFIG_LOGGING_CONFIG_TMPL``
* :inmanta.config:option:`logging.compiler`: ``INMANTA_LOGGING_COMPILER_CONTENT`` or ``INMANTA_LOGGING_COMPILER_TMPL``
* :inmanta.config:option:`logging.server`: ``INMANTA_LOGGING_SERVER_CONTENT`` or ``INMANTA_LOGGING_SERVER_TMPL``
* :inmanta.config:option:`logging.scheduler`: ``INMANTA_LOGGING_SCHEDULER_CONTENT`` or ``INMANTA_LOGGING_SCHEDULER_TMPL``

The ``_TMPL`` suffix indicates that the provided configuration is a template. The ``_CONTENT`` suffix indicates
a non-template configuration.

:ref:`As command line options,<reference_commands_inmanta>` the following are available:

* ``-v``: When used in combination with a log file, it will force a CLI logger to be loaded on top of the provided configuration
* ``--logging-config``: Log configuration file for this command, overrides the config option
* ``-X``: When exiting with an error, show full stack trace.
* If a config file is loaded, all other coarse grained configuration options are ignored!

For templated config files, we use python f-string syntax.
For the scheduler, one variable is available in the template: ``{environment}``. This is used to customize the scheduler log files to the environment the scheduler is working for.

Converting to fine grained configuration
----------------------------------------

A tool is provided to convert the existing coarse grained configuration into a config file.

For example, to convert the config for a component, take the command you use to start it, then put `print-default-logging-config` before the `server`, `compiler` or `scheduler`:

.. code-block:: sh

    inmanta -c /etc/inmanta/inmanta.cfg \
        --log-file /var/log/inmanta/server.log \
        --log-file-level INFO \
        --timed-logs \
        print-default-logging-config server



Default configurations
----------------------


.. only:: oss

    Default configuration for the server:

    .. literalinclude:: ../../misc/server_log.yml
        :linenos:
        :language: yaml
        :caption: server_log.yml


.. only:: iso

    Default configuration for the server, including LSM:

    .. literalinclude:: ../../misc/server_lsm_log.yml
        :linenos:
        :language: yaml
        :caption: server_log.yml



Default configuration for the scheduler:

.. literalinclude:: ../../misc/scheduler_log.yml.tmpl
        :linenos:
        :language: yaml
        :caption: scheduler_log.yml.tmpl



