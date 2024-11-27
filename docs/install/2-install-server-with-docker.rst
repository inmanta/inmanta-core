.. _install-server-with-docker:

Install Inmanta with Docker
***************************

This page explains how to setup an orchestration server using docker.
This guide assumes you already have `docker <https://docs.docker.com/get-docker/>`_ and `docker-compose <https://docs.docker.com/compose/install/>`_ installed on your machine.

Pull the image
##############

.. only:: oss

    Use docker pull to get the desired image:

    .. code-block:: sh

        docker pull ghcr.io/inmanta/orchestrator:latest


    This command will pull the latest version of the Inmanta OSS Orchestrator image.

.. only:: iso

    Step 1: Log in to Cloudsmith registry
    -------------------------------------

    Connect to the Cloudsmith registry using your entitlement token.

    .. code-block:: console

        $ docker login containers.inmanta.com
        Username: containers
        Password: <your-entitlement-token>

        Login Succeeded
        $


    Replace ``<your-entitlement-token>`` with the entitlement token provided with your license.


    Step 2: Pull the image
    ----------------------

    Use docker pull to get the desired image:

    .. code-block:: sh
       :substitutions:

        docker pull containers.inmanta.com/containers/service-orchestrator:|version_major|


    This command will pull the latest version of the Inmanta Service Orchestrator image.

Start the server with docker-compose
####################################

Here is a minimalistic docker-compose file content that can be used to deploy the server on your machine.



.. only:: oss

    .. code-block:: yaml

        version: '3'
        services:
            postgres:
                container_name: inmanta_db
                image: postgres:13
                environment:
                    POSTGRES_USER: inmanta
                    POSTGRES_PASSWORD: inmanta
                    PGDATA: /var/lib/postgresql/data/pgdata
                networks:
                    inm_net:
                        ipv4_address: 172.30.0.2
                volumes:
                    - pgdata:/var/lib/postgresql/data
            inmanta-server:
                container_name: inmanta_orchestrator
                image: ghcr.io/inmanta/orchestrator:latest
                environment:
                    INMANTA_DATABASE_HOST: 172.30.0.2
                    INMANTA_DATABASE_USERNAME: inmanta
                    INMANTA_DATABASE_PASSWORD: inmanta
                ports:
                    - 8888:8888
                networks:
                    inm_net:
                        ipv4_address: 172.30.0.3
                volumes:
                    - server-data:/var/lib/inmanta
                    - server-logs:/var/logs/inmanta
                depends_on:
                    - "postgres"

        networks:
            inm_net:
                ipam:
                    driver: default
                    config:
                        - subnet: 172.30.0.0/16

        volumes:
            pgdata: {}
            server-data: {}
            server-logs: {}


.. only:: iso

    .. code-block:: yaml
       :substitutions:

        version: '3'
        services:
            postgres:
                container_name: inmanta_db
                image: postgres:13
                environment:
                    POSTGRES_USER: inmanta
                    POSTGRES_PASSWORD: inmanta
                    PGDATA: /var/lib/postgresql/data/pgdata
                networks:
                    inm_net:
                        ipv4_address: 172.30.0.2
                volumes:
                    - type: volume
                      source: pgdata
                      target: /var/lib/postgresql/data
            inmanta-server:
                container_name: inmanta_orchestrator
                image: containers.inmanta.com/containers/service-orchestrator:|version_major|
                environment:
                    INMANTA_DATABASE_HOST: 172.30.0.2
                    INMANTA_DATABASE_USERNAME: inmanta
                    INMANTA_DATABASE_PASSWORD: inmanta
                    INMANTA_LICENSE_ENTITLEMENT_FILE: /etc/inmanta/license/com.inmanta.jwe
                    INMANTA_LICENSE_LICENSE_KEY: /etc/inmanta/license/com.inmanta.license
                ports:
                    - 8888:8888
                volumes:
                    - server-data:/var/lib/inmanta
                    - server-logs:/var/logs/inmanta
                    - ./resources/com.inmanta.license:/etc/inmanta/license/com.inmanta.license
                    - ./resources/com.inmanta.jwe:/etc/inmanta/license/com.inmanta.jwe
                networks:
                    inm_net:
                        ipv4_address: 172.30.0.3
                depends_on:
                    - "postgres"

        networks:
            inm_net:
                ipam:
                    driver: default
                    config:
                        - subnet: 172.30.0.0/16

        volumes:
            pgdata: {}
            server-data: {}
            server-logs: {}

    You can paste this script in a file named `docker-compose.yml` and ensure you have you license files available.
    With the proposed config, they should be located in a ``resources/`` folder on the side of the docker-compose file you create,
    and the license files should be named ``com.inmanta.license`` and ``com.inmanta.jwe``. You can of course update the content
    of the docker-compose file to match your current configuration.
    Then bring the containers up by running the following command:

