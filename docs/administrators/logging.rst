.. _administrators_doc_logging:


*******
Logging
*******

This page describes the different logs files produced by the Inmanta server and its agents and explains what can be
configured regarding to logging.


Overview different log files
============================

By default log files are collected in the directory ``/var/log/inmanta/``. Three different types of log files exist: the
server log, the resources action logs and the agent logs. The server log and the resource action log files are produced by
the Inmanta server. The agent log files are produces by the Inmanta agents.


Server log
----------

The ``server.log`` file contains general debugging information regarding the Inmanta server. It shows information about actions
performed by the Inmanta server (renewing parameters, purging resource action logs, etc.), API requests received by the
Inmanta server, etc.


Resource action logs
--------------------

The resource action log files contain information about actions performed on a specific resource. Each environment has one
resource action log file. The filename of this log file looks as follows:
``<server.resource-action-log-prefix>-<environment-id>.log``. The prefix can be configured with the configuration option
:inmanta.config:option:`server.resource-action-log-prefix`.

The resource action log file contains information about the following resource action:

* **Store**: A new version of a configuration model and its resources has been pushed to the Inmanta server.
* **Pull**: An agent pulled its resources from the Inmanta server.
* **Deploy**: When an agent starts and ends the deployment of a certain resource.
* **Dryrun**: Execute a dryrun for a certain resource.


Agent logs
----------

One agent produces the following three log files:

* ``agent-<environment-id>.log``: This is the main log file of an agent. It contains information about when the agent
  started a deployment, which trigger caused that deployment, whether heartbeat messages are received from the server,
  whether the agent is a primary agent, etc.
* ``agent-<environment-id>.out``: This log file contains all the messages written to the standard output stream of the resource
  handlers used by the agent.
* ``agent-<environment-id>.err``: This log file contains all the messages written to the standard error stream of the resource
  handlers used by the agent.


Configure logging
=================

Configuration options in Inmanta config file
--------------------------------------------

The following log-related options can be set in an Inmanta config file:

* ``log-dir``
* ``purge-resource-action-logs-interval``
* ``resource-action-log-prefix``

Documentation on these options can be found in the :ref:`Inmanta configuration reference<config_reference>`.


Change log levels server log
----------------------------

Edit the ``--log-file-level`` option in the ExecStart command of the inmanta-server service file. The inmanta-server service
file can be found at ``/usr/lib/systemd/system/inmanta-server.service``.

.. code-block:: text

  [Unit]
  Description=The server of the Inmanta platform
  After=network.target

  [Service]
  Type=simple
  User=inmanta
  Group=inmanta
  ExecStart=/usr/bin/inmanta --log-file /var/log/inmanta/server.log --log-file-level 2 --timed-logs server
  Restart=on-failure

  [Install]
  WantedBy=multi-user.target

The ``--log-file-level`` takes the log-level as an integer, where ``0=ERROR``, ``1=WARNING``, ``2=INFO`` and ``3=DEBUG``.

Apply the changes by reloading the service file and restarting the Inmanta server:

.. code-block:: sh

  sudo systemctl daemon-reload inmanta-server
  sudo systemctl restart inmanta-server


Log level manually started agent
--------------------------------

The log level of a manually started agent can be changed in the same way as changing the log level of the Inmanta server. The
service file for a Inmanta agent can be found at ``/usr/lib/systemd/system/inmanta-agent.service``.


Log level auto-started agents
-----------------------------

The default log level of an auto-started agent is INFO. Currently it's not possible to change this log level.


Resource action logs
--------------------

The log level of the resource action log file is DEBUG. Currently it's not possible to change this log level.


Log level server-side compiles
------------------------------

The logs of a server side compile can be seen via the "Compile Reports" button in the web-console. The log level of these logs is
DEBUG. Currently, it's not possible to change this log level.


Log level on CLI
----------------

By default logs are written to standard output when the ``inmanta`` or the ``inmanta-cli`` command is executed. The default
log level is INFO. The log level of these commands can be changed by passing the correct number of v's with the option
``-v``.

* ``-v = warning``
* ``-vv = info``
* ``-vvv = debug``
* ``-vvvv = traces``

By specifying the ``-X`` option, stacktraces are also shown written to standard output when an error occurs. When the
``--log-file`` option is specified on the commandline, logs are written to file instead of the standard output.
