Overwrite default server configuration
######################################

By default the server will use the file located in the image at ``/etc/inmanta/inmanta.cfg``.  
If you want to change it, you can copy this file, edit it, then mount it in the container, 
where the original file was located.

If you use docker-compose, you can simply update this section of the example above:

.. code-block:: yaml

    inmanta-server:
        container_name: iso_server
        image: ghcr.io/inmanta/oss:2022
        ports:
            - 8888:8888
        volumes:
            - ./resources/my-server-conf.cfg:/etc/inmanta/inmanta.cfg


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
        container_name: iso_server
        ...
        command: "server-with-ssh"

.. warning::
    By default, the inmanta user doesn't have any password, if you want to ssh into the container, 
    you also need to set the authorized_keys file for the inmanta user.  You can do so by mounting 
    your public key to the following path in the container: ``/var/lib/inmanta/.ssh/authorized_keys``.  
    When starting, the container will make sure that the file has the correct ownership and permissions.


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
        container_name: iso_server
        ...
        command: "server --wait-for-host <your-db-host> --wait-for-port <your-db-port>"


Setting environment variables
#############################

You might want your inmanta server to be able to reach some environment variables.  
There are two ways you can achieve this:
 1. Set the environment variables with docker, either using the ``--env`` argument or in your 
    docker-compose file.  Those variables will be accessible to the inmanta server and any 
    agent it starts, but not to any other process running in the container (if you for example 
    login via ssh to the container and try to install a project again).
 2. (Recommended) Set the environment variables in a file and mount it to the following path in the 
    container: ``/etc/inmanta/env``.  This file will be loaded when starting the server and for 
    every session that the inmanta user starts in the container.

.. code-block:: yaml

    inmanta-server:
        container_name: iso_server
        image: ghcr.io/inmanta/oss:2022
        ports:
            - 8888:8888
        volumes:
            - ./resources/my-server-conf.cfg:/etc/inmanta/inmanta.cfg
            - ./resources/my-env-file:/etc/inmanta/env


Log rotation
############

By default, the container won't do any log rotation, to let you the choice of dealing with the logs
according to your own preferences.  We recommend that you do so by mounting a folder inside of the container
at the following path: ``/var/log``.  This path contains all the logs of inmanta (unless you specified
a different path in the config of the server).

