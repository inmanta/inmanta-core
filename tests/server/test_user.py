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

import base64

import jwt
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


async def test_login_session_expire(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """
    The login session token gets its own lifetime via server.login_session_expire, decoupled from the
    auth_jwt `expire` (which is 0/eternal in this fixture and governs agent/compiler service tokens).
    """
    response = await auth_client.add_user("admin", "adminadmin")
    assert response.code == 200

    # By default login sessions expire after one hour, even though the signing config's expire is 0.
    response = await auth_client.login("admin", "adminadmin")
    assert response.code == 200
    claims = jwt.decode(response.result["data"]["token"], options={"verify_signature": False})
    assert claims["exp"] - claims["iat"] == 3600

    # Setting the option to 0 restores the old behavior: fall back to the signing config's expire (eternal here).
    config.Config.set("server", "login_session_expire", "0")
    response = await auth_client.login("admin", "adminadmin")
    assert response.code == 200
    claims = jwt.decode(response.result["data"]["token"], options={"verify_signature": False})
    assert "exp" not in claims

    # A custom value is honored.
    config.Config.set("server", "login_session_expire", "7200")
    response = await auth_client.login("admin", "adminadmin")
    assert response.code == 200
    claims = jwt.decode(response.result["data"]["token"], options={"verify_signature": False})
    assert claims["exp"] - claims["iat"] == 7200


async def test_login_reports_expires_in(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """login reports the session lifetime in seconds so a client can renew before it expires."""
    assert (await auth_client.add_user("admin", "adminadmin")).code == 200

    response = await auth_client.login("admin", "adminadmin")
    assert response.code == 200
    assert response.result["data"]["expires_in"] == 3600

    # When the option is 0 (eternal), no lifetime is reported.
    config.Config.set("server", "login_session_expire", "0")
    response = await auth_client.login("admin", "adminadmin")
    assert response.code == 200
    assert response.result["data"]["expires_in"] is None


async def test_login_renew(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """A logged-in user renews their session with the session token and gets a fresh, working token."""
    assert (await auth_client.add_user("admin", "adminadmin")).code == 200

    login = await auth_client.login("admin", "adminadmin")
    assert login.code == 200
    session_token = login.result["data"]["token"]

    # A client holding the session token can renew it (no password), getting a new token and lifetime.
    config.Config.set("client_rest_transport", "token", session_token)
    session_client = protocol.Client("client")
    renew = await session_client.login_renew()
    assert renew.code == 200
    assert renew.result["data"]["expires_in"] == 3600
    new_token = renew.result["data"]["token"]
    claims = jwt.decode(new_token, options={"verify_signature": False})
    assert claims["sub"] == "admin"

    # The renewed token authenticates subsequent calls.
    config.Config.set("client_rest_transport", "token", new_token)
    renewed_client = protocol.Client("client")
    assert (await renewed_client.list_users()).code == 200


async def test_login_renew_reflects_current_admin_status(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """A renewed token carries the user's current admin status, not the status captured at login time."""
    assert (await auth_client.add_user("admin", "adminadmin")).code == 200

    login = await auth_client.login("admin", "adminadmin")
    assert login.code == 200
    session_token = login.result["data"]["token"]
    assert jwt.decode(session_token, options={"verify_signature": False})[const.INMANTA_IS_ADMIN_URN] is False

    # Promote the user, then renew: the fresh token must reflect the new admin status.
    assert (await auth_client.set_is_admin("admin", True)).code == 200
    config.Config.set("client_rest_transport", "token", session_token)
    session_client = protocol.Client("client")
    renew = await session_client.login_renew()
    assert renew.code == 200
    assert jwt.decode(renew.result["data"]["token"], options={"verify_signature": False})[const.INMANTA_IS_ADMIN_URN] is True


async def test_login_renew_rejects_non_session_token(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """Renewal only applies to login sessions: a token without a sub claim (an API token) is rejected."""
    # The auth_client fixture's token is a bare API token, minted without a sub claim.
    response = await auth_client.login_renew()
    assert response.code == 400
    assert "login sessions" in response.result["message"]


async def test_login_renew_rejects_external_issuer_token(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """
    A token from another issuer must not be renewable, even when its username matches a local account.
    In the break-glass topology (a local sign=true section alongside an external OIDC issuer) this would
    otherwise let a user authenticated against the external issuer obtain a locally-signed token carrying
    the roles and admin status of a same-named local account.
    """
    assert (await auth_client.add_user("admin", "adminadmin")).code == 200

    # Register a second, verify-only issuer, as an external OIDC provider would be. It shares the HS256 key
    # of the fixture's signing config purely to keep the test deterministic; only the issuer differs.
    key_b64 = "eciwliGyqECVmXtIkNpfVrtBLutZiITZKSKYhogeHMM"
    key_bytes = base64.urlsafe_b64decode((key_b64 + "==").encode("ascii"))
    external_issuer = "https://external.example/"
    config.Config.set("auth_jwt_external", "algorithm", "HS256")
    config.Config.set("auth_jwt_external", "sign", "false")
    config.Config.set("auth_jwt_external", "client_types", "api")
    config.Config.set("auth_jwt_external", "key", key_b64)
    config.Config.set("auth_jwt_external", "issuer", external_issuer)
    config.Config.set("auth_jwt_external", "audience", external_issuer)

    # A token minted by that external issuer whose sub happens to match the local "admin" account.
    external_token = jwt.encode(
        {"iss": external_issuer, "aud": [external_issuer], "sub": "admin"},
        key_bytes,
        algorithm="HS256",
    )
    config.Config.set("client_rest_transport", "token", external_token)
    external_client = protocol.Client("client")

    response = await external_client.login_renew()
    assert response.code == 400
    assert "issued by this server" in response.result["message"]


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
