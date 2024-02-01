.. _install-server-with-podman:

Install Inmanta with Podman and Systemd
***************************************

This page explains how to setup an Inmanta orchestration server using Podman and Systemd.
This guide assumes you already have `Podman <http://podman.io/>`_ installed on your machine and that you are running a Linux distribution using Systemd.

.. note::
    The instructions below will show you how to install the orchestrator, and make the orchestrator run as a non-root user on the host.  To achieve this
    you can either follow the rootless instructions (``User setup``), running them as a simple user without elevated privileged, or as root (``Root setup``).  
    If you follow the latter, make sure to create a system user that we will use to run the orchestrator process.  We will assume in the next steps that such
    system user is named ``inmanta`` and its ``HOME`` folder is ``/var/lib/inmanta``.


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

2.  The user that will run the orchestrator has the ``runRoot`` folder configured as follow.

    .. tab-set::

        .. tab-item:: User setup
            :sync: rootless-setup

            .. code-block:: console

                $ podman info | grep runRoot
                  runRoot: /run/user/1000/containers

            The value ``1000`` should match the id of your user.

            .. code-block:: console

                $ id -u
                1000

        .. tab-item:: Root setup
            :sync: rootful-setup

            .. code-block:: console

                # sudo -i -u inmanta -- podman info | grep runRoot
                  runRoot: /run/inmanta/containers
            
            We overwrite the default value that podman will set for this system user for two reasons:  

            1.  The default values it picks depends on the way you used ``podman`` for the first time with this user.
            2.  The default values it picks will contain the id of the ``inmanta`` user in its path, which we don't want to make any assumption about in the next steps.

            You can change this value by updating the file at ``/var/lib/inmanta/.config/containers/storage.conf``, making sure this entry is in the configuration:

            .. code-block::

                [storage]
                runroot = "/run/inmanta/containers"

            Then create the folder and reset podman.

            .. code-block:: console

                # mkdir -p /run/inmanta
                # chown -R inmanta:inmanta /run/inmanta
                # sudo -i -u inmanta -- podman system reset -f
                A "/var/lib/inmanta/.config/containers/storage.conf" config file exists.
                Remove this file if you did not modify the configuration.


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


Prepare the orchestrator configuration
######################################

1.  Get the default configuration file:

    As of now, the container cannot be configured with environment variables, we should use a configuration file, mounted inside the container.
    To do this, you can get the current configuration file from the container, edit it, and mount it where it should be in the container.

    .. tab-set::

        .. tab-item:: User setup
            :sync: rootless-setup

            Let's create a file on the host at ``~/.config/inmanta/inmanta.cfg``. We can take as template the default file already packaged in our
            container image.

            .. only:: oss

                .. code-block:: console

                    $ mkdir -p ~/.config/inmanta
                    $ podman run --rm ghcr.io/inmanta/orchestrator:latest cat /etc/inmanta/inmanta.cfg > ~/.config/inmanta/inmanta.cfg

            .. only:: iso

                .. code-block:: console
                    :substitutions:

                    $ mkdir -p ~/.config/inmanta
                    $ podman run --rm containers.inmanta.com/containers/service-orchestrator:|version_major| cat /etc/inmanta/inmanta.cfg > ~/.config/inmanta/inmanta.cfg

        .. tab-item:: Root setup
            :sync: rootful-setup

            Let's create a file on the host at ``/etc/inmanta/inmanta.cfg``. We can take as template the default file already packaged in our
            container image.

            .. only:: oss

                .. code-block:: console

                    # mkdir -p /etc/inmanta
                    # chown -R inmanta:inmanta /etc/inmanta
                    # sudo -i -u inmanta -- podman run --rm ghcr.io/inmanta/orchestrator:latest cat /etc/inmanta/inmanta.cfg | sudo -i -u inmanta -- tee /etc/inmanta/inmanta.cfg

            .. only:: iso

                .. code-block:: console
                    :substitutions:

                    # mkdir -p /etc/inmanta
                    # chown -R inmanta:inmanta /etc/inmanta
                    # sudo -i -u inmanta -- podman run --rm containers.inmanta.com/containers/service-orchestrator:|version_major| cat /etc/inmanta/inmanta.cfg | sudo -i -u inmanta -- tee /etc/inmanta/inmanta.cfg

