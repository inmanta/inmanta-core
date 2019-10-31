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


@pytest.mark.asyncio
async def test_environment_settings(client, server, environment):
    """
        Test environment settings
    """
    result = await client.list_settings(tid=environment)
    assert result.code == 200
    assert "settings" in result.result
    assert "metadata" in result.result
    assert "auto_deploy" in result.result["metadata"]
    assert len(result.result["settings"]) == 0

    # set invalid value
    result = await client.set_setting(tid=environment, id="auto_deploy", value="test")
    assert result.code == 500

    # set non existing setting
    result = await client.set_setting(tid=environment, id="auto_deploy_non", value=False)
    assert result.code == 404

    result = await client.set_setting(tid=environment, id="auto_deploy", value=False)
    assert result.code == 200

    result = await client.list_settings(tid=environment)
    assert result.code == 200
    assert len(result.result["settings"]) == 1

    result = await client.get_setting(tid=environment, id="auto_deploy")
    assert result.code == 200
    assert not result.result["value"]

    result = await client.get_setting(tid=environment, id="test2")
    assert result.code == 404

    result = await client.set_setting(tid=environment, id="auto_deploy", value=True)
    assert result.code == 200

    result = await client.get_setting(tid=environment, id="auto_deploy")
    assert result.code == 200
    assert result.result["value"]

    result = await client.delete_setting(tid=environment, id="test2")
    assert result.code == 404

    result = await client.delete_setting(tid=environment, id="auto_deploy")
    assert result.code == 200

    result = await client.list_settings(tid=environment)
    assert result.code == 200
    assert "settings" in result.result
    assert len(result.result["settings"]) == 1

    result = await client.set_setting(tid=environment, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, value=20)
    assert result.code == 200

    result = await client.set_setting(tid=environment, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, value="30")
    assert result.code == 200

    result = await client.get_setting(tid=environment, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME)
    assert result.code == 200
    assert result.result["value"] == 30

    result = await client.delete_setting(tid=environment, id=data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME)
    assert result.code == 200

    result = await client.set_setting(
        tid=environment, id=data.AUTOSTART_AGENT_MAP, value={"agent1": "", "agent2": "localhost", "agent3": "user@agent3"}
    )
    assert result.code == 200

    result = await client.set_setting(tid=environment, id=data.AUTOSTART_AGENT_MAP, value="")
    assert result.code == 500


@pytest.mark.asyncio
async def test_environment_settings_v2(client_v2, server, environment):
    """
        Test environment settings
    """
    response = await client_v2.environment_settings_list(tid=environment)
    assert response.code == 200
    assert "settings" in response.result["data"]
    assert "definition" in response.result["data"]
    assert "auto_deploy" in response.result["data"]["definition"]
    assert len(response.result["data"]["settings"]) == 0

    response = await client_v2.environment_settings_set(tid=environment, id="auto_deploy", value=False)
    assert response.code == 200

    response = await client_v2.environment_settings_set(tid=environment, id="auto_deploy2", value=False)
    assert response.code == 404

    response = await client_v2.environment_settings_set(tid=environment, id="auto_deploy", value="error")
    assert response.code == 500

    response = await client_v2.environment_setting_delete(tid=environment, id="auto_deploy")
    assert response.code == 200

    response = await client_v2.environment_setting_delete(tid=environment, id="auto_deploy2")
    assert response.code == 404
