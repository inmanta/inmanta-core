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
import logging
import os

import pytest

from inmanta import data
from inmanta.util import get_compiler_version
from utils import log_contains


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_agent(server, client, environment, cli):
    result = await cli.run("agent", "list", "-e", environment)
    assert result.exit_code == 0


@pytest.mark.parametrize("push_method", [([]), (["-p"]), (["-p", "--full"])])
@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_inmanta_cli_http_version(server, client, cli, caplog):
    with caplog.at_level(logging.DEBUG):
        result = await cli.run("project", "create", "-n", "test_project")
        assert result.exit_code == 0
        log_contains(caplog, "inmanta.protocol.rest.server", logging.DEBUG, "HTTP version of request: HTTP/1.1")
