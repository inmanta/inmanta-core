"""
    Copyright 2021 Inmanta

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
import uuid
from typing import Awaitable, Callable
from uuid import UUID

import pytest

import inmanta.protocol
from inmanta import const, data, util
from inmanta.agent.agent_new import Agent
from inmanta.data import CORE_SCHEMA_NAME, PACKAGE_WITH_UPDATE_FILES
from inmanta.data.schema import DBSchema
from inmanta.protocol import methods
from inmanta.server import SLICE_COMPILER, SLICE_SERVER
from inmanta.server.services.compilerservice import CompilerService

if __file__ and os.path.dirname(__file__).split("/")[-2] == "inmanta_tests":
    from inmanta_tests.utils import wait_for_version, wait_until_deployment_finishes  # noqa: F401
else:
    from utils import wait_for_version, wait_until_deployment_finishes


def check_result(result: inmanta.protocol.Result) -> bool:
    assert result.code == 200


async def populate_facts_and_parameters(client, env_id: str):
    parameters: list[dict[str, str]] = [
        {
            "id": "fact1",
            "source": const.ParameterSource.fact,
            "value": "value1",
            "resource_id": "std::testing::NullResource[localhost,name=test1]",
            "expires": False,
        },
        {
            "id": "fact2",
            "source": const.ParameterSource.fact,
            "value": "value2",
            "resource_id": "std::testing::NullResource[localhost,name=test2]",
            "expires": None,
        },
        {
            "id": "fact3",
            "source": const.ParameterSource.fact,
            "value": "value3",
            "resource_id": "std::testing::NullResource[localhost,name=test3]",
            "expires": True,
        },
        {
            "id": "parameter1",
            "source": const.ParameterSource.fact,
            "value": "value1",
            "expires": False,
        },
        {
            "id": "parameter2",
            "source": const.ParameterSource.fact,
            "value": "value2",
            "expires": None,
        },
        {
            "id": "parameter3",
            "source": const.ParameterSource.fact,
            "value": "value3",
            "expires": False,
        },
    ]
    for param_data in parameters:
        check_result(
            await client.set_param(
                tid=UUID(env_id),
                id=param_data["id"],
                source=param_data["source"],
                value=param_data["value"],
                resource_id=param_data.get("resource_id", None),
                expires=param_data.get("expires", None),
            )
        )


@pytest.mark.parametrize("no_agent", [True])  # set config value
async def test_dump_db(
    server,
    client,
    postgres_db,
    database_name,
    agent_factory: Callable[[uuid.UUID], Awaitable[Agent]],
    resource_container,
    no_agent,
) -> None:
    if False:
        # trick autocomplete to have autocomplete on client
        client = methods

    compilerslice: CompilerService = server.get_slice(SLICE_COMPILER)

    result = await client.create_project("project-test-a")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev-1")
    assert result.code == 200
    env_id_1 = result.result["environment"]["id"]
    env1 = await data.Environment.get_by_id(uuid.UUID(env_id_1))
    await agent_factory(env_id_1)

    env_1_version = 1

    check_result(await client.create_environment(project_id=project_id, name="dev-2"))

    project_dir = os.path.join(server.get_slice(SLICE_SERVER)._server_storage["server"], str(env_id_1), "compiler")
    project_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..", "data", "simple_project")

    # Get correct version
    version = sorted([v.version for v in DBSchema(CORE_SCHEMA_NAME, PACKAGE_WITH_UPDATE_FILES, None)._get_update_functions()])[
        -1
    ]
    outfile = os.path.join(os.path.dirname(__file__), "dumps", f"v{version}.sql")
    print("Project at: ", project_dir)

    shutil.copytree(project_source, project_dir)

    check_result(await client.set_setting(env_id_1, "autostart_agent_deploy_splay_time", 0))
    check_result(await client.set_setting(env_id_1, "autostart_agent_deploy_interval", "0"))
    check_result(await client.set_setting(env_id_1, "autostart_agent_repair_splay_time", 0))
    check_result(await client.set_setting(env_id_1, "autostart_agent_repair_interval", "600"))
    check_result(await client.set_setting(env_id_1, "auto_deploy", False))

    check_result(await client.notify_change(id=env_id_1))

    versions = await wait_for_version(client, env_id_1, env_1_version, compile_timeout=40)
    v1 = versions["versions"][0]["version"]

    check_result(
        await client.release_version(env_id_1, v1, push=True, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy)
    )

    await wait_until_deployment_finishes(client, env_id_1, 20)

    check_result(await client.notify_change(id=env_id_1, update=False))

    env_1_version += 1
    await wait_for_version(client, env_id_1, env_1_version)

    remote_id1 = uuid.uuid4()
    await compilerslice.request_recompile(
        env=env1, force_update=False, do_export=True, remote_id=remote_id1, env_vars={"add_one_resource": "true"}
    )

    env_1_version += 1
    await wait_for_version(client, env_id_1, env_1_version)

    check_result(
        await client.release_version(
            env_id_1, env_1_version, push=True, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy
        )
    )

    await wait_until_deployment_finishes(client, env_id_1, 20)

    # a version that is release, but not deployed
    check_result(await client.notify_change(id=env_id_1, update=False))

    env_1_version += 1
    await wait_for_version(client, env_id_1, env_1_version)
    check_result(
        await client.release_version(
            env_id_1, env_1_version, push=False, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy
        )
    )

    await populate_facts_and_parameters(client, env_id_1)

    # a not released version
    check_result(await client.notify_change(id=env_id_1, update=False))
    env_1_version += 1
    await wait_for_version(client, env_id_1, env_1_version)
    check_result(await client.notify_change(id=env_id_1))
    env_1_version += 1
    await wait_for_version(client, env_id_1, env_1_version)

    # Partial compile
    rid2 = "test::Resource[agent2,key=key2]"
    resources_partial = [
        {
            "key": "key2",
            "version": 0,
            "id": f"{rid2},v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {rid2: "set-a"}
    resource_states = {rid2: const.ResourceState.available}
    check_result(
        await client.put_partial(
            tid=env_id_1,
            resources=resources_partial,
            resource_state=resource_states,
            unknowns=[],
            version_info=None,
            resource_sets=resource_sets,
        )
    )

    result = await client.create_environment(project_id=project_id, name="dev-3")
    assert result.code == 200
    env_id_3 = result.result["environment"]["id"]
    await agent_factory(env_id_3)

    check_result(await client.set_setting(env_id_3, "autostart_agent_deploy_splay_time", 0))
    check_result(await client.set_setting(env_id_3, "autostart_agent_deploy_interval", "0"))
    check_result(await client.set_setting(env_id_3, "autostart_agent_repair_splay_time", 0))
    check_result(await client.set_setting(env_id_3, "autostart_agent_repair_interval", "600"))
    check_result(await client.set_setting(env_id_3, "auto_deploy", False))

    def get_resources(version: int) -> list[dict[str, object]]:
        return [
            {
                "key": "key1",
                "value": "val1",
                "version": version,
                "id": f"test::Resource[agent1,key=key1],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key2",
                "value": "val2",
                "version": version,
                "id": f"test::Fail[agent1,key=key2],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key3",
                "value": "val3",
                "version": version,
                "id": f"test::Resource[agent1,key=key3],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [f"test::Fail[agent1,key=key2],v={version}"],
            },
            {
                "key": "key4",
                "value": "val4",
                "version": version,
                "id": f"test::Resource[agent1,key=key4],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key5",
                "value": "val5",
                "version": version,
                "id": f"test::Resource[agent1,key=key5],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [f"test::Resource[agent1,key=key4],v={version}"],
            },
            {
                "key": "key6",
                "value": "val6",
                "version": version,
                "id": f"test::Resource[agent1,key=key6],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [],
            },
        ]

    res = await client.reserve_version(env_id_3)
    assert res.code == 200
    version = res.result["data"]
    res = await client.put_version(
        tid=env_id_3,
        version=version,
        resources=get_resources(version),
        resource_state={
            "test::Resource[agent1,key=key1]": const.ResourceState.available,
            "test::Resource[agent1,key=key2]": const.ResourceState.available,
            "test::Resource[agent1,key=key3]": const.ResourceState.available,
            "test::Resource[agent1,key=key4]": const.ResourceState.undefined,
            "test::Resource[agent1,key=key5]": const.ResourceState.available,
            "test::Resource[agent1,key=key6]": const.ResourceState.available,
        },
        compiler_version=util.get_compiler_version(),
    )
    assert res.code == 200
    res = await client.release_version(
        env_id_3, id=1, push=True, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy
    )
    assert res.code == 200
    await wait_until_deployment_finishes(client, env_id_3)

    # Create a second version in environment dev3 that doesn't have resource key6, but has a new resource key7
    res = await client.reserve_version(env_id_3)
    assert res.code == 200
    version = res.result["data"]
    res = await client.put_version(
        tid=env_id_3,
        version=version,
        resources=[
            *get_resources(version)[0:-1],
            {
                "key": "key7",
                "value": "val7",
                "version": version,
                "id": f"test::Resource[agent1,key=key7],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [],
            },
        ],
        resource_state={
            "test::Resource[agent1,key=key1]": const.ResourceState.available,
            "test::Resource[agent1,key=key2]": const.ResourceState.available,
            "test::Resource[agent1,key=key3]": const.ResourceState.available,
            "test::Resource[agent1,key=key4]": const.ResourceState.undefined,
            "test::Resource[agent1,key=key5]": const.ResourceState.available,
            "test::Resource[agent1,key=key7]": const.ResourceState.available,
        },
        compiler_version=util.get_compiler_version(),
    )
    assert res.code == 200
    res = await client.release_version(
        env_id_3, id=2, push=True, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy
    )
    assert res.code == 200
    await wait_until_deployment_finishes(client, env_id_3)

    # Make sure we have a new, unreleased resource
    res = await client.halt_environment(env_id_3)
    assert res.code == 200
    res = await client.reserve_version(env_id_3)
    assert res.code == 200
    version = res.result["data"]
    res = await client.put_version(
        tid=env_id_3,
        version=version,
        resources=[
            *get_resources(version)[0:-1],
            {
                "key": "key7",
                "value": "val7",
                "version": version,
                "id": f"test::Resource[agent1,key=key7],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key8",
                "value": "val8",
                "version": version,
                "id": f"test::Resource[agent1,key=key8],v={version}",
                "send_event": True,
                "purged": False,
                "requires": [],
            },
        ],
        resource_state={
            "test::Resource[agent1,key=key1]": const.ResourceState.available,
            "test::Resource[agent1,key=key2]": const.ResourceState.available,
            "test::Resource[agent1,key=key3]": const.ResourceState.available,
            "test::Resource[agent1,key=key4]": const.ResourceState.undefined,
            "test::Resource[agent1,key=key5]": const.ResourceState.available,
            "test::Resource[agent1,key=key7]": const.ResourceState.available,
            "test::Resource[agent1,key=key8]": const.ResourceState.available,
        },
        compiler_version=util.get_compiler_version(),
    )
    assert res.code == 200

    proc = await asyncio.create_subprocess_exec(
        "pg_dump", "-h", "127.0.0.1", "-p", str(postgres_db.port), "-f", outfile, "-O", "-U", postgres_db.user, database_name
    )
    await proc.wait()

    # Remove undesired lines in the database dump
    lines_to_remove = [
        "SELECT pg_catalog.set_config('search_path', '', false);\n",
        "SET default_table_access_method = heap;\n",
    ]
    with open(outfile, "r+") as fh:
        all_lines = fh.readlines()
        assert all(to_remove in all_lines for to_remove in lines_to_remove)
        fh.seek(0)
        for line in all_lines:
            fh.write(f"--{line}" if line in lines_to_remove else line)
        fh.truncate()
