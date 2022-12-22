"""
    Copyright 2017 Inmanta

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
"""
import datetime
import os
import uuid
from typing import Dict

import pytest

from inmanta import data
from inmanta.const import Change, ResourceAction, ResourceState
from inmanta.util import get_compiler_version
from utils import get_resource


async def test_project(server, client, cli):
    # create a new project
    result = await cli.run("project", "create", "-n", "test_project")
    assert result.exit_code == 0

    projects = await client.list_projects()
    assert len(projects.result["projects"]) == 1

    project = projects.result["projects"][0]
    assert project["id"] in result.output
    assert project["name"] in result.output

    # show the project
    result = await cli.run("project", "show", project["id"])
    assert result.exit_code == 0
    assert project["id"] in result.output
    assert project["name"] in result.output

    result = await cli.run("project", "show", project["name"])
    assert result.exit_code == 0
    assert project["id"] in result.output
    assert project["name"] in result.output

    # modify the project
    new_name = "test_project_2"
    result = await cli.run("project", "modify", "-n", new_name, project["name"])
    assert result.exit_code == 0
    assert project["id"] in result.output
    assert new_name in result.output

    new_name = "test_project_3"
    result = await cli.run("project", "modify", "-n", new_name, project["id"])
    assert result.exit_code == 0
    assert project["id"] in result.output
    assert new_name in result.output

    # delete the project
    result = await cli.run("project", "delete", project["id"])
    assert result.exit_code == 0


async def test_environment(server, client, cli, tmpdir):
    project_name = "test_project"
    result = await client.create_project(project_name)
    assert result.code == 200
    project_id = result.result["project"]["id"]

    # create a new environment
    result = await cli.run("environment", "create", "-n", "test1", "-r", "/git/repo", "-b", "dev1", "-p", project_name)
    assert result.exit_code == 0

    result = await cli.run("environment", "create", "-n", "test2", "-r", "/git/repo", "-b", "dev2", "-p", project_id)
    assert result.exit_code == 0

    environments = await client.list_environments()
    assert len(environments.result["environments"]) == 2
    environments = environments.result["environments"]

    # list environments
    result = await cli.run("environment", "list")
    assert result.exit_code == 0
    assert "test_project" in result.output
    assert "test1" in result.output
    assert "test2" in result.output

    # show an environment
    env_name = environments[0]["name"]
    env_id = environments[0]["id"]

    result = await cli.run("environment", "show", env_name)
    assert result.exit_code == 0
    assert env_name in result.output
    assert env_id in result.output

    result = await cli.run("environment", "show", "--format", "{id}--{name}--{project}--{repo_url}--{repo_branch}", env_name)
    assert result.exit_code == 0
    assert result.output.strip() == f"{env_id}--{env_name}--{project_id}--/git/repo--dev1"

    result = await cli.run("environment", "show", env_id)
    assert result.exit_code == 0
    assert env_name in result.output
    assert env_id in result.output

    os.chdir(tmpdir)
    result = await cli.run("environment", "save", env_name)
    assert result.exit_code == 0

    path_dot_inmanta_file = os.path.join(tmpdir, ".inmanta")
    assert os.path.isfile(path_dot_inmanta_file)
    with open(path_dot_inmanta_file, "r", encoding="utf-8") as f:
        file_content = f.read()
        assert f"environment={env_id}" in file_content


