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
                image: postgres:16
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
                image: ghcr.io/inmanta/orchestrator:latest
                ports:
                    - 8888:8888
                environment:
                    INMANTA_DATABASE_HOST: inmanta_db
                    INMANTA_DATABASE_USERNAME: inmanta
                    INMANTA_DATABASE_PASSWORD: inmanta
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
            pgdata:


.. only:: iso

    .. code-block:: yaml
       :substitutions:

        version: '3'
        services:
            postgres:
                container_name: inmanta_db
                image: postgres:16
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
                ports:
                    - 8888:8888
                volumes:
                    - ./resources/com.inmanta.license:/etc/inmanta/license.key
                    - ./resources/com.inmanta.jwe:/etc/inmanta/entitlement.jwe
                environment:
                    INMANTA_DATABASE_HOST: inmanta_db
                    INMANTA_DATABASE_USERNAME: inmanta
                    INMANTA_DATABASE_PASSWORD: inmanta
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
            pgdata:

    You can paste this yaml snippet in a file named `docker-compose.yml` and ensure you have your license files available.
    With the proposed config, they should be located in a ``resources/`` folder on the side of the docker-compose file you create,
    and the license files should be named ``com.inmanta.license`` and ``com.inmanta.jwe``. You can of course update the content
    of the docker-compose file to match your current configuration.
    Then bring the containers up by running the following command:

.. code-block:: sh

    docker-compose up

You should be able to reach the orchestrator to this address: `http://172.30.0.3:8888 <http://172.30.0.3:8888>`_.

The PostgreSQL server started by the above-mentioned docker-compose file has a named volume ``pgdata`` attached. This
means that no data will be lost when the PostgreSQL container restarts. Pass the ``-v`` option to the
``docker-compose down`` to remove the volume.

The default server config assumes that the orchestrator can reach the database server on localhost.
To change this behavior you can use the environment variables as shown in the snippet above.
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

If you want to change the default server configuration, the recommended way is to provide the server
config options via environment variables as done in the above example.
All the different options and associated environment variables are described :ref:`here<config_reference>`.
It is also possible to provide a configuration file. Make sure to mount it in ``/etc/inmanta/inmanta.cfg``.

Starting the ssh server
#######################

By default, no ssh server is running in the container.  You don't need it to have a functional
orchestrator.
If you want to enable ssh anyway, for easy access to the orchestrator,
you can overwrite the startup command of the container with the following:

.. code-block:: sh

    server-with-ssh


If you use docker-compose, it should look like:

.. code-block:: yaml

    inmanta-server:
        container_name: inmanta_orchestrator
        ...
        command: "server-with-ssh"

.. warning::
    By default, the inmanta user doesn't have any password, if you want to ssh into the container,
    you also need to set the authorized_keys file for the inmanta user.  You can do so by mounting
    your public key to the following path in the container: ``/var/lib/inmanta/.ssh/authorized_keys``.
    When starting, the container will make sure that the file has the correct ownership and permissions.

Setting environment variables
#############################

You might want your inmanta server to be able to reach some environment variables.
There are two ways you can achieve this:

    1.  Set the environment variables with docker, either using the ``--env`` argument or in your
        docker-compose file.  Those variables will be accessible to the inmanta server and any
        agent it starts, but not to any other process running in the container.

    2.  Set the environment variables in a file and use the ``env_file`` section of docker compose to specify the path of your env file.

.. only:: oss

    .. code-block:: yaml

        inmanta-server:
            container_name: inmanta_orchestrator
            image: ghcr.io/inmanta/orchestrator:latest
            ports:
                - 8888:8888
            env_file: ./resources/my-env-file
            environment:
                INMANTA_DATABASE_HOST: inmanta_db
                INMANTA_DATABASE_USERNAME: inmanta
                INMANTA_DATABASE_PASSWORD: inmanta
            volumes:
                - ./resources/my-server-conf.cfg:/etc/inmanta/inmanta.cfg

.. only:: iso

    .. code-block:: yaml
        :substitutions:

        inmanta-server:
            container_name: inmanta_orchestrator
            image: containers.inmanta.com/containers/service-orchestrator:|version_major|
            ports:
                - 8888:8888
            env_file: ./resources/my-env-file
            environment:
                INMANTA_DATABASE_HOST: inmanta_db
                INMANTA_DATABASE_USERNAME: inmanta
                INMANTA_DATABASE_PASSWORD: inmanta
            volumes:
                - ./resources/com.inmanta.license:/etc/inmanta/license/com.inmanta.license
                - ./resources/com.inmanta.jwe:/etc/inmanta/license/com.inmanta.jwe
                - ./resources/my-server-conf.cfg:/etc/inmanta/inmanta.cfg

Mounting files/directories
##########################

The recommended way to mount files and directories is to use docker volumes:

.. code-block:: sh

    docker volume create mydockervolume

And then you can use it in docker-compose file:

.. code-block:: yaml

    volumes:
        - mydockervolume:/etc/inmanta/myfolder


However if you really need to mount a file or directory from the host, you can use bind mounts. You just need to make sure to change the ownership of
the file/directory you want to mount to make sure it has same uid/gid as the inmanta user inside the container. To find them, in the container, you can use ``id`` command.
By default, currently, inmanta user ``uid`` is 997 and ``gid`` is 995. On your host you can easily change ownership of your file/directory with these values:

.. code-block:: sh

    sudo chown -R 997:995 myfolder/


Log rotation
############

By default, the container won't do any log rotation, to let you the choice of dealing with the logs
according to your own preferences.  We recommend that you do so by mounting a folder inside of the container
at the following path: ``/var/log``. This path contains all the logs of inmanta (unless you specified
a different path in the config of the server).
