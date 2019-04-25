Migrate from MongoDB to PostgreSQL
**********************************

Since release 2019.2, PostgreSQL is used as the backend database system of the Inmanta server instead of MongoDB. This page
describes how an Inmanta server running on MongoDB can be migrated to PostgreSQL.

Note: This procedure doesn't perform a full database migration. Existing version of a configurationmodel are not migrated to the PostgreSQL database. As such, it is requires
to create a new version of the configuration model after the migration. The following things are part of the migration:

* Projects
* Environments (including the settings of an environment)
* Forms
* Parameters

Migration procedure
###################

Step 1: Install and configure PostgreSQL
----------------------------------------

This can be done by following :ref:`step 2<install-step-2>` and :ref:`step 3<install-step-3>` of the Inmanta
installation guide.

Step 2: Stop and update the Inmanta server
------------------------------------------

.. code-block:: sh

  sudo systemctl stop inmanta-server
  sudo yum update -y python3-inmanta python3-inmanta-server python3-inmanta-agent

# TODO: Set exact version

Step 3: Migrate the database
----------------------------

The database migration tool can be executed with the ``inmanta-migrate-db`` command.

.. code-block:: sh

  inmanta-migrate-db --mongo-database inmanta --pg-database inmanta --pg-username inmanta --pg-password <password>

Replace <password> with the password of the Inmanta database on PostgreSQL.

The full listing of all options of the ``inmanta-migrate-db`` command can be obtained via the ``--help`` option:

.. code-block:: sh

  inmanta-migrate-db --help

  Usage: inmanta-migrate-db [OPTIONS]

    Migrate the database of the Inmanta server from MongoDB to PostgreSQL.

    Note: This script only migrates the collections: Project, Environment, Parameter, Form andFormRecord.

  Options:
    --mongo-host TEXT      Host running the MongoDB database.
    --mongo-port INTEGER   The port on which the MongoDB server is listening.
    --mongo-database TEXT  The name of the MongoDB database.
    --pg-host TEXT         Host running the PostgreSQL database.
    --pg-port INTEGER      The port on which the PostgreSQL database is
                           listening.
    --pg-database TEXT     The name of the PostgreSQL database.
    --pg-username TEXT     The username to use to login on the PostgreSQL
                           database
    --pg-password TEXT     The password that belongs to user specified with
                           --pg-username  [required]
    --help



Step 4: Set the database connection details
-------------------------------------------

This can be done by following :ref:`step 4<install-step-4>` of the Inmanta installation guide.

Step 5: Start the Inmanta server
--------------------------------

Start the Inmanta server with the following command:

.. code-block:: sh

  sudo systemctl start inmanta-server

Step 6: Create a new version of the configurationmodel
------------------------------------------------------

# TODO