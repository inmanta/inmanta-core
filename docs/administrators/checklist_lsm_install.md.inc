# Required Information:

  * [ ] The entry point for exporting the API definition is:
  * [ ] The environment id is:

# Pre-Upgrade steps:

1. Verify that environment safety settings are on (this should always be the case)

   * [ ] `protected_environment = True`

2. Temporarily disable auto_deploy

   * [ ] `auto_deploy = False`

3. [ ] Click ‘recompile’ to install the project.
4. [ ] Send the new service definition to the server:
    Log onto the orchestrator and navigate to the folder for this environment.
    ```sh
    cd /var/lib/inmanta/$envid/
    inmanta -vvv -X export -j /tmp/dump.json -e $envid -f loader.cf --export-plugin service_entities_exporter
    ```
5. [ ] Click `Recompile`
6. [ ] Verify that the resources in this first version are as expected.

7. [ ] Click deploy to make the changes effective
8. [ ] Monitor progress
9. [ ] Verify that automation setting are on

    * `agent_trigger_method_on_auto_deploy = push_incremental_deploy`
    * `auto_deploy = true`
    * `push_on_auto_deploy = true`
    * `server_compile = true`


10. Perform initial tests of all services via the API.
