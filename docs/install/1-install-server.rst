.. _install-server:

Install Inmanta
***************

This page explains how to install the Inmanta orchestrator software and setup an orchestration server. Regardless what platform
you installed it on, Inmanta requires at least Python and Git to be installed.


Install the software
####################

.. only:: oss

    Step 1: Install the software
    ----------------------------

    .. tab-set::

        .. tab-item:: RHEL 8 and 9

            For RHEL, Almalinux and Rockylinux 8 and 9  based systems use dnf:

            .. code-block:: sh
                :substitutions:


                sudo tee /etc/yum.repos.d/inmanta-oss-stable.repo <<EOF
                [inmanta-oss-stable]
                name=inmanta-oss-stable
                baseurl=https://packages.inmanta.com/public/oss-stable/rpm/el/\$releasever/\$basearch
                repo_gpgcheck=1
                enabled=1
                gpgkey=https://packages.inmanta.com/public/oss-stable/gpg.|oss_gpg_key|.key
                gpgcheck=1
                sslverify=1
                sslcacert=/etc/pki/tls/certs/ca-bundle.crt
                metadata_expire=300
                pkg_gpgcheck=1
                autorefresh=1
                type=rpm-md
                EOF

                sudo dnf install -y inmanta-oss inmanta-oss-server inmanta-oss-agent

            The first package (inmanta-oss) contains all the code and the commands. The server and the agent packages install config
            files and systemd unit files. The web-console is installed with the server package.


        .. tab-item:: Debian, Ubuntu and derivatives.

            First make sure Python >= 3.9 and git are installed. Inmanta requires many dependencies so it is recommended to create a virtual env.
            Next install inmanta with pip install in the newly created virtual env.

            Please note, the path to the virtual env is arbitrary. Your desired path can override below example.

            .. code-block:: sh

                # Install GCC, python3 >= 3.9 and pip
                sudo apt-get update
                sudo apt-get install build-essential
                sudo apt-get install python3-pip

                # Install wheel and inmanta in a python venv
                sudo apt-get install python3-venv
                sudo python3 -m venv /opt/inmanta
                sudo /opt/inmanta/bin/pip install -U pip wheel
                sudo /opt/inmanta/bin/pip install inmanta
                sudo /opt/inmanta/bin/inmanta --help

                # Install PostgreSQL
                sudo apt-get install postgresql postgresql-client


            Download the configuration files named ``inmanta.cfg`` and ``extensions.cfg`` (these names are arbitrary) in your virtual env:

            .. code-block:: sh

                sudo mkdir /opt/inmanta/inmanta.d
                sudo apt-get install wget
                sudo wget -O /opt/inmanta/inmanta.cfg "https://raw.githubusercontent.com/inmanta/inmanta-core/master/misc/inmanta.cfg"
                sudo wget -O /opt/inmanta/inmanta.d/extensions.cfg "https://raw.githubusercontent.com/inmanta/inmanta-core/master/misc/extensions.cfg"


            If you want to use the web-console you need to install it as well:

            Get the pre-built package from our `web-console github page <https://github.com/inmanta/web-console/packages/>`_. Click on the the package name to go to the package's main page, then on the right hand side under ``Assets``, you will see the compressed package. Download and extract it to your desired directory (preferably, on the same virtual env which was created earlier, in this case, /opt/inmanta). Next, open the ``inmanta.cfg`` file and at the bottom of the file, under the ``[web-console]`` section, change the ``path`` value to the ``dist`` directory of where you extracted the pre-built package. For instance:

            .. code-block:: ini

                path=/opt/inmanta/web-console/package/dist


            Then the Inmanta server can be started using below command (please note, below command has to be run after completing the  :ref:`configure-server`) part:

            .. code-block:: bash

                sudo /opt/inmanta/bin/inmanta -vv -c /opt/inmanta/inmanta.cfg --config-dir /opt/inmanta/inmanta.d server


        .. tab-item:: Other

            First make sure Python >= 3.9 and git are installed. Inmanta requires many dependencies so it is recommended to create a virtual env.
            Next install inmanta with ``pip install`` in the newly created virtual env.

            Please note, the path to the virtual env is arbitrary. Your desired path can override below example.

            .. code-block:: sh

                # Install python3 >= 3.9 and git
                # If git is not already installed, by running git in your terminal, the installation guide will be shown
                sudo python3 -m venv /opt/inmanta
                sudo /opt/inmanta/bin/pip install -U pip wheel
                sudo /opt/inmanta/bin/pip install inmanta
                sudo /opt/inmanta/bin/inmanta --help


            Install PostgreSQL using this `guide <https://www.postgresql.org/docs/13/tutorial-install.html>`_



            Download the configuration files named ``inmanta.cfg`` and ``extensions.cfg`` (these names are arbitrary) in your virtual env:

            .. code-block:: sh

                sudo mkdir /opt/inmanta/inmanta.d
                sudo wget -O /opt/inmanta/inmanta.cfg "https://raw.githubusercontent.com/inmanta/inmanta-core/master/misc/inmanta.cfg"
                sudo wget -O /opt/inmanta/inmanta.d/extensions.cfg "https://raw.githubusercontent.com/inmanta/inmanta-core/master/misc/extensions.cfg"


            If you want to use the web-console you need to install it as well:

            Get the pre-built package from our `web-console github page <https://github.com/inmanta/web-console/packages/>`_. Click on the the package name to go to the package's main page, then on the right hand side under ``Assets``, you will see the compressed package. Download and extract it to your desired directory (preferably, on the same virtual env which was created earlier, in this case, /opt/inmanta). Next, open the ``inmanta.cfg`` file and at the bottom of the file, under the ``[web-console]`` section, change the ``path`` value to the ``dist`` directory of where you extracted the pre-built package. For instance:

            .. code-block:: ini

                path=/opt/inmanta/web-console/package/dist


            Then the Inmanta server can be started using below command (please note, below command has to be run after completing the  :ref:`configure-server`) part:

            .. code-block:: bash

                sudo /opt/inmanta/bin/inmanta -vv -c /opt/inmanta/inmanta.cfg --config-dir /opt/inmanta/inmanta.d server


        .. tab-item:: Windows

            On Windows only the compile and export commands are supported. This is useful in the :ref:`push-to-server` deployment mode of
            inmanta. First make sure you have Python >= 3.9 and git. Inmanta requires many dependencies so it is recommended to create a virtual env.
            Next install inmanta with pip install in the newly created virtual env.

            .. code-block:: powershell

                # Install python3 >= 3.9 and git
                python3 -m venv C:\inmanta\env
                C:\inmanta\env\Script\pip install inmanta
                C:\inmanta\env\Script\inmanta --help


        .. tab-item:: Source

            Get the source either from our `release page on github <https://github.com/inmanta/inmanta-core/releases>`_ or clone/download a branch directly.

            .. code-block:: sh

                git clone https://github.com/inmanta/inmanta-core.git
                cd inmanta
                pip install -c requirements.txt .

    .. warning::
        When you use Inmanta modules that depend on python libraries with native code, python headers and a working compiler are required as well.

    .. _configure-server:

    Configure server
    ################
    This guide goes through the steps to set up an Inmanta service orchestrator server. This guide assumes a RHEL 8 based
    server is used. The rpm packages install the server configuration file in `/etc/inmanta/inmanta.cfg`.




