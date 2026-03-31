Container-based installation
****************************

This page describes how to install the Inmanta orchestrator using Podman and Systemd.


The Inmanta docker image
########################

.. only:: oss

   The Inmanta docker image can be found at: ``ghcr.io/inmanta/orchestrator:<version_tag>``. Replace ``<version_tag>`` with the specific version you want to run.

.. only:: iso

   The Inmanta docker image can be found at: ``containers.inmanta.com/containers/service-orchestrator:<version_tag>``. Replace ``<version_tag>`` with the specific version you want to run.


The details about the Inmanta container image can be found below:

* **uid:** 997
* **gid:** 995
* **Default port:** 8888
* **Main directories:**
   * Configuration directory: ``/etc/inmanta``
   * Log directory: ``/var/log/inmanta``
   * State/Home directory: ``/var/lib/inmanta``
* **Environment variables:** Each config option of the Inmanta server can also be set using an environment variable. The names of these environment variables can be found on :ref:`this page<config_reference>`.


.. _install-server-with-podman:

Install Inmanta using Podman and Systemd
########################################

This section provides an opinionated way of installing the Inmanta orchestrator using Podman and Systemd on RedHat Enterprise Linux and derivatives.


Install Podman
==============

Run the following command to install Podman:

.. code-block:: console

   $ sudo dnf -y install podman


Create a system user
====================

Create a system user that will be used to run the Inmanta container.

.. code-block:: console

   $ sudo useradd -r -m inmanta

Enable lingering
================

Make sure the inmanta user is allowed to linger. This is required to let the orchestrator run even when no active session exists for the user.
You can check whether lingering is enabled for the inmanta user by verifying whether there is a file named inmanta in the ``/var/lib/systemd/linger`` directory.

.. code-block:: console

   $ ls /var/lib/systemd/linger | grep inmanta
   inmanta

If the inmanta user doesn't show in the output, then you need to enable lingering for that user, which can be done this way:

.. code-block:: console

   $ sudo loginctl enable-linger inmanta


Add subordinate ids
===================

Make sure that the Inmanta user has subordinate uids (subuids) and gids (subgids) assigned. Those are required to map the inmanta user from the host to the uids and gids used inside the container, allowing the container to run rootless. Verify the subuid and subgid assignment by inspecting the content of the ``/etc/subuid`` and ``/etc/subgid`` files:

.. code-block:: console

   $ cat /etc/subuid
   rocky:100000:65536

   $ cat /etc/subgid
   rocky:100000:65536

These files represent a colon-separated list of subuid and subgid assignments. The first element is the username, the second element is the first subuid/subgid in the range assigned to that user and the last element in the length of the range. If required, add a range of subuids and subgids to the inmanta user. Make sure that it has at least 65535 subuids and subgids and make sure that the new range doesn't overlap with existing ranges. Assigning subuids/subgids be done by executing the following command:

.. code-block:: console

   $ sudo usermod --add-subuids <first-uid-in-range>-<last-uid-in-range> --add-subgids <first-gid-in-range>-<last-gid-in-range> inmanta

For the above-mentioned example we can add the range 200000-265535 for both the subuids and subgids:

.. code-block:: console

   $ sudo usermod --add-subuids 200000-265535 --add-subgids 200000-265535 inmanta

The ``/etc/subuid`` and ``/etc/subgid`` files will now look as follows:

.. code-block:: console

   $ cat /etc/subuid
   rocky:100000:65536
   inmanta:200000:65536

   $ cat /etc/subgid
   rocky:100000:65536
   inmanta:200000:65536

Finally, you need to execute the following command to make Podman aware about the above-mentioned changes:

.. code-block:: console

   $ podman system migrate

For more information about rootless Podman and subordinate ids consult the `Podman documentation <https://github.com/containers/podman/blob/2ba36051082d7ba6ba387f4151e1cfcf338bbc4d/docs/tutorials/rootless_tutorial.md>`_.

The next steps in this procedure should be executed as the ``inmanta`` user.
You have to login as the ``inmanta`` user directly. Logging is as a different user
and changing to the ``inmanta`` user using the su command will make the systemctl commands
fail.

Prepare directories for bind mounts
===================================

The Inmanta orchestrator and its PostgreSQL database will rely on bind mounts for their persistent storage.
Here we will create those directories:

.. code-block:: console

   $ mkdir -p /home/inmanta/mount/{db,orchestrator}
   $ mkdir -p /home/inmanta/mount/orchestrator/{log,state,config}

.. only:: iso

    Get the orchestrator license
    ============================

    Together with the access to the inmanta container repo, you should also have received a license and an entitlement file.
    The orchestrator will need them in order to run properly.  We will assume that these files are named ``license.key`` and
    ``entitlement.jwe``. Put these files in the ``/home/inmanta/mount/orchestrator/config`` directory on the host.

