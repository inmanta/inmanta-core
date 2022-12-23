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

from inmanta import config
from inmanta.protocol import endpoints
from inmanta.server import SLICE_USER, protocol


async def test_create_user(server: protocol.Server, client: endpoints.Client) -> None:
    """test operations on users and login without testing the actual auth"""
    assert server.get_slice(SLICE_USER)

    response = await client.list_users()
    assert response.code == 200
    assert not response.result["data"]

    response = await client.add_user("admin", "test")
    assert response.code == 200

    response = await client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    response = await client.login("admin", "test")
    assert response.code == 200
    assert response.result["data"]

    response = await client.login("admin", "wrong")
    assert response.code == 401

    response = await client.delete_user("admin")
    assert response.code == 200

    response = await client.list_users()
    assert response.code == 200
    assert not response.result["data"]


async def test_login(server: protocol.Server, client: endpoints.Client) -> None:
    """Test the built-in user authentication"""
    response = await client.list_users()
    assert response.code == 200

    response = await client.add_user("admin", "test")
    assert response.code == 200

    response = await client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    config.Config.set("server", "auth", "true")

    response = await client.list_users()
    assert response.code == 401

    response = await client.login("admin", "test")
    assert response.code == 200
    assert response.result["data"]

    token = response.result["data"]
    config.Config.set("client_rest_transport", "token", token)

    auth_client = protocol.Client("client")
    response = await auth_client.list_users()
    assert response.code == 200
