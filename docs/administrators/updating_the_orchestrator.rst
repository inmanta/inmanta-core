.. _updating_the_orchestrator:


Updating the orchestrator
-------------------------

Migrating from one running orchestrator to another running orchestrator
#######################################################################

This document describes the procedure to migrate from one running orchestrator
to another one. This procedure should be followed when an in-place update of
the orchestrator is not possible e.g. when the operating system needs to be
updated alongside the orchestrator or when updating the orchestrator to a
different major version.

Context
+++++++

The procedure below describes how to migrate from one running orchestrator
denoted as the 'old orchestrator' to another one denoted as the 'new orchestrator'.

Procedure
+++++++++

On the old orchestrator:
1. Halt all environments (by pressing the `STOP` button in the dashboard for each environment).
2. Stop the server:

.. code-block:: bash

    sudo systemctl stop inmanta-server.service

3. Make a dump of the server database using `pgdump`.

On the new orchestrator:
1. *Preliminary step*: Make sure the desired version of the orchestrator is installed, by following the
[installation instructions](https://docs.inmanta.com/inmanta-service-orchestrator/latest/install/1-install-server.html)
and setup a project manually, validating that the setup of the orchestrator works (config, credentials, access to packages, etc.).
2. Make sure the server is stopped:

.. code-block:: bash

    sudo systemctl stop inmanta-server.service

3. Load the dump of the server database using `pgsql`.
4. Start the orchestrator service, it will take some time before the orchestrator goes up, as some database migration will be done:

.. code-block:: bash

    sudo systemctl start inmanta-server.service

5. When accessing the web console, all the environments from the old orchestrator should be visible, and still halted.
6. One environment at a time:
   1. Disable the `auto_deploy` option in the environment settings.  (`/console/settings?env=<your-env-id>&state.Settings.tab=Configuration`)
   2. In the *desired state* page of the environment, click `Update project & recompile`, accessible via the dropdown of the `Recompile` button. (`/console/desiredstate?env=<your-env-id>`).
   3. Resume the environment by pressing the green `Resume` button in the bottom left corner of the console.
   4. Make a dry-run and check that no difference is detected by the orchestrator.
   5. Enable `auto_deploy` in the settings of the environment.
