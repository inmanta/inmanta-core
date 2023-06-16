.. _upgrading_the_orchestrator:


Upgrading the orchestrator
-------------------------

Upgrading by migrating from one orchestrator to another orchestrator
#######################################################################

This document describes how to upgrade to a new version of the orchestrator by setting
up a new orchestrator next to the existing orchestrator and migrating all the state from
the existing to the new orchestrator. This procedure should be followed when an in-place
upgrade of the orchestrator is not possible e.g. when the operating system needs to be
upgraded alongside the orchestrator.

Terminology
+++++++++++

The procedure below describes how to migrate from one running orchestrator
denoted as the 'old orchestrator' to another one denoted as the 'new orchestrator'.

Procedure
+++++++++


.. note::
    **Pre-requisite**

    - Before upgrading the orchestrator to a new major version, make sure the old orchestrator is at the latest version available within its major.
    - Upgrades should be done one major version at a time. Upgrading from major
      version :code:`X` to major version :code:`X+2`, should be done by upgrading from :code:`X` to :code:`X+1` and then from :code:`X+1` to :code:`X+2`.


_________

1. **[New Orchestrator]**: Make sure the desired version of the orchestrator is installed, by following the
installation instructions (see :ref:`install-server`) and set up a project manually, validating that the setup
of the orchestrator works (config, credentials, access to packages, etc.).

_________


2. **[Old Orchestrator]** Halt all environments (by pressing the ``STOP`` button in the web-console for each environment).
3. **[Old Orchestrator]** Stop the server:

.. code-block:: bash

    sudo systemctl disable --now inmanta-server.service

4. **[Old Orchestrator]** Make a dump of the server database using ``pgdump``.


.. code-block:: bash

    pg_dump -U <user> -W -h <host> <db_name> > <db_dump_file>

_________



5. **[New Orchestrator]** Make sure the server is stopped:

.. code-block:: bash

    sudo systemctl stop inmanta-server.service

6. **[New Orchestrator]** Drop the inmanta database and recreate it:


.. code-block:: bash

    # drop the database
    psql -h <host> -U <user> -W
    drop database <db_name>;

    # re-create it
    sudo -u postgres -i bash -c "createdb -O <user> <db_name>"


7. **[New Orchestrator]** Load the dump of the server database using ``psql``.


.. code-block:: bash

    cat <db_dump_file> | psql -U <user> -W -h <host> <db_name>


8. **[New Orchestrator]** Start the orchestrator service, it will take some time before the orchestrator goes up, as some database migration will be done:

.. code-block:: bash

    sudo systemctl enable --now inmanta-server.service

9. **[New Orchestrator]** When accessing the web console, all the environments will be visible, and still halted.
10. **[New Orchestrator]** One environment at a time:

    a. In the **Desired State** page of the environment, click ``Update project & recompile``, accessible via the
    dropdown of the ``Recompile`` button. (``/console/desiredstate?env=<your-env-id>``).

    b. Resume the environment by pressing the green ``Resume`` button in the bottom left corner of the console.

    .. warning::

        Make sure the compilation has finished and was successful before moving on to the next steps.

