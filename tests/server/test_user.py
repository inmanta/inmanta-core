"""
Copyright 2023 Inmanta

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

import nacl.pwhash
from inmanta import config, const, data
from inmanta.data.model import AuthMethod
from inmanta.protocol import endpoints
from inmanta.protocol.auth import auth
from inmanta.server import SLICE_USER, protocol


@pytest.fixture
def server_pre_start(server_config, tmpdir):
    """Ensure that the server started by the server fixtures have authentication enabled with auth_method database"""
    config.Config.set("server", "auth", "true")
    config.Config.set("server", "auth_method", "database")
    config.Config.set("auth_jwt_default", "algorithm", "HS256")
    config.Config.set("auth_jwt_default", "sign", "true")
    config.Config.set("auth_jwt_default", "client_types", "agent,compiler,api")
    config.Config.set("auth_jwt_default", "key", "eciwliGyqECVmXtIkNpfVrtBLutZiITZKSKYhogeHMM")
    config.Config.set("auth_jwt_default", "expire", "0")
    config.Config.set("auth_jwt_default", "issuer", "https://localhost:8888/")
    config.Config.set("auth_jwt_default", "audience", "https://localhost:8888/")


@pytest.fixture
def auth_client(server_pre_start):
    token = auth.encode_token([str(const.ClientType.api.value)], expire=None)
    config.Config.set("client_rest_transport", "token", token)
    auth_client = protocol.Client("client")
    return auth_client


async def test_create_and_delete_user(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """test operations on users and login without testing the actual auth"""
    assert server.get_slice(SLICE_USER)
    response = await auth_client.list_users()
    assert response.code == 200
    assert not response.result["data"]

    # Try adding a user with a password that is too short
    response = await auth_client.add_user("admin", "test")
    assert response.code == 400
    assert response.result["message"] == "Invalid request: the password should be at least 8 characters long"

    # Try adding a user with no username
    response = await auth_client.add_user("", "test12345")
    assert response.code == 400
    assert response.result["message"] == "Invalid request: the username cannot be an empty string"

    response = await auth_client.add_user("admin", "test1234")
    assert response.code == 200

    response = await auth_client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    # Try adding a user with the same username
    response = await auth_client.add_user("admin", "test12345")
    assert response.code == 409
    assert (
        response.result["message"] == "Request conflicts with the current state of the resource: A user with name admin "
        "already exists."
    )

    response = await auth_client.delete_user("admin")
    assert response.code == 200

    response = await auth_client.list_users()
    assert response.code == 200
    assert not response.result["data"]


async def test_login(server: protocol.Server, client: endpoints.Client, auth_client: endpoints.Client) -> None:
    """Test the built-in user authentication"""
    response = await auth_client.add_user("admin", "test1234")
    assert response.code == 200

    response = await auth_client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    response = await client.list_users()
    assert response.code == 401

    response = await client.login("user_does_not_exist", "test1234")
    assert response.code == 401

    response = await client.login("admin", "wrong")
    assert response.code == 401

    response = await client.login("admin", "test1234")
    assert response.code == 200
    assert "token" in response.result["data"]
    assert "user" in response.result["data"]
    assert response.result["data"]["user"]["username"] == "admin"

    data, _ = auth.decode_token(response.result["data"]["token"])
    assert "sub" in data
    assert data["sub"] == "admin"

    token = response.result["data"]["token"]
    config.Config.set("client_rest_transport", "token", token)

    new_auth_client = protocol.Client("client")
    response = await new_auth_client.list_users()
    assert response.code == 200
    assert response.result["data"][0]["username"] == "admin"


async def test_set_password(server: protocol.Server, auth_client: endpoints.Client) -> None:
    old_pw = "old_password"
    new_pw = "new_password"
    response = await auth_client.add_user("admin", old_pw)
    assert response.code == 200

    response = await auth_client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    response = await auth_client.set_password("admin", "toshort")
    assert response.code == 400
    assert response.result["message"] == "Invalid request: the password should be at least 8 characters long"

    response = await auth_client.set_password("admin", new_pw)
    assert response.code == 200

    response = await auth_client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    response = await auth_client.login("admin", old_pw)
    assert response.code == 401

    response = await auth_client.login("admin", new_pw)
    assert response.code == 200


async def test_environment_create_token(server: protocol.Server, auth_client: endpoints.Client, monkeypatch) -> None:
    """
    Verify that the environment_create_token endpoint works correctly when the server.auth=true
    option is set via an environment variable.
    Reproduction of bug: https://github.com/inmanta/inmanta-core/issues/8962
    """
    config.Config.set("server", "auth", "false")
    monkeypatch.setenv("INMANTA_SERVER_AUTH", "true")
    user = data.User(
        username="admin",
        password_hash=nacl.pwhash.str("adminadmin".encode()).decode(),
        auth_method=AuthMethod.database,
    )
    await user.insert()

    response = await auth_client.login("admin", "adminadmin")
    assert response.code == 200
    token = response.result["data"]["token"]
    config.Config.set("client_rest_transport", "token", token)
    auth_client = protocol.Client("client")

    response = await auth_client.project_create(name="test")
    assert response.code == 200
    project_id = response.result["data"]["id"]

    response = await auth_client.environment_create(project_id=project_id, name="test")
    assert response.code == 200
    env_id = response.result["data"]["id"]

    response = await auth_client.environment_create_token(tid=env_id, client_types=["api"])
    assert response.code == 200
    assert response.result["data"]
