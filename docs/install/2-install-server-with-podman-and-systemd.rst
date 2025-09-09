.. _install-server-with-podman:

Install Inmanta with Podman and Systemd
***************************************

This page explains how to setup an Inmanta orchestration server using Podman and Systemd.
This guide assumes you already have `Podman <http://podman.io/>`_ installed on your machine and that you are running a Linux distribution using Systemd.

.. note::
    The instructions below will show you how to install the orchestrator, and make the orchestrator run as a non-root user on the host.  To achieve this
    you can either follow the rootless instructions (``User setup``), running them as a simple user without elevated privileged, or as root (``Root setup``).
    If you follow the latter, make sure to create a system user that we will use to run the orchestrator process.  We will assume in the next steps that such
    system user is named ``inmanta``.

.. warning::
    The following instructions make some assumptions on the system used, you may have to adapt the examples depending on your environment.
    For example the uids and gids may already be in use, selinux may be configured differently, ...


System configuration
####################

1.  Make sure the user running the orchestrator is allowed to linger.  This is required to let the orchestrator run even when no active session is active for the user.
    You can check whether lingering is enabled for the user running the orchestrator this way:

    .. tab-set::

        .. tab-item:: User setup
            :sync: rootless-setup

            .. code-block:: console

                $ ls /var/lib/systemd/linger | grep $USER
                inmanta

        .. tab-item:: Root setup
            :sync: rootful-setup

            .. code-block:: console

                # ls /var/lib/systemd/linger | grep inmanta
                inmanta

    If the name of the user used to run the orchestrator doesn't show in the output, then you need to enable lingering for that user, which can be done this way:

    .. tab-set::

        .. tab-item:: User setup
            :sync: rootless-setup

            .. code-block:: console

                $ loginctl enable-linger

        .. tab-item:: Root setup
            :sync: rootful-setup

            .. code-block:: console

                # loginctl enable-linger inmanta


Podman configuration
####################

Follow the `Podman documentation <https://github.com/containers/podman/blob/2ba36051082d7ba6ba387f4151e1cfcf338bbc4d/docs/tutorials/rootless_tutorial.md>`_ to make sure that:

1.  The user that will run the orchestrator (your unprivileged user, or the ``inmanta`` system user) has a range of ``subuids`` and ``subgids`` available to use.
    You can check it is the case running those commands:

    .. tab-set::

        .. tab-item:: User setup
            :sync: rootless-setup

            .. code-block:: console

                $ podman unshare cat /proc/self/uid_map
                        0       1000          1
                        1     524288      65536
                $ podman unshare cat /proc/self/gid_map
                        0       1000          1
                        1     524288      65536

        .. tab-item:: Root setup
            :sync: rootful-setup

            .. code-block:: console

                # sudo -i -u inmanta -- podman unshare cat /proc/self/uid_map
                        0        976          1
                        1    1000000      65536
                # sudo -i -u inmanta -- podman unshare cat /proc/self/gid_map
                        0        975          1
                        1    1000000      65536

    If it is not the case, you can set these up following the podman documentation referred above.

Pull the image
##############

.. only:: oss

    Use ``podman pull`` to get the desired image:

    .. tab-set::

        .. tab-item:: User setup
            :sync: rootless-setup

            .. code-block:: console

                $ podman pull ghcr.io/inmanta/orchestrator:latest

        .. tab-item:: Root setup
            :sync: rootful-setup

            .. code-block:: console

                # sudo -i -u inmanta -- podman pull ghcr.io/inmanta/orchestrator:latest

    This command will pull the latest version of the Inmanta OSS Orchestrator image.

.. only:: iso

    Step 1: Log in to container registry
    -------------------------------------

    Connect to the container registry using your entitlement token.

    .. tab-set::

        .. tab-item:: User setup
            :sync: rootless-setup

            .. code-block:: console

                $ podman login containers.inmanta.com
                Username: containers
                Password: <your-entitlement-token>

                Login Succeeded

        .. tab-item:: Root setup
            :sync: rootful-setup

            .. code-block:: console

                # sudo -i -u inmanta -- podman login containers.inmanta.com
                Username: containers
                Password: <your-entitlement-token>

                Login Succeeded

    Replace ``<your-entitlement-token>`` with the entitlement token provided with your license.


    Step 2: Pull the image
    ----------------------

    Use ``podman pull`` to get the desired image:

    .. tab-set::

        .. tab-item:: User setup
            :sync: rootless-setup

            .. code-block:: console
                :substitutions:

                $ podman pull containers.inmanta.com/containers/service-orchestrator:|version_major|

        .. tab-item:: Root setup
            :sync: rootful-setup

            .. code-block:: console
                :substitutions:

                # sudo -i -u inmanta -- podman pull containers.inmanta.com/containers/service-orchestrator:|version_major|

    This command will pull the latest release of the Inmanta Service Orchestrator image within this major version.

.. only:: iso

    Get the orchestrator license
    ############################

    Together with the access to the inmanta container repo, you should also have received a license and an entitlement file.
    The orchestrator will need them in order to run properly.  We will assume that these files are named ``license.key`` and
    ``entitlement.jwe`` and are located in the folder ``/etc/inmanta`` on the host where the containers will be deployed and
    owned by the user that will be running the orchestrator container.

