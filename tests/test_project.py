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
import base64
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, cast

import pytest

from inmanta.data import model
from inmanta.module import ModuleLoadingException, Project
from inmanta.server import SLICE_ENVIRONMENT
from inmanta.server.services.environmentservice import EnvironmentAction, EnvironmentListener, EnvironmentService
from utils import log_contains


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
    assert result.code == 400

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


async def test_modify_environment_project(client_v2):
    """Test modifying the project of an environment"""

    # Create two projects and two environments
    result = await client_v2.project_create("dev-project")
    assert result.code == 200
    project_id_a = result.result["data"]["id"]

    result = await client_v2.environment_create(project_id=project_id_a, name="env")
    assert result.code == 200
    env1_id = result.result["data"]["id"]

    result = await client_v2.project_create("test-project")
    assert result.code == 200

    project_id_b = result.result["data"]["id"]
    result = await client_v2.environment_create(project_id=project_id_b, name="env")
    assert result.code == 200

    # Try to move environment from project a to b, but the name in that project is not free
    result = await client_v2.environment_modify(id=env1_id, name="env", project_id=project_id_b)
    assert result.code == 400

    # Move and rename environment from project a to b
    result = await client_v2.environment_modify(id=env1_id, name="new-env", project_id=project_id_b)
    assert result.code == 200
    assert result.result["data"]["project_id"] == project_id_b

    # Delete project a
    response = await client_v2.project_delete(project_id_a)
    assert response.code == 200

    # The environment should still exist
    result = await client_v2.environment_get(id=env1_id)
    assert result.code == 200

    # Try to move it back to the not existing project
    result = await client_v2.environment_modify(id=env1_id, name="new-env", project_id=project_id_a)
    assert result.code == 400

    # Make sure that specifying the current project id does not cause problems
    result = await client_v2.environment_modify(id=env1_id, name="new-env", project_id=project_id_b)
    assert result.code == 200


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


async def test_project_cascade(client):
    result = await client.create_project("env-test")
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    result = await client.create_environment(project_id=project_id, name="prod")

    result = await client.delete_project(project_id)
    assert result.code == 200

    result = await client.list_environments()
    assert len(result.result["environments"]) == 0


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


@pytest.mark.parametrize("install", [True, False])
def test_project_load_install(snippetcompiler_clean, install: bool) -> None:
    """
    Verify that loading a project only installs modules when install is True.
    """
    project: Project = snippetcompiler_clean.setup_for_snippet("", autostd=True, install_project=False)
    if install:
        project.load(install=True)
    else:
        with pytest.raises(ModuleLoadingException, match="Failed to load module std"):
            project.load()
        # make sure project load works after installing modules
        project.install_modules()
        project.load()


@pytest.fixture
def environment_icons() -> Dict[str, str]:
    icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "icon")
    icon_names = ["logo.jpeg", "logo.png", "logo.svg", "logo.webp"]
    icon_dict = {}
    for name in icon_names:
        icon_dict[name.split(".")[1]] = base64.b64encode(Path(os.path.join(icon_dir, name)).read_bytes()).decode("utf-8")
    return icon_dict


