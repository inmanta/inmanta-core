"""
Copyright 2025 Inmanta

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

import os.path
import uuid

import pytest

import nacl
import utils
from inmanta import config, const, data
from inmanta.data.model import AuthMethod
from inmanta.protocol import endpoints
from inmanta.server.config import AuthorizationProviderName


def read_file(file_name: str) -> str:
    """
    Returns the config of the given file.
    """
    with open(file_name, "r") as fh:
        return fh.read()


@pytest.mark.parametrize("enable_auth", [True])
@pytest.mark.parametrize("auth_method", [AuthMethod.database])
@pytest.mark.parametrize("authorization_provider", [AuthorizationProviderName.policy_engine])
@pytest.mark.parametrize(
    "access_policy",
    [read_file(os.path.join(os.path.dirname(__file__), "..", "src", "inmanta", "protocol", "auth", "default_policy.rego"))],
)
@pytest.mark.parametrize(
    "role,is_admin,expected_response_codes",
    [
        ("read-only", False, [200, 403, 403, 403]),
        ("noc", False, [200, 200, 403, 403]),
        ("environment-admin", False, [200, 200, 200, 403]),
        (None, True, [200, 200, 200, 200]),
    ],
)
async def test_default_policy(server, client, role: str | None, is_admin: bool, expected_response_codes: int) -> None:
    """
    Test the behavior of the default policy.
    """
    # Create a user
    user = data.User(
        username="user",
        password_hash=nacl.pwhash.str("user".encode()).decode(),
        auth_method=AuthMethod.database,
    )
    await user.insert()

    global_admin_client = utils.get_auth_client(
        env_to_role_dct={},
        is_admin=True,
        client_types=[const.ClientType.api],
    )

    # Create project and environment
    result = await global_admin_client.project_create(name="test")
    assert result.code == 200
    project_id = result.result["data"]["id"]

    result = await global_admin_client.environment_create(project_id=project_id, name="test")
    assert result.code == 200
    env_id = result.result["data"]["id"]

    client = utils.get_auth_client(
        env_to_role_dct={env_id: [role]} if role else {},
        is_admin=is_admin,
        client_types=[const.ClientType.api],
    )

    (
        read_only_op_expected_response,
        noc_op_expected_response,
        env_admin_op_expected_response,
        global_admin_op_expected_response,
    ) = expected_response_codes

    # Read-only operation
    result = await client.environment_list()
    assert result.code == read_only_op_expected_response

    # Noc operation
    result = await client.all_agents_action(tid=env_id, action=const.AgentAction.unpause.value)
    assert result.code == noc_op_expected_response

    # Environment admin operation
    result = await client.environment_settings_set(tid=env_id, id=data.AUTO_DEPLOY, value=True)
    assert result.code == env_admin_op_expected_response

    # Global admin operation
    result = await client.project_create(name="new-project", project_id=uuid.uuid4())
    assert result.code == global_admin_op_expected_response


@pytest.mark.parametrize("enable_auth", [True])
@pytest.mark.parametrize("auth_method", [AuthMethod.database])
@pytest.mark.parametrize("authorization_provider", [AuthorizationProviderName.policy_engine])
@pytest.mark.parametrize(
    "access_policy",
    [read_file(os.path.join(os.path.dirname(__file__), "..", "src", "inmanta", "protocol", "auth", "default_policy.rego"))],
)
async def test_default_policy_unauthorized_user(server, client) -> None:
    """
    Verify that an unauthorized user is denied access.
    """
    config.Config.get_instance().remove_option("client_rest_transport", "token")
    unauthorized_client = endpoints.Client("client")

    result = await unauthorized_client.environment_list()
    assert result.code == 401
