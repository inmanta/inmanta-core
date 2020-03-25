**************************
Database Schema Management
**************************

This page describes how database schema updates are managed by the Inmanta core.


Definition new schema version
#############################

A new version of the database schema is defined by adding a new Python module to the ``inmanta.db.versions`` package. The
name of this module should have the format ``v<version>.py``, where <version> is an integer indicating the version of
the new database schema. Version numbers start at 1.

Each of these Python modules should implement an asynchronous function ``update`` that accepts a database connection object
as an argument. This function should execute all database queries required to update from the previous version of the
database schema (<version> - 1) to the new version of the database schema (<version>). **All changes done by the update
function should be executed in the transaction.** An example is given in the code snippet below.

Each each of these Python modules must also contain the field ``DISABLED`` set to false to make the changes effective.

.. code-block:: python

    # File: src/inmanta/db/versions/v1.py
    from asyncpg import Connection

    DISABLED = False

    async def update(connection: Connection) -> None:
        schema = """
        ALTER TABLE public.test
        ADD COLUMN new_column;
        """
        async with connection.transaction():
            await connection.execute(schema)


Executing schema updates
########################

Schema updates are applied automatically when the Inmanta server starts. The following algorithm is used to apply schema
updates:

1. Retrieve the current version of the database schema from the ``public.schemamanager`` table of the database.
2. Check if the ``inmanta.db.versions`` package contains any schema updates.
3. When schema updates are available, each ``update`` function between the current version and the latest version is executed
   in the right order.

When a schema update fails, the database schema is rolled-back to the latest schema version for which the ``update`` function
did succeed. In that case the Inmanta server will fail to start.