.. code-block:: sh

    docker-compose up

You should be able to reach the orchestrator to this address: `http://172.30.0.3:8888 <http://172.30.0.3:8888>`_.

The PostgreSQL server started by the above-mentioned docker-compose file has a named volume ``pgdata`` attached. This
means that no data will be lost when the PostgreSQL container restarts. Pass the ``-v`` option to the
``docker-compose down`` to remove the volume.  The same applies to the data and logs folders of the orchestrator container.

When using a different setup than the one mentioned above, you should overwrite the server config with one
matching your needs.  You can find more instructions for overwriting the config in a following section,
:ref:`here<docker_overwrite_server_conf>`.

.. warning::
    We don't recommend using the setup described above as a production environment. Hosting a database in a
    container as shown here is not ideal in term of performance, reliability and raises some serious data
    persistence concerns.


.. _docker_overwrite_server_conf:

Overwrite default server configuration
######################################

By default the server will use the file located in the image at ``/etc/inmanta/inmanta.cfg``.
If you want to overwrite any configuration value provided in there, the recommended way is to simply
set the environment variable corresponding to the configuration option on the container itself, as it
is done for the database host in the example above.

Access the orchestrator file system
###################################

The orchestrator container is only meant to run the inmanta server and its own components (compiler, scheduler, agents, ...).  
For previous versions of the container image, it was possible to also run an ssh server in the image, this is not supported anymore.
To access the file system of the orchestrator, you can either use `docker exec` or ssh in another container which shares the relevant
volumes with the orchestrator.

1. Using `docker exec`.

This is the simple solution, if the process that needs access to the orchestrator file system has enough permissions to interact with the docker daemon.
In this scenario, simply use `docker exec` to open a shell inside the container.

.. code-block:: sh

    # This command should be executed on the host where the orchestrator container is running
    docker exec -ti inmanta_orchestrator bash

If you didn't use the same docker compose file as shown above, you might have to adapt the name of the container from `inmanta_orchestrator` to the one that matches the orchestrator.

2. Using an ssh sidecar.

This solution is more advanced and only makes sense when the process that needs access to the orchestrator file system should not have any elevated privileges on the host where the orchestrator container is running.  
You can deploy a second container which shares the volumes of the orchestrator so that you can read and modify the files located in them.  To do this, we recommend to simply run another container which uses as base
image the orchestrator image, installs sshd in there, and replaces the entrypoint by the ssh daemon.  If you are using the docker-compose setup shown above, you can simply extend it like this:

.. only:: oss

    .. code-block:: yaml

        version: '3'
        services:
            postgres:
                container_name: inmanta_db
                image: postgres:13
                environment:
                    POSTGRES_USER: inmanta
                    POSTGRES_PASSWORD: inmanta
                    PGDATA: /var/lib/postgresql/data/pgdata
                networks:
                    inm_net:
                        ipv4_address: 172.30.0.2
                volumes:
                    - pgdata:/var/lib/postgresql/data
            inmanta-server:
                container_name: inmanta_orchestrator
                image: ghcr.io/inmanta/orchestrator:latest
                environment:
                    INMANTA_DATABASE_HOST: 172.30.0.2
                    INMANTA_DATABASE_USERNAME: inmanta
                    INMANTA_DATABASE_PASSWORD: inmanta
                ports:
                    - 8888:8888
                networks:
                    inm_net:
                        ipv4_address: 172.30.0.3
                volumes:
                    - server-data:/var/lib/inmanta
                    - server-logs:/var/logs/inmanta
                depends_on:
                    - "postgres"
            ssh-sidecar:
                container_name: inmanta_orchestrator
                image: orchestrator-ssh-sidecar:|version_major|
                build:
                    context: .
                    dockerfile_inline: |
                        FROM ghcr.io/inmanta/orchestrator:latest
                        USER root:root
                        RUN apt-get install -y openssh-server && ssh-keygen -A
                        EXPOSE 22
                        ENTRYPOINT ["/usr/sbin/sshd"]
                        CMD ["-D"]
                ports:
                    - 2222:22
                networks:
                    inm_net:
                        ipv4_address: 172.30.0.4
                volumes:
                    - server-data:/var/lib/inmanta
                    - server-logs:/var/logs/inmanta
                    - ./resources/id_rsa.pub:/var/lib/inmanta/.ssh/authorized_keys

        networks:
            inm_net:
                ipam:
                    driver: default
                    config:
                        - subnet: 172.30.0.0/16

        volumes:
            pgdata: {}
            server-data: {}
            server-logs: {}


