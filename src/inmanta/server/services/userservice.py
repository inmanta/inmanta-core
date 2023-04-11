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

import asyncpg

import nacl.exceptions
import nacl.pwhash
from inmanta import const, data, protocol
from inmanta.const import MIN_PASSWORD_LENGTH
from inmanta.data import AuthMethod, model
from inmanta.protocol import common, exceptions
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


class UserService(server_protocol.ServerSlice):
    """Slice for managing users"""

    def __init__(self) -> None:
        super().__init__(SLICE_USER)

    def get_dependencies(self) -> list[str]:
        return [SLICE_DATABASE]

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    @protocol.handle(protocol.methods_v2.list_users)
    async def list_users(self) -> list[model.User]:
        return [user.to_dao() for user in await data.User.get_list(order_by_column="username", order="ASC")]

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
        user = await data.User.get_one(username=username)
        if not user or not user.password_hash:
            raise exceptions.UnauthorizedException()
        try:
            nacl.pwhash.verify(user.password_hash.encode(), password.encode())
        except nacl.exceptions.InvalidkeyError:
            raise exceptions.UnauthorizedException()

        token = common.encode_token([str(const.ClientType.api.value)], expire=None)
        return common.ReturnValue(
            status_code=200,
            headers={"Authentication": f"Bearer {token}"},
            response=model.LoginReturn(
                user=user.to_dao(),
                token=token,
            ),
        )
