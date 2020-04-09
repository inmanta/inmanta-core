"""
    Copyright 2016 Inmanta

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
import uuid
from typing import cast

import pytest

from inmanta.data import model
from inmanta.server import SLICE_ENVIRONMENT
from inmanta.server.services.environmentservice import EnvironmentAction, EnvironmentListener, EnvironmentService
from utils import log_contains


@pytest.mark.asyncio
async def test_project_api_v1(client):
    result = await client.create_project("project-test")
    assert result.code == 200
    assert "project" in result.result
    assert "id" in result.result["project"]

    project_id = result.result["project"]["id"]

    result = await client.create_project("project-test")
    assert result.code == 500

    result = await client.list_projects()
    assert result.code == 200
    assert "projects" in result.result
    assert len(result.result["projects"]) == 1

    assert result.result["projects"][0]["id"] == project_id

    result = await client.get_project(id=project_id)
    assert result.code == 200
    assert "project" in result.result
    assert result.result["project"]["id"] == project_id
    assert result.result["project"]["name"] == "project-test"

    result = await client.modify_project(id=project_id, name="project-test2")
    assert result.code == 200
    assert "project" in result.result
    assert result.result["project"]["id"] == project_id
    assert result.result["project"]["name"] == "project-test2"

    result = await client.get_project(id=project_id)
    assert result.code == 200
    assert "project" in result.result
    assert result.result["project"]["id"] == project_id
    assert result.result["project"]["name"] == "project-test2"

    result = await client.delete_project(id=project_id)
    assert result.code == 200

    result = await client.list_projects()
    assert result.code == 200
    assert "projects" in result.result
    assert len(result.result["projects"]) == 0

    # get non existing environment
    response = await client.get_environment(uuid.uuid4())
    assert response.code == 404


@pytest.mark.asyncio
async def test_project_api_v2(client_v2):
    result = await client_v2.project_create("project-test")
    assert result.code == 200
    assert "data" in result.result
    assert "id" in result.result["data"]

    project_id = result.result["data"]["id"]

    result = await client_v2.environment_create(project_id=project_id, name="dev")
    assert result.code == 200
    assert "data" in result.result
    assert "id" in result.result["data"]
    assert "project_id" in result.result["data"]
    assert project_id == result.result["data"]["project_id"]
    assert "dev" == result.result["data"]["name"]
    env1_id = result.result["data"]["id"]

    result = await client_v2.environment_create(project_id=project_id, name="dev2")
    assert result.code == 200
    assert "data" in result.result
    assert "id" in result.result["data"]
    assert "project_id" in result.result["data"]
    assert project_id == result.result["data"]["project_id"]
    assert "dev2" == result.result["data"]["name"]

    # modify branch and repo
    result = await client_v2.environment_modify(id=env1_id, name="dev", repository="test")
    assert result.code == 200

    result = await client_v2.environment_modify(id=env1_id, name="dev", branch="test")
    assert result.code == 200

    result = await client_v2.project_list()
    assert result.code == 200
    assert "data" in result.result
    assert len(result.result["data"]) == 1
    assert len(result.result["data"][0]["environments"]) == 2

    # Failure conditions

    # Delete non existing project
    response = await client_v2.project_delete(uuid.uuid4())
    assert response.code == 404

    # Modify non existing project
    response = await client_v2.project_modify(uuid.uuid4(), name="test")
    assert response.code == 404

    # Modify to duplicate name
    response = await client_v2.project_create("project2")
    assert response.code == 200

    response = await client_v2.project_modify(project_id, name="project2")
    assert response.code == 500

    # Get non existing project
    response = await client_v2.project_get(uuid.uuid4())
    assert response.code == 404

    # Create env in non existing project
    result = await client_v2.environment_create(project_id=uuid.uuid4(), name="dev")
    assert result.code == 404

    # Create a duplicate environment
    result = await client_v2.environment_create(project_id=project_id, name="dev")
    assert result.code == 500

    # Modify a non existing environment
    result = await client_v2.environment_modify(id=uuid.uuid4(), name="dev")
    assert result.code == 404

    # Create a duplicate environment
    result = await client_v2.environment_create(project_id=project_id, name="dev", repository="")
    assert result.code == 400

    # Modify to duplicate environment
    result = await client_v2.environment_modify(id=env1_id, name="dev2")
    assert result.code == 500

    # Get an environment
    result = await client_v2.environment_get(id=env1_id)
    assert result.code == 200
    assert result.result["data"]["name"] == "dev"

    # Operation on non existing
    result = await client_v2.environment_get(id=uuid.uuid4())
    assert result.code == 404

    result = await client_v2.environment_delete(id=uuid.uuid4())
    assert result.code == 404

    # Decommission
    result = await client_v2.environment_decommission(id=env1_id)
    assert result.code == 200


@pytest.mark.asyncio
async def test_env_api(client):
    result = await client.create_project("env-test")
    assert result.code == 200
    assert "project" in result.result
    assert "id" in result.result["project"]
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    assert result.code == 200
    assert "environment" in result.result
    assert "id" in result.result["environment"]
    assert "project" in result.result["environment"]
    assert project_id == result.result["environment"]["project"]
    assert "dev" == result.result["environment"]["name"]

    env_id = result.result["environment"]["id"]

    result = await client.modify_environment(id=env_id, name="dev2")
    assert result.code == 200
    assert "environment" in result.result
    assert result.result["environment"]["id"] == env_id
    assert result.result["environment"]["name"] == "dev2"

    result = await client.get_environment(id=env_id)
    assert result.code == 200
    assert "environment" in result.result
    assert result.result["environment"]["id"] == env_id
    assert result.result["environment"]["project"] == project_id
    assert result.result["environment"]["name"] == "dev2"

    project_result = await client.get_project(id=project_id)
    assert project_result.code == 200
    assert "project" in project_result.result
    assert env_id in project_result.result["project"]["environments"]

    result = await client.list_environments()
    assert result.code == 200
    assert len(result.result) == 1

    result = await client.delete_environment(id=env_id)
    assert result.code == 200

    result = await client.list_environments()
    assert result.code == 200
    assert "environments" in result.result
    assert len(result.result["environments"]) == 0


@pytest.mark.asyncio
async def test_project_cascade(client):
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    result = await client.create_environment(project_id=project_id, name="prod")

    result = await client.delete_project(project_id)
    assert result.code == 200

    result = await client.list_environments()
    assert len(result.result["environments"]) == 0


@pytest.mark.asyncio
async def test_create_with_id(client):
    project_id = uuid.uuid4()
    result = await client.create_project(name="test_project", project_id=project_id)
    assert result.result["project"]["id"] == str(project_id)

    env_id = uuid.uuid4()
    result = await client.create_environment(project_id=project_id, name="test_env", environment_id=env_id)
    env = result.result["environment"]
    assert env["id"] == str(env_id)
    assert env["project"] == str(project_id)

    result = await client.create_environment(project_id=project_id, name="test_env2", environment_id=env_id)
    assert result.code == 500


@pytest.mark.asyncio
async def test_environment_listener(server, client_v2, caplog):
    class EnvironmentListenerCounter(EnvironmentListener):
        def __init__(self):
            self.created_counter = 0
            self.updated_counter = 0
            self.cleared_counter = 0
            self.deleted_counter = 0

        async def environment_action_cleared(self, env: model.Environment) -> None:
            self.cleared_counter += 1

        async def environment_action_created(self, env: model.Environment) -> None:
            self.created_counter += 1
            if self.created_counter == 3:
                raise Exception("Something is not right")

        async def environment_action_deleted(self, env: model.Environment) -> None:
            self.deleted_counter += 1

        async def environment_action_updated(self, updated_env: model.Environment, original_env: model.Environment) -> None:
            self.updated_counter += 1

    environment_listener = EnvironmentListenerCounter()

    environment_service = cast(EnvironmentService, server.get_slice(SLICE_ENVIRONMENT))
    environment_service.register_listener_for_multiple_actions(
        environment_listener,
        {EnvironmentAction.created, EnvironmentAction.updated, EnvironmentAction.deleted, EnvironmentAction.cleared},
    )
    result = await client_v2.project_create("project-test")
    assert result.code == 200

    project_id = result.result["data"]["id"]

    result = await client_v2.environment_create(project_id=project_id, name="dev")
    assert result.code == 200
    env1_id = result.result["data"]["id"]

    result = await client_v2.environment_create(project_id=project_id, name="dev2")
    assert result.code == 200

    # modify branch and repo
    result = await client_v2.environment_modify(id=env1_id, name="dev", repository="test")
    assert result.code == 200

    result = await client_v2.environment_modify(id=env1_id, name="dev", branch="test")
    assert result.code == 200

    result = await client_v2.project_list()
    assert result.code == 200

    # Get an environment
    result = await client_v2.environment_get(id=env1_id)
    assert result.code == 200
    assert result.result["data"]["name"] == "dev"

    result = await client_v2.environment_delete(id=uuid.uuid4())
    assert result.code == 404

    # Decommission
    result = await client_v2.environment_decommission(id=env1_id)
    assert result.code == 200

    # Clear
    result = await client_v2.environment_clear(id=env1_id)
    assert result.code == 200

    # Delete
    result = await client_v2.environment_delete(id=env1_id)
    assert result.code == 200

    result = await client_v2.environment_create(project_id=project_id, name="dev3")
    assert result.code == 200

    log_contains(
        caplog,
        "inmanta.server.services.environmentservice",
        logging.WARNING,
        "Notifying listener of created failed with the following exception",
    )

    assert environment_listener.created_counter == 3
    assert environment_listener.updated_counter == 2
    assert environment_listener.cleared_counter == 1
    assert environment_listener.deleted_counter == 1
