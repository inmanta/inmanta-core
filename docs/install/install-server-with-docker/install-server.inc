Pull the image
##############

Use docker pull to get the desired image:

.. code-block:: sh

    docker pull ghcr.io/inmanta/oss:2022


This command will pull the latest version of the Inmanta OSS Orchestrator image.


Start the server with docker-compose
####################################

Here is a minimalist docker-compose file content that can be used to deploy the server on your machine.

.. code-block:: yaml

    version: '3'
    services:
        postgres:
            container_name: iso_postgres
            image: postgres:10
            environment:
                POSTGRES_USER: inmanta
                POSTGRES_PASSWORD: inmanta
            networks:
                iso_net:
                    ipv4_address: 172.30.0.2

        inmanta-server:
            container_name: iso_server
            image: ghcr.io/inmanta/oss:2022
            ports:
                - 8888:8888
            depends_on:
                - postgres
            networks:
                iso_net:
                    ipv4_address: 172.30.0.3

    networks:
        iso_net:
            ipam:
                driver: default
                config:
                    - subnet: 172.30.0.0/16

Then bring the containers up by running the following command:

.. code-block:: sh

    docker-compose up

You should be able to reach the orchestrator to this address: `http://172.30.0.3:8888 <http://172.30.0.3:8888>`_.