Start the server with systemd
#############################

With the quadlet project, we can write simplified unit files for pod and containers and let podman generate the corresponding systemd services.
To learn more about quadlet and how podman integrates nicely with systemd, please refer to `podman's documentation <https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html>`_.

Step 1: Install the required files
----------------------------------

We need to create three files: two containers and one network.
The two container files are for the orchestrator an its database.
The network file is to setup a bridge that both containers can use to communicate with each other.

.. tab-set::

    .. tab-item:: User setup
        :sync: rootless-setup

        Create the files in the ``~/.config/containers/systemd/`` folder in your unprivileged user's home folder.

        .. code-block::

            .config/containers/systemd/
            ├── inmanta-orchestrator-db.container
            ├── inmanta-orchestrator-net.network
            └── inmanta-orchestrator-server.container

    .. tab-item:: Root setup
        :sync: rootful-setup

        Create the files in the shared ``/etc/containers/systemd/users/`` systemd folder.

        .. code-block::

            /etc/containers/systemd/users/
            ├── inmanta-orchestrator-db.container
            ├── inmanta-orchestrator-net.network
            └── inmanta-orchestrator-server.container

The file ``inmanta-orchestrator-net.network`` defines the bridge.  We keep all the defaults provided by podman and pick an explicit name for the network.

.. code-block:: systemd

    [Unit]
    Description=Inmanta orchestrator network
    Documentation=https://docs.inmanta.com

    [Network]
    NetworkName=inmanta-orchestrator-net

The file ``inmanta-orchestrator-db.container`` defines the database container, its storage is persisted in a volume named ``inmanta-db-data``.

.. code-block:: systemd

    [Unit]
    Description=Inmanta orchestrator db
    Documentation=https://docs.inmanta.com

    [Container]
    ContainerName=inmanta-db
    Image=docker.io/library/postgres:16
    Network=inmanta-orchestrator-net.network
    Environment=POSTGRES_USER=inmanta
    Environment=POSTGRES_PASSWORD=inmanta
    # The following mappings allow you to use bind mounts instead of volumes
    # for persisting the storage of the orchestrator, while making sure that
    # all the files on the host file system will be owned by the user running
    # the container.  When using volumes it is optional.
    # UIDMap=+999:0:1
    # GIDMap=+999:0:1
    Volume=inmanta-db-data:/var/lib/postgresql/data:z
    Exec=postgres -c jit=off

The file ``inmanta-orchestrator-server.container`` defines the orchestrator containers, its storage is persisted in a volume named ``inmanta-server-data``
and its logs in a volume named ``inmanta-server-logs``.

.. only:: oss

    .. code-block:: systemd

        [Unit]
        Description=Inmanta orchestrator server
        Documentation=https://docs.inmanta.com

        [Container]
        ContainerName=inmanta-orchestrator
        Image=ghcr.io/inmanta/orchestrator:latest
        PublishPort=127.0.0.1:8888:8888
        Network=inmanta-orchestrator-net.network
        Environment=INMANTA_DATABASE_HOST=inmanta-db
        Environment=INMANTA_DATABASE_USERNAME=inmanta
        Environment=INMANTA_DATABASE_PASSWORD=inmanta
        # The following mappings allow you to use bind mounts instead of volumes
        # for persisting the storage of the orchestrator, while making sure that
        # all the files on the host file system will be owned by the user running
        # the container.  When using volumes it is optional.
        # UIDMap=+997:0:1
        # GIDMap=+995:0:1
        Volume=inmanta-server-data:/var/lib/inmanta:z
        Volume=inmanta-server-logs:/var/log/inmanta:z

.. only:: iso

    This container also needs to load the license files of the orchestrator.  In this example, these are stored on the host in the ``/etc/inmanta``.
    You can of course update these paths to match your current configuration.

    .. code-block:: systemd
        :substitutions:

        [Unit]
        Description=Inmanta service orchestrator server
        Documentation=https://docs.inmanta.com

        [Container]
        ContainerName=inmanta-orchestrator
        Image=containers.inmanta.com/containers/service-orchestrator:|version_major|
        PublishPort=127.0.0.1:8888:8888
        Network=inmanta-orchestrator-net.network
        Environment=INMANTA_DATABASE_HOST=inmanta-db
        Environment=INMANTA_DATABASE_USERNAME=inmanta
        Environment=INMANTA_DATABASE_PASSWORD=inmanta
        # The following mappings allow you to use bind mounts instead of volumes
        # for persisting the storage of the orchestrator, while making sure that
        # all the files on the host file system will be owned by the user running
        # the container.  When using volumes it is optional.
        # UIDMap=+997:0:1
        # GIDMap=+995:0:1
        Volume=inmanta-server-data:/var/lib/inmanta:z
        Volume=inmanta-server-logs:/var/log/inmanta:z
        Volume=/etc/inmanta/license.key:/etc/inmanta/license.key:z
        Volume=/etc/inmanta/entitlement.jwe:/etc/inmanta/entitlement.jwe:z

