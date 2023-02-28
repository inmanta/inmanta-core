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
import nacl
from inmanta import config, data
from inmanta.protocol import endpoints
from inmanta.server import SLICE_USER, protocol


async def test_create_and_delete_user(server: protocol.Server, client: endpoints.Client) -> None:
    """test operations on users and login without testing the actual auth"""
    assert server.get_slice(SLICE_USER)

    response = await client.list_users()
    assert response.code == 200
    assert not response.result["data"]

    # Try adding a user with a password that is too short
    response = await client.add_user("admin", "test")
    assert response.code == 400
    assert response.result["message"] == "Invalid request: the password should be at least 8 characters long"

    response = await client.add_user("admin", "test1234")
    assert response.code == 200

    response = await client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    # Try adding a user with the same username
    response = await client.add_user("admin", "test12345")
    assert response.code == 409
    assert (
        response.result["message"] == "Request conflicts with the current state of the resource: A user with name admin "
        "already exists."
    )

    response = await client.delete_user("admin")
    assert response.code == 200

    response = await client.list_users()
    assert response.code == 200
    assert not response.result["data"]


async def test_login(server: protocol.Server, client: endpoints.Client) -> None:
    """Test the built-in user authentication"""
    response = await client.list_users()
    assert response.code == 200

    response = await client.add_user("admin", "test1234")
    assert response.code == 200

    response = await client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    config.Config.set("server", "auth", "true")

    response = await client.list_users()
    assert response.code == 401

    response = await client.login("user_does_not_exist", "test1234")
    assert response.code == 401
    assert response.result["message"] == "Access to this resource is unauthorized: User does not exist or is disabled"

    response = await client.login("admin", "wrong")
    assert response.code == 401

    response = await client.login("admin", "test1234")
    assert response.code == 200
    assert "token" in response.result["data"]
    assert "user" in response.result["data"]
    assert "expiry" in response.result["data"]
    assert response.result["data"]["user"]["username"] == "admin"

    token = response.result["data"]["token"]
    config.Config.set("client_rest_transport", "token", token)

    auth_client = protocol.Client("client")
    response = await auth_client.list_users()
    assert response.code == 200
    assert response.result["data"][0]["username"] == "admin"


async def test_set_password(client: endpoints.Client) -> None:
    old_pw = "old_password"
    new_pw = "new_password"
    response = await client.add_user("admin", old_pw)
    assert response.code == 200

    response = await client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    response = await client.set_password("admin", "toshort")
    assert response.code == 400
    assert response.result["message"] == "Invalid request: the password should be at least 8 characters long"

    response = await client.set_password("admin", new_pw)
    assert response.code == 200

    response = await client.list_users()
    assert response.code == 200
    assert response.result["data"]
    assert response.result["data"][0]["username"] == "admin"

    response = await client.login("admin", old_pw)
    assert response.code == 401

    response = await client.login("admin", new_pw)
    assert response.code == 200