2.  Update database settings:

    It is very unlikely that your database setup will match the one described in the default config we just got.  Update the configuration in the ``[database]`` section
    to reflect the setup you have.

    .. note::
        The setup described here assumes you already have a PostgreSQL instance available that the orchestrator can use for its persistent storage.  If it is not the case, 
        please :ref:`jump to the end of this document<install-postgresql-with-podman>`, where we explain to you how to easily deploy a database using Postman and Systemd.

3.  Make sure that there is a folder on your host that can persist all the logs of the server and that it is owned by the user running the orchestrator service.  

    .. tab-set::

        .. tab-item:: User setup
            :sync: rootless-setup

            In this setup, the log folder on the host will be ``~/.local/share/inmanta-orchestrator-server/logs``.

            .. code-block:: console

                $ mkdir -p ~/.local/share/inmanta-orchestrator-server/logs

        .. tab-item:: Root setup
            :sync: rootful-setup

            In this setup, the log folder on the host will be ``/var/log/inmanta``.

            .. code-block:: console

                # mkdir -p /var/log/inmanta
                # chown -R inmanta:inmanta /var/log/inmanta

    .. warning:: 
        Inside of the container, this folder will be mounted at ``/var/log/inmanta`` as it is the default location where the orchestrator saves its logs.  This
        location is configurable in the orchestrator configuration file.  If you for any reason would change this location in the configuration, make sure to update any usage
        of the ``/var/log/inmanta`` folder in the next installation steps.

.. only:: iso

    4.  Get the license files:

        Together with the access to the inmanta container repo, you should also have received a license and an entitlement file. The orchestrator will need them
        in order to run properly.  You can also place them in a config directory on your host.  
        
        .. tab-set::

            .. tab-item:: User setup
                :sync: rootless-setup

                After this step, we assume that this folder is ``~/.config/inmanta/license/`` and that both files are named ``com.inmanta.license`` 
                and ``com.inmanta.jwe`` respectively.

                .. code-block:: console

                    $ tree .config/inmanta
                    .config/inmanta
                    ├── inmanta.cfg
                    └── license
                        ├── com.inmanta.jwe
                        └── com.inmanta.license

                    2 directories, 3 files

            .. tab-item:: Root setup
                :sync: rootful-setup

                After this step, we assume that this folder is ``/etc/inmanta/license/`` and that both files are named ``com.inmanta.license`` 
                and ``com.inmanta.jwe`` respectively.

                .. code-block:: console

                    # tree /etc/inmanta
                    /etc/inmanta
                    ├── inmanta.cfg
                    └── license
                        ├── com.inmanta.jwe
                        └── com.inmanta.license

                    2 directories, 3 files


.. _setup-systemd-unit:

Start the server with systemd
#############################

Here is a systemd unit file that can be used to deploy the server on your machine.

