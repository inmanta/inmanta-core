.. _install-server-with-docker:

Install Inmanta with Docker
***************************

This page explains how to setup an orchestration server using docker.
This guide assumes you already have `docker <https://docs.docker.com/get-docker/>`_ installed on your machine.

Pull the image
##############

.. only:: oss

    Use docker pull to get the desired image:

    .. code-block:: sh

        sudo docker pull ghcr.io/inmanta/orchestrator:latest


    This command will pull the latest version of the Inmanta OSS Orchestrator image.

.. only:: iso

    Step 1: Log in to Cloudsmith registry
    -------------------------------------

    Connect to the Cloudsmith registry using your entitlement token.

    .. code-block:: console

        $ sudo docker login containers.inmanta.com
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

        sudo docker pull containers.inmanta.com/containers/service-orchestrator:|version_major|


    This command will pull the latest version of the Inmanta Service Orchestrator image.

.. only:: iso

    Get the orchestrator license
    ############################

    Together with the access to the inmanta container repo, you should also have received a license and an entitlement file.
    The orchestrator will need them in order to run properly.  We will assume that these files are named ``license.key`` and
    ``entitlement.jwe`` and are located in the folder ``/etc/inmanta`` on the host where the containers will be deployed.


Start the server with docker-compose
####################################

Here is a minimalistic docker-compose file content that can be used to deploy the server on your machine.

.. only:: oss

    .. code-block:: yaml

        services:
            db:
                container_name: inmanta-db
                image: postgres:16
                environment:
                    POSTGRES_USER: inmanta
                    POSTGRES_PASSWORD: inmanta
                volumes:
                    - inmanta-db-data:/var/lib/postgresql/data
                command: "postgres -c jit=off"
            server:
                container_name: inmanta-orchestrator
                image: ghcr.io/inmanta/orchestrator:latest
                ports:
                    - 127.0.0.1:8888:8888
                environment:
                    INMANTA_DATABASE_HOST: inmanta-db
                    INMANTA_DATABASE_USERNAME: inmanta
                    INMANTA_DATABASE_PASSWORD: inmanta
                volumes:
                    - inmanta-server-data:/var/lib/inmanta
                    - inmanta-server-logs:/var/log/inmanta

        volumes:
            inmanta-db-data: {}
            inmanta-server-data: {}
            inmanta-server-logs: {}

    You can paste this yaml snippet in a file named `docker-compose.yml`.

.. only:: iso

    .. code-block:: yaml
       :substitutions:

        services:
            db:
                container_name: inmanta-db
                image: postgres:16
                environment:
                    POSTGRES_USER: inmanta
                    POSTGRES_PASSWORD: inmanta
                volumes:
                    - inmanta-db-data:/var/lib/postgresql/data
                command: "postgres -c jit=off"
            server:
                container_name: inmanta-orchestrator
                image: containers.inmanta.com/containers/service-orchestrator:|version_major|
                ports:
                    - 127.0.0.1:8888:8888
                environment:
                    INMANTA_DATABASE_HOST: inmanta-db
                    INMANTA_DATABASE_USERNAME: inmanta
                    INMANTA_DATABASE_PASSWORD: inmanta
                volumes:
                    - inmanta-server-data:/var/lib/inmanta
                    - inmanta-server-logs:/var/log/inmanta
                    - /etc/inmanta/license.key:/etc/inmanta/license.key
                    - /etc/inmanta/entitlement.jwe:/etc/inmanta/entitlement.jwe

        volumes:
            inmanta-db-data: {}
            inmanta-server-data: {}
            inmanta-server-logs: {}

    You can paste this yaml snippet in a file named `docker-compose.yml` and ensure you have your license files available.
    With the proposed config, they should be located in a ``/etc/inmanta/`` folder, and the license files should be named 
    ``license.key`` and ``entitlement.jwe``. You can of course update the content of the docker-compose file to match your
    current configuration. 
    Then bring the containers up by running the following command:

.. code-block:: sh

    sudo docker compose up

You should be able to reach the orchestrator to this address: `http://127.0.0.1:8888 <http://127.0.0.1:8888>`_.

To stop the orchestrator and the database and remove the containers, use ``docker compose`` again:

.. code-block:: sh

    sudo docker compose down

.. note:: 
    The database and orchestrator containers started in the above-mentioned docker-compose file make use of docker volumes to persist their relevant data in between restarts.
    If you want to clear this data, you must remove these volumes, which can be done easily by adding the ``-v`` option to the ``sudo docker compose down`` command.
    Be aware that using ``-v`` will remove all volumes (for both the database and orchestrator containers).

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
Be aware that values provided in the configuration file are overwritten by values provided in environment variables, and that
the orchestrator image contains some `default environment variable values <https://raw.githubusercontent.com/inmanta/inmanta/refs/heads/master/docker/native_image/Dockerfile#:~:text=ENV>`_.

Setting environment variables
#############################

The inmanta server will share any environment variable it received from docker with all its compiler and agent sub processes.  So if you need
to make some environment variables available to the compiler or agent, you can simply tell docker to pass them on to the orchestrator container.
In the example shown above, this can be done by using either of the ``environment`` or ``env_file`` attributes in the ``server`` service of the docker compose file.
More details about these options can be found in `docker's documentation <https://docs.docker.com/reference/compose-file/services/>`_.

.. warning::
    If you are migrating from an rpm install, be aware that the format of environment files for `docker` (and `podman` for that matter) are different from what is supported by systemd which you may have been relying on up to now.
    The format is simply `[KEY]=[VALUE]` separated by new lines, without any quoting or multi-line support.
    cf. `podman#19565 <https://github.com/containers/podman/issues/19565#issuecomment-1672891535>`_.


Accessing the orchestrator file system
######################################

If you want to have a look inside the running orchestrator container, it contains a traditional file system, you can enter it using ``docker exec`` on the host where the container is running:

.. code-block:: sh

    sudo docker exec -ti inmanta-orchestrator bash

If you need to enter the container via ssh, we recommend deploying an ssh sidecar, alongside the orchestrator container, as shown here: `https://github.com/inmanta/inmanta-docker <https://github.com/inmanta/inmanta-docker>`_

Mounting files/directories
##########################

The recommended way to persist the orchestrator data is to use docker volumes, as shown in the example above. However if you really need to mount a file or directory from the host, you can use bind mounts. You just need to make sure to change the ownership of
the file/directory you want to mount to make sure it has same uid/gid as the inmanta user inside the container. To find them, in the container, you can use the ``id`` command:

.. only:: oss

    .. code-block:: console

        $ sudo docker run --rm -ti --entrypoint bash ghcr.io/inmanta/orchestrator:latest -c id
        uid=997(inmanta) gid=995(inmanta) groups=995(inmanta)

.. only:: iso

    .. code-block:: console
        :substitutions:

        $ sudo docker run --rm -ti --entrypoint bash containers.inmanta.com/containers/service-orchestrator:|version_major| -c id
        uid=997(inmanta) gid=995(inmanta) groups=995(inmanta)

By default, currently, inmanta user ``uid`` is 997 and ``gid`` is 995. On your host you can easily change ownership of your file/directory with these values:

.. code-block:: sh

    sudo chown -R 997:995 myfolder/

Log rotation
############

By default, the container won't do any log rotation, to let you the choice of dealing with the logs
according to your own preferences.  You can setup log rotation using a sidecar as shown here: `https://github.com/inmanta/inmanta-docker <https://github.com/inmanta/inmanta-docker>`_