async def test_environment_recompile(server, environment, client, cli):
    result = await client.get_compile_reports(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 0

    result = await cli.run("environment", "recompile", environment)
    assert result.exit_code == 0
    assert "Recompile triggered successfully" in result.output

    result = await cli.run("environment", "recompile", environment, "--update")
    assert result.exit_code == 0
    assert "Update & Recompile triggered successfully" in result.output

    result = await client.get_compile_reports(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 2

    await client.set_setting(environment, data.SERVER_COMPILE, False)
    result = await cli.run("environment", "recompile", environment)
    assert result.exit_code == 0
    assert "Skipping compile" in result.output
    assert "Recompile triggered successfully" not in result.output


async def test_environment_settings(server, environment, client, cli):
    result = await cli.run("environment", "setting", "list", "-e", environment)
    assert result.exit_code == 0

    result = await cli.run("environment", "setting", "set", "-e", environment, "-k", "auto_deploy", "-o", "true")
    assert result.exit_code == 0
    result = await cli.run("environment", "setting", "set", "-e", environment, "--key", "auto_deploy", "--value", "true")
    assert result.exit_code == 0

    result = await cli.run("environment", "setting", "list", "-e", environment)
    assert result.exit_code == 0
    assert environment in result.output
    assert "auto_deploy" in result.output

    result = await cli.run("environment", "setting", "get", "-e", environment, "--key", "auto_deploy")
    assert result.exit_code == 0
    assert "True" in result.output

    result = await cli.run("environment", "setting", "delete", "-e", environment, "--key", "auto_deploy")
    assert result.exit_code == 0


async def test_agent(server, client, environment, cli):
    result = await cli.run("agent", "list", "-e", environment)
    assert result.exit_code == 0


@pytest.mark.parametrize("push_method", [([]), (["-p"]), (["-p", "--full"])])
async def test_version(server, client, clienthelper, environment, cli, push_method):
    version = str(await clienthelper.get_version())
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=" + version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=" + version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=" + version,
            "send_event": False,
            "requires": [],
            "purged": False,
        },
        {
            "key": "key3",
            "value": None,
            "id": "test::Resource[agent1,key=key3],v=" + version,
            "send_event": False,
            "requires": [],
            "purged": True,
        },
    ]

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    result = await cli.run("version", "list", "-e", environment)
    assert result.exit_code == 0
    assert version in result.output
    assert "pending" in result.output

    result = await cli.run("version", "release", "-e", environment, version, *push_method)
    assert result.exit_code == 0
    assert version in result.output

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["result"] == "deploying"

    result = await cli.run("version", "report", "-e", environment, "-i", version)
    assert result.exit_code == 0


async def test_param(server, client, environment, cli):
    await client.set_setting(environment, data.SERVER_COMPILE, False)

    result = await cli.run("param", "set", "-e", environment, "--name", "var1", "--value", "value1")
    assert result.exit_code == 0
    assert "value1" in result.output

    result = await cli.run("param", "get", "-e", environment, "--name", "var1")
    assert result.exit_code == 0
    assert "value1" in result.output

    result = await cli.run("param", "list", "-e", environment)
    assert result.exit_code == 0
    assert "var1" in result.output


async def test_create_environment(tmpdir, server, client, cli):
    """
    Tests the "inmanta-cli environment create" command
    and overwrite prompt/overwriting of the .inmanta file
    """
    os.chdir(tmpdir)
    file_path = os.path.join(os.getcwd(), ".inmanta")
    result = await client.create_project("test")
    assert result.code == 200

    result = await cli.run("environment", "create", "-n", "test-env-0", "-p", "test", "--save")
    assert result.exit_code == 0
    assert os.path.exists(file_path)

    with open(file_path, "r") as inmanta_file:
        file_content_0 = inmanta_file.read()
    ctime_0 = os.path.getctime(file_path)

    result = await cli.run("environment", "create", "-n", "test-env-1", "-p", "test", "--save", input="n")
    assert result.exit_code == 0

    with open(file_path, "r") as inmanta_file:
        file_content_1 = inmanta_file.read()

    ctime_1 = os.path.getctime(file_path)

    assert file_content_0 == file_content_1
    assert ctime_0 == ctime_1

    result = await cli.run("environment", "create", "-n", "test-env-2", "-p", "test", "--save", input="y")
    assert result.exit_code == 0

    with open(file_path, "r") as inmanta_file:
        file_content_2 = inmanta_file.read()

    ctime_2 = os.path.getctime(file_path)

    assert file_content_0 != file_content_2
    assert ctime_0 != ctime_2


async def test_inmanta_cli_http_version(server, client, cli):
    result = await cli.run("project", "create", "-n", "test_project")
    assert result.exit_code == 0


