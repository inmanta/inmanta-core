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
"""

from uuid import UUID

import pytest

from inmanta import data
from inmanta.data import Environment, Setting, convert_boolean
from inmanta.util import get_compiler_version


def get_environment_setting_default(setting: str) -> object:
    return data.Environment._settings[setting].default


def check_only_contains_default_setting(settings_dict: dict[str, object]) -> None:
    """
    Depending on when the background cleanup processes are run, it is possible that environment settings are set, independently
    of the tests below. This method ensures these settings are properly set with their default values.
    """
    for setting_name, setting_value in settings_dict.items():
        assert setting_value == get_environment_setting_default(setting_name)


async def test_api_return_type(client, server, environment):
    """
    https://github.com/inmanta/inmanta-core/pull/6574 changed the type of AUTOSTART_AGENT_REPAIR_INTERVAL and
    AUTOSTART_AGENT_DEPLOY_INTERVAL from int to str. This test makes sure the type returned by the api is correct
    """
    result = await client.get_setting(tid=environment, id=data.AUTOSTART_AGENT_REPAIR_INTERVAL)

    assert result.code == 200
    assert result.result["value"] == "86400"


async def test_environment_settings(client, server, environment_default):
    """
    Test environment settings
    """
    result = await client.list_settings(tid=environment_default)
    assert result.code == 200
    assert "settings" in result.result
    assert "metadata" in result.result
    assert "auto_deploy" in result.result["metadata"]

    check_only_contains_default_setting(result.result["settings"])

    # set invalid value
    result = await client.set_setting(tid=environment_default, id="auto_deploy", value="test")
    assert result.code == 400

    # set non existing setting
    result = await client.set_setting(tid=environment_default, id="auto_deploy_non", value=False)
    assert result.code == 404

    result = await client.set_setting(tid=environment_default, id="auto_deploy", value=False)
    assert result.code == 200

    result = await client.list_settings(tid=environment_default)
    assert result.code == 200

    for setting_name, setting_value in result.result["settings"].items():
        if setting_name == "auto_deploy":
            assert setting_value is False
        else:
            assert setting_value == get_environment_setting_default(setting_name)

    result = await client.get_setting(tid=environment_default, id="auto_deploy")
    assert result.code == 200
    assert not result.result["value"]

    result = await client.get_setting(tid=environment_default, id="test2")
    assert result.code == 404

    result = await client.set_setting(tid=environment_default, id="auto_deploy", value=True)
    assert result.code == 200

    result = await client.get_setting(tid=environment_default, id="auto_deploy")
    assert result.code == 200
    assert result.result["value"]

    result = await client.delete_setting(tid=environment_default, id="test2")
    assert result.code == 404

    result = await client.delete_setting(tid=environment_default, id="auto_deploy")
    assert result.code == 200

    result = await client.list_settings(tid=environment_default)
    assert result.code == 200
    assert "settings" in result.result

    check_only_contains_default_setting(result.result["settings"])

    result = await client.set_setting(tid=environment_default, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, value=20)
    assert result.code == 200

    result = await client.set_setting(tid=environment_default, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, value="30")
    assert result.code == 200

    result = await client.get_setting(tid=environment_default, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME)
    assert result.code == 200
    assert result.result["value"] == 30

    result = await client.delete_setting(tid=environment_default, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME)
    assert result.code == 200

    agent_map = {"internal": "", "agent1": "", "agent2": "localhost", "agent3": "user@agent3"}
    result = await client.set_setting(
        tid=environment_default,
        id=data.AUTOSTART_AGENT_MAP,
        value=agent_map,
    )
    assert result.code == 200

    # Internal agent is missing
    result = await client.set_setting(tid=environment_default, id=data.AUTOSTART_AGENT_MAP, value={"agent1": ""})
    assert result.code == 400
    assert "The internal agent must be present in the autostart_agent_map" in result.result["message"]
    # Assert agent_map didn't change
    result = await client.get_setting(tid=environment_default, id=data.AUTOSTART_AGENT_MAP)
    assert result.code == 200
    assert result.result["value"] == agent_map

    result = await client.set_setting(tid=environment_default, id=data.AUTOSTART_AGENT_MAP, value="")
    assert result.code == 400
    assert "Agent map should be a dict" in result.result["message"]
    # Assert agent_map didn't change
    result = await client.get_setting(tid=environment_default, id=data.AUTOSTART_AGENT_MAP)
    assert result.code == 200
    assert result.result["value"] == agent_map


async def test_environment_settings_v2(client_v2, server, environment_default):
    """
    Test environment settings
    """
    response = await client_v2.environment_settings_list(tid=environment_default)
    assert response.code == 200
    assert "settings" in response.result["data"]
    assert "definition" in response.result["data"]
    assert "auto_deploy" in response.result["data"]["definition"]
    check_only_contains_default_setting(response.result["data"]["settings"])

    response = await client_v2.environment_settings_set(tid=environment_default, id="auto_deploy", value=False)
    assert response.code == 200

    response = await client_v2.environment_settings_set(tid=environment_default, id="auto_deploy2", value=False)
    assert response.code == 404

    response = await client_v2.environment_settings_set(tid=environment_default, id="auto_deploy", value="error")
    assert response.code == 500

    response = await client_v2.environment_settings_set(tid=environment_default, id="recompile_backoff", value="-42.5")
    assert response.code == 500

    response = await client_v2.environment_setting_delete(tid=environment_default, id="auto_deploy")
    assert response.code == 200

    response = await client_v2.environment_setting_delete(tid=environment_default, id="auto_deploy2")
    assert response.code == 404


async def test_delete_protected_environment(server, client):
    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    async def create_environment() -> str:
        result = await client.create_environment(project_id=project_id, name="dev")
        assert result.code == 200
        return result.result["environment"]["id"]

    async def assert_env_deletion(env_id: str, deletion_succeeds: bool) -> None:
        # Execute delete operation
        result = await client.environment_delete(env_id)
        assert result.code == 200 if deletion_succeeds else 403
        # Assert result
        result = await client.environment_get(env_id)
        assert result.code == 404 if deletion_succeeds else 200

    # Test default setting
    env_id = await create_environment()
    await assert_env_deletion(env_id, deletion_succeeds=True)

    # Test environment is protected
    env_id = await create_environment()
    result = await client.environment_settings_set(env_id, data.PROTECTED_ENVIRONMENT, True)
    assert result.code == 200
    await assert_env_deletion(env_id, deletion_succeeds=False)

    # Test environment is unprotected
    result = await client.environment_settings_set(env_id, data.PROTECTED_ENVIRONMENT, False)
    assert result.code == 200
    await assert_env_deletion(env_id, deletion_succeeds=True)


async def test_clear_protected_environment(server, client):
    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    assert result.code == 200
    env_id = result.result["environment"]["id"]

    async def push_version_to_environment() -> None:
        res = await client.reserve_version(env_id)
        assert res.code == 200
        version = res.result["data"]

        result = await client.put_version(
            tid=env_id,
            version=version,
            resources=[],
            unknowns=[],
            compiler_version=get_compiler_version(),
        )
        assert result.code == 200

    async def assert_clear_env(env_id: str, clear_succeeds: bool) -> None:
        result = await client.list_versions(env_id)
        assert result.code == 200
        assert len(result.result["versions"]) != 0
        # Execute clear operation
        result = await client.environment_clear(env_id)
        assert result.code == 200 if clear_succeeds else 403
        # Assert result
        result = await client.list_versions(env_id)
        assert result.code == 200
        assert (len(result.result["versions"]) == 0) == clear_succeeds

    # Test default settings
    await push_version_to_environment()
    await assert_clear_env(env_id, clear_succeeds=True)

    # Test environment is protected
    await push_version_to_environment()
    result = await client.environment_settings_set(env_id, data.PROTECTED_ENVIRONMENT, True)
    assert result.code == 200
    await assert_clear_env(env_id, clear_succeeds=False)

    # Test environment is unprotected
    result = await client.environment_settings_set(env_id, data.PROTECTED_ENVIRONMENT, False)
    assert result.code == 200
    await assert_clear_env(env_id, clear_succeeds=True)


async def test_environment_add_new_setting_parameter(server, client, environment):
    new_setting: Setting = Setting(
        name="a new setting",
        default=False,
        typ="bool",
        validator=convert_boolean,
        doc="a new setting",
    )

    data.Environment.register_setting(new_setting)

    result = await client.get_setting(tid=environment, id="a new setting")
    assert result.code == 200
    assert result.result["value"] is False

    result = await client.set_setting(tid=environment, id="a new setting", value=True)
    assert result.code == 200

    result = await client.get_setting(tid=environment, id="a new setting")
    assert result.code == 200
    assert result.result["value"] is True

    result = await client.get_setting(tid=environment, id=data.AUTO_DEPLOY)
    assert result.code == 200
    assert result.result["value"] is False

    existing_setting: Setting = Setting(
        name=data.AUTO_DEPLOY,
        default=False,
        typ="bool",
        validator=convert_boolean,
        doc="an existing setting",
    )
    with pytest.raises(KeyError):
        data.Environment.register_setting(existing_setting)

    result = await client.get_setting(tid=environment, id=data.AUTO_DEPLOY)
    assert result.code == 200
    assert result.result["value"] is False


async def test_get_setting_no_longer_exist(server, client, environment):
    """
    Test what happens when a setting exists in the database for which the definition no longer exists
    """
    env_id = UUID(environment)
    env = await data.Environment.get_by_id(env_id)
    project_id = env.project
    setting_db_query = (
        "UPDATE environment SET settings=jsonb_set(settings, $1::text[], "
        "to_jsonb($2::boolean), TRUE) WHERE name=$3 AND project=$4"
    )
    values = [["new_setting"], True, "dev", project_id]
    await Environment._execute_query(setting_db_query, *values)

    result = await client.get_setting(tid=environment, id="a setting")
    assert result.code == 404
    assert result.result["message"] == "Request or referenced resource does not exist"

    result = await client.list_settings(tid=environment)
    assert result.code == 200
    assert "new_setting" not in result.result["settings"].keys()

    new_setting: Setting = Setting(
        name="new_setting",
        default=False,
        typ="bool",
        validator=convert_boolean,
        doc="new_setting",
    )

    data.Environment.register_setting(new_setting)

    result = await client.get_setting(tid=environment, id="new_setting")
    assert result.code == 200
    assert result.result["value"] is True

    result = await client.list_settings(tid=environment)
    assert result.code == 200
    assert "new_setting" in result.result["settings"].keys()
