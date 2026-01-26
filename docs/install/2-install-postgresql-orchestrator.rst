.. _postgresql-install-doc:

Install PostgreSQL
##################

This page describes how to install PostgreSQL on RedHat Enterprise Linux or derivatives.

Step 1: Install PostgreSQL 16
-----------------------------

.. only:: oss

    For most platforms you can install PostgreSQL 16 following the `installation guide <https://www.postgresql.org/download/>`_ for your
    platform.

    For RHEL based systems you can also use the PostgreSQL that comes with the distribution.

    .. code-block:: sh

        sudo dnf module install postgresql:16/server

.. only:: iso

    Install the PostgreSQL 16 package included in RHEL. More info in the 'Included in Distribution' section
    of the `postgresql documentation <https://www.postgresql.org/download/linux/redhat/>`_.

    .. tab-set::

        .. tab-item:: RHEL 9

            .. code-block:: sh

                sudo dnf module install postgresql:16/server
                sudo systemctl enable postgresql

            .. warning::
                Before moving on to the next step, make sure that the locale used by the system is actually installed.
                By default, RHEL9 uses the ``en_US.UTF-8`` locale which can be installed via:

                .. code-block:: sh

                    sudo dnf install langpacks-en -y

                .. note::
                    If your system uses a different locale, please install the corresponding langpack.

        .. tab-item:: RHEL 8

            .. code-block:: sh

                sudo dnf module install postgresql:16/server
                sudo systemctl enable postgresql


Step 2: Setup a PostgreSQL database for the Inmanta server
----------------------------------------------------------

Initialize the PostgreSQL server:

.. code-block:: sh

    sudo su - postgres -c "postgresql-setup --initdb"

Start the PostgreSQL database and make sure it is started at boot.

.. code-block:: sh

    sudo systemctl enable --now postgresql

Create an inmanta user and an inmanta database by executing the following command. This command will request you to choose a
password for the inmanta database.

.. code-block:: sh

    sudo -u postgres -i bash -c "createuser --pwprompt inmanta"
    sudo -u postgres -i bash -c "createdb -O inmanta inmanta"

Change the authentication method for local connections to md5 by changing the following lines in the
``/var/lib/pgsql/data/pg_hba.conf`` file.

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

This will make sure you can authenticate using username and password from localhost.
If you need password authentication from a different interface, change the
``127.0.0.1`` and ``::1/128`` values in the example to the correct interfaces.

Make sure JIT is disabled for the PostgreSQL database as it might result in poor query performance.
To disable JIT, set

.. code-block:: text

    # disable JIT
    jit = off

in ``/var/lib/pgsql/data/postgresql.conf``.

Restart the PostgreSQL server to apply the changes made in the ``pg_hba.conf`` and  ``postgresql.conf`` files:

.. code-block:: sh

    sudo systemctl restart postgresql