async def test_pause_agent(server, cli):
    project = data.Project(name="test")
    await project.insert()
    env1 = data.Environment(name="env1", project=project.id)
    await env1.insert()
    env2 = data.Environment(name="env2", project=project.id)
    await env2.insert()

    await data.Agent(environment=env1.id, name="agent1", paused=False).insert()
    await data.Agent(environment=env1.id, name="agent2", paused=False).insert()
    await data.Agent(environment=env2.id, name="agent3", paused=False).insert()

    async def assert_agent_paused(env_id: uuid.UUID, expected_records: Dict[str, bool]) -> None:
        result = await cli.run("agent", "list", "-e", str(env_id))
        assert result.exit_code == 0
        output = result.stdout.replace(" ", "")
        assert "Agent|Environment|Paused" in output
        for (agent_name, paused) in expected_records.items():
            assert f"{agent_name}|{env_id}|{paused}" in output

    await assert_agent_paused(env_id=env1.id, expected_records=dict(agent1=False, agent2=False))
    await assert_agent_paused(env_id=env2.id, expected_records=dict(agent3=False))

    # Pause
    result = await cli.run("agent", "pause", "-e", str(env1.id), "--agent", "agent1")
    assert result.exit_code == 0
    await assert_agent_paused(env_id=env1.id, expected_records=dict(agent1=True, agent2=False))
    await assert_agent_paused(env_id=env2.id, expected_records=dict(agent3=False))

    # Unpause
    result = await cli.run("agent", "unpause", "-e", str(env1.id), "--agent", "agent1")
    assert result.exit_code == 0
    await assert_agent_paused(env_id=env1.id, expected_records=dict(agent1=False, agent2=False))
    await assert_agent_paused(env_id=env2.id, expected_records=dict(agent3=False))

    # Pause all agents in env1
    result = await cli.run("agent", "pause", "-e", str(env1.id), "--all")
    assert result.exit_code == 0
    await assert_agent_paused(env_id=env1.id, expected_records=dict(agent1=True, agent2=True))
    await assert_agent_paused(env_id=env2.id, expected_records=dict(agent3=False))

    # Unpause all agents in env1
    result = await cli.run("agent", "unpause", "-e", str(env1.id), "--all")
    assert result.exit_code == 0
    await assert_agent_paused(env_id=env1.id, expected_records=dict(agent1=False, agent2=False))
    await assert_agent_paused(env_id=env2.id, expected_records=dict(agent3=False))

    # Mandatory option -e not specified
    for action in ["pause", "unpause"]:
        result = await cli.run("agent", action, "--agent", "agent1")
        assert result.exit_code != 0

    # --agent and --all are both set
    for action in ["pause", "unpause"]:
        result = await cli.run("agent", action, "-e", str(env1.id), "--agent", "agent1", "--all")
        assert result.exit_code != 0

    # --agent and --all are both not set
    for action in ["pause", "unpause"]:
        result = await cli.run("agent", action, "-e", str(env1.id))
        assert result.exit_code != 0