.. only:: iso

    .. code-block:: yaml
       :substitutions:


.. warning::
    This solution also has some limitations.  As the ssh daemon runs in another container, it doesn't share the same file system and namespaces.  Which means that the following actions will not be possible:
    - Check the processes running in the orchestrator container.
    - Modify the filesystem of the orchestrator outside of the shared volumes (`/var/logs/inmanta` and `/var/lib/inmanta`)
    - Reach the orchestrator api on localhost.
    - Check the environment variables that the orchestrator container has access to.


Waiting for the database
########################

Depending on you setup, you might want your container to wait for the database to be ready
to accept connections before starting the server (as this one would fail, trying to reach
the db).
You can do this by adding the following arguments to the startup command of the container:

.. code-block:: sh

    server --wait-for-host <your-db-host> --wait-for-port <your-db-port>


If you use docker-compose, it should look like:

.. code-block:: yaml

    inmanta-server:
        container_name: inmanta_orchestrator
        ...
        command: "server --wait-for-host <your-db-host> --wait-for-port <your-db-port>"


Setting environment variables
#############################

You might want your inmanta server to be able to reach some environment variables.
There are two ways you can achieve this:

    1.  Set the environment variables with docker, either using the ``--env`` argument or in your
        docker-compose file.  Those variables will be accessible to the inmanta server and any
        agent it starts, but not to any other process running in the container (if you for example
        login via ssh to the container and try to install a project again).

    2.  (Recommended) Set the environment variables in a file and mount it to the following path in the
        container: ``/etc/inmanta/env``.  This file will be loaded when starting the server and for
        every session that the inmanta user starts in the container.

.. only:: oss

    .. code-block:: yaml

        inmanta-server:
            container_name: inmanta_orchestrator
            image: ghcr.io/inmanta/orchestrator:latest
            ports:
                - 8888:8888
            volumes:
                - ./resources/my-server-conf.cfg:/etc/inmanta/inmanta.cfg
                - ./resources/my-env-file:/etc/inmanta/env

.. only:: iso

    .. code-block:: yaml
        :substitutions:

        inmanta-server:
            container_name: inmanta_orchestrator
            image: containers.inmanta.com/containers/service-orchestrator:|version_major|
            ports:
                - 8888:8888
            volumes:
                - ./resources/com.inmanta.license:/etc/inmanta/license/com.inmanta.license
                - ./resources/com.inmanta.jwe:/etc/inmanta/license/com.inmanta.jwe
                - ./resources/my-server-conf.cfg:/etc/inmanta/inmanta.cfg
                - ./resources/my-env-file:/etc/inmanta/env


Changing inmanta user/group id
##############################

If you mount a folder of your host in the container, and expect the inmanta user to interact with it,
you might face the issue that the inmanta user inside the container doesn't have ownership of the files.
You could fix this by changing the ownership in the container, but this change would also be reflected
on the host, meaning that you would lose the ownership of you files.  This is a very uncomfortable
situation.
While ``Podman`` has been offering the possibility to do a mapping of a user id in the container to a
user id on the host at runtime, which would solve our problem here, ``Docker`` still doesn't offer this
functionality.
The inmanta container allows you to change the user and group id of the inmanta user inside the
container when starting the container to match the user on the host, getting rid that way of any
conflict in the files ownership.

This can be done easily by simply setting those environment variables:
 - ``INMANTA_UID``: Will change, when starting the container, the id of the inmanta user.
 - ``INMANTA_GID``: Will change, when starting the container, the id of the inmanta group.

If you use docker-compose, you can simply update this section of the example above:

.. code-block:: yaml

    inmanta-server:
        container_name: inmanta_orchestrator
        ...
        environment:
            INMANTA_UID: 1000
            INMANTA_GID: 1000


Log rotation
############

By default, the container won't do any log rotation, to let you the choice of dealing with the logs
according to your own preferences.  We recommend that you do so by mounting a folder inside of the container
at the following path: ``/var/log``. This path contains all the logs of inmanta (unless you specified
a different path in the config of the server) and the logs of the SSH server.
