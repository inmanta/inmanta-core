Install Inmanta
****************
This page explain how to install the Inmanta orchestrator software and setup an orchestration server. On any platform
Inmanta requires at least the latest Python 3.6 or 3.7 and git.

.. tabs::

    .. tab:: CentOS 7

        For CentOS use yum and install epel-release:

        .. code-block:: sh

          cat > /etc/yum.repos.d/inmanta_oss_stable.repo <<EOF
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

    .. tab:: Fedora

        For Fedora use dnf:

        .. code-block:: sh

          cat > /etc/yum.repos.d/inmanta_oss_stable.repo <<EOF
          [inmanta-oss-stable]
          name=Inmanta OSS stable
          baseurl=https://pkg.inmanta.com/inmanta-oss-stable/f\$releasever/
          gpgcheck=1
          gpgkey=https://pkg.inmanta.com/inmanta-oss-stable/inmanta-oss-stable-public-key
          repo_gpgcheck=1
          enabled=1
          enabled_metadata=1
          EOF
          sudo dnf install -y python3-inmanta python3-inmanta-server python3-inmanta-agent

        The first package (python3-inmanta) contains all the code and the commands. The server and the agent
        packages install config files and systemd unit files. The dashboard is installed with the server
        package.


    .. tab:: Other Linux and Mac

        First make sure you have Python >= 3.6 and git. Inmanta requires many dependencies so it is recommended to create a virtual env.
        Next install inmanta with pip install in the newly created virtual env.

        .. code-block:: sh

            # Install python3 >= 3.6 and git
            sudo python3 -m venv /opt/inmanta
            sudo /opt/inmanta/bin/pip install inmanta
            sudo /opt/inmanta/bin/inmanta --help


        The misc folder in the source distribution contains systemd service files for both the server and the agent. Also
        install ``server.cfg`` from the misc folder in ``/etc/inmanta/server.cfg``

        If you want to use the dashboard you need to install it as well. Get the source from
        `our github page <https://github.com/inmanta/inmanta-dashboard/releases>`_ Next, build and install the dashboard. For
        this you need to have yarn and grunt:

        .. code-block:: sh

            tar xvfz inmanta-dashboard-20xx.x.x.tar.gz
            cd inmanta-dashboard-20xx.x.x
            yarn install
            grunt dist

        This creates a dist.tgz file in the current directory. Unpack this tarball in ``/opt/inmanta/dashboard`` and point
        the server in ``/etc/inmanta/server.cfg`` to this location: change :inmanta.config:option:`dashboard.path` to
        ``/opt/inmanta/dashboard``


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

        Get the source either from our `release page on github <https://github.com/inmanta/inmanta/releases>`_ or from source
        repo.

        .. code-block:: sh

            git clone https://github.com/inmanta/inmanta.git
            cd inmanta
            pip install -c requirements.txt .

.. warning::
    When you use Inmanta modules that depend on python libraries with native code, python headers and a working compiler is required as well.


Configure server
################
This guide goes through the steps to setup an Inmanta service orchestrator server. This guide assumes a RHEL 7 or CentOS 7
server. The rpm packages install the server configuration file in /etc/inmanta/server.cfg

Optional step 1: Setup SSL and authentication
---------------------------------------------

Follow the instructions in :ref:`auth-setup` to configure both SSL and authentication. It is not mandatory but still highly
recommended.

.. _install-step-2:

Step 2: Install PostgreSQL 10
-----------------------------

PostgreSQL 10 can be installed by following the `installation guide <https://www.postgresql.org/download/>`_ for your
platform.


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
``/var/lib/pgsql/10/data/pg_hba.conf`` file.

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

Adjust the ``/etc/inmanta/server.cfg`` file as such that it contains the correct database connection details. Add/Change the
database section of that file in the following way:

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
in the configuration file stored at ``/etc/inmanta/server.cfg``.

.. note:: If you deploy configuration models that modify resolver configuration it is recommended to use the IP address instead
  of the hostname.


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

Optional Step 8: Setup influxdb for collection of performance metrics
---------------------------------------------------------------------

Follow the instructions in :ref:`metering-setup` to send performance metrics to influxdb.
This is only recommended for production deployments.

Optional Step 9: Configure logging
----------------------------------

Logging can be configured by following the instructions in :ref:`administrators_doc_logging`.
