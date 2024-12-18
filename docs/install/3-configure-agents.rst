.. _configure_agents:

Configure agents
****************

Inmanta agents can be started automatically (auto-started agents) or manually (manually-started agents). This section
describes how both types of agents can be set up and configured. Inmanta agents only run on Linux.


Auto-started agents
-------------------

Auto-started agents always run on the Inmanta server. The Inmanta server manages the full lifecycle of these agents.


Configuring auto-started agents via environment settings
========================================================

Auto-started agents can be configured via the settings of the environment where the auto-started agent belongs to. The
following options are configurable:

* :inmanta.environment-settings:setting:`autostart_agent_map`
* :inmanta.environment-settings:setting:`autostart_agent_deploy_interval`
* :inmanta.environment-settings:setting:`autostart_agent_deploy_splay_time`
* :inmanta.environment-settings:setting:`autostart_agent_repair_interval`
* :inmanta.environment-settings:setting:`autostart_agent_repair_splay_time`
* :inmanta.environment-settings:setting:`autostart_on_start`

The :inmanta.environment-settings:setting:`autostart_agent_map` requires an entry for each agent that should be autostarted.
The key is the name of the agent and the value is either ``local:`` for agents that map to the Inmanta server or an SSH
connection string when the agent maps to a remote machine. The SSH connection string requires the following format:
``ssh://<user>@<host>:<port>?<options>``. Options is a ampersand-separated list of ``key=value`` pairs. The following options
can be provided:

===========  =============  =====================================================================================================================
Option name  Default value  Description
===========  =============  =====================================================================================================================
retries      10             The amount of times the orchestrator will try to establish the SSH connection when the initial attempt failed.
retry_wait   30             The amount of second between two attempts to establish the SSH connection.
python       python         The Python3 interpreter available on the remote side. This executable has to be discoverable through the system PATH.
===========  =============  =====================================================================================================================


Auto-started agents start when they are required by a specific deployment or when the Inmanta server starts if the
:inmanta.environment-settings:setting:`autostart_on_start` setting is set to true. When the agent doesn't come up when required,
consult the :ref:`troubleshooting documentation<agent_doesnt_come_up>` to investigate the root cause of the issue.


Configuring the autostart_agent_map via the std::AgentConfig entity
===================================================================

The :inmanta:entity:`std::AgentConfig` entity provides functionality to add an entry to the
:inmanta.environment-settings:setting:`autostart_agent_map` of a specific environment. As such, the auto-started agents can be
managed in the configuration model.

Special Requirements for remote std::File, std::Package, std::Service and exec::Run
===================================================================================

..
    This refers to std::File and others, which are to be removed, but it is explicitly only about them, so this will be removed with it

When using the agents built-in ssh capability, to perform actions over ssh on remote hosts, the following requirements must be met:

* The Inmanta server should have passphraseless SSH access on the machine it maps to. More information on how to set up SSH
  connectivity can be found at :ref:`configure_server_step_6`
* The remote machine should have a Python 2 or 3 interpreter installed. The binary executed by default is ``python``.
* The user to log into the remote machine should either be ``root`` or have the ability to do a passwordless sudo.
  To enable passwordless sudo for the user ``username``, add a file to ``/etc/sudoers.d/`` containing ``username ALL=(ALL) NOPASSWD: ALL``.
  It is advisable to use a safe editor such as ``visudo`` or ``sudoedit`` for this. For more details, go `here <https://www.sudo.ws/man/sudoers.man.html>`_.


Manually-started agents
-----------------------

Manually started agents can be run on any Linux device, but they should be started and configured manually as the name
suggests.

Requirements
============

The following requirements should be met for agents that don't map to the host running the agent process (i.e. The managed
device is remote with respect to the Inmanta agent and the agent has to execute I/O operations on the remote machine using
``self._io``):

* The Inmanta agent should have passphraseless SSH access on the machine it maps to. More information on how to set up SSH
  connectivity can be found at :ref:`configure_server_step_6`
* The remote machine should have a Python 2 or 3 interpreter installed. The binary executed by default is ``python``.



Step 1: Installing the required Inmanta packages
================================================

.. only:: oss

    In order to run a manually started agent, the ``inmanta-oss-agent`` package is required on the
    machine that will run the agent.

    .. code-block:: sh
        :substitutions:

        sudo tee /etc/yum.repos.d/inmanta-oss-stable.repo <<EOF
        [inmanta-oss-stable]
        name=Inmanta OSS stable
        baseurl=https://packages.inmanta.com/public/oss-stable/rpm/el/\$releasever/\$basearch
        gpgcheck=1
        gpgkey=https://packages.inmanta.com/public/oss-stable/gpg.|oss_gpg_key|.key
        repo_gpgcheck=1
        enabled=1
        enabled_metadata=1
        EOF

        sudo dnf install -y inmanta-oss-agent

.. only:: iso

    In order to run a manually started agent, the ``inmanta-service-orchestrator-agent`` package is required on the
    machine that will run the agent.

    .. code-block:: sh
       :substitutions:

        sudo tee /etc/yum.repos.d/inmanta.repo <<EOF
        [inmanta-service-orchestrator-|version_major|-stable]
        name=inmanta-service-orchestrator-|version_major|-stable
        baseurl=https://packages.inmanta.com/<token>/inmanta-service-orchestrator-|version_major|-stable/rpm/el/8/$basearch
        gpgcheck=1
        gpgkey=https://packages.inmanta.com/<token>/inmanta-service-orchestrator-|version_major|-stable/cfg/gpg/gpg.|iso_gpg_key|.key
        repo_gpgcheck=1
        enabled=1
        enabled_metadata=1
        EOF

        sudo dnf install -y inmanta-service-orchestrator-agent

    Replace ``<token>`` with the token provided with your license.


Step 2: Configuring the manually-started agent
==============================================

The manually-started agent can be configured via a ``/etc/inmanta/inmanta.d/*.cfg`` config file. The following options
configure the behavior of the manually started agent:

* :inmanta.config:option:`config.state-dir`
* :inmanta.config:option:`config.environment`
* :inmanta.config:option:`config.agent-deploy-splay-time`
* :inmanta.config:option:`config.agent-deploy-interval`
* :inmanta.config:option:`config.agent-repair-splay-time`
* :inmanta.config:option:`config.agent-repair-interval`
* :inmanta.config:option:`config.agent-reconnect-delay`
* :inmanta.config:option:`config.server-timeout`
* :inmanta.config:option:`agent_rest_transport.port`
* :inmanta.config:option:`agent_rest_transport.host`
* :inmanta.config:option:`agent_rest_transport.token`
* :inmanta.config:option:`agent_rest_transport.ssl`
* :inmanta.config:option:`agent_rest_transport.ssl-ca-cert-file`

The agent will follow the pip configuration defined in the :ref:`project_yml`. Make sure it can access the pip
index configured by the project (See the `pip documentation for netrc <https://pip.pypa.io/en/stable/topics/authentication/#netrc-support>`_ for more information on how to setup authentication).

The :inmanta.config:option:`config.agent-map` option can be configured in the same way as the ``autostart_agent_map`` for
auto-started agents.


Step 3: Starting the manually-started agent
===========================================

Finally, enable and start the ``inmanta-agent`` service:

.. code-block:: sh

    sudo systemctl enable inmanta-agent
    sudo systemctl start inmanta-agent


The logs of the agent are written to ``/var/log/inmanta/agent.log``. When the agent doesn't come up after starting the
``inmanta-agent`` service, consult the :ref:`troubleshooting documentation<agent_doesnt_come_up>` to investigate the root cause of
the issue.
