Install Inmanta
****************
This page explain how to install the Inmanta orchestrator software and setup an orchestration server. Regardless what platform
you installed it on, Inmanta requires at least the latest Python 3.6 or 3.7 and git.

.. tabs::

    .. tab:: CentOS 7

        For CentOS use yum and install epel-release:

        .. code-block:: sh

          sudo tee /etc/yum.repos.d/inmanta_oss_stable.repo <<EOF
          [inmanta-oss-stable]
          name=Inmanta OSS stable
          baseurl=https://pkg.inmanta.com/inmanta-oss-stable/el7/
          gpgcheck=1
          gpgkey=https://pkg.inmanta.com/inmanta-oss-stable/inmanta-oss-stable-public-key
          repo_gpgcheck=1
          enabled=1
          enabled_metadata=1
          EOF

          sudo yum install -y epel-release
          sudo yum install -y python3-inmanta python3-inmanta-server python3-inmanta-agent

        The first package (python3-inmanta) contains all the code and the commands. The server and the agent packages install config
        files and systemd unit files. The dashboard is installed with the server package.


    .. tab:: Other Linux and Mac

        First make sure Python >= 3.6 and git are installed. Inmanta requires many dependencies so it is recommended to create a virtual env.
        Next install inmanta with pip install in the newly created virtual env.

        .. code-block:: sh

            # Install python3 >= 3.6 and git
            sudo python3 -m venv /opt/inmanta
            sudo /opt/inmanta/bin/pip install inmanta
            sudo /opt/inmanta/bin/inmanta --help


        The misc folder in the source distribution contains systemd service files for both the server and the agent. Also
        install ``inmanta.cfg`` from the misc folder in ``/etc/inmanta/inmanta.cfg``

        If you want to use the dashboard you need to install it as well. Get the source from
        `our github page <https://github.com/inmanta/inmanta-dashboard/releases>`_ Next, build and install the dashboard. For
        this you need to have yarn and grunt:

        .. code-block:: sh

            tar xvfz inmanta-dashboard-20xx.x.x.tar.gz
            cd inmanta-dashboard-20xx.x.x
            yarn install
            grunt dist

        This creates a dist.tgz file in the current directory. Unpack this tarball in ``/opt/inmanta/dashboard`` and point
        the server in ``/etc/inmanta/inmanta.cfg`` to this location: set
        :inmanta.config:option:`dashboard.path` to ``/opt/inmanta/dashboard``


    .. tab:: Windows

        On Windows only the compile and export commands are supported. This is useful in the :ref:`push-to-server` deployment mode of
        inmanta. First make sure you have Python >= 3.6 and git. Inmanta requires many dependencies so it is recommended to create a virtual env.
        Next install inmanta with pip install in the newly created virtual env.

        .. code-block:: powershell

            # Install python3 >= 3.6 and git
            python3 -m venv C:\inmanta\env
            C:\inmanta\env\Script\pip install inmanta
            C:\inmanta\env\Script\inmanta --help


    .. tab:: Source

        Get the source either from our `release page on github <https://github.com/inmanta/inmanta/releases>`_ or clone/download a branch directly.

        .. code-block:: sh

            git clone https://github.com/inmanta/inmanta.git
            cd inmanta
            pip install -c requirements.txt .

.. warning::
    When you use Inmanta modules that depend on python libraries with native code, python headers and a working compiler are required as well.


Configure server
################
This guide goes through the steps to set up an Inmanta service orchestrator server. This guide assumes a RHEL 7 or CentOS 7
server is used. The rpm packages install the server configuration file in `/etc/inmanta/inmanta.cfg`.

Optional step 1: Setup SSL and authentication
---------------------------------------------

Follow the instructions in :ref:`auth-setup` to configure both SSL and authentication.
While not mandatory, it is highly recommended you do so.

.. _install-step-2:

Step 2: Install PostgreSQL 10
-----------------------------

PostgreSQL 10 can be installed by following the `installation guide <https://www.postgresql.org/download/>`_ for your
platform.


If you are in the process of migrating an existing Inmanta server from MongoDB to PosgreSQL, you can use the following
database migration procedure: :ref:`Migrate from MongoDB to PostgreSQL<migrate-to-postgresql>`.

.. _install-step-3:

