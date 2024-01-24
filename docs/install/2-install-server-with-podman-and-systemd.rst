.. _install-server-with-podman:

Install Inmanta with Podman and Systemd
***************************************

This page explains how to setup an orchestration server using podman and systemd.
This guide assumes you already have `podman <http://podman.io/>`_ installed on your machine and that you are running a linux distribution with systemd.

.. note::
    The full setup should be doable without any root privilege (rootless) on the host, running the orchestrator with your current user.  

.. warning::
    The setup described below assumes you already have a postgresql instance available that the orchestrator can use for its persistent storage.  If it is not the case, 
    please jump to the end of this document, where we explain to you how to easily deploy a database using postman and systemd: :ref:`here<install-postgresql-with-podman>`


Pull the image
##############

.. only:: oss

    Use ``podman pull`` to get the desired image:

    .. code-block:: sh

        podman pull ghcr.io/inmanta/orchestrator:latest


    This command will pull the latest version of the Inmanta OSS Orchestrator image.

.. only:: iso

    Step 1: Log in to container registry
    -------------------------------------

    Connect to the container registry using your entitlement token.

    .. code-block:: console

        $ podman login containers.inmanta.com
        Username: containers
        Password: <your-entitlement-token>

        Login Succeeded
        $


    Replace ``<your-entitlement-token>`` with the entitlement token provided with your license.


    Step 2: Pull the image
    ----------------------

    Use ``podman pull`` to get the desired image:

    .. code-block:: sh
        :substitutions:

        podman pull containers.inmanta.com/containers/service-orchestrator:|version_major|


    This command will pull the latest version of the Inmanta Service Orchestrator image.


Prepare the orchestrator configuration
######################################

1.  Get configuration file.
    As of now, the container can not be configured with environment variables, we should use a configuration file, mounted inside of the container.
    To do this, you can get the current configuration file from the container, edit it, and mount it where it should be in the container.
    Let's create a file at ``~/.config/inmanta/inmanta.cfg``, we can take as template the default file already packaged in our
    container image.

    .. only:: oss

        .. code-block:: sh

            mkdir -p ~/.config/inmanta
            podman run --rm -ti ghcr.io/inmanta/orchestrator:latest cat /etc/inmanta/inmanta.cfg > ~/.config/inmanta/inmanta.cfg

    .. only:: iso

        .. code-block:: sh
            :substitutions:

            mkdir -p ~/.config/inmanta
            podman run --rm -ti containers.inmanta.com/containers/service-orchestrator:|version_major| cat /etc/inmanta/inmanta.cfg > ~/.config/inmanta/inmanta.cfg

2.  Update database settings
    It is very unlikely that your database setup will match the one described in the default config we just got.  Update the configuration in the ``[database]`` section
    to reflect the setup you have.

.. only:: iso

    3.  Get the license files
        Together with the access to the inmanta container repo, you should also have received a license and an entitlement files.  The orchestrator will need them
        in order to run properly.  You can also place them in a config directory on your host.  After this step, we assume that this folder is
        ``~/.config/inmanta/license/`` and that both files are named ``com.inmanta.license`` and ``com.inmanta.jwe`` respectively.

        .. code-block:: console

            $ tree .config/inmanta
            .config/inmanta
            ├── inmanta.cfg
            └── license
                ├── com.inmanta.jwe
                └── com.inmanta.license

            2 directories, 3 files


.. _setup-systemd-unit:

Start the server with systemd
#############################

Here is a systemd unit file that can be used to deploy the server on your machine.

.. only:: oss

    .. code-block:: 

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
                --gidmap=993:0:1 \
                --gidmap=0:1:993 \
                --name=inmanta-orchestrator-server \
                --volume=%E/inmanta/inmanta.cfg:/etc/inmanta/inmanta.cfg:z \
                --entrypoint=/usr/bin/inmanta \
                --user=993:993 \
                ghcr.io/inmanta/orchestrator:latest \
                -vvv --timed-logs server
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

    .. code-block:: 
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
                --gidmap=993:0:1 \
                --gidmap=0:1:993 \
                --name=inmanta-orchestrator-server \
                --volume=%E/inmanta/inmanta.cfg:/etc/inmanta/inmanta.cfg:z \
                --volume=%E/inmanta/license/com.inmanta.license:/etc/inmanta/license/com.inmanta.license:z \
                --volume=%E/inmanta/license/com.inmanta.jwe:/etc/inmanta/license/com.inmanta.jwe:z \
                --entrypoint=/usr/bin/inmanta \
                --user=993:993 \
                containers.inmanta.com/containers/service-orchestrator:|version_major| \
                -vvv --timed-logs server
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

Once the systemd unit files are in place, make sure to enable them and reload the systemctl daemon.

.. code-block:: sh

    systemctl --user daemon-reload
    systemctl --user enable inmanta-orchestrator-server.service

Then start the container by running the following command:

.. code-block:: sh

    systemctl --user start inmanta-orchestrator-server.service

You should be able to reach the orchestrator at this address: `http://127.0.0.1:8888 <http://127.0.0.1:8888>`_.


Setting environment variables
#############################

You might want your inmanta server to be able to use some environment variables.
You can set the environment by updating your systemd unit file, relying on the ``--env/--env-file``
options of the ``podman run`` command.  Those variables will be accessible to the inmanta server, the compiler,
and any agent started by the server.


Log rotation
############

By default, the container won't do any log rotation, to let you the choice of dealing with the logs
according to your own preferences.  We recommend that you do so by mounting a folder inside of the container
at the following path: ``/var/log/inmanta``. This path contains all the logs of inmanta (unless you specified
a different path in the config of the server).


.. _install-postgresql-with-podman:

Deploy postgresql with podman and systemd
#########################################

1.  Pull the postgresql image from dockerhub.

    .. code-block:: sh

        podman pull docker.io/library/postgres:13

2.  Create a podman network for your database and the orchestrator.

    .. code-block:: sh

        podman network create --subnet 172.42.0.0/24 inmanta-orchestrator-net

3.  Create a systemd unit file for your database, let's name it ``~/.config/systemd/user/inmanta-orchestrator-db.service``.

    .. code-block::

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
                --gidmap=999:0:1 \
                --gidmap=0:1:999 \
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

4.  Create the folder that will container the persistent storage for the database: ``~/.local/shared/inmanta-orchestrator-db/data``.

    .. code-block:: sh

        mkdir -p ~/.local/share/inmanta-orchestrator-db/data

5.  Reload the systemd daemon, enable the service, and start it.

    .. code-block:: sh

        systemctl --user daemon-reload
        systemctl --user enable inmanta-orchestrator-db.service
        systemctl --user start inmanta-orchestrator-db.service

6.  In the unit file of the orchestrator (as described :ref:`here<setup-systemd-unit>`), make sure to attach the orchestrator
    container to the network the database is a part of, using the ``--network`` option of the ``podman run`` command.

7.  Don't forget to update the ip address of the database in the inmanta server configuration file (``~/.config/inmanta/inmanta.cfg``)!