.. tab-set::

    .. tab-item:: User setup
        :sync: rootless-setup

        .. only:: oss

            .. code-block:: systemd

                [Unit]
                Description=Podman 
                Documentation=https://docs.inmanta.com
                Wants=network-online.target
                After=network-online.target
                RequiresMountsFor=%t/containers

                [Service]
                Environment=PODMAN_SYSTEMD_UNIT=%n
                Restart=on-failure
                TimeoutStopSec=70
                ExecStart=/usr/bin/podman run \
                        --cidfile=%t/%n.ctr-id \
                        --cgroups=no-conmon \
                        --sdnotify=conmon \
                        -d \
                        --replace \
                        --publish=127.0.0.1:8888:8888 \
                        --uidmap=993:0:1 \
                        --uidmap=0:1:993 \
                        --uidmap=994:994:64543 \
                        --gidmap=993:0:1 \
                        --gidmap=0:1:993 \
                        --gidmap=994:994:64543 \
                        --name=inmanta-orchestrator-server \
                        --volume=%E/inmanta/inmanta.cfg:/etc/inmanta/inmanta.cfg:z \
                        --volume=%h/.local/share/inmanta-orchestrator-server/logs:/var/log/inmanta:z \
                        --entrypoint=/usr/bin/inmanta \
                        --user=993:993 \
                        ghcr.io/inmanta/orchestrator:latest \
                        --log-file /var/log/inmanta/server.log --log-file-level 2 --timed-logs server
                ExecStop=/usr/bin/podman stop \
                        --ignore -t 10 \
                        --cidfile=%t/%n.ctr-id
                ExecStopPost=/usr/bin/podman rm \
                        -f \
                        --ignore -t 10 \
                        --cidfile=%t/%n.ctr-id
                Type=notify
                NotifyAccess=all

                [Install]
                WantedBy=default.target

        .. only:: iso

            .. code-block:: systemd
                :substitutions:

                [Unit]
                Description=Podman 
                Documentation=https://docs.inmanta.com
                Wants=network-online.target
                After=network-online.target
                RequiresMountsFor=%t/containers

                [Service]
                Environment=PODMAN_SYSTEMD_UNIT=%n
                Restart=on-failure
                TimeoutStopSec=70
                ExecStart=/usr/bin/podman run \
                        --cidfile=%t/%n.ctr-id \
                        --cgroups=no-conmon \
                        --sdnotify=conmon \
                        -d \
                        --replace \
                        --publish=127.0.0.1:8888:8888 \
                        --uidmap=993:0:1 \
                        --uidmap=0:1:993 \
                        --uidmap=994:994:64543 \
                        --gidmap=993:0:1 \
                        --gidmap=0:1:993 \
                        --gidmap=994:994:64543 \
                        --name=inmanta-orchestrator-server \
                        --volume=%E/inmanta/inmanta.cfg:/etc/inmanta/inmanta.cfg:z \
                        --volume=%E/inmanta/license/com.inmanta.license:/etc/inmanta/license/com.inmanta.license:z \
                        --volume=%E/inmanta/license/com.inmanta.jwe:/etc/inmanta/license/com.inmanta.jwe:z \
                        --volume=%h/.local/share/inmanta-orchestrator-server/logs:/var/log/inmanta:z \
                        --entrypoint=/usr/bin/inmanta \
                        --user=993:993 \
                        containers.inmanta.com/containers/service-orchestrator:|version_major| \
                        --log-file /var/log/inmanta/server.log --log-file-level 2 --timed-logs server
                ExecStop=/usr/bin/podman stop \
                        --ignore -t 10 \
                        --cidfile=%t/%n.ctr-id
                ExecStopPost=/usr/bin/podman rm \
                        -f \
                        --ignore -t 10 \
                        --cidfile=%t/%n.ctr-id
                Type=notify
                NotifyAccess=all

                [Install]
                WantedBy=default.target


        You can paste this configuration in a file named ``inmanta-orchestrator-server.service`` in the systemd folder for your user.
        This folder is typically ``~/.config/systemd/user/``.

    .. tab-item:: Root setup
        :sync: rootful-setup

        .. only:: oss

            .. code-block:: systemd

                [Unit]
                Description=Podman 
                Documentation=https://docs.inmanta.com
                Wants=network-online.target
                After=network-online.target
                RequiresMountsFor=/run/inmanta/containers

                [Service]
                User=inmanta
                Group=inmanta
                Environment=PODMAN_SYSTEMD_UNIT=%n
                Restart=on-failure
                TimeoutStopSec=70
                ExecStart=/usr/bin/podman run \
                        --cidfile=/run/inmanta/%n.ctr-id \
                        --cgroups=no-conmon \
                        --sdnotify=conmon \
                        -d \
                        --replace \
                        --publish=127.0.0.1:8888:8888 \
                        --uidmap=993:0:1 \
                        --uidmap=0:1:993 \
                        --uidmap=994:994:64543 \
                        --gidmap=993:0:1 \
                        --gidmap=0:1:993 \
                        --gidmap=994:994:64543 \
                        --name=inmanta-orchestrator-server \
                        --volume=/etc/inmanta/inmanta.cfg:/etc/inmanta/inmanta.cfg:z \
                        --volume=/var/log/inmanta:/var/log/inmanta:z \
                        --entrypoint=/usr/bin/inmanta \
                        --user=993:993 \
                        ghcr.io/inmanta/orchestrator:latest \
                        --log-file /var/log/inmanta/server.log --log-file-level 2 --timed-logs server
                ExecStop=/usr/bin/podman stop \
                        --ignore -t 10 \
                        --cidfile=/run/inmanta/%n.ctr-id
                ExecStopPost=/usr/bin/podman rm \
                        -f \
                        --ignore -t 10 \
                        --cidfile=/run/inmanta/%n.ctr-id
                Type=notify
                NotifyAccess=all

                [Install]
                WantedBy=default.target

        .. only:: iso

            .. code-block:: systemd
                :substitutions:

                [Unit]
                Description=Podman 
                Documentation=https://docs.inmanta.com
                Wants=network-online.target
                After=network-online.target
                RequiresMountsFor=/run/inmanta/containers

                [Service]
                User=inmanta
                Group=inmanta
                Environment=PODMAN_SYSTEMD_UNIT=%n
                Restart=on-failure
                TimeoutStopSec=70
                ExecStart=/usr/bin/podman run \
                        --cidfile=/run/inmanta/%n.ctr-id \
                        --cgroups=no-conmon \
                        --sdnotify=conmon \
                        -d \
                        --replace \
                        --publish=127.0.0.1:8888:8888 \
                        --uidmap=993:0:1 \
                        --uidmap=0:1:993 \
                        --uidmap=994:994:64543 \
                        --gidmap=993:0:1 \
                        --gidmap=0:1:993 \
                        --gidmap=994:994:64543 \
                        --name=inmanta-orchestrator-server \
                        --volume=/etc/inmanta/inmanta.cfg:/etc/inmanta/inmanta.cfg:z \
                        --volume=/etc/inmanta/license/com.inmanta.license:/etc/inmanta/license/com.inmanta.license:z \
                        --volume=/etc/inmanta/license/com.inmanta.jwe:/etc/inmanta/license/com.inmanta.jwe:z \
                        --volume=/var/log/inmanta:/var/log/inmanta:z \
                        --entrypoint=/usr/bin/inmanta \
                        --user=993:993 \
                        containers.inmanta.com/containers/service-orchestrator:|version_major| \
                        --log-file /var/log/inmanta/server.log --log-file-level 2 --timed-logs server
                ExecStop=/usr/bin/podman stop \
                        --ignore -t 10 \
                        --cidfile=/run/inmanta/%n.ctr-id
                ExecStopPost=/usr/bin/podman rm \
                        -f \
                        --ignore -t 10 \
                        --cidfile=/run/inmanta/%n.ctr-id
                Type=notify
                NotifyAccess=all

                [Install]
                WantedBy=default.target

        You can paste this configuration in a file named ``inmanta-orchestrator-server.service`` in the systemd folder ``/etc/systemd/system``.

