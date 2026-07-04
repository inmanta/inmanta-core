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

import logging

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
    assert response.result["message"] == "Invalid request: the password should be at least 12 characters long"

    # Try adding a user with no username
    response = await auth_client.add_user("", "test12345")
    assert response.code == 400
    assert response.result["message"] == "Invalid request: the username cannot be an empty string"

    response = await auth_client.add_user("admin", "Str0ng-Pass!")
    assert response.code == 200

    response = await auth_client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    # Try adding a user with the same username
    response = await auth_client.add_user("admin", "Str0ng-Pass!")
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
    response = await auth_client.add_user("admin", "Str0ng-Pass!")
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

    response = await client.login("admin", "Str0ng-Pass!")
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


async def test_login_audit_logging_and_redaction(
    server: protocol.Server, client: endpoints.Client, auth_client: endpoints.Client, caplog
) -> None:
    """Login attempts are audit-logged and passwords are never written to the logs (SecretStr redaction)."""
    password = "sup3r-s3cret-unique-pw"
    wrong_password = "wrong-unique-pw"
    response = await auth_client.add_user("admin", password)
    assert response.code == 200

    with caplog.at_level(logging.DEBUG):
        response = await client.login("admin", wrong_password)
        assert response.code == 401
        response = await client.login("admin", password)
        assert response.code == 200

    # Every login attempt is audit-logged with the username and the connection peer IP.
    failed = [
        r.getMessage()
        for r in caplog.records
        if r.levelno == logging.WARNING and "Failed login for user 'admin'" in r.getMessage()
    ]
    succeeded = [
        r.getMessage()
        for r in caplog.records
        if r.levelno == logging.INFO and "Successful login for user 'admin'" in r.getMessage()
    ]
    assert failed
    assert succeeded
    # The source IP is captured from the connection (not "unknown"), which is the direct client
    # for the in-process test rather than an X-Forwarded-For header.
    assert all("unknown" not in line for line in failed + succeeded)

    # The dispatcher logs the call arguments at debug level; the password must be redacted there.
    login_call_logs = [record.getMessage() for record in caplog.records if "Calling method login" in record.getMessage()]
    assert login_call_logs
    assert all(password not in message and wrong_password not in message for message in login_call_logs)


async def test_set_password(server: protocol.Server, auth_client: endpoints.Client) -> None:
    old_pw = "Old-Passw0rd!"
    new_pw = "New-Passw0rd!"
    response = await auth_client.add_user("admin", old_pw)
    assert response.code == 200

    response = await auth_client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    response = await auth_client.set_password("admin", "toshort")
    assert response.code == 400
    assert response.result["message"] == "Invalid request: the password should be at least 12 characters long"

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


async def test_environment_create_token(server: protocol.Server, auth_client: endpoints.Client, monkeypatch, caplog) -> None:
    """
    Verify that the environment_create_token endpoint works correctly when the server.auth=true
    option is set via an environment variable.
    Reproduction of bug: https://github.com/inmanta/inmanta-core/issues/8962

    Also verify that the minted token is attributed to its creator (a created_by claim) and that
    the access log attributes calls made with it to that creator instead of the anonymous user=<>.
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

    # The token is attributed to the user that created it via a dedicated claim. It is deliberately
    # not stored in sub, because the policy engine authorizes on sub.
    api_token = response.result["data"]
    claims, _ = auth.decode_token(api_token)
    assert claims[const.INMANTA_CREATED_BY_URN] == "admin"
    assert "sub" not in claims

    # A call made with that token is attributed to its creator in the access log, instead of user=<>.
    config.Config.set("client_rest_transport", "token", api_token)
    token_client = protocol.Client("client")
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="inmanta.protocol.rest"):
        response = await token_client.environment_create_token(tid=env_id, client_types=["api"])
        assert response.code == 200
    access_logs = [r.getMessage() for r in caplog.records if "Calling method environment_create_token" in r.getMessage()]
    assert access_logs
    assert all(
        "token=api" in message and "created_by=admin" in message and f"env={env_id}" in message for message in access_logs
    )
    assert all("user=<>" not in message for message in access_logs)
    # Attribution chains: a token minted using an attributed token keeps the original creator, even
    # though the minting token has no sub.
    chained_claims, _ = auth.decode_token(response.result["data"])
    assert chained_claims[const.INMANTA_CREATED_BY_URN] == "admin"
    assert "sub" not in chained_claims


async def test_password_max_length(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """Passwords longer than MAX_PASSWORD_LENGTH are rejected, on both add_user and set_password."""
    too_long = "a" * (const.MAX_PASSWORD_LENGTH + 1)
    at_max = "Aa1" + "a" * (const.MAX_PASSWORD_LENGTH - 3)

    response = await auth_client.add_user("bob", too_long)
    assert response.code == 400
    assert "at most" in response.result["message"]

    response = await auth_client.add_user("bob", at_max)
    assert response.code == 200

    response = await auth_client.set_password("bob", too_long)
    assert response.code == 400
    assert "at most" in response.result["message"]


async def test_login_malformed_hash_is_401(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """A stored password hash that cannot be parsed yields 401, not a 500 server error."""
    # A garbage-prefixed hash raises InvalidkeyError; a well-formed but oversized hash raises a plain
    # ValueError. Use the latter so the dedicated (ValueError, CryptoError) branch is actually exercised.
    for bad_hash in ["not-a-valid-argon2-hash", "$argon2id$" + "x" * 200]:
        user = data.User(username=f"corrupt-{len(bad_hash)}", password_hash=bad_hash, auth_method=AuthMethod.database)
        await user.insert()
        response = await auth_client.login(user.username, "some_password_123")
        assert response.code == 401


async def test_set_password_self_service_requires_current(
    server: protocol.Server, auth_client: endpoints.Client, caplog
) -> None:
    """Changing your own password requires the current password; an admin changing another user's does not."""
    old = "old_password_123"
    new = "new_password_123"

    response = await auth_client.add_user("carol", old)
    assert response.code == 200

    # Log in as carol to obtain a session token whose sub is carol (i.e. a self-service caller).
    response = await auth_client.login("carol", old)
    assert response.code == 200
    config.Config.set("client_rest_transport", "token", response.result["data"]["token"])
    carol_client = protocol.Client("client")

    # Self-service without the current password is refused.
    response = await carol_client.set_password("carol", new)
    assert response.code == 400

    # Self-service with a wrong current password is refused and audited.
    with caplog.at_level(logging.WARNING):
        response = await carol_client.set_password("carol", new, current_password="not_the_password")
        assert response.code == 401
    assert any("Failed password change for user 'carol'" in r.getMessage() for r in caplog.records)

    # Self-service with the correct current password succeeds and is audited.
    caplog.clear()
    with caplog.at_level(logging.INFO):
        response = await carol_client.set_password("carol", new, current_password=old)
        assert response.code == 200
    assert any("Password for user 'carol' changed by 'carol'" in r.getMessage() for r in caplog.records)
    response = await auth_client.login("carol", new)
    assert response.code == 200

    # An administrator (a caller with a different identity) can reset it without the current password.
    response = await auth_client.set_password("carol", "admin_reset_123")
    assert response.code == 200


def test_verify_dummy_password_smoke() -> None:
    """The dummy-hash verification used for username-enumeration resistance runs without raising."""
    from pydantic import SecretStr

    from inmanta.server.services.userservice import verify_dummy_password

    verify_dummy_password(SecretStr("any password"))
