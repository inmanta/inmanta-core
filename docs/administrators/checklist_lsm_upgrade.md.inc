# Required Information:

  * [ ] The entry point for exporting the API definition is:
  * [ ] The environment id is:

# Pre-Upgrade steps:

1. Verify that environment safety settings are on (this should always be the case)

   * [ ] `protected_environment = True`

2. Temporarily disable auto_deploy

   * [ ] `auto_deploy = False`

3. [ ] Click ‘recompile’ to verify that no new deploy would start.

   * A new version will appear but it will not start to deploy

4. [ ] Inspect the current state of the latest active version, verify no failures are happening and the deploy looks healthy
5. [ ] (Optional) Perform a dryrun. Wait for the dryrun to complete and take note of all changes detected by the dryrun. Ideally there should be none.
6. [ ] Block out all north-bound api calls
7. [ ] Pause all agents
8. [ ] Backup the database `pgdump`

# Upgrade procedure

1. [ ] Click `Update and recompile`

    * A new version will appear but it will not start to deploy

2. [ ] Send the new service definition to the server:
    Log onto the orchestrator and navigate to the folder for this environment.
    ```sh
    cd /var/lib/inmanta/$envid/
    inmanta -vvv -X export -j /tmp/dump.json -e $envid -f loader.cf --export-plugin service_entities_exporter
    ```
3. [ ] Click `Recompile`
4. [ ] Re-enable the agents

5. [ ] Click dryrun on the new version

    * The dryrun report will open
    * Wait for the dryrun to finish
    * [ ] Inspect any changes found by the dryrun, determine if they are expected. If unexpected things are present, go to the abort procedure.
6. [ ] If all is OK, click deploy to make the changes effective

# Post Upgrade procedure

1. Re-enable auto_deploy

    * [ ] `auto_deploy = True`

2. Allow requests to be sent to the north bound api again


# Upgrade abort/revert

1. [ ] Delete the bad (latest) version
2. [ ] Push a revert commit onto the release branch (`git commit revert HEAD; git push`)
3. [ ] Click `Update and recompile`
4. [ ] Send the old service definition to the server:
    Log onto the orchestrator and navigate to the folder for this environment.
    ```sh
    cd /var/lib/inmanta/$envid/
    inmanta -vvv -X export -j /tmp/dump.json -e $envid -f loader.cf --export-plugin service_entities_exporter
    ```
3. [ ] Click `Recompile`
4. [ ] Re-enable the agents
5. [ ] Click dryrun on the new version

    * The dryrun report will open
    * Wait for the dryrun to finish
    * [ ] Inspect any changes found by the dryrun, this should be identical to the dryrun before the upgrade. If this is not the case, hit the emergency stop button and and contact support.
6. If the API update is irreversible or the end-result after revert is different from the expected result, restore the database tables `lsm_serviceentity` and `lsm_serviceinstance`.
