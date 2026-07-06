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
import unicodedata
import uuid
from collections.abc import Mapping
from typing import Optional

import asyncpg
from pydantic import SecretStr

import nacl.exceptions
import nacl.pwhash
from inmanta import const, data, protocol, util
from inmanta.data import AuthMethod, model
from inmanta.protocol import common, exceptions
from inmanta.protocol.auth import auth
from inmanta.server import SLICE_DATABASE, SLICE_TRANSPORT, SLICE_USER
from inmanta.server import config as server_config
from inmanta.server import protocol as server_protocol

LOGGER = logging.getLogger(__name__)


def verify_authentication_enabled() -> None:
    """raises an BadRequest exception if server authentication is not enabled"""
    if not server_config.server_enable_auth.get():
        raise exceptions.BadRequest(
            "Server authentication should be enabled. To setup the initial user use the inmanta-initial-user-setup tool."
        )


def verify_password_policy(password: str) -> None:
    """Raise a BadRequest if the password does not satisfy the password policy (length and complexity)."""
    violation = util.password_policy_violation(password)
    if violation is not None:
        raise exceptions.BadRequest(violation)


_dummy_password_hash: Optional[str] = None


def verify_dummy_password(password: SecretStr) -> None:
    """
    Verify the password against a constant dummy hash. This makes the response time of a login for an
    unknown user match that of a known user with a wrong password, preventing username enumeration
    through timing.
    """
    global _dummy_password_hash
    if _dummy_password_hash is None:
        _dummy_password_hash = nacl.pwhash.str(b"a constant dummy password used only for timing").decode()
    try:
        nacl.pwhash.verify(_dummy_password_hash.encode(), password.get_secret_value().encode())
    except nacl.exceptions.InvalidkeyError:
        pass


def normalize_password(password: str) -> str:
    """
    Normalize a password to Unicode NFKC before it is hashed or verified.

    The same password can be entered as different byte sequences depending on the operating system,
    keyboard, or input method: for example an accented character may be a single code point (é, U+00E9)
    on one machine and a base letter plus a combining accent (e + U+0301) on another, and compatibility
    characters (ligatures, full-width forms, ...) have canonical equivalents too. Because the hash is
    computed over the raw bytes, without normalization the exact same password typed on two machines can
    fail to verify. NFKC collapses these variants to a single canonical form so a password is accepted
    regardless of how it was typed. This is recommended by NIST SP 800-63B. For ASCII passwords it is a
    no-op.
    """
    return unicodedata.normalize("NFKC", password)


def verify_password(stored_hash: str, password: str) -> tuple[bool, bool]:
    """
    Verify a password against a stored hash, tolerating hashes created before NFKC normalization.

    Passwords are normalized (see normalize_password) before being hashed, but hashes stored by older
    versions were computed from the raw, non-normalized input. Verifying only the normalized form would
    lock those users out, and a hash cannot be re-normalized in place. So we verify the normalized form
    first and, only if that fails and the input actually changed under normalization, fall back to the
    raw form. A match on the raw form is reported via the second return value so the caller can
    transparently re-hash the password to its normalized form, migrating the account on next use.

    :return: (matched, needs_rehash). matched is True when the password is correct; needs_rehash is True
             only when it matched the pre-normalization (raw) form and the stored hash should be updated.
    :raises nacl.exceptions.CryptoError: (except InvalidkeyError) or ValueError when the stored hash
             itself cannot be parsed; the caller decides how to report that.
    """
    # Reject pathologically long input before normalizing. normalize runs on the unauthenticated login
    # path, and NFKC on a very large string is expensive enough to stall the event loop; no legitimate
    # password approaches this cap. A too-long password simply does not match.
    if len(password) > const.MAX_RAW_PASSWORD_LENGTH:
        return False, False
    normalized = normalize_password(password)
    try:
        nacl.pwhash.verify(stored_hash.encode(), normalized.encode())
        return True, False
    except nacl.exceptions.InvalidkeyError:
        pass
    if password != normalized:
        try:
            nacl.pwhash.verify(stored_hash.encode(), password.encode())
            return True, True
        except nacl.exceptions.InvalidkeyError:
            pass
    return False, False


def normalize_new_password(password: SecretStr) -> str:
    """
    Normalize a to-be-stored password to NFKC, rejecting pathologically long input before normalizing
    (NFKC on a very large string is expensive). Returns the normalized secret to hash.
    """
    raw = password.get_secret_value()
    if len(raw) > const.MAX_RAW_PASSWORD_LENGTH:
        raise exceptions.BadRequest(f"the password should be at most {const.MAX_PASSWORD_LENGTH} characters long")
    return normalize_password(raw)


