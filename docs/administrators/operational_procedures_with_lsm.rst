..
    This document is excluded from the oss doc build via the exclude_patterns variable in conf.py

.. _operational_procedures_lsm:

Operational Procedures With LSM
--------------------------------


This document describes the best practices for various operational procedures, when using Lifecycle and Service Management.
These procedures are an extension to the ones described in :ref:`operational_procedures`.

.. note::
    issue templates for all procedures are available at the bottom of this page


Upgrade of service model on the orchestrator
#############################################

This process describes how to safely take an existing project from one version to the next.

Context
++++++++
* The orchestrator has the project already deployed and running
* The project is released (as described here: :ref:`operational_procedures_release`)

Pre-Upgrade steps
++++++++++++++++++
1. Determine if this update in any way affects the service definition.
   If the update doesn't change the lifecycle or any aspect of the schema of the north bound api,
   flow the procedure here: :ref:`operational_procedures_upgrade`.
   Otherwise, go to the next step.
2. Determine if the update changes the structure of existing instances in the service inventory
   (i.e. add or remove fields). If this is the case, a database backup is required to revert the update.
3. Ensure you have shell access to the orchestrator.
4. Verify with the development team what the correct entry point is for exporting the API definition.
   Exporting the api definition requires the model to compile.
   Often, the model requires a correct API definition to compile.
   To break this cycle, developers have to provide an alternative entry point into the code (other than `main.cf`) that loads only the definitions.
   We will assume this file is called `loader.cf`
5. Verify that environment safety settings are on (this should always be the case)

   * :inmanta.environment-settings:setting:`protected_environment` = True

6. Temporarily disable auto_deploy

   * :inmanta.environment-settings:setting:`auto_deploy` = False

4. Click ‘recompile’ to verify that no new deploy would start.

   * A new version will appear but it will not start to deploy

5. Inspect the current state of the latest deployed version, verify no failures are happening and the deploy looks healthy
6. (Optional) Perform a dryrun. Wait for the dryrun to complete and take note of all changes detected by the dryrun. Ideally there should be none.
7. Block out all north-bound api calls (in the north-bound load balancer or firewall). This is to prevent instance changes during the update.
8. Pause all agents, to prevent state transitions during the update.
9. Backup the database (if required as described in step 2).
   A full backup is preferable (using eg `pgdump`).
   The tables `lsm_serviceentity` and `lsm_serviceinstance` are most crucial.
   A schema update may cause the instances in the database to be irreversible rewritten.
   This backup will ensure a way back.


Upgrade procedure
++++++++++++++++++

1. Instruct the orchestrator to pull in the latest version by clicking `Update project & recompile`

* The compiler pulls in the latest version
* This compile may fail or produce a new version, that will not start to deploy

2. Send the new service definition to the server:
Log onto the orchestrator and navigate to the folder for this environment.

If no instance updates are expected use:

.. code-block:: sh

    inmanta-workon $envid
    inmanta -vvv -X export -j /dev/null -e $envid -f loader.cf --export-plugin service_entities_exporter_strict

If instance update are expected (and you made a database backup), use:

.. code-block:: sh

    inmanta-workon $envid
    inmanta -vvv -X export -j /dev/null -e $envid -f loader.cf --export-plugin service_entities_exporter

3. Click `Recompile`

   * The compiler will produce a new version, that will not start to deploy

4. Re-enable the agents.

5. Click `Perform dry run` on the new version

   * The dryrun report will open
   * Wait for the dryrun to finish
   * Inspect any changes found by the dryrun, determine if they are expected. If unexpected things are present, go to the abort procedure.

4. If all is OK, click deploy to make the changes effective

Post Upgrade procedure
+++++++++++++++++++++++++

1. Re-enable auto_deploy

   * :inmanta.environment-settings:setting:`auto_deploy` = True

2. Allow requests to be sent to the north bound api again

Upgrade abort/revert
+++++++++++++++++++++++

1. Delete the bad (latest) version produced during the update in the web-console
2. Push a revert commit onto the release branch (`git revert HEAD; git push`)
3. Go through the Upgrade procedure again to make this revert effective
4. If the API update is irreversible or the end-result after revert is different from the expected result, restore the database tables `lsm_serviceentity` and `lsm_serviceinstance`.

Deployment of a new service model to the orchestrator
########################################################

This process describes how to safely deploy a new model to the orchestrator.

Context
++++++++
* The orchestrator has an environment set up for the project, but it has not been deployed yet.
* The project is released (as described above)

Procedure
++++++++++

1. Cross check all settings in the environment settings tab with the development team.
2. Verify with the development team what the correct entry point is for exporting the API definition.
   Exporting the api definition requires the model to compile.
   Often, the model requires a correct API definition to compile.
   To break this cycle, developers have to provide an alternative entry point into the code (other than `main.cf`) that loads only the definitions.
   We will assume this file is called `loader.cf`

3. Verify that environment safety settings are on (should always be the case)

   * :inmanta.environment-settings:setting:`protected_environment` = True

4. Temporarily disable auto_deploy

   * :inmanta.environment-settings:setting:`auto_deploy` = False

5. Click ‘recompile’ to install the project.

   * To check if the compile is done, check the `Compile Reports`
   * A new version may appear but it will not start to deploy
   * This may take a while as the project has to be installed.

6. Send the new service definition to the server:
Log onto the orchestrator and navigate to the folder for this environment.

If no instance updates are expected use:

.. code-block:: sh

    inmanta-workon $envid
    inmanta -vvv -X export -j /dev/null -e $envid -f loader.cf --export-plugin service_entities_exporter_strict

1. Click `Recompile`

   * The compiler will produce a new version, that will not start to deploy

2. Verify that the resources in this first version are as expected.
3. Click deploy to make the changes effective

   * Keep a close eye on progress and problems that may arise.
   * In case of trouble, hit the emergency stop. Resuming after a stop is very easy and stopping gives you time to investigate.

7. Verify that automation setting are on

   * :inmanta.environment-settings:setting:`agent_trigger_method_on_auto_deploy` = push_incremental_deploy
   * :inmanta.environment-settings:setting:`auto_deploy` = True
   * :inmanta.environment-settings:setting:`push_on_auto_deploy` = True
   * :inmanta.environment-settings:setting:`server_compile` = True

8. Perform initial tests of all services via the API.


Issue templates
###############

For convenient inclusion in issue tickets, this section provides ready made markdown templates.


Upgrade of service model on the orchestrator
+++++++++++++++++++++++++++++++++++++++++++++

.. literalinclude:: checklist_lsm_upgrade.md.inc
    :language: markdown

Install of service model on the orchestrator
+++++++++++++++++++++++++++++++++++++++++++++

.. literalinclude:: checklist_lsm_install.md.inc
    :language: markdown
