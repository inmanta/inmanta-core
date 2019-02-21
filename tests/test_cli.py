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
import pytest


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
async def test_environment(server, client, cli):
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


@pytest.mark.parametrize("push_method", [([]),
                                         (["-p"]),
                                         (["-p", "--full"])])
@pytest.mark.asyncio
async def test_version(server, client, environment, cli, push_method):
    version = "12345"
    resources = [{'key': 'key1',
                  'value': 'value1',
                  'id': 'test::Resource[agent1,key=key1],v=' + version,
                  'send_event': False,
                  'purged': False,
                  'requires': ['test::Resource[agent1,key=key2],v=' + version],
                  },
                 {'key': 'key2',
                  'value': 'value2',
                  'id': 'test::Resource[agent1,key=key2],v=' + version,
                  'send_event': False,
                  'requires': [],
                  'purged': False,
                  },
                 {'key': 'key3',
                  'value': None,
                  'id': 'test::Resource[agent1,key=key3],v=' + version,
                  'send_event': False,
                  'requires': [],
                  'purged': True,
                  }
                 ]

    result = await client.put_version(tid=environment, version=version, resources=resources, unknowns=[], version_info={})
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
async def test_form_and_records(server, client, environment, cli):
    form_type = "FormType"
    result = await client.put_form(tid=environment, id=form_type,
                                   form={'attributes': {'field1': {'default': 1, 'options': {'min': 1, 'max': 100},
                                                                   'type': 'number'},
                                                        'field2': {'default': "", 'options': {}, 'type': 'string'}},
                                         'options': {},
                                         'type': form_type}
                                   )
    assert(result.code == 200)
    form_id = result.result["form"]["id"]

    result = await cli.run("form", "list", "-e", environment)
    assert result.exit_code == 0
    assert form_id in result.output

    result = await cli.run("form", "show", "-e", environment, "-t", form_type)
    assert result.exit_code == 0
    assert "field1" in result.output
    assert "field2" in result.output

    result = await cli.run("record", "create", "-e", environment, "-t", form_type, "-p", "field1=1234", "-p", "field2=test456")
    assert result.exit_code == 0
    assert "1234" in result.output
    assert "test456" in result.output

    records = await client.list_records(tid=environment, form_type=form_type)
    assert records.code == 200
    record = records.result["records"][0]
    record_id = record["id"]

    result = await cli.run("record", "list", "-e", environment, "-t", form_type)
    assert result.exit_code == 0
    assert record_id in result.output

    result = await cli.run("record", "list", "-e", environment, "-t", form_type, "--show-all")
    assert result.exit_code == 0

    result = await cli.run("record", "update", "-e", environment, "-r", record_id, "-p", "field1=98765")
    assert result.exit_code == 0
    assert "98765" in result.output

    result = await cli.run("record", "delete", "-e", environment, record_id)
    assert result.exit_code == 0

    records = await client.list_records(tid=environment, form_type=form_type)
    assert records.code == 200
    assert len(records.result["records"]) == 0


@pytest.mark.asyncio
async def test_import_export(server, client, environment, cli, tmpdir):
    form_type = "FormType"
    result = await client.put_form(tid=environment, id=form_type,
                                   form={'attributes': {'field1': {'default': 1, 'options': {'min': 1, 'max': 100},
                                                                   'type': 'number'},
                                                        'field2': {'default': "", 'options': {}, 'type': 'string'}},
                                         'options': {},
                                         'type': form_type}
                                   )
    form_id = result.result["form"]["id"]

    result = await cli.run("record", "create", "-e", environment, "-t", form_type, "-p", "field1=1234", "-p", "field2=test456")
    assert result.exit_code == 0

    result = await cli.run("form", "export", "-e", environment, "-t", form_type)
    assert form_id in result.output

    f = tmpdir.join("export.json")
    f.write(result.output)

    records = await client.list_records(tid=environment, form_type=form_type)
    assert records.code == 200
    record = records.result["records"][0]

    await client.delete_record(tid=environment, id=record["id"])
    records = await client.list_records(tid=environment, form_type=form_type)
    assert records.code == 200
    assert len(records.result["records"]) == 0

    result = await cli.run("form", "import", "-e", environment, "-t", form_type, "--file", str(f))

    records = await client.list_records(tid=environment, form_type=form_type)
    assert records.code == 200
    assert len(records.result["records"]) == 1
