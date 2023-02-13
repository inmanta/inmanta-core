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

import nacl.exceptions
import nacl.pwhash
from inmanta import const, data, protocol
from inmanta.data import model
from inmanta.protocol import common, exceptions
from inmanta.server import SLICE_TRANSPORT, SLICE_USER
from inmanta.server import protocol as server_protocol

LOGGER = logging.getLogger(__name__)


class UserService(server_protocol.ServerSlice):
    """Slice for managing users"""

    def __init__(self) -> None:
        super().__init__(SLICE_USER)

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    @protocol.handle(protocol.methods_v2.list_users)
    async def list_users(self) -> list[model.User]:
        return [user.to_dao() for user in await data.User.get_list()]

    @protocol.handle(protocol.methods_v2.add_user)
    async def add_user(self, username: str, password: str) -> model.User:
        # check if the user already exists
        existing = await data.User.get_one(username=username)
        if existing:
            raise exceptions.Conflict(f"A user with name {username} already exists.")

        # hash the password
        pw_hash = nacl.pwhash.str(password.encode())

        # insert the user
        user = data.User(
            username=username,
            password=pw_hash.decode(),
            enabled=True,
            auth_method="password",
        )
        await user.insert()
        return user.to_dao()

    @protocol.handle(protocol.methods_v2.delete_user)
    async def delete_user(self, username: str) -> None:
        user = await data.User.get_one(username=username)
        if user is None:
            raise exceptions.NotFound(f"User with name {username} does not exist.")

        await user.delete()

    @protocol.handle(protocol.methods_v2.set_password)
    async def set_password(self, username: str, password: str) -> None:
        # check if the user already exists
        user = await data.User.get_one(username=username)
        if not user:
            raise exceptions.NotFound(f"User with name {username} does not exist.")

        # hash the password
        pw_hash = nacl.pwhash.str(password.encode())

        # insert the user
        await user.update_fields(password=pw_hash.decode())

    @protocol.handle(protocol.methods_v2.login)
    async def login(self, username: str, password: str) -> common.ReturnValue[model.LoginReturn]:
        # check if the user exists
        user = await data.User.get_one(username=username)
        if not user:
            raise exceptions.UnauthorizedException()

        if not user.password:
            raise exceptions.UnauthorizedException()

        try:
            nacl.pwhash.verify(user.password.encode(), password.encode())
        except nacl.exceptions.InvalidkeyError:
            raise exceptions.UnauthorizedException()

        # TODO: set an expire
        token = common.encode_token([str(const.ClientType.api.value)], expire=None)
        return common.ReturnValue(
            status_code=200,
            headers={"Authentication": f"Bearer {token}"},
            response=model.LoginReturn(
                user=user.to_dao(),
                token=token,
                expiry=0,
            ),
        )
