.. _administrators_doc_logging:


*******
Logging
*******

This page describes the different logs files produced by the Inmanta server and its agents and explains what can be
configured regarding to logging.


Overview different log files
============================

By default log files are collected in the directory ``/var/log/inmanta/``. Three different types of log files exist: the
server log, the resource action logs and the agent logs. The server log and the resource action log files are produced by
the Inmanta server. The agent log files are produced by the Inmanta agents.


Server log
----------

The ``server.log`` file contains general debugging information regarding the Inmanta server. It shows information about actions
performed by the Inmanta server (renewing parameters, purging resource action logs, etc.), API requests received by the
Inmanta server, etc.


Resource action logs
--------------------

The resource action log files contain information about actions performed on a specific resource. Each environment has one
resource action log file. The filename of this log file looks as follows:
``resource-actions-<environment-id>.log``. The prefix can be configured with the configuration option
:inmanta.config:option:`server.resource-action-log-prefix`.

The resource action log file contains information about the following resource action:

* **Store**: A new version of a configuration model and its resources has been pushed to the Inmanta server.
* **Pull**: An agent pulled its resources from the Inmanta server.
* **Deploy**: When an agent starts and ends the deployment of a certain resource.
* **Dryrun**: Execute a dryrun for a certain resource.


Scheduler logs
--------------

For every environment, the scheduler produces the following three log files:

* ``agent-<environment-id>.log``: This is the main log file of an scheduler. It contains information about when any executor
  started a deployment, which trigger caused that deployment, whether heartbeat messages are received from the server, etc.
* ``agent-<environment-id>.out``: This log file contains all the messages written to the standard output stream of the resource
  handlers used by the scheduler.
* ``agent-<environment-id>.err``: This log file contains all the messages written to the standard error stream of the resource
  handlers used by the scheduler.

For reasons of backward comaptiblity, these files are called 'agent' and not 'scheduler'

Configure logging
=================

Logging can be configured in two main way:
- course grained configuration using configuration and command line options. This is sufficient in most cases.
- fine grained configuration using a config file. Here the logging config is fully user controlled.



Course grained configuration
----------------------------

The following log-related options can be set in an Inmanta config file:

* :inmanta.config:option:`config.log-dir`: determines the folder that will contain the log files

:ref:`As command line options,<reference_commands_inmanta>` the following are available:

* ``--timed-logs``: Add timestamps to logs
* ``--log-file``: Path to the logfile, enables logging to file, disables logging to console
* ``--log-file-level``: Log level for messages going to the logfile, options  `ERROR`, `WARNING`, `INFO`, `DEBUG`, `TRACE`
* ``-v``: Log level for messages going to the console. Default is warnings only. -v warning, -vv info, -vvv debug and -vvvv trace.
* ``-X``: When exiting with an error, show full stack trace.
* ``--keep-logger-names``: When using the compiler, don't shorten logger names

To update the server startup config when using the RPM based install, edit the inmanta-server service
file at ``/usr/lib/systemd/system/inmanta-server.service``.

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

For fine grained configuration, `a standard python dict config file<https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig>` can be passed in via the config file for each component individually or via a cli option:

.. code-block:: yaml

    [logging]
    server = server_log.yml
    scheduler = scheduler.log.tmpl
    compiler = compiler.yml

or

.. code-block:: sh

    inmanta --logging-config server_log.yml server


The log config has to be either a `yaml` file, containing `python dict config<https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig>` or a template of a `yaml` file. In this case, the file name has to end with `tmpl`.

The following log-related options can be set in an Inmanta config file:

* :inmanta.config:option:`logging.compiler`: determines the log config for the compiler
* :inmanta.config:option:`logging.server`: determines the log config for the server
* :inmanta.config:option:`logging.scheduler`: determines the log config for the scheduler. This is always a template.

:ref:`As command line options,<reference_commands_inmanta>` the following are available:

* ``-v``: When used in combination with a log file, it will force a CLI logger to be loaded on top of the provided configuration
* ``--logging-config``: Log configuration file for this command, overrides the config option

For templated config files, we use pythons f-string syntax.
For the scheduler, one variable is available in the template: `{environment}`. This is used to customize the scheduler log files to the environment the scheduler is working for.

Converting to fine grained configuration
----------------------------------------

A tool is provided to convert the existing course grained configuration into a config file.

For example, to

.. code-block:: sh

    inmanta -c /etc/inmanta/inmanta.cfg --log-file /var/log/inmanta/server.log --log-file-level 2 --timed-logs print_default_logging_config server

To convert the config for a component, take a the command you use to start it, then put `print_default_logging_config` before the `server`, `compiler` or `scheduler`


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