.. note::
    In the configuration above, you can observe that the usage of the ``--uidmap`` and ``--gidmap`` options.  We use them three times to do the following:
        1.  Map the user ``993`` inside of the container (the container's ``inmanta`` user) to the user ``0`` in the podman user namespace.
            This user ``0`` in the user namespace is actually itself mapped to the user running the ``podman run`` command on the host.
        2.  Map all users from ``0`` to ``65536`` (except for ``993``) inside of the container to subids of the host user running the container.

    This allow us to easily share files between the host user and the ``inmanta`` user inside the container, avoiding any ownership conflict as they
    are then the same user (just seen from a different user namespace).
    Strictly speaking, if the image is already pulled on the host, you might get away with mapping only the ``inmanta`` 
    (``--uidmap=993:0:1 --gidmap=993:0:1``) and the ``root`` (``--uidmap=0:1:1 --gidmap=0:1:1``) user and group inside of the container. 
    But you would face issue if the container image was deleted from your host and the ``run`` command in the unit file tried to automatically
    pull the image, as the container image does contain a lot more users and groups than ``inmanta`` and ``root`` in its filesystem.

Once the systemd unit files are in place, make sure to enable them and reload the systemctl daemon.

.. tab-set::

    .. tab-item:: User setup
        :sync: rootless-setup
        
        .. code-block:: console

            $ systemctl --user daemon-reload
            $ systemctl --user enable inmanta-orchestrator-server.service

    .. tab-item:: Root setup
        :sync: rootful-setup

        .. code-block:: console

            # systemctl daemon-reload
            # systemctl enable inmanta-orchestrator-server.service

Then start the container by running the following command:

.. tab-set::

    .. tab-item:: User setup
        :sync: rootless-setup

        .. code-block:: console

            $ systemctl --user start inmanta-orchestrator-server.service

    .. tab-item:: Root setup
        :sync: rootful-setup

        .. code-block:: console

            # systemctl start inmanta-orchestrator-server.service

You should be able to reach the orchestrator at this address: `http://127.0.0.1:8888 <http://127.0.0.1:8888>`_ on the host.


Setting environment variables
#############################

You might want your inmanta server to be able to use some environment variables.
You can set the environment variables by updating your Systemd unit file, relying on the ``--env/--env-file``
options of the ``podman run`` command.  Those variables will be accessible to the inmanta server, the compiler
and any agent started by the server.


Log rotation
############

By default, the container won't do any log rotation, we let you the choice of dealing with the logs
according to your own preferences.  We recommend you to setup some log rotation, for example using a logrotate service running on
your host.


.. _install-postgresql-with-podman:

Deploy postgresql with podman and systemd
#########################################

.. tab-set::

    .. tab-item:: User setup
        :sync: rootless-setup

        1.  Pull the postgresql image from dockerhub.

            .. code-block:: console

                $ podman pull docker.io/library/postgres:13

        2.  Create a podman network for your database and the orchestrator.

            .. code-block:: console

                $ podman network create --subnet 172.42.0.0/24 inmanta-orchestrator-net

        3.  Create a systemd unit file for your database, let's name it ``~/.config/systemd/user/inmanta-orchestrator-db.service``.

            .. code-block:: systemd

                [Unit]
                Description=Podman 
                Documentation=https://docs.inmanta.com
                Wants=network-online.target
                After=network-online.target
                RequiresMountsFor=%t/containers

                [Service]
                Environment=PODMAN_SYSTEMD_UNIT=%n
                Restart=on-failure
                TimeoutStopSec=70
                ExecStart=/usr/bin/podman run \
                        --cidfile=%t/%n.ctr-id \
                        --cgroups=no-conmon \
                        --sdnotify=conmon \
                        -d \
                        --replace \
                        --network=inmanta-orchestrator-net:ip=172.42.0.2 \
                        --uidmap=999:0:1 \
                        --uidmap=0:1:999 \
                        --uidmap=1000:1000:64537 \
                        --gidmap=999:0:1 \
                        --gidmap=0:1:999 \
                        --gidmap=1000:1000:64537 \
                        --name=inmanta-orchestrator-db \
                        --volume=%h/.local/share/inmanta-orchestrator-db/data:/var/lib/postgresql/data:z \
                        --env=POSTGRES_USER=inmanta \
                        --env=POSTGRES_PASSWORD=inmanta \
                        docker.io/library/postgres:13 
                ExecStop=/usr/bin/podman stop \
                        --ignore -t 10 \
                        --cidfile=%t/%n.ctr-id
                ExecStopPost=/usr/bin/podman rm \
                        -f \
                        --ignore -t 10 \
                        --cidfile=%t/%n.ctr-id
                Type=notify
                NotifyAccess=all

                [Install]
                WantedBy=default.target

        4.  Create the folder that will contain the persistent storage for the database: ``~/.local/shared/inmanta-orchestrator-db/data``.

            .. code-block:: console

                $ mkdir -p ~/.local/share/inmanta-orchestrator-db/data

        5.  Reload the systemd daemon, enable the service, and start it.

            .. code-block:: console

                $ systemctl --user daemon-reload
                $ systemctl --user enable inmanta-orchestrator-db.service
                $ systemctl --user start inmanta-orchestrator-db.service

        6.  In the unit file of the orchestrator (as described :ref:`here<setup-systemd-unit>`), make sure to attach the orchestrator
            container to the network the database is a part of, using the ``--network`` option of the ``podman run`` command.

        7.  Don't forget to update the ip address of the database in the inmanta server configuration file (``~/.config/inmanta/inmanta.cfg``)!

    .. tab-item:: Root setup
        :sync: rootful-setup

        For a proper install of postgres on your host system as root, please refer to the postgres documentation regarding your operating system.
