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
import pytest

from inmanta import data
from inmanta.util import get_compiler_version


@pytest.mark.asyncio
async def test_environment_settings(client, server, environment_default):
    """
    Test environment settings
    """
    result = await client.list_settings(tid=environment_default)
    assert result.code == 200
    assert "settings" in result.result
    assert "metadata" in result.result
    assert "auto_deploy" in result.result["metadata"]
    assert len(result.result["settings"]) == 0

    # set invalid value
    result = await client.set_setting(tid=environment_default, id="auto_deploy", value="test")
    assert result.code == 500

    # set non existing setting
    result = await client.set_setting(tid=environment_default, id="auto_deploy_non", value=False)
    assert result.code == 404

    result = await client.set_setting(tid=environment_default, id="auto_deploy", value=False)
    assert result.code == 200

    result = await client.list_settings(tid=environment_default)
    assert result.code == 200
    assert len(result.result["settings"]) == 1

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
    assert len(result.result["settings"]) == 1

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
    assert result.code == 500
    assert "The internal agent must be present in the autostart_agent_map" in result.result["message"]
    # Assert agent_map didn't change
    result = await client.get_setting(tid=environment_default, id=data.AUTOSTART_AGENT_MAP)
    assert result.code == 200
    assert result.result["value"] == agent_map

    result = await client.set_setting(tid=environment_default, id=data.AUTOSTART_AGENT_MAP, value="")
    assert result.code == 500
    assert "Agent map should be a dict" in result.result["message"]
    # Assert agent_map didn't change
    result = await client.get_setting(tid=environment_default, id=data.AUTOSTART_AGENT_MAP)
    assert result.code == 200
    assert result.result["value"] == agent_map


@pytest.mark.asyncio
async def test_environment_settings_v2(client_v2, server, environment_default):
    """
    Test environment settings
    """
    response = await client_v2.environment_settings_list(tid=environment_default)
    assert response.code == 200
    assert "settings" in response.result["data"]
    assert "definition" in response.result["data"]
    assert "auto_deploy" in response.result["data"]["definition"]
    assert len(response.result["data"]["settings"]) == 0

    response = await client_v2.environment_settings_set(tid=environment_default, id="auto_deploy", value=False)
    assert response.code == 200

    response = await client_v2.environment_settings_set(tid=environment_default, id="auto_deploy2", value=False)
    assert response.code == 404

    response = await client_v2.environment_settings_set(tid=environment_default, id="auto_deploy", value="error")
    assert response.code == 500

    response = await client_v2.environment_setting_delete(tid=environment_default, id="auto_deploy")
    assert response.code == 200

    response = await client_v2.environment_setting_delete(tid=environment_default, id="auto_deploy2")
    assert response.code == 404


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_decommission_protected_environment(server, client):
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

    async def assert_decomission_env(env_id: str, decommission_succeeds: bool) -> None:
        result = await client.list_versions(env_id)
        assert result.code == 200
        original_number_of_versions = len(result.result["versions"])
        assert original_number_of_versions != 0
        # Execute clear operation
        result = await client.environment_decommission(env_id)
        assert result.code == 200 if decommission_succeeds else 403
        # Assert result
        result = await client.list_versions(env_id)
        assert result.code == 200
        # Another version is added when decommissioning succeeds
        assert (len(result.result["versions"]) > original_number_of_versions) == decommission_succeeds

    # Test default settings
    await push_version_to_environment()
    await assert_decomission_env(env_id, decommission_succeeds=True)

    # Test environment is protected
    await push_version_to_environment()
    result = await client.environment_settings_set(env_id, data.PROTECTED_ENVIRONMENT, True)
    assert result.code == 200
    await assert_decomission_env(env_id, decommission_succeeds=False)

    # Test environment is unprotected
    result = await client.environment_settings_set(env_id, data.PROTECTED_ENVIRONMENT, False)
    assert result.code == 200
    await assert_decomission_env(env_id, decommission_succeeds=True)


@pytest.mark.asyncio
async def test_default_value_purge_on_delete_setting(server, client):
    """
    Ensure that the purge_on_delete setting of an environment is set to false by default.
    """
    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = await client.create_environment(project_id=project_id, name="dev")
    assert result.code == 200
    env_id = result.result["environment"]["id"]

    result = await client.get_setting(tid=env_id, id=data.PURGE_ON_DELETE)
    assert result.code == 200
    assert result.result["value"] is False