Step 2: Generate the systemd services
-------------------------------------

Once the quadlet files are in place, let podman generate the corresponding systemd unit files by calling ``daemon-reload``.

.. tab-set::

    .. tab-item:: User setup
        :sync: rootless-setup

        .. code-block:: console

            $ systemctl --user daemon-reload

    .. tab-item:: Root setup
        :sync: rootful-setup

        .. code-block:: console

            # sudo -i -u inmanta -- systemctl --user daemon-reload

Step 3: Start the orchestrator
------------------------------

Then start the orchestrator database and server by running the following commands:

.. tab-set::

    .. tab-item:: User setup
        :sync: rootless-setup

        .. code-block:: console

            $ systemctl --user start inmanta-orchestrator-db.service
            $ systemctl --user start inmanta-orchestrator-server.service

    .. tab-item:: Root setup
        :sync: rootful-setup

        .. code-block:: console

            # sudo -i -u inmanta -- systemctl --user start inmanta-orchestrator-db.service
            # sudo -i -u inmanta -- systemctl --user start inmanta-orchestrator-server.service

You should be able to reach the orchestrator at this address: `http://127.0.0.1:8888 <http://127.0.0.1:8888>`_ on the host.

(Optional) To make sure the orchestrator is started when the host is booted, enable the container services:

.. tab-set::

    .. tab-item:: User setup
        :sync: rootless-setup

        .. code-block:: console

            $ systemctl --user enable inmanta-orchestrator-db.service
            $ systemctl --user enable inmanta-orchestrator-server.service

    .. tab-item:: Root setup
        :sync: rootful-setup

        .. code-block:: console

            # sudo -i -u inmanta -- systemctl --user enable inmanta-orchestrator-db.service
            # sudo -i -u inmanta -- systemctl --user enable inmanta-orchestrator-server.service

Troubleshooting
###############

If the orchestrator doesn't seem to come up, the first thing to check are its logs.

In this setup, the container is managed by systemd, and the logs of the container process are saved in the journal.  To access them, simply use ``journalctl``:

.. tab-set::

    .. tab-item:: User setup
        :sync: rootless-setup

        .. code-block:: console

            $ journalctl --user-unit inmanta-orchestrator-server.service

    .. tab-item:: Root setup
        :sync: rootful-setup

        .. code-block:: console

            # sudo -i -u inmanta -- journalctl --user-unit inmanta-orchestrator-server.service

If the user running the container can not access the journal, because it is not part of any of the authorized groups, the alternative is to check the logs directly using ``podman logs``:

.. tab-set::

    .. tab-item:: User setup
        :sync: rootless-setup

        .. code-block:: console

            $ systemctl --user start inmanta-orchestrator-server.service; podman logs -f inmanta-orchestrator

    .. tab-item:: Root setup
        :sync: rootful-setup

        .. code-block:: console

            # sudo -i -u inmanta
            $ systemctl --user start inmanta-orchestrator-server.service; podman logs -f inmanta-orchestrator

Overwrite default server configuration
######################################

If you want to change the default server configuration, the recommended way is to provide the server
config options via environment variables as done in the above example.
All the different options and associated environment variables are described :ref:`here<config_reference>`.
It is also possible to provide a configuration file. Make sure to mount it in ``/etc/inmanta/inmanta.cfg``.
Be aware that values provided in the configuration file are overwritten by values provided in environment variables, and that
the orchestrator image contains some `default environment variable values <https://raw.githubusercontent.com/inmanta/inmanta/refs/heads/master/docker/native_image/Dockerfile#:~:text=ENV>`_.

Setting environment variables
#############################

The inmanta server will share any environment variable it received from podman with all its compiler and agent sub processes.  So if you need
to make some environment variables available to the compiler or agent, you can simply tell podman to pass them on to the orchestrator container.
In the example shown above, this can be done by using either of the ``Environment`` or ``EnvironmentFile`` options in the orchestrator container unit (``inmanta-orchestrator-server.container``).
More details about these options can be found in `podman's documentation <https://docs.podman.io/en/latest/markdown/podman-container.unit.5.html#environment-env-value-env-value>`_.

Accessing the orchestrator file system
######################################

If you want to have a look inside the running orchestrator container, it contains a traditional file system, you can enter it using ``podman exec`` on the host where the container is running:

.. tab-set::

    .. tab-item:: User setup
        :sync: rootless-setup

        .. code-block:: console

            $ podman exec -ti inmanta-orchestrator bash

    .. tab-item:: Root setup
        :sync: rootful-setup

        .. code-block:: console

            # sudo -i -u inmanta -- podman exec -ti inmanta-orchestrator bash

Mounting files/directories
##########################

The recommended way to persist the orchestrator data is to use podman volumes, as shown in the example above.
However if you really need to mount a file or directory from the host, you can use bind mounts.
You just need to make sure to configure podman to map your user on the host to the inmanta user inside the container.
This can be done easily using the ``UIDMap`` and ``GIDMap`` options as shown in the example above.

Log rotation
############

By default, the container won't do any log rotation, to let you the choice of dealing with the logs
according to your own preferences.
