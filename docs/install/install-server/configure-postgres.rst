.. _install-step-2:

Step 2: Install PostgreSQL 10
-----------------------------

PostgreSQL 10 can be installed by following the `installation guide <https://www.postgresql.org/download/>`_ for your
platform.

.. _install-step-3:

Step 3: Setup a PostgreSQL database for the Inmanta server
----------------------------------------------------------

Initialize the PostgreSQL server:

.. code-block:: sh

  sudo /usr/pgsql-10/bin/postgresql-10-setup initdb

Start the PostgreSQL database

.. code-block:: sh

   sudo systemctl start postgresql-10

Create a inmanta user and an inmanta database by executing the following command. This command will request you to choose a
password for the inmanta database.

.. code-block:: sh

  sudo -u postgres -i sh -c "createuser --pwprompt inmanta; createdb -O inmanta inmanta"

Change the authentication method for local connections to md5 by changing the following lines in the
``/var/lib/pgsql/10/data/pg_hba.conf`` file

.. code-block:: text

  # IPv4 local connections:
  host    all             all             127.0.0.1/32            ident
  # IPv6 local connections:
  host    all             all             ::1/128                 ident

to

.. code-block:: text

  # IPv4 local connections:
  host    all             all             127.0.0.1/32            md5
  # IPv6 local connections:
  host    all             all             ::1/128                 md5


Restart the PostgreSQL server to apply the changes made in the ``pg_hba.conf`` file:

.. code-block:: sh

   sudo systemctl restart postgresql-10