Step 3: Setup a PostgreSQL database for the Inmanta server
----------------------------------------------------------

Initialize the PostgreSQL server:

.. code-block:: sh

  sudo /usr/pgsql-10/bin/postgresql-10-setup initdb

Start the PostgreSQL database

.. code-block:: sh

   sudo systemctl start postgresql-10

Create a inmanta user and an inmanta database by executing the following command. This command will request you to choose a
password for the inmanta database.

.. code-block:: sh

  sudo -u postgres -i sh -c "createuser --pwprompt inmanta; createdb -O inmanta inmanta"

Change the authentication method for local connections to md5 by changing the following lines in the
``/var/lib/pgsql/10/data/pg_hba.conf`` file

.. code-block:: text

  # IPv4 local connections:
  host    all             all             127.0.0.1/32            ident
  # IPv6 local connections:
  host    all             all             ::1/128                 ident

to

.. code-block:: text

  # IPv4 local connections:
  host    all             all             127.0.0.1/32            md5
  # IPv6 local connections:
  host    all             all             ::1/128                 md5


Restart the PostgreSQL server to apply the changes made in the ``pg_hba.conf`` file:

.. code-block:: sh

   sudo systemctl restart postgresql-10

.. _install-step-4:

Step 4: Set the database connection details
-------------------------------------------

Add a ``/etc/inmanta/inmanta.d/database.cfg`` file as such that it contains the correct database connection details.
That file should look as follows:

.. code-block:: text

  [database]
  name=inmanta
  username=inmanta
  password=<password>

Replace <password> in the above-mentioned snippet with the password of the inmanta database. By default Inmanta tries to
connect to the local server and uses the database inmanta. See the :inmanta.config:group:`database` section in the
configfile for other options.


Step 5: Set the server address
------------------------------

When virtual machines are started by this server that install the inmanta agent, the correct
:inmanta.config:option:`server.server-address` needs to be
configured. This address is used to create the correct boot script for the virtual machine.

Set this value to the hostname or IP address that others systems use to connect to the server
in the configuration file stored at ``/etc/inmanta/inmanta.d/server.cfg``.

.. note:: If you deploy configuration models that modify resolver configuration it is recommended to use the IP address instead
  of the hostname.


.. _configure_server_step_6:

Step 6: Configure ssh of the inmanta user
-----------------------------------------

The inmanta user that runs the server needs a working ssh client. This client is required to checkout git repositories over
ssh and if the remote agent is used.

1. Provide the inmanta user with one or more private keys:

  a. Generate a new key with ssh-keygen as the inmanta user: ``sudo -u inmanta ssh-keygen -N ""``
  b. Install an exiting key in ``/var/lib/inmanta/.ssh/id_rsa``
  c. Make sure the permissions and ownership are set correctly.

  .. code-block:: text

    ls -l /var/lib/inmanta/.ssh/id_rsa

    -rw-------. 1 inmanta inmanta 1679 Mar 21 13:55 /var/lib/inmanta/.ssh/id_rsa

2. Configure ssh to accept all host keys or white list the hosts that are allowed or use signed host keys
   (depends on your security requirements). This guide configures ssh client for the inmanta user to accept all host keys.
   Create ``/var/lib/inmanta/.ssh/config`` and create the following content:

  .. code-block:: text

    Host *
        StrictHostKeyChecking no
        UserKnownHostsFile=/dev/null

  Ensure the file belongs to the inmanta user:

  .. code-block:: shell

    sudo chown inmanta:inmanta /var/lib/inmanta/.ssh/config

3. Add the public key to any git repositories and save if to include in configuration models that require remote agents.
4. Test if you can login into a machine that has the public key and make sure ssh does not show you any prompts to store
   the host key.


Step 7: Start the Inmanta server
--------------------------------

Start the Inmanta server and make sure it is started at boot.

.. code-block:: sh

  sudo systemctl enable inmanta-server
  sudo systemctl start inmanta-server

Step 8: Connect to the dashboard
--------------------------------

The server dashboard is now available on port '8888'

Optional Step 9: Setup influxdb for collection of performance metrics
---------------------------------------------------------------------

Follow the instructions in :ref:`metering-setup` to send performance metrics to influxdb.
This is only recommended for production deployments.

