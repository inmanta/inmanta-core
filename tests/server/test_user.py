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
import datetime
import logging
import uuid

import jwt
import pytest

import nacl.pwhash
from inmanta import config, const, data
from inmanta.data.model import AuthMethod
from inmanta.data.sqlalchemy import Token, TokenRepository
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


async def test_login_session_expire(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """
    The login session token gets its own lifetime via server.login_session_expire, decoupled from the
    auth_jwt `expire` (which is 0/eternal in this fixture and governs agent/compiler service tokens).
    """
    response = await auth_client.add_user("admin", "Str0ng-Pass!")
    assert response.code == 200

    # By default login sessions expire after one hour, even though the signing config's expire is 0.
    response = await auth_client.login("admin", "Str0ng-Pass!")
    assert response.code == 200
    claims = jwt.decode(response.result["data"]["token"], options={"verify_signature": False})
    assert claims["exp"] - claims["iat"] == 3600

    # Setting the option to 0 restores the old behavior: fall back to the signing config's expire (eternal here).
    config.Config.set("server", "login_session_expire", "0")
    response = await auth_client.login("admin", "Str0ng-Pass!")
    assert response.code == 200
    claims = jwt.decode(response.result["data"]["token"], options={"verify_signature": False})
    assert "exp" not in claims

    # A custom value is honored.
    config.Config.set("server", "login_session_expire", "7200")
    response = await auth_client.login("admin", "Str0ng-Pass!")
    assert response.code == 200
    claims = jwt.decode(response.result["data"]["token"], options={"verify_signature": False})
    assert claims["exp"] - claims["iat"] == 7200


async def test_login_reports_expires_in(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """login reports the session lifetime in seconds so a client can renew before it expires."""
    assert (await auth_client.add_user("admin", "Str0ng-Pass!")).code == 200

    response = await auth_client.login("admin", "Str0ng-Pass!")
    assert response.code == 200
    assert response.result["data"]["expires_in"] == 3600

    # When the option is 0 (eternal), no lifetime is reported.
    config.Config.set("server", "login_session_expire", "0")
    response = await auth_client.login("admin", "Str0ng-Pass!")
    assert response.code == 200
    assert response.result["data"]["expires_in"] is None


async def test_login_renew(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """A logged-in user renews their session with the session token and gets a fresh, working token."""
    assert (await auth_client.add_user("admin", "Str0ng-Pass!")).code == 200

    login = await auth_client.login("admin", "Str0ng-Pass!")
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
    assert (await auth_client.add_user("admin", "Str0ng-Pass!")).code == 200

    login = await auth_client.login("admin", "Str0ng-Pass!")
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
    assert (await auth_client.add_user("admin", "Str0ng-Pass!")).code == 200

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

    # By default the token is non-idempotent: it carries a jti and is tracked in the registry so it
    # can be listed and revoked.
    assert "jti" in claims
    response = await auth_client.environment_token_list(tid=env_id)
    assert response.code == 200
    assert [t["jti"] for t in response.result["data"]] == [claims["jti"]]

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
    assert "jti" in chained_claims


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


async def test_password_nfkc(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """
    Passwords are matched in Unicode NFKC form, so the same password verifies regardless of how it was
    typed, and hashes stored (by older versions) before normalization still work and are migrated.
    """
    decomposed = "Pa\u0308ssw0rd-123"  # base 'a' + combining diaeresis (U+0308); NFKC + policy compliant
    composed = "P\u00e4ssw0rd-123"  # precomposed 'a'-umlaut (U+00E4); the NFKC form of decomposed
    assert decomposed != composed

    # A user created with the decomposed form can log in with either form (both normalize to the same).
    response = await auth_client.add_user("nina", decomposed)
    assert response.code == 200
    assert (await auth_client.login("nina", composed)).code == 200
    assert (await auth_client.login("nina", decomposed)).code == 200

    # Migration: a hash stored from the raw, non-normalized bytes (as an older version would have).
    user = data.User(
        username="olof",
        password_hash=nacl.pwhash.str(decomposed.encode()).decode(),
        auth_method=AuthMethod.database,
    )
    await user.insert()
    # The composed form does not match the raw-decomposed hash yet.
    assert (await auth_client.login("olof", composed)).code == 401
    # The decomposed form matches via the fallback and upgrades the stored hash to the normalized form.
    assert (await auth_client.login("olof", decomposed)).code == 200
    # After the upgrade the composed form works too.
    assert (await auth_client.login("olof", composed)).code == 200


async def test_token_registry(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """
    Non-idempotent tokens are registered in the token registry and can be listed and revoked; idempotent
    tokens stay stateless (no jti, not tracked). A revoked token is rejected on subsequent requests.
    """
    user = data.User(
        username="admin",
        password_hash=nacl.pwhash.str("adminadmin".encode()).decode(),
        auth_method=AuthMethod.database,
    )
    await user.insert()

    response = await auth_client.login("admin", "adminadmin")
    assert response.code == 200
    config.Config.set("client_rest_transport", "token", response.result["data"]["token"])
    admin_client = protocol.Client("client")

    response = await admin_client.project_create(name="test")
    assert response.code == 200
    project_id = response.result["data"]["id"]
    response = await admin_client.environment_create(project_id=project_id, name="test")
    assert response.code == 200
    env_id = response.result["data"]["id"]

    # An idempotent token is stateless: no jti and not tracked in the registry.
    response = await admin_client.environment_create_token(tid=env_id, client_types=["api"], idempotent=True)
    assert response.code == 200
    assert "jti" not in jwt.decode(response.result["data"], options={"verify_signature": False})
    response = await admin_client.environment_token_list(tid=env_id)
    assert response.code == 200
    assert response.result["data"] == []

    # A non-idempotent token gets a jti and is registered.
    response = await admin_client.environment_create_token(tid=env_id, client_types=["api"], idempotent=False)
    assert response.code == 200
    revocable_token = response.result["data"]
    jti = jwt.decode(revocable_token, options={"verify_signature": False})["jti"]

    response = await admin_client.environment_token_list(tid=env_id)
    assert response.code == 200
    assert len(response.result["data"]) == 1
    assert response.result["data"][0]["jti"] == jti
    assert response.result["data"][0]["created_by"] == "admin"
    assert response.result["data"][0]["revoked_at"] is None

    # The registered token works for authenticated calls.
    config.Config.set("client_rest_transport", "token", revocable_token)
    token_client = protocol.Client("client")
    response = await token_client.environment_token_list(tid=env_id)
    assert response.code == 200

    # After revocation the same token is rejected.
    response = await admin_client.environment_token_revoke(tid=env_id, jti=jti)
    assert response.code == 200
    response = await token_client.environment_token_list(tid=env_id)
    assert response.code == 403

    # The revocation moment is recorded and exposed in the listing.
    response = await admin_client.environment_token_list(tid=env_id)
    assert response.code == 200
    [revoked_entry] = [t for t in response.result["data"] if t["jti"] == jti]
    assert revoked_entry["revoked_at"] is not None

    # Revoking again succeeds (idempotent) and keeps the original revocation time.
    response = await admin_client.environment_token_revoke(tid=env_id, jti=jti)
    assert response.code == 200
    response = await admin_client.environment_token_list(tid=env_id)
    [entry_after_second_revoke] = [t for t in response.result["data"] if t["jti"] == jti]
    assert entry_after_second_revoke["revoked_at"] == revoked_entry["revoked_at"]

    # A legacy token without a jti keeps working (stateless validation, non-breaking migration).
    legacy_token = auth.encode_token([str(const.ClientType.api.value)], environment=str(env_id))
    assert "jti" not in jwt.decode(legacy_token, options={"verify_signature": False})
    config.Config.set("client_rest_transport", "token", legacy_token)
    legacy_client = protocol.Client("client")
    response = await legacy_client.environment_token_list(tid=env_id)
    assert response.code == 200

    # Revoking a jti that does not exist returns 404.
    response = await admin_client.environment_token_revoke(tid=env_id, jti=uuid.uuid4())
    assert response.code == 404

    # A token cannot be revoked through a different environment (no cross-environment revoke).
    response = await admin_client.environment_create_token(tid=env_id, client_types=["api"], idempotent=False)
    assert response.code == 200
    other_jti = jwt.decode(response.result["data"], options={"verify_signature": False})["jti"]
    response = await admin_client.environment_create(project_id=project_id, name="other")
    assert response.code == 200
    other_env = response.result["data"]["id"]
    response = await admin_client.environment_token_revoke(tid=other_env, jti=other_jti)
    assert response.code == 404
    # It is untouched (still present and unrevoked) in its own environment.
    response = await admin_client.environment_token_list(tid=env_id)
    assert any(t["jti"] == other_jti and t["revoked_at"] is None for t in response.result["data"])

    # A token whose jti claim is not a valid UUID is rejected.
    bad_token = auth.encode_token(
        [str(const.ClientType.api.value)], environment=str(env_id), custom_claims={"jti": "not-a-uuid"}
    )
    config.Config.set("client_rest_transport", "token", bad_token)
    bad_client = protocol.Client("client")
    response = await bad_client.environment_token_list(tid=env_id)
    assert response.code == 403


async def test_token_expire_param(server: protocol.Server, auth_client: endpoints.Client) -> None:
    """
    An explicit expire on environment_create_token drives both the JWT exp claim and the registry
    expires_at; a non-positive expire and the idempotent+expire combination are rejected.
    """
    user = data.User(
        username="admin",
        password_hash=nacl.pwhash.str("Str0ng-Pass!".encode()).decode(),
        auth_method=AuthMethod.database,
    )
    await user.insert()
    response = await auth_client.login("admin", "Str0ng-Pass!")
    assert response.code == 200
    config.Config.set("client_rest_transport", "token", response.result["data"]["token"])
    admin_client = protocol.Client("client")

    response = await admin_client.project_create(name="test")
    assert response.code == 200
    response = await admin_client.environment_create(project_id=response.result["data"]["id"], name="test")
    assert response.code == 200
    env_id = response.result["data"]["id"]

    # The expire argument drives the exp claim and the registry expires_at.
    response = await admin_client.environment_create_token(tid=env_id, client_types=["api"], expire=3600)
    assert response.code == 200
    expiring_token = response.result["data"]
    claims = jwt.decode(expiring_token, options={"verify_signature": False})
    assert claims["exp"] == claims["iat"] + 3600
    response = await admin_client.environment_token_list(tid=env_id)
    assert response.code == 200
    [entry] = response.result["data"]
    issued_at = datetime.datetime.fromisoformat(entry["issued_at"])
    expires_at = datetime.datetime.fromisoformat(entry["expires_at"])
    assert expires_at - issued_at == datetime.timedelta(seconds=3600)

    # The expiring token authenticates as long as it has not expired.
    config.Config.set("client_rest_transport", "token", expiring_token)
    token_client = protocol.Client("client")
    response = await token_client.environment_token_list(tid=env_id)
    assert response.code == 200

    # A non-positive expire is rejected.
    response = await admin_client.environment_create_token(tid=env_id, client_types=["api"], expire=0)
    assert response.code == 400
    response = await admin_client.environment_create_token(tid=env_id, client_types=["api"], expire=-5)
    assert response.code == 400

    # An idempotent token carries no time-based claims, so it cannot have an expiry.
    response = await admin_client.environment_create_token(tid=env_id, client_types=["api"], idempotent=True, expire=3600)
    assert response.code == 400


async def test_token_registry_cleanup(server: protocol.Server) -> None:
    """
    delete_stale removes entries that expired or were revoked before the retention cutoff, while keeping
    valid, non-expiring, recently-expired and recently-revoked ones (the latter two kept for auditing).
    """
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    old_expired_jti, fresh_expired_jti = uuid.uuid4(), uuid.uuid4()
    valid_jti, eternal_jti = uuid.uuid4(), uuid.uuid4()
    old_revoked_jti, fresh_revoked_jti = uuid.uuid4(), uuid.uuid4()
    async with data.get_session() as session:
        repo = TokenRepository(session)
        await repo.add(Token(jti=old_expired_jti, issued_at=now, expires_at=now - datetime.timedelta(days=2)))
        await repo.add(Token(jti=fresh_expired_jti, issued_at=now, expires_at=now - datetime.timedelta(hours=1)))
        await repo.add(Token(jti=valid_jti, issued_at=now, expires_at=now + datetime.timedelta(hours=1)))
        await repo.add(Token(jti=eternal_jti, issued_at=now, expires_at=None))
        await repo.add(Token(jti=old_revoked_jti, issued_at=now, revoked_at=now - datetime.timedelta(days=2)))
        await repo.add(Token(jti=fresh_revoked_jti, issued_at=now, revoked_at=now - datetime.timedelta(hours=1)))
        await session.commit()

    async with data.get_session() as session:
        await TokenRepository(session).delete_stale(cutoff=now - datetime.timedelta(days=1))
        await session.commit()

    async with data.get_session() as session:
        repo = TokenRepository(session)
        assert await repo.get_by_jti(old_expired_jti) is None
        assert await repo.get_by_jti(fresh_expired_jti) is not None
        assert await repo.get_by_jti(valid_jti) is not None
        assert await repo.get_by_jti(eternal_jti) is not None
        assert await repo.get_by_jti(old_revoked_jti) is None
        assert await repo.get_by_jti(fresh_revoked_jti) is not None