Start the server with systemd
=============================

The following steps rely on the quadlet project to generate systemd unit files from simplified, systemd-like unit files that are Podman specific. To learn more about quadlet and how podman integrates nicely with systemd, please refer to `podman's documentation <https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html>`_.

Step 1: Install the required files
----------------------------------

We need to create four files: two containers, one network and one image.
The two container files are for the orchestrator and its database.
The network file is to setup a bridge that both containers can use to communicate with each other.
Finally, the image file is used to store the credentials of the container registry.

Create the files in the ``/home/inmanta/.config/containers/systemd/`` folder:

.. code-block::

    /home/inmanta/.config/containers/systemd/
    ├── inmanta.network
    ├── inmanta-server.image
    ├── inmanta-db.container
    └── inmanta-server.container


The file ``inmanta.network`` defines the bridge.  We keep all the defaults provided by podman and pick an explicit name for the network.

.. code-block:: systemd

    [Unit]
    Description=Inmanta orchestrator network
    Documentation=https://docs.inmanta.com

    [Network]
    NetworkName=inmanta


The file ``inmanta-server.image`` defines the details of how/when to pull the docker image for the Inmanta orchestrator.

.. only:: oss

    .. code-block:: systemd

       [Unit]
       Description=The Inmanta orchestrator image.
       Documentation=https://docs.inmanta.com

       [Image]
       AllTags=false
       Image=ghcr.io/inmanta/orchestrator:<version_tag>
       TLSVerify=true
       Policy=missing

    Replace ``<version_tag>`` with the specific version your want to run. It's recommended to use a specific version instead of using "latest" to prevent unexpected upgrades to a newer version.

.. only:: iso

    .. code-block:: systemd

       [Unit]
       Description=The Inmanta orchestrator image.
       Documentation=https://docs.inmanta.com

       [Image]
       AllTags=false
       Creds=containers:<your-entitlement-token>
       Image=containers.inmanta.com/containers/service-orchestrator:<version_tag>
       TLSVerify=true
       Policy=missing

    Replace ``<your-entitlement-token>`` with the entitlement token provided with your license. Replace ``<version_tag>`` with the specific version your want to run. It's recommended to use a specific version instead of using "latest" or just the major version number to prevent unexpected upgrades to a newer version.

The file ``inmanta-db.container`` defines the database container. The data is stored in the ``/home/inmanta/mount/db`` directory on the host.

.. code-block:: systemd
    :substitutions:

    [Unit]
    Description=Inmanta orchestrator db
    Documentation=https://docs.inmanta.com

    [Container]
    ContainerName=inmanta-db
    Image=docker.io/library/postgres:|pg_version|
    Network=inmanta.network
    Environment=POSTGRES_USER=<db_username>
    Environment=POSTGRES_PASSWORD=<db_password>
    UIDMap=+999:0:1
    GIDMap=+999:0:1
    Volume=/home/inmanta/mount/db:/var/lib/postgresql/data:z
    Exec=postgres -c jit=off


Replace ``<db_username>`` and ``<db_password>`` with respectively the username and password you want to use to authenticate to the database server.

The file ``inmanta-server.container`` defines the orchestrator container. Its state, log and config are persisted in
their respective directories in ``/home/inmanta/mount/orchestrator``.

.. only:: oss

    .. code-block:: systemd

        [Unit]
        Description=Inmanta orchestrator server
        Documentation=https://docs.inmanta.com
        After=network.target
        Wants=inmanta-db.container
        After=inmanta-db.container

        [Container]
        ContainerName=inmanta-server
        Image=inmanta-server.image
        PublishPort=127.0.0.1:8888:8888
        Network=inmanta.network
        Environment=INMANTA_DATABASE_HOST=inmanta-db
        Environment=INMANTA_DATABASE_USERNAME=<db_username>
        Environment=INMANTA_DATABASE_PASSWORD=<db_password>
        UIDMap=+997:0:1
        GIDMap=+995:0:1
        Volume=/home/inmanta/mount/orchestrator/state:/var/lib/inmanta:z
        Volume=/home/inmanta/mount/orchestrator/log:/var/log/inmanta:z
        Volume=/home/inmanta/mount/orchestrator/config:/etc/inmanta:z