.. only:: iso

    Step 1: Install the software
    ----------------------------

    Create a repositories file to point yum to the inmanta service orchestrator release repository. Create a file
    ``/etc/yum.repos.d/inmanta.repo`` with the following content:


    .. code-block:: sh
        :substitutions:

        [inmanta-service-orchestrator-|version_major|-stable]
        name=inmanta-service-orchestrator-|version_major|-stable
        baseurl=https://packages.inmanta.com/<token>/inmanta-service-orchestrator-|version_major|-stable/rpm/el/8/$basearch
        repo_gpgcheck=1
        enabled=1
        gpgkey=https://packages.inmanta.com/<token>/inmanta-service-orchestrator-|version_major|-stable/cfg/gpg/gpg.|iso_gpg_key|.key
        gpgcheck=1
        sslverify=1
        sslcacert=/etc/pki/tls/certs/ca-bundle.crt
        metadata_expire=300
        pkg_gpgcheck=1
        autorefresh=1
        type=rpm-md


    Replace ``<token>`` with the token provided with your license.

    Use dnf to install the software:

    .. code-block:: sh

        sudo dnf install -y inmanta-service-orchestrator-server


    This command installs the software and all of its dependencies.


    Install the license
    ###################

    For the orchestration server to start a license and entitlement file should be loaded into the server. This section describes how to
    configure the license. The license consists of two files:

    - The file with the .license extension is the license file
    - The file with the .jwe extension is the entitlement file

    Copy both files to the server and store them for example in ``/etc/inmanta/license``. If this directory does not exist, create it. Then create a
    configuration file to point the orchestrator to the license files. Create a file ``/etc/inmanta/inmanta.d/license.cfg`` with the following content:

    .. code-block::

        [license]
        license-key=/etc/inmanta/license/<license name>.license
        entitlement-file=/etc/inmanta/license/<license name>.jwe


    Replace ``<license name>`` with the name of the license you received.


Optional step 2: Setup SSL and authentication
---------------------------------------------

Follow the instructions in :ref:`auth-setup` to configure both SSL and authentication.
While not mandatory, it is highly recommended you do so.

.. _install-step-2:

Step 3: Install PostgreSQL 13
-----------------------------

.. only:: oss

    For most platforms you can install PostgreSQL 13 following the `installation guide <https://www.postgresql.org/download/>`_ for your
    platform.

    For RHEL based systems you can also use the PostgreSQL that comes with the distribution.

    .. code-block:: sh

        sudo dnf module install postgresql:13/server

