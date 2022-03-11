Pull the image
##############

Use docker pull to get the desired image:

.. code-block:: sh

    docker pull ghcr.io/inmanta/orchestrator:2022


This command will pull the latest version of the Inmanta Orchestrator image.


Start the server with docker-compose
####################################

Here is a minimalist docker-compose file content that can be used to deploy the server on your machine.

.. code-block:: yaml

    version: '3'
    services:
        postgres:
            container_name: inmanta_db
            image: postgres:13
            environment:
                POSTGRES_USER: inmanta
                POSTGRES_PASSWORD: inmanta
            networks:
                inm_net:
                    ipv4_address: 172.30.0.2

        inmanta-server:
            container_name: inmanta_orchestrator
            image: ghcr.io/inmanta/orchestrator:2022
            ports:
                - 8888:8888
            networks:
                inm_net:
                    ipv4_address: 172.30.0.3
            command: "server --wait-for-host inmanta_db --wait-for-port 5432"

    networks:
        inm_net:
            ipam:
                driver: default
                config:
                    - subnet: 172.30.0.0/16

Then bring the containers up by running the following command:

.. code-block:: sh

    docker-compose up

You should be able to reach the orchestrator to this address: `http://172.30.0.3:8888 <http://172.30.0.3:8888>`_.

The default server config included in the container images assumes that the orchestrator will have a database 
with hostname ``inmanta_db`` reachable and that it can authenticate to it using the username ``inmanta`` 
and password ``inmanta``.  
When using a different setup than the one mentioned above, you should overwrite the server config with one
matching your needs.  You can find more instructions for overwriting the config in a following section, 
:ref:`here<docker_overwrite_server_conf>`.

.. warning::
    We don't recommend using the setup described above as a production environment.  Hosting a database in a
    container as shown here is not ideal in term of performance, reliability and raises some serious data
    persistence concerns.