async def test_list_actionlog(server, environment, client, cli, agent, clienthelper):
    """
    Test the `inmanta-cli action-log list` command.
    """

    def assert_nr_records_in_output_table(output: str, nr_records: int) -> None:
        lines = [line.strip() for line in output.split("\n") if line.strip() and line.strip().startswith("|")]
        actual_nr_of_records = len(lines) - 1  # Exclude the header
        assert nr_records == actual_nr_of_records

    result = await client.reserve_version(tid=environment)
    assert result.code == 200
    version = result.result["data"]

    resource1 = get_resource(version, key="test1")
    resource2 = get_resource(version, key="test2")
    await clienthelper.put_version_simple(resources=[resource1, resource2], version=version)

    result = await agent._client.resource_action_update(
        tid=environment,
        resource_ids=[resource1["id"]],
        action_id=uuid.uuid4(),
        action=ResourceAction.deploy,
        started=datetime.datetime.now(),
        finished=datetime.datetime.now(),
        status=ResourceState.failed,
        messages=[
            {
                "level": "INFO",
                "msg": "Deploying",
                "timestamp": datetime.datetime.now().isoformat(timespec="microseconds"),
                "args": [],
            },
            {
                "level": "ERROR",
                "msg": "Deployment failed",
                "timestamp": datetime.datetime.now().isoformat(timespec="microseconds"),
                "args": [],
                "status": ResourceState.failed.value,
            },
        ],
        changes={},
        change=Change.nochange,
        send_events=False,
    )
    assert result.code == 200
    result = await agent._client.resource_action_update(
        tid=environment,
        resource_ids=[resource2["id"]],
        action_id=uuid.uuid4(),
        action=ResourceAction.deploy,
        started=datetime.datetime.now(),
        finished=datetime.datetime.now(),
        status=ResourceState.deployed,
        messages=[
            {
                "level": "INFO",
                "msg": "Deployed successfully",
                "timestamp": datetime.datetime.now().isoformat(timespec="microseconds"),
                "args": [],
            },
        ],
        changes={},
        change=Change.nochange,
        send_events=False,
    )
    assert result.code == 200

    # Get all resource actions for resource1
    result = await cli.run("action-log", "list", "-e", str(environment), "--rvid", resource1["id"])
    assert result.exit_code == 0
    assert_nr_records_in_output_table(result.output, nr_records=2)  # 1 store action + 1 deploy action

    # Get deploy resource actions for resource1
    result = await cli.run("action-log", "list", "-e", str(environment), "--rvid", resource1["id"], "--action", "deploy")
    assert result.exit_code == 0
    assert_nr_records_in_output_table(result.output, nr_records=1)  # 1 deploy action

    # Resource id is provided instead of resource version id
    resource_id = resource1["id"].rsplit(",", maxsplit=1)[0]
    result = await cli.run("action-log", "list", "-e", str(environment), "--rvid", resource_id)
    assert result.exit_code != 0
    assert f"Invalid value for '--rvid': {resource_id}" in result.stderr

    # Incorrect format resource version id
    result = await cli.run("action-log", "list", "-e", str(environment), "--rvid", "test")
    assert result.exit_code != 0
    assert "Invalid value for '--rvid': test" in result.stderr


async def test_show_messages_actionlog(server, environment, client, cli, agent, clienthelper):
    """
    Test the `inmanta-cli action-log show-messages` command.
    """
    result = await client.reserve_version(tid=environment)
    assert result.code == 200
    version = result.result["data"]

    resource1 = get_resource(version, key="test1")
    await clienthelper.put_version_simple(resources=[resource1], version=version)

    result = await agent._client.resource_action_update(
        tid=environment,
        resource_ids=[resource1["id"]],
        action_id=uuid.uuid4(),
        action=ResourceAction.deploy,
        started=datetime.datetime.now(),
        finished=datetime.datetime.now(),
        status=ResourceState.deployed,
        messages=[
            {
                "level": "DEBUG",
                "msg": "Started deployment",
                "timestamp": datetime.datetime.now().isoformat(timespec="microseconds"),
                "args": [],
            },
            {
                "level": "INFO",
                "msg": "Deployed successfully",
                "timestamp": datetime.datetime.now().isoformat(timespec="microseconds"),
                "args": [],
            },
        ],
        changes={},
        change=Change.nochange,
        send_events=False,
    )
    assert result.code == 200

    # Obtain action_id
    result = await client.get_resource(tid=environment, id=resource1["id"], logs=True, log_action=ResourceAction.deploy)
    assert result.code == 200
    assert len(result.result["logs"]) == 1
    action_id = result.result["logs"][0]["action_id"]

    result = await cli.run(
        "action-log", "show-messages", "-e", str(environment), "--rvid", resource1["id"], "--action-id", str(action_id)
    )
    assert result.exit_code == 0
    assert "DEBUG Started deployment" in result.output
    assert "INFO Deployed successfully" in result.output
