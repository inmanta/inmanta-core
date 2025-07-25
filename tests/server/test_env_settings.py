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

import logging
from typing import Mapping
from uuid import UUID

import pytest

from inmanta import data
from inmanta.data import Environment, Setting, convert_boolean, model
from inmanta.util import get_compiler_version
from utils import log_contains


def get_environment_setting_default(setting: str) -> object:
    return data.Environment._settings[setting].default


def check_only_contains_default_setting(settings_dict: Mapping[str, object]) -> None:
    """
    Depending on when the background cleanup processes are run, it is possible that environment settings are set, independently
    of the tests below. This method ensures these settings are properly set with their default values.
    """
    for setting_name, setting_value in settings_dict.items():
        assert setting_value == get_environment_setting_default(setting_name)


def assert_not_protected(settings_dict: Mapping[str, model.EnvironmentSettingDetails]) -> None:
    """
    Assert that the environment settings, in the given settings_dict, are not protected.
    """
    for value in settings_dict.values():
        assert not value.protected
        assert value.protected_by is None


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
    # Removed setting
    assert "autostart_agent_deploy_splay_time" not in result.result

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


async def test_environment_settings_v2(client_v2, server, environment_default):
    """
    Test environment settings
    """
    response = await client_v2.environment_settings_list(tid=environment_default)
    assert response.code == 200
    assert "settings" in response.result["data"]
    assert "definition" in response.result["data"]
    assert "auto_deploy" in response.result["data"]["definition"]
    settings_dict = response.result["data"]["settings"]
    settings_v2_dict = response.result["data"]["settings_v2"]
    assert settings_dict.keys() == settings_v2_dict.keys()
    check_only_contains_default_setting(settings_dict)
    assert_not_protected({key: model.EnvironmentSettingDetails(**value) for key, value in settings_v2_dict.items()})

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


@pytest.mark.parametrize("no_agent", [True])
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
    setting_db_query = """
        UPDATE environment
        SET settings=jsonb_set(
            settings,
            ARRAY['settings', $1],
            jsonb_build_object(
                'value',
                $2::boolean,
                'protected',
                FALSE,
                'protected_by',
                NULL
            ),
            TRUE
        )
        WHERE name=$3 AND project=$4"""
    values = ["new_setting", True, "dev", project_id]
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


async def test_halt_env_before_deletion(environment, server, client, caplog):
    """
    Verify env will be halted before it is deleted.
    """
    with caplog.at_level(logging.INFO):
        result = await client.environment_delete(environment)
        assert result.code == 200

    log_contains(caplog, "inmanta.server.services.environmentservice", logging.INFO, f"Halting Environment {environment}")


async def test_resume_marked_for_delete(environment, server, client, caplog):
    """
    Cannot resume environment that is marked for deletion
    """

    env1 = await data.Environment.get_by_id(environment)
    await env1.mark_for_deletion()

    result = await client.resume_environment(environment)
    assert result.code == 400
    assert result.result["message"] == "Invalid request: Cannot resume an environment that is marked for deletion."


async def test_protect_environment_settings(environment, server, client):
    """
    Test the `protected_environment_settings_set_batch` endpoint.
    """

    async def assert_protected_settings(protected_settings: set[str]) -> None:
        """
        Assert that the given set of settings is protected and the others are not.
        """
        result = await client.environment_settings_list(tid=environment)
        assert result.code == 200
        for setting_name, setting_details in result.result["data"]["settings_v2"].items():
            if setting_name in protected_settings:
                assert setting_details["protected"]
                assert model.ProtectedBy(setting_details["protected_by"]) is model.ProtectedBy.project_yml
            else:
                assert not setting_details["protected"]
                assert setting_details["protected_by"] is None

    # Mark settings are protected
    result = await client.protected_environment_settings_set_batch(
        tid=environment,
        settings={data.AUTO_DEPLOY: False, data.RESOURCE_ACTION_LOGS_RETENTION: 12},
        protected_by=model.ProtectedBy.project_yml,
    )
    assert result.code == 200

    # Verify protection status
    await assert_protected_settings(protected_settings={data.AUTO_DEPLOY, data.RESOURCE_ACTION_LOGS_RETENTION})

    # Verify protected setting cannot be updated
    result = await client.environment_settings_set(tid=environment, id=data.AUTO_DEPLOY, value=True)
    assert result.code == 403
    result = await client.environment_setting_delete(tid=environment, id=data.AUTO_DEPLOY)
    assert result.code == 403
    result = await client.set_setting(tid=environment, id=data.AUTO_DEPLOY, value=True)
    assert result.code == 403
    result = await client.delete_setting(tid=environment, id=data.AUTO_DEPLOY)
    assert result.code == 403
    # Verify that the value of the setting hasn't changed and that the setting is still protected
    result = await client.environment_setting_get(tid=environment, id=data.AUTO_DEPLOY)
    assert result.code == 200
    setting_details = result.result["data"]["settings_v2"][data.AUTO_DEPLOY]
    assert setting_details["value"] is False
    assert setting_details["protected"] is True
    assert model.ProtectedBy(setting_details["protected_by"]) is model.ProtectedBy.project_yml

    # Update set of protected settings
    result = await client.protected_environment_settings_set_batch(
        tid=environment,
        settings={data.RESOURCE_ACTION_LOGS_RETENTION: 12, data.AVAILABLE_VERSIONS_TO_KEEP: 5},
        protected_by=model.ProtectedBy.project_yml,
    )
    assert result.code == 200

    await assert_protected_settings(protected_settings={data.RESOURCE_ACTION_LOGS_RETENTION, data.AVAILABLE_VERSIONS_TO_KEEP})

    # Verify that we can update the AUTO_DEPLOY setting again
    result = await client.environment_settings_set(tid=environment, id=data.AUTO_DEPLOY, value=True)
    assert result.code == 200
    # Verify that the value of the setting hasn't changed and that the setting is still protected
    result = await client.environment_setting_get(tid=environment, id=data.AUTO_DEPLOY)
    assert result.code == 200
    assert result.result["data"]["settings_v2"][data.AUTO_DEPLOY]["value"] is True
    assert result.result["data"]["settings_v2"][data.AUTO_DEPLOY]["protected"] is False
    assert result.result["data"]["settings_v2"][data.AUTO_DEPLOY]["protected_by"] is None