.. only:: iso

    .. code-block:: systemd
        :substitutions:

        [Unit]
        Description=Inmanta service orchestrator server
        Documentation=https://docs.inmanta.com
        After=network.target
        Wants=inmanta-db.container
        After=inmanta-db.container

        [Container]
        ContainerName=inmanta-server
        Image=inmanta-server.image
        PublishPort=127.0.0.1:8888:8888
        Network=inmanta.network
        Environment=INMANTA_DATABASE_HOST=inmanta-db
        Environment=INMANTA_DATABASE_USERNAME=<db_username>
        Environment=INMANTA_DATABASE_PASSWORD=<db_password>
        UIDMap=+997:0:1
        GIDMap=+995:0:1
        Volume=/home/inmanta/mount/orchestrator/state:/var/lib/inmanta:z
        Volume=/home/inmanta/mount/orchestrator/log:/var/log/inmanta:z
        Volume=/home/inmanta/mount/orchestrator/config:/etc/inmanta:z

Replace ``<db_username>`` and ``<db_password>`` with the username and password chosen in the ``inmanta-db.container`` file.


Step 2: Generate the systemd services
-------------------------------------

Once the quadlet files are in place, let podman generate the corresponding systemd unit files by calling ``daemon-reload``.

.. code-block:: console

    $ systemctl --user daemon-reload

The generated systemd files can be found in the ``/var/run/user/$(id -u)/systemd/generator`` directory.


Step 3: Start the orchestrator
------------------------------

Then start the orchestrator database and server by running the following command. This command will also start the database,
because the ``inmanta-server.service`` unit defines a dependency on ``inmanta-db.service`` unit. Executing this command might
take a while because Podman needs to download the container images from the container registry.

.. code-block:: console

    $ systemctl --user start inmanta-server.service

You should be able to reach the orchestrator at this address: `http://127.0.0.1:8888 <http://127.0.0.1:8888>`_ on the host.

(Optional) To make sure the orchestrator is started when the host is booted, add the following install section to the `inmanta-server.container` file:

.. code-block:: systemd

    [Install]
    WantedBy=default.target

Then regenerate the unit files:

.. code-block:: console

    $ systemctl --user daemon-reload


Troubleshooting
###############

If the orchestrator doesn't come up, the source of the problem can be situated at the Podman level (e.g. Podman cannot pull a container image) or at the application level (e.g. the orchestrator or database application fails to start). Problems within the Podman runtime will be shown in the output of the ``systemctl --user status <unit>`` command. Execute the following command and inspect the output:

.. code-block:: console

    $ systemctl --user status inmanta-server.service

If the above-mentioned command doens't provide any insight into the source of the problem, consult the logs of the Inmanta server. These logs can be found in the ``/home/inmanta/mount/orchestrator/log`` directory on the host.


Listen on non-loopback interface
################################

The above-mentioned configuration exposes the orchestrator port on the loopback interface of the host machine using
the ``PublishPort=127.0.0.1:8888:8888`` config option in the ``inmanta-server.container`` file.
Change the ``127.0.0.1`` value of that option to a different interface if the orchestrator should be exposed
on a different interface than the loopback interface.


Overwrite default server configuration
######################################

If you want to change the default server configuration, you can do that either by adding a ``.cfg`` file to
``/home/inmanta/mount/orchestrator/config/inmanta.d/`` on the host or by settings the corresponding environment variables.
All the different configuration options and associated environment variables are described :ref:`here<config_reference>`.
Be aware that values provided in the configuration file are overwritten by values provided in environment variables, and that
the orchestrator image contains some `default environment variable values <https://raw.githubusercontent.com/inmanta/inmanta/refs/heads/master/docker/native_image/Dockerfile#:~:text=ENV>`_.


Setting environment variables
#############################

The inmanta server will share any environment variable it received from podman with all its compiler and agent sub processes.  So if you need
to make some environment variables available to the compiler or agent, you can simply tell podman to pass them on to the orchestrator container.
In the example shown above, this can be done by using either of the ``Environment`` or ``EnvironmentFile`` options in the orchestrator container unit (``inmanta-server.container``).
More details about these options can be found in `podman's documentation <https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html#environment>`_.

.. warning::
    If you are migrating from an rpm install, be aware that the format of environment files for `podman` (and `docker` for that matter) are different from what is supported by systemd which you may have been relying on up to now.
    The format is simply `[KEY]=[VALUE]` separated by new lines, without any quoting or multi-line support.
    cf. `podman#19565 <https://github.com/containers/podman/issues/19565#issuecomment-1672891535>`_.


.. include:: compatibility_check.rst


Accessing the orchestrator file system
######################################

If you want to have a look inside the running orchestrator container, it contains a traditional file system. You can enter it using ``podman exec`` on the host where the container is running:

.. code-block:: console

    $ podman exec -ti inmanta-server bash


Log rotation
############

By default, the container won't do any log rotation, to let you the choice of dealing with the logs
according to your own preferences.
