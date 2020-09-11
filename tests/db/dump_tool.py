"""
    Copyright 2019 Inmanta

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: code@inmanta.com


    Tool to populate the database and dump it for database update testing
"""
import asyncio
import os
import shutil

import pytest

from inmanta import const
from inmanta.protocol import methods
from inmanta.server import SLICE_SERVER

if __file__ and os.path.dirname(__file__).split("/")[-2] == "inmanta_tests":
    from inmanta_tests.utils import _wait_until_deployment_finishes, wait_for_version  # noqa: F401
else:
    from utils import _wait_until_deployment_finishes, wait_for_version


def check_result(result):
    assert result.code == 200


@pytest.mark.asyncio
async def test_dump_db(server, client, postgres_db, database_name):
    """
    Note: remove following line from the dump: SELECT pg_catalog.set_config('search_path', '', false);

    """

    if False:
        # trick autocomplete to have autocomplete on client
        client = methods

    result = await client.create_project("project-test-a")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev-1")
    assert result.code == 200
    env_id_1 = result.result["environment"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev-2")
    assert result.code == 200

    project_dir = os.path.join(server.get_slice(SLICE_SERVER)._server_storage["environments"], str(env_id_1))
    project_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "simple_project")
    outname = "dbdump"
    print("Project at: ", project_dir)

    shutil.copytree(project_source, project_dir)

    check_result(await client.set_setting(env_id_1, "autostart_agent_deploy_splay_time", 0))
    check_result(await client.set_setting(env_id_1, "autostart_agent_deploy_interval", 0))
    check_result(await client.set_setting(env_id_1, "autostart_agent_repair_splay_time", 0))
    check_result(await client.set_setting(env_id_1, "autostart_agent_repair_interval", 600))

    await client.notify_change(id=env_id_1)

    versions = await wait_for_version(client, env_id_1, 1)
    v1 = versions["versions"][0]["version"]

    await client.release_version(env_id_1, v1, push=True, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy)

    await _wait_until_deployment_finishes(client, env_id_1, v1, 20)

    await client.notify_change(id=env_id_1)

    versions = await wait_for_version(client, env_id_1, 2)
    v2 = versions["versions"][0]["version"]

    await client.release_version(env_id_1, v2, push=True, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy)

    await _wait_until_deployment_finishes(client, env_id_1, v2, 20)

    proc = await asyncio.create_subprocess_exec(
        "pg_dump", "-h", "127.0.0.1", "-p", str(postgres_db.port), "-f", outname, "-O", "-U", postgres_db.user, database_name
    )
    await proc.wait()
