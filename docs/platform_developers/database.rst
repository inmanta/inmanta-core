**************************
Database Schema Management
**************************

In some situation a change to the database schema is required. To perform these database schema
migration, we implemented a migration tool and associated testing framework. This page describes how to create a new
version of the database schema and test the migration script.


Definition new schema version
#############################

The version number of the database schema evolves independently from any other versioned Inmanta element
(product version, extension version, etc.). Each commit can introduce changes to the database schema. When that happens
the commit creates a new database schema version. This means that multiple schema version can exist between two
consecutive stable releases of the orchestrator.

A new version of the database schema is defined by adding a new Python module to the ``inmanta.db.versions`` package. The
name of this module should have the format ``v<timestamp><i>.py``, where the timestamp is in the form
``YYYYMMDD`` and ``i`` is an index to allow more than one schema update per day (e.g. ``v202102220.py``).

Each of these Python modules should implement an asynchronous function ``update`` that accepts a database connection object
as an argument. This function should execute all database queries required to update from the previous version of the
database schema to the new version of the database schema.

An example is given in the code snippet below:

.. code-block:: python

    # File: src/inmanta/db/versions/v202102220.py
    from asyncpg import Connection

    async def update(connection: Connection) -> None:
        schema = """
        ALTER TABLE public.test
        ADD COLUMN new_column;
        """
        await connection.execute(schema)


Executing schema updates
########################

Schema updates are applied automatically when the Inmanta server starts. The following algorithm is used to apply schema
updates:

1. Retrieve the current version of the database schema from the ``public.schemamanager`` table of the database.
2. Check if the ``inmanta.db.versions`` package contains any schema updates.
3. When schema updates are available, each ``update`` function between the current version and the latest version is executed
   in the right order.

When a schema update fails, the database schema is rolled-back to the state before the start of the Inmanta server. In
that case the Inmanta server will fail to start.


Testing database migrations
###########################

Each database migration script should be tested using an automated test case. The tests that verify the migration from
schema version ``<old_version>`` to ``<new_version>`` are stored in a file named
``tests/db/test_v<old_version>_to_v<new_version>.py``.

In general, a database schema migration test has the following flow:

1. Load a database dump that uses the database schema version directly preceding the version being tested.
2. Perform assertions that verify the database schema before the migration.
3. Start the inmanta server to trigger the database migration scripts.
4. Perform assertions to verify that the migration was done correctly.

The example below shows a test for the above-mentioned database migration script.

.. code-block:: python
    :linenos:

    # File: tests/db/test_v202101010_to_v202102220.py
    @pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202101010.sql"))
    async def test_add_new_column_to_test_table(
        migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
        get_columns_in_db_table: abc.Callable[[str], list[str]],
    ) -> None:
        """
        Verify that the database migration script v202102220.py correctly add the column new_column to the table test.
        """
        # Assert state before migration
        assert "new_column" not in await get_columns_in_db_table(table_name="test")
        # Migrate DB schema
        await migrate_db_from()
        # Assert state after migration
        assert "new_column" in await get_columns_in_db_table(table_name="test")


The most important elements of the test case are the following:

* Line 2: The ``db_restore_dump`` annotation makes the ``migrate_db_from`` fixture load the database dump
  ``tests/db/dumps/v202101010.sql`` in the database used by the test case. This happens in the setup stage of the
  fixture. As such, the database contains the old version of the database schema at the beginning of the test case.
* Line 11: Verifies that the column ``new_column`` doesn't exist in the table test. The test case uses the fixture
  ``get_columns_in_db_table`` to obtain that information, but the ``postgresql_client`` fixture can be used as well
  to run arbitrary queries against the database.
* Line 13: Invokes the callable returned by the ``migrate_db_from`` fixture. This function call starts an Inmanta
  server against the database used by the test case, which runs the migration script being tested.
* Line 15: Verifies whether the migration script correctly added the column ``new_column`` to the table test.

Each commit that creates a new database version should also add a database dump for that new version to the
``tests/db/dumps/`` directory. Generating this dump can be done using the ``tests/db/dump_tool.py`` script. This script
does the following:

1. Start an Inmanta server using the latest database schema available in ``inmanta.db.versions`` package.
2. Execute some API calls against the server to populate the database tables with some dummy data.
3. Dump the content of the database to ``tests/db/dumps/v<latest_version>.sql``.

If a new table or column is added using a database migration script, the developer should make sure to adjust the
``dump_tool.py`` script with the necessary API calls to populate the table or column if required.
