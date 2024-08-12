.. _operational_procedures:

Operational Procedures
----------------------

This document describes the best practices for various operational procedures.

.. note::
    issue templates for all procedures are available at the bottom of this page

.. _operational_procedures_release:

Project Release for Production
###############################

This process describes the steps to prepare an inmanta project for production release.

For small projects relying exclusively on public modules and Python dependencies, the default pip config, which pulls
packages from ``https://pypi.org/`` can be used. If the project requires private packages, then, for security
reasons, the default pip config, which pulls packages from ``https://pypi.org/`` should not be used and all packages
should be hosted in an internal, curated python repository (like nexus or devpi). See
`PEP 708 <https://peps.python.org/pep-0708/#motivation>`_ for more information. See the :ref:`specify_location_pip`
section for more information on how to set the project's pip configuration.

Context
++++++++
* The project development and testing is complete
* All modules have been properly released (See :ref:`Releasing and distributing modules` for the procedure).
* The project is in a git repo, with a specific branch dedicated to production releases
* The project is checked out on disk.
* All modules are checked out on the correct, tagged commit.

Procedure
++++++++++

1. Check modules install mode:

   - For v1 modules (if any): ensure that ``install_mode`` in ``project.yml`` is set to ``release``.
   - For v2 modules (if any): ensure that ``pip.pre`` is not set in ``project.yml``.

2. Freeze all modules with:

.. code-block:: bash

    inmanta -vv -X project freeze --recursive --operator "=="

This will cause the ``project.yml`` file to be updated with constraints that only allow this project to work with
this exact set of module versions. This ensures that no unwanted updates can 'leak' into the production environment.

3. Verify that all modules are frozen to the correct version:

   * Open ``project.yml`` and verify that all module versions are frozen to the expected versions

4. Commit this change.

.. code-block:: bash

    git commit -a

5. Push to the release branch.

.. code-block:: bash

    git push

.. _operational_procedures_upgrade:

Upgrade of service model on the orchestrator
#############################################

This process describes how to safely take an existing project from one version to the next.

Context
++++++++
* The orchestrator has the project already deployed and running
* The project is released (as described above)

Pre-Upgrade steps
++++++++++++++++++
1. Verify that environment safety settings are on (this should always be the case)

   * :inmanta.environment-settings:setting:`protected_environment` = True

2. Temporarily disable auto_deploy

   * :inmanta.environment-settings:setting:`auto_deploy` = False

3. Click ‘recompile’ to verify that no new deploy would start:

   * A new version will appear but it will not start to deploy

4. Inspect the current state of the latest deployed version, verify no failures are happening and the deploy looks healthy
5. (Optional) Perform a dryrun. Wait for the dryrun to complete and take note of all changes detected by the dryrun. Ideally there should be none.

Upgrade procedure
++++++++++++++++++
1. Click `Update project & recompile`

   * A new version will appear but it will not start to deploy

2. Click `Perform dry run` on the new version

   * The dryrun report will open
   * Wait for the dryrun to finish
   * Inspect any changes found by the dryrun, determine if they are expected. If unexpected things are present, go to the abort procedure.

3. If all is OK, click deploy to make the changes effective

Post Upgrade procedure
+++++++++++++++++++++++++

1. Re-enable auto_deploy

   * :inmanta.environment-settings:setting:`auto_deploy` = True


Upgrade abort/revert
+++++++++++++++++++++++

1. Delete the bad (latest) version
2. Push a revert commit onto the release branch (`git revert HEAD; git push`)
3. Go through the Upgrade procedure again to make this revert effective


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
2. Verify that environment safety settings are on (should always be the case)

   * :inmanta.environment-settings:setting:`protected_environment` = True

3. Temporarily disable auto_deploy

   * :inmanta.environment-settings:setting:`auto_deploy` = False

4. Click ‘recompile’ to install the project.

   * A new version will appear but it will not start to deploy
   * This may take a while as the project has to be installed.
   * In case of problems, consult the Compile Reports

5. Verify that the resources in this first version are as expected.
6. Click deploy to make the changes effective

   * Keep a close eye on progress and problems that may arise.
   * In case of trouble, hit the emergency stop. Resuming after a stop is very easy and stopping gives you the time to investigate.

7. Verify that automation settings are on

   * :inmanta.environment-settings:setting:`agent_trigger_method_on_auto_deploy` = push_incremental_deploy
   * :inmanta.environment-settings:setting:`auto_deploy` = True
   * :inmanta.environment-settings:setting:`push_on_auto_deploy` = True
   * :inmanta.environment-settings:setting:`server_compile` = True

