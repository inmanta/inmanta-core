.. _install-step-4:

Step 4: Set the database connection details
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

Step 5: Set the server address
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

Step 7: Configure the server bind address
-----------------------------------------

By default the server only listens on localhost, port 8888.
This can be changed by altering the
:inmanta.config:option:`server.bind-address` and :inmanta.config:option:`server.bind-port`
options in the ``/etc/inmanta/inmanta.d/server.cfg`` file.

.. code-block:: text

  [server]
  bind-address=<server-bind-address>
  bind-port=<server-bind-port>

Step 8: Start the Inmanta server
--------------------------------

Start the Inmanta server and make sure it is started at boot.

.. code-block:: sh

  sudo systemctl enable --now inmanta-server


The server dashboard is now available on the port and host configured in step 7.

Optional Step 9: Setup influxdb for collection of performance metrics
---------------------------------------------------------------------

Follow the instructions in :ref:`metering-setup` to send performance metrics to influxdb.
This is only recommended for production deployments.

Optional Step 10: Configure logging
-----------------------------------

Logging can be configured by following the instructions in :ref:`administrators_doc_logging`.