def _get_source_ip(context: common.CallContext) -> str:
    """
    Source of the request for audit logging. This is the connection peer IP, which is the client
    for direct access (the common case for the web console) and the reverse proxy when the API is
    fronted by one. In the latter case the originating client is reported by the proxy in the
    X-Forwarded-For header, so it is appended when present.
    """
    remote_ip = context.remote_ip or "unknown"
    forwarded = context.request_headers.get("X-Forwarded-For") or context.request_headers.get("x-forwarded-for")
    if forwarded:
        return f"{remote_ip} (X-Forwarded-For: {forwarded.split(',')[0].strip()})"
    return remote_ip


class UserService(server_protocol.ServerSlice):
    """Slice for managing users"""

    def __init__(self) -> None:
        super().__init__(SLICE_USER)

    def get_dependencies(self) -> list[str]:
        return [SLICE_DATABASE]

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    @protocol.handle(protocol.methods_v2.list_users)
    async def list_users(self) -> list[model.UserWithRoles]:
        return await data.User.list_users_with_roles()

    @protocol.handle(protocol.methods_v2.add_user)
    async def add_user(self, username: str, password: SecretStr) -> model.User:
        verify_authentication_enabled()
        if not username:
            raise exceptions.BadRequest("the username cannot be an empty string")
        secret = normalize_new_password(password)
        verify_password_policy(secret)

        # hash the password
        pw_hash = nacl.pwhash.str(secret.encode())

        # insert the user
        try:
            user = data.User(
                username=username,
                password_hash=pw_hash.decode(),
                auth_method=AuthMethod.database,
            )
            await user.insert()
        except asyncpg.UniqueViolationError:
            raise exceptions.Conflict(f"A user with name {username} already exists.")
        return user.to_dao()

    @protocol.handle(protocol.methods_v2.delete_user)
    async def delete_user(self, username: str) -> None:
        verify_authentication_enabled()
        user = await data.User.get_one(username=username)
        if user is None:
            raise exceptions.NotFound(f"User with name {username} does not exist.")

        await user.delete()

    @protocol.handle(protocol.methods_v2.set_password)
    async def set_password(
        self,
        username: str,
        password: SecretStr,
        context: common.CallContext,
        current_password: Optional[SecretStr] = None,
    ) -> None:
        verify_authentication_enabled()
        secret = normalize_new_password(password)
        verify_password_policy(secret)
        source_ip = _get_source_ip(context)
        # check if the user already exists
        user = await data.User.get_one(username=username)
        if not user:
            raise exceptions.NotFound(f"User with name {username} does not exist.")

        # Changing your own password requires proving you know the current one, so a hijacked session
        # cannot silently take over the account. An administrator changing another user's password does not.
        if context.auth_username == username:
            if current_password is None:
                raise exceptions.BadRequest("changing your own password requires the current password")
            current_password_ok = bool(user.password_hash)
            if current_password_ok:
                try:
                    # The current password only has to match; the account is re-hashed with the new one below,
                    # so any pre-normalization rehash flag can be ignored here.
                    current_password_ok, _ = verify_password(user.password_hash, current_password.get_secret_value())
                except (ValueError, nacl.exceptions.CryptoError):
                    current_password_ok = False
            else:
                # No local password (e.g. an OIDC-only account): still run a verification so the response
                # time does not reveal whether the account has a password.
                verify_dummy_password(current_password)
            if not current_password_ok:
                LOGGER.warning("Failed password change for user '%s' from %s: incorrect current password", username, source_ip)
                raise exceptions.UnauthorizedException(message="The current password is incorrect", no_prefix=True)

        # hash the password
        pw_hash = nacl.pwhash.str(secret.encode())

        # insert the user
        await user.update_fields(password_hash=pw_hash.decode())
        LOGGER.info("Password for user '%s' changed by '%s' from %s", username, context.auth_username or "<unknown>", source_ip)

    @protocol.handle(protocol.methods_v2.login)
    async def login(
        self, username: str, password: SecretStr, context: common.CallContext
    ) -> common.ReturnValue[model.LoginReturn]:
        verify_authentication_enabled()
        source_ip = _get_source_ip(context)
        # check if the user exists
        invalid_username_password_msg = "Invalid username or password"
        user = await data.User.get_one(username=username)
        if not user or not user.password_hash:
            # Still run a verification against a dummy hash so the timing does not reveal that the user
            # does not exist (username-enumeration resistance).
            verify_dummy_password(password)
            LOGGER.warning("Failed login for user '%s' from %s: no such user", username, source_ip)
            raise exceptions.UnauthorizedException(message=invalid_username_password_msg, no_prefix=True)
        try:
            matched, needs_rehash = verify_password(user.password_hash, password.get_secret_value())
        except (ValueError, nacl.exceptions.CryptoError):
            # A stored hash that cannot be parsed is an authentication failure, not a server error. (Most
            # malformed hashes raise InvalidkeyError, a CryptoError subclass; a well-formed but too-long
            # hash raises a plain ValueError. Both are handled here.)
            LOGGER.warning("Failed login for user '%s' from %s: malformed stored password hash", username, source_ip)
            raise exceptions.UnauthorizedException(message=invalid_username_password_msg, no_prefix=True)
        if not matched:
            LOGGER.warning("Failed login for user '%s' from %s: invalid password", username, source_ip)
            raise exceptions.UnauthorizedException(message=invalid_username_password_msg, no_prefix=True)
        if needs_rehash:
            # The password only matched its pre-normalization form: best-effort migrate the stored hash to
            # the normalized form so future logins verify on the first attempt. Authentication has already
            # succeeded, so a failure here (e.g. a transient DB error) must not fail the login.
            try:
                await user.update_fields(
                    password_hash=nacl.pwhash.str(normalize_password(password.get_secret_value()).encode()).decode()
                )
            except Exception:
                LOGGER.warning("Could not migrate the stored password hash for user '%s' to the normalized form", username)

        LOGGER.info("Successful login for user '%s' from %s", username, source_ip)
        role_assignments: model.RoleAssignmentsPerEnvironment = await data.Role.get_roles_for_user(username)

        custom_claims: Mapping[str, str | bool | Mapping[str, list[str]]] = {
            "sub": username,
            const.INMANTA_ROLES_URN: {str(env_id): roles for env_id, roles in role_assignments.assignments.items()},
            const.INMANTA_IS_ADMIN_URN: user.is_admin,
        }
        token = auth.encode_token([str(const.ClientType.api.value)], expire=None, custom_claims=custom_claims)
        return common.ReturnValue(
            status_code=200,
            headers={"Authorization": f"Bearer {token}"},
            response=model.LoginReturn(
                user=user.to_dao(),
                token=token,
            ),
        )

    @protocol.handle(protocol.methods_v2.get_current_user)
    async def get_current_user(self, context: common.CallContext) -> model.CurrentUser:
        if context.auth_username:
            return model.CurrentUser(username=context.auth_username)
        raise exceptions.NotFound("No current user found, probably an API token is used.")

    @protocol.handle(protocol.methods_v2.list_roles)
    async def list_roles(self) -> list[str]:
        return [r.name for r in await data.Role.get_list(order_by_column="name")]

    @protocol.handle(protocol.methods_v2.create_role)
    async def create_role(self, name: str) -> None:
        verify_authentication_enabled()
        try:
            await data.Role(id=uuid.uuid4(), name=name).insert()
        except asyncpg.UniqueViolationError:
            raise exceptions.BadRequest(f"Role {name} already exists.")

    @protocol.handle(protocol.methods_v2.delete_role)
    async def delete_role(self, name: str) -> None:
        verify_authentication_enabled()
        try:
            await data.Role.delete_role(name=name)
        except data.RoleStillAssignedException:
            raise exceptions.BadRequest(f"Role {name} cannot be delete because it's still assigned to a user.")
        except KeyError:
            raise exceptions.BadRequest(f"Role {name} doesn't exist.")

    @protocol.handle(protocol.methods_v2.list_roles_for_user)
    async def list_roles_for_user(self, username: str) -> model.RoleAssignmentsPerEnvironment:
        return await data.Role.get_roles_for_user(username)

    @protocol.handle(protocol.methods_v2.assign_role)
    async def assign_role(self, username: str, environment: uuid.UUID, role: str) -> None:
        verify_authentication_enabled()
        try:
            await data.Role.assign_role_to_user(username, environment=environment, role=role)
        except data.CannotAssignRoleException:
            raise exceptions.BadRequest(
                f"Cannot assign role {role} to user {username}."
                f" Role {role}, environment {environment} or user {username} doesn't exist."
            )

    @protocol.handle(protocol.methods_v2.unassign_role)
    async def unassign_role(self, username: str, environment: uuid.UUID, role: str) -> None:
        verify_authentication_enabled()
        try:
            await data.Role.unassign_role_from_user(username, environment=environment, role=role)
        except KeyError:
            raise exceptions.BadRequest(f"Role {role} (environment={environment}) is not assigned to user {username}")

    @protocol.handle(protocol.methods_v2.set_is_admin)
    async def set_is_admin(self, username: str, is_admin: bool) -> None:
        verify_authentication_enabled()
        try:
            await data.User.set_is_admin(username=username, is_admin=is_admin)
        except KeyError:
            raise exceptions.BadRequest(f"No user exists with username {username}.")