8. If this model uses LSM, perform initial tests of all services via the API.

Extra careful deploy procedure
+++++++++++++++++++++++++++++++

For models that are considered risky, it is possible to enable the model in a more gradual way.
The general idea is to disengage all features on the orchestrator that make the agents perform unsupervised deployments.
Then the agents can be activated by hand, one-by-one.

This procedure only works when all agents are autostarted by the server.

1. Take note of the following settings

   * :inmanta.environment-settings:setting:`autostart_agent_deploy_interval`
   * :inmanta.environment-settings:setting:`autostart_agent_repair_interval`

2. Disable spontaneous deployment

   * :inmanta.environment-settings:setting:`autostart_agent_deploy_interval` = 0
   * :inmanta.environment-settings:setting:`autostart_agent_repair_interval` = 0
   * :inmanta.environment-settings:setting:`auto_deploy` = True
   * :inmanta.environment-settings:setting:`push_on_auto_deploy` = False

3. Click ‘recompile’ to install the project.

   * A new version will appear
   * It will go to the deploying state
   * But no resources will be deployed

4. In the agent tab, click `deploy on agent` on the 'internal' agent.

   * Press `force repair` in the dropdown menu.
   * All agents will come online

5. Perform a dryrun, to verify there are no undesirable effects.
6. Click `deploy on agent/force repair` on each agent. Verify results.
7. Ensure all environment setting are set correctly

   * :inmanta.environment-settings:setting:`agent_trigger_method_on_auto_deploy` = push_incremental_deploy
   * :inmanta.environment-settings:setting:`auto_deploy` = True
   * :inmanta.environment-settings:setting:`push_on_auto_deploy` = True
   * :inmanta.environment-settings:setting:`server_compile` = True
   * :inmanta.environment-settings:setting:`autostart_agent_deploy_interval` (restore initial value from step 1)
   * :inmanta.environment-settings:setting:`autostart_agent_repair_interval` (restore initial value from step 1)

Issue templates
###############

For convenient inclusion in issue tickets, this section provides ready made markdown templates.

Project Release for Production
++++++++++++++++++++++++++++++

.. code-block:: markdown

   * [ ] Verify in `project.yml` that `install_mode` is set to `release`.
   * [ ] Freeze all modules with `inmanta -vv -X project freeze --recursive --operator "=="`
   * [ ] Verify that all modules are frozen to the correct version
   * [ ] Commit this change (`git commit -a`)
   * [ ] Push to the release branch (`git push`)

Upgrade of service model on the orchestrator
+++++++++++++++++++++++++++++++++++++++++++++

.. code-block:: markdown

   * Pre-Upgrade steps:

   1. Verify that environment safety settings are on (this should always be the case)

       * [ ] `protected_environment = True`

   2. Temporarily disable auto_deploy

      * [ ] `auto_deploy = False`

   3. [ ] Click ‘recompile’ to verify that no new deploy would start.

       * A new version will appear but it will not start to deploy

   4. [ ] Inspect the current state of the latest active version, verify no failures are happening and the deploy looks healthy
   5. [ ] (Optional) Perform a dryrun. Wait for the dryrun to complete and take note of all changes detected by the dryrun. Ideally there should be none.

   * Upgrade procedure

   1. [ ] Click `Update and recompile`

      * A new version will appear but it will not start to deploy

   2. [ ] Click dryrun on the new version

      * The dryrun report will open
      * Wait for the dryrun to finish
      * [ ] Inspect any changes found by the dryrun, determine if they are expected. If unexpected things are present, go to the abort procedure.
   3. [ ] If all is OK, click deploy to make the changes effective

   * Post Upgrade procedure

   1. Re-enable auto_deploy

       * [ ] `auto_deploy = True`

   * Upgrade abort/revert

   1. [ ] Delete the bad (latest) version
   2. [ ] Push a revert commit onto the release branch (`git commit revert HEAD; git push`)
   3. [ ] Click `Update and recompile`

      * A new version will appear but it will not start to deploy

   4. [ ] Click dryrun on the new version

      * The dryrun report will open
      * Wait for the dryrun to finish
      * [ ] Inspect any changes found by the dryrun, this should be identical to the dryrun before the upgrade. If this is not the case, hit the emergency stop button and and contact support.