.. only:: iso

    Install the PostgreSQL 13 package included in RHEL. More info in the 'Included in Distribution' section
    of the `postgresql documentation <https://www.postgresql.org/download/linux/redhat/>`_.

    .. tab-set::

        .. tab-item:: RHEL 8

            .. code-block:: sh

                sudo dnf module install postgresql:13/server
                sudo systemctl enable postgresql

        .. tab-item:: RHEL 9

            .. code-block:: sh

                sudo dnf install postgresql-server
                sudo systemctl enable postgresql

            .. warning::
                Before moving on to the next step, make sure that the locale used by the system is actually installed.
                By default, RHEL9 uses the ``en_US.UTF-8`` locale which can be installed via:

                .. code-block:: sh

                    sudo dnf install langpacks-en -y

                .. note::
                    If your system uses a different locale, please install the corresponding langpack.

.. _install-step-3:

Step 4: Setup a PostgreSQL database for the Inmanta server
----------------------------------------------------------

Initialize the PostgreSQL server:

.. only:: oss

    .. code-block:: sh

        sudo su - postgres -c "postgresql-13-setup --initdb"

.. only:: iso

    .. code-block:: sh

        sudo su - postgres -c "postgresql-setup --initdb"


Start the PostgreSQL database and make sure it is started at boot.

.. only:: oss

    .. code-block:: sh

        sudo systemctl enable --now postgresql-13

.. only:: iso

    .. code-block:: sh

        sudo systemctl enable --now postgresql

Create a inmanta user and an inmanta database by executing the following command. This command will request you to choose a
password for the inmanta database.

.. code-block:: sh

  sudo -u postgres -i bash -c "createuser --pwprompt inmanta"
  sudo -u postgres -i bash -c "createdb -O inmanta inmanta"

Change the authentication method for local connections to md5 by changing the following lines in the
``/var/lib/pgsql/data/pg_hba.conf`` file

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

Make sur JIT is disabled for the psql database as it will impact performances.
To disable JIT, set ``jit = off`` in ``/etc/postgresql/13/main/postgresql.conf``.

Restart the PostgreSQL server to apply the changes made in the ``pg_hba.conf`` and  ``postgresql.conf`` files:

.. only:: oss

    .. code-block:: sh

        sudo systemctl restart postgresql-13

.. only:: iso

    .. code-block:: sh

        sudo systemctl restart postgresql

.. _install-step-4:

Step 5: Set the database connection details
-------------------------------------------

Add a ``/etc/inmanta/inmanta.d/database.cfg`` file as such that it contains the correct database connection details.
That file should look as follows:

.. code-block:: text

  [database]
  host=<ip-address-database-server>
  name=inmanta
  username=inmanta
  password=<password>

Replace <password> in the above-mentioned snippet with the password of the inmanta database. By default Inmanta tries to
connect to the local server and uses the database inmanta. See the :inmanta.config:group:`database` section in the
configfile for other options.

.. _configure_server_step_5:

Step 6: Set the server address
------------------------------

When virtual machines are started by this server that install the inmanta agent, the correct
:inmanta.config:option:`server.server-address` needs to be
configured. This address is used to create the correct boot script for the virtual machine.

Set this value to the hostname or IP address that other systems use to connect to the server
in the configuration file stored at ``/etc/inmanta/inmanta.d/server.cfg``.

.. code-block:: text

  [server]
  server-address=<server-ip-address-or-hostname>

.. note:: If you deploy configuration models that modify resolver configuration it is recommended to use the IP address instead
  of the hostname.


.. _configure_server_step_6:

Step 7: Configure ssh of the inmanta user
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

3. Add the public key to any git repositories and save it to include in configuration models that require remote agents.
4. Test if you can login into a machine that has the public key and make sure ssh does not show you any prompts to store
   the host key.

Step 8: Configure the server bind address
-----------------------------------------

By default the server only listens on localhost, port 8888.
This can be changed by altering the
:inmanta.config:option:`server.bind-address` and :inmanta.config:option:`server.bind-port`
options in the ``/etc/inmanta/inmanta.d/server.cfg`` file.

.. code-block:: text

  [server]
  bind-address=<server-bind-address>
  bind-port=<server-bind-port>

Step 9: Enable the required Inmanta extensions
----------------------------------------------

Make sure that the required Inmanta extensions are enabled. This is done by adding a configuration file with the following content to ``/etc/inmanta/inmanta.d/extensions.cfg``.

.. only:: oss

    .. code-block:: text

       [server]
       enabled_extensions=ui

.. only:: iso

    .. code-block:: text

        [server]
        enabled_extensions=lsm,ui,support,license

This file is also installed by the RPM.


Step 10: Start the Inmanta server
---------------------------------

Start the Inmanta server and make sure it is started at boot.

.. code-block:: sh

  sudo systemctl enable --now inmanta-server


The web-console is now available on the port and host configured in step 8.

Optional Step 11: Setup influxdb for collection of performance metrics
----------------------------------------------------------------------

Follow the instructions in :ref:`metering-setup` to send performance metrics to influxdb.
This is only recommended for production deployments.

Optional Step 12: Configure logging
-----------------------------------

Logging can be configured by following the instructions in :ref:`administrators_doc_logging`.
