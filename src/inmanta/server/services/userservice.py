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
import uuid
from collections.abc import Mapping

import asyncpg

import nacl.exceptions
import nacl.pwhash
from inmanta import const, data, protocol
from inmanta.const import MIN_PASSWORD_LENGTH
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


def issue_session_token(user: data.User, role_assignments: model.RoleAssignmentsPerEnvironment) -> tuple[str, int | None]:
    """
    Mint a login-session token for the given user and return it together with its lifetime in seconds
    (None when the token does not expire). Shared by the login and session-renewal endpoints so both issue
    identical claims and honor the same session lifetime, and so renewal always reflects the user's current
    roles and admin status.
    """
    custom_claims: Mapping[str, str | bool | Mapping[str, list[str]]] = {
        "sub": user.username,
        const.INMANTA_ROLES_URN: {str(env_id): roles for env_id, roles in role_assignments.assignments.items()},
        const.INMANTA_IS_ADMIN_URN: user.is_admin,
    }
    # Give login sessions their own lifetime, decoupled from the auth_jwt expire that governs
    # agent/compiler service tokens. When the option is 0, fall back to the signing config's expire.
    session_expire = server_config.server_login_session_expire.get()
    expires_in = session_expire if session_expire > 0 else None
    token = auth.encode_token(
        [str(const.ClientType.api.value)],
        expire=expires_in,
        custom_claims=custom_claims,
    )
    return token, expires_in


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
    async def add_user(self, username: str, password: str) -> model.User:
        verify_authentication_enabled()
        if not username:
            raise exceptions.BadRequest("the username cannot be an empty string")
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise exceptions.BadRequest("the password should be at least 8 characters long")

        # hash the password
        pw_hash = nacl.pwhash.str(password.encode())

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
    async def set_password(self, username: str, password: str) -> None:
        verify_authentication_enabled()
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise exceptions.BadRequest("the password should be at least 8 characters long")
        # check if the user already exists
        user = await data.User.get_one(username=username)
        if not user:
            raise exceptions.NotFound(f"User with name {username} does not exist.")

        # hash the password
        pw_hash = nacl.pwhash.str(password.encode())

        # insert the user
        await user.update_fields(password_hash=pw_hash.decode())

    @protocol.handle(protocol.methods_v2.login)
    async def login(self, username: str, password: str) -> common.ReturnValue[model.LoginReturn]:
        verify_authentication_enabled()
        # check if the user exists
        invalid_username_password_msg = "Invalid username or password"
        user = await data.User.get_one(username=username)
        if not user or not user.password_hash:
            raise exceptions.UnauthorizedException(message=invalid_username_password_msg, no_prefix=True)
        try:
            nacl.pwhash.verify(user.password_hash.encode(), password.encode())
        except nacl.exceptions.InvalidkeyError:
            raise exceptions.UnauthorizedException(message=invalid_username_password_msg, no_prefix=True)

        role_assignments: model.RoleAssignmentsPerEnvironment = await data.Role.get_roles_for_user(username)
        token, expires_in = issue_session_token(user, role_assignments)
        return common.ReturnValue(
            status_code=200,
            headers={"Authorization": f"Bearer {token}"},
            response=model.LoginReturn(user=user.to_dao(), token=token, expires_in=expires_in),
        )

    @protocol.handle(protocol.methods_v2.login_renew)
    async def login_renew(self, context: common.CallContext) -> common.ReturnValue[model.LoginReturn]:
        verify_authentication_enabled()
        # Renewal is authenticated by the caller's current, still-valid token: a valid token is the
        # credential, so no password is checked. Two things must hold for a token to be renewable:
        #  1. It carries a sub claim identifying the user; a service token (agent/compiler/API) has none.
        #  2. It was minted by this server's own signing authority. A token merely accepted by decode_token
        #     is not enough: with an external issuer configured (the break-glass topology where a local
        #     sign=true section coexists with an OIDC section), a user authenticated against that external
        #     issuer would otherwise be handed a fresh, locally-signed token carrying the roles and is_admin
        #     of a same-named local account. So we require the token's issuer to be our own signing issuer.
        # The user is taken from the token's sub claim, so a caller can only ever renew their own session.
        sign_config = auth.AuthJWTConfig.get_sign_config()
        username = context.auth_username
        token_issuer = context.auth_token.get("iss") if context.auth_token else None
        if not username or sign_config is None or token_issuer != sign_config.issuer:
            raise exceptions.BadRequest("Only login sessions issued by this server can be renewed.")
        user = await data.User.get_one(username=username)
        if not user:
            # The user was removed while the session was still active; force a fresh login.
            raise exceptions.UnauthorizedException(message="User account no longer exists.", no_prefix=True)

        role_assignments: model.RoleAssignmentsPerEnvironment = await data.Role.get_roles_for_user(username)
        token, expires_in = issue_session_token(user, role_assignments)
        LOGGER.debug("Renewed the login session for user '%s'", username)
        return common.ReturnValue(
            status_code=200,
            headers={"Authorization": f"Bearer {token}"},
            response=model.LoginReturn(user=user.to_dao(), token=token, expires_in=expires_in),
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
