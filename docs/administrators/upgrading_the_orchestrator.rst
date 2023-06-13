.. _upgrading_the_orchestrator:


Upgrading the orchestrator
-------------------------

Migrating from one running orchestrator to another running orchestrator
#######################################################################

This document describes how to upgrade to a new version of the orchestrator by setting
up a new orchestrator next to the existing orchestrator and migrating all the state from
the existing to the new orchestrator. This procedure should be followed when an in-place
update of the orchestrator is not possible e.g. when the operating system needs to be
updated alongside the orchestrator.

Terminology
+++++++++++

The procedure below describes how to migrate from one running orchestrator
denoted as the 'old orchestrator' to another one denoted as the 'new orchestrator'.

Procedure
+++++++++


.. note::
    **Pre-requisite**

    - Before upgrading the orchestrator to a new major version, an update should be done first.
    - Upgrades should be done one major version at a time. So if you want to upgrade from major
    version X to major version X+2, you should do an upgrade from X to X+1 and then from X+1 to X+2.




1. **[New Orchestrator]**: Make sure the desired version of the orchestrator is installed, by following the
installation instructions: :ref:`install-server` and set up a project manually, validating that the setup
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

6. Load the dump of the server database using ``pgsql``.


.. code-block:: bash

    cat <db_dump_file> | psql -U <user> -W -h <host> <db_name>


7. Start the orchestrator service, it will take some time before the orchestrator goes up, as some database migration will be done:

.. code-block:: bash

    sudo systemctl enable --now inmanta-server.service

8. When accessing the web console, all the environments will be visible, and still halted.
9. One environment at a time:

   a. Disable the ``auto_deploy`` option in the environment settings.  (``/console/settings?env=<your-env-id>&state.Settings.tab=Configuration``)
   b. In the **desired state** page of the environment, click ``Update project & recompile``, accessible via the
   dropdown of the ``Recompile`` button. (``/console/desiredstate?env=<your-env-id>``).

.. warning::

    Make sure the compilation has finished and was successful before moving on to the next steps.

   c. Resume the environment by pressing the green ``Resume`` button in the bottom left corner of the console.
   d. Make a dry-run and check that no difference is detected by the orchestrator.
   e. Enable ``auto_deploy`` in the settings of the environment.