async def test_environment_icon_description(client_v2, environment_icons: Dict[str, str]):
    """Test creating an environment with an icon and description"""

    result = await client_v2.project_create("dev-project")
    assert result.code == 200
    project_id_a = result.result["data"]["id"]
    desc = "This is an environment"
    result = await client_v2.environment_create(project_id=project_id_a, name="env", description=desc)
    assert result.code == 200
    assert result.result["data"]["description"] == desc

    # Test description length
    result = await client_v2.environment_create(project_id=project_id_a, name="env2", description="a" * 256)
    assert result.code == 400
    result = await client_v2.environment_create(project_id=project_id_a, name="env2", description="a" * 255)
    assert result.code == 200

    for image_type, image in environment_icons.items():
        mime_type = image_type if image_type != "svg" else "svg+xml"
        result = await client_v2.environment_create(
            project_id=project_id_a, name=f"env_{image_type}", description=desc, icon=f"image/{mime_type};base64,{image}"
        )
        assert result.code == 200

    raw_icon = environment_icons["svg"]

    # Test invalid icon data strings
    result = await client_v2.environment_create(
        project_id=project_id_a, name="envx", description=desc, icon=f"image/svg+xm;base64,{raw_icon}"
    )
    assert result.code == 400

    # Specify an icon with an invalid base64 encoding
    result = await client_v2.environment_create(
        project_id=project_id_a, name="envx", description=desc, icon=f"image/svg+xml;base64,{raw_icon[0:10]}"
    )
    assert result.code == 400
    result = await client_v2.environment_create(
        project_id=project_id_a, name="envx", description=desc, icon=f"image/svg+xml;,{raw_icon}"
    )
    assert result.code == 400
    result = await client_v2.environment_create(
        project_id=project_id_a, name="envx", description=desc, icon=f"image/svg+xml;{raw_icon}"
    )
    assert result.code == 400
    result = await client_v2.environment_create(
        project_id=project_id_a, name="envx", description=desc, icon=f"image/svg+xml;base64;{raw_icon}"
    )
    assert result.code == 400
    result = await client_v2.environment_create(
        project_id=project_id_a, name="envx", description=desc, icon=f"image/svg+xml,base64;{raw_icon}"
    )
    assert result.code == 400
    result = await client_v2.environment_create(
        project_id=project_id_a, name="envx", description=desc, icon=f"image/svg+xml,base64,{raw_icon}"
    )
    assert result.code == 400
    result = await client_v2.environment_create(
        project_id=project_id_a, name="envx", description=desc, icon=f"image/svg+xmlbase64{raw_icon}"
    )
    assert result.code == 400
    result = await client_v2.environment_create(
        project_id=project_id_a, name="envx", description=desc, icon=f"image/svg+xml;base64{raw_icon}"
    )
    assert result.code == 400

    # Check too large icon, base64 encoding increases the size
    large_icon = base64.b64encode(b"a" * 65535).decode("utf-8")
    result = await client_v2.environment_create(
        project_id=project_id_a, name="envx", description=desc, icon=f"image/png;base64,{large_icon}"
    )
    assert result.code == 400

    result = await client_v2.environment_create(
        project_id=project_id_a, name="envx", description=desc, icon="image/png;base64,"
    )
    assert result.code == 400

    # Test modification of the description and icon
    name_of_env_to_modify = "env_no_icon"
    result = await client_v2.environment_create(project_id=project_id_a, name=name_of_env_to_modify, description=desc, icon="")
    assert result.code == 200
    id_of_env_to_modify = result.result["data"]["id"]

    icon_data_url = f"image/png;base64,{environment_icons['png']}"
    # Add an icon
    result = await client_v2.environment_modify(id_of_env_to_modify, name_of_env_to_modify, icon=icon_data_url)
    assert result.code == 200
    assert result.result["data"]["icon"] == icon_data_url

    new_description = "new desc"
    # Change the description, but keep the icon the same
    result = await client_v2.environment_modify(id_of_env_to_modify, name_of_env_to_modify, description=new_description)
    assert result.code == 200
    assert result.result["data"]["icon"] == icon_data_url

    # Make sure GET request works
    result = await client_v2.environment_get(id_of_env_to_modify, details=True)
    assert result.code == 200
    assert result.result["data"]["icon"] == icon_data_url
    assert result.result["data"]["description"] == new_description

    # Delete the icon
    result = await client_v2.environment_modify(id_of_env_to_modify, name_of_env_to_modify, icon="")
    assert result.code == 200

    result = await client_v2.environment_get(id_of_env_to_modify, details=True)
    assert result.code == 200
    assert result.result["data"]["icon"] == ""

    result = await client_v2.environment_modify(id_of_env_to_modify, name_of_env_to_modify, description="b" * 256)
    assert result.code == 400


async def test_environment_icon_with_details_only(client_v2, environment_icons: Dict[str, str]):
    """Test that the icon for an environment is only returned when explicitly requested"""
    result = await client_v2.project_create("dev-project")
    assert result.code == 200
    project_id_a = result.result["data"]["id"]
    # Create environment with description and icon
    icon_data_string = f"image/png;base64,{environment_icons['png']}"
    description = "desc"
    result = await client_v2.environment_create(
        project_id=project_id_a, name="env", description=description, icon=icon_data_string
    )
    assert result.code == 200
    env_id = result.result["data"]["id"]
    # Check that the icon and description are not returned without the details flag
    result = await client_v2.environment_get(env_id)
    assert result.code == 200
    assert result.result["data"]["icon"] == ""
    assert result.result["data"]["description"] == ""
    # With the details, they should be returned correctly
    result = await client_v2.environment_get(env_id, details=True)
    assert result.code == 200
    assert result.result["data"]["icon"] == icon_data_string
    assert result.result["data"]["description"] == description

    result = await client_v2.environment_list()
    assert result.code == 200
    assert result.result["data"][0]["icon"] == ""
    assert result.result["data"][0]["description"] == ""

    result = await client_v2.environment_list(details=True)
    assert result.code == 200
    assert result.result["data"][0]["icon"] == icon_data_string
    assert result.result["data"][0]["description"] == description

    result = await client_v2.project_get(project_id_a)
    assert result.code == 200
    assert result.result["data"]["environments"][0]["icon"] == ""
    assert result.result["data"]["environments"][0]["description"] == ""

    result = await client_v2.project_get(project_id_a, environment_details=True)
    assert result.code == 200
    assert result.result["data"]["environments"][0]["icon"] == icon_data_string
    assert result.result["data"]["environments"][0]["description"] == description

    result = await client_v2.project_list()
    assert result.code == 200
    assert result.result["data"][0]["environments"][0]["icon"] == ""
    assert result.result["data"][0]["environments"][0]["description"] == ""

    result = await client_v2.project_list(environment_details=True)
    assert result.code == 200
    assert result.result["data"][0]["environments"][0]["icon"] == icon_data_string
    assert result.result["data"][0]["environments"][0]["description"] == description