Optional Step 10: Configure logging
-----------------------------------

Logging can be configured by following the instructions in :ref:`administrators_doc_logging`.


Configure agents
################

Inmanta agents can be started automatically (auto-started agents) or manually (manually-started agents). This section
describes how both types of agents can be set up and configured.


Auto-started agents
-------------------

Auto-started agents always run on the Inmanta server. When handler code needs to be executed on a remote managed device, this
is done over SSH.


Requirements
^^^^^^^^^^^^

If the handler code should be executed on another machine than the Inmanta server, the following requirements should be met:

* The Inmanta server should have passphraseless SSH access on the remote machine. More information on how to set up SSH
  connectivity can be found at :ref:`configure_server_step_6`
* The remote machine should have a Python interpreter installed.


Configure auto-started agents via environment settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Auto-started agents can be configured via the settings of the environment where the auto-started agent belongs to. The
following options are configurable:

* autostart_agent_map
* autostart_agent_deploy_interval
* autostart_agent_deploy_splay_time
* autostart_agent_repair_interval
* autostart_agent_repair_splay_time
* autostart_on_start

The ``autostarted_agent_map`` requires an entry for each agent that should be autostarted. The key is the name of the agent and
the value is either ``local:`` if the handlers should be executed on the Inmanta server or an SSH connection string when the
handlers should be executed on a remote machine.The SSH connection string requires the following format:
``ssh://<user>@<host>:<port>?<options>``. Options is a ampersand-separated list of ``key=value`` pairs. The following options
can be provided:

===========  =============  ==============================================================================================================
Option name  Default value  Description
===========  =============  ==============================================================================================================
retries      10             The amount of times the orchestrator will try to establish the SSH connection when the initial attempt failed.
retry_wait   30             The amount of second between two attempts to establish the SSH connection.
python       python         The Python interpreter available on the remote side.
===========  =============  ==============================================================================================================


Auto-started agents start when they are required by a specific deployment or when the Inmanta server starts if the
``autostart_on_start`` setting is set to true.


Configure the autostart_agent_map via the std::AgentConfig entity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :inmanta:entity:`std::AgentConfig` entity provides functionality to add an entry to the ``autostart_agent_map`` of a
specific environment. As such, the auto-started agents can be managed in the configuration model.


Manually started agents
-----------------------

Manually started agents can be run on any Linux device, but they should be started and configured manually as the name
suggests.

Requirements
^^^^^^^^^^^^

If the handler code should be executed another machine than where the agent is running, the following requirements should be
met:

* The Inmanta agent should have passphraseless SSH access on the remote machine. More information on how to set up SSH
  connectivity can be found at :ref:`configure_server_step_6`
* The remote machine should have a Python interpreter installed.



Step 1: Installing the required Inmanta packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to run a manually started agent, the ``python3-inmanta`` and the ``python3-inmanta-agent`` packages are required on the
machine that will run the agent.

.. code-block:: sh

    sudo tee /etc/yum.repos.d/inmanta_oss_stable.repo <<EOF
    [inmanta-oss-stable]
    name=Inmanta OSS stable
    baseurl=https://pkg.inmanta.com/inmanta-oss-stable/el7/
    gpgcheck=1
    gpgkey=https://pkg.inmanta.com/inmanta-oss-stable/inmanta-oss-stable-public-key
    repo_gpgcheck=1
    enabled=1
    enabled_metadata=1
    EOF

    sudo yum install -y python3-inmanta python3-inmanta-agent


Step 2: Configuring the manually-started agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The manually-started agent can be configured via a ``/etc/inmanta/inmanta.d/*.cfg`` config file. The following options
configure the behavior of the manually started agent:

* :inmanta.config:option:`config.state-dir`
* :inmanta.config:option:`config.agent-names`
* :inmanta.config:option:`config.environment`
* :inmanta.config:option:`config.agent-map`
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


The :inmanta.config:option:`config.agent-map` option can be configured in the same way as the ``autostart_agent_map`` for
auto-started agents.


Step 3: Starting the manually-started agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Finally, enable and start the ``inmanta-agent`` service:

.. code-block:: sh

    sudo systemctl enable inmanta-agent
    sudo systemctl start inmanta-agent


The logs of the agent are written to ``/var/log/inmanta/agent.log``.
