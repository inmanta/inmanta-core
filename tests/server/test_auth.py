"""
Copyright 2024 Inmanta

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
from inmanta.data.model import AuthMethod, RoleAssignmentsPerEnvironment
from inmanta.protocol import common, rest
from inmanta.protocol.auth import auth, decorators, policy_engine, providers
from inmanta.protocol.decorators import handle, method, typedmethod
from inmanta.server import config as server_config
from inmanta.server import protocol
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.protocol import Server, SliceStartupException
from inmanta.data.model import AuthMethod
from inmanta.protocol import auth
from inmanta.server import SLICE_USER, protocol


@pytest.fixture
def server_pre_start(server_config):
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


def get_auth_client(claim_rules: list[str], claims: dict[str, str | list[str]]) -> protocol.Client:
    config.Config.set("auth_jwt_default", "claims", "\n    ".join(claim_rules) + "\n")
    auth.AuthJWTConfig.reset()

    token = auth.encode_token([str(const.ClientType.api.value)], expire=None, custom_claims=claims)
    config.Config.set("client_rest_transport", "token", token)
    auth_client = protocol.Client("client")
    return auth_client


async def test_claim_assertions(server: protocol.Server, server_pre_start) -> None:
    """test various claim assertions"""
    assert server.get_slice(SLICE_USER)

    # test claims that match rules
    client = get_auth_client(
        claim_rules=["prod in environments", "type is dc"], claims=dict(environments=["prod", "lab"], type="dc", username="bob")
    )
    assert (await client.list_users()).code == 200

    # test a wrong claim
    client = get_auth_client(
        claim_rules=["prod in environments", "type is dc"],
        claims=dict(environments=["prod", "lab"], type="lab", username="bob"),
    )
    assert (await client.list_users()).code == 403

    # test a rule that is not correct: use in on string
    client = get_auth_client(
        claim_rules=["dc in type"],
        claims=dict(environments=["prod", "lab"], type="lab", username="bob"),
    )
    assert (await client.list_users()).code == 403

    # test a rule that is not correct: use is on list
    client = get_auth_client(
        claim_rules=["environments is prod"],
        claims=dict(environments=["prod", "lab"], type="lab", username="bob"),
    )
    assert (await client.list_users()).code == 403


async def test_provide_token_as_parameter(server: protocol.Server, client) -> None:
    """
    Validate whether the authorization token is handled correctly
    when provided using a parameter instead of a header.
    """
    config.Config.set("server", "auth", "true")
    config.Config.set("server", "auth_method", "database")
    user = data.User(
        username="admin",
        password_hash=nacl.pwhash.str("adminadmin".encode()).decode(),
        auth_method=AuthMethod.database,
    )
    await user.insert()

    # No authorization token provided
    result = await client.get_api_docs()
    assert result.code == 401

    response = await client.login("admin", "adminadmin")
    assert response.code == 200
    token = response.result["data"]["token"]

    result = await client.get_api_docs(token=token)
    assert result.code == 200


async def test_login_failed(server, client) -> None:
    """
    Ensure that a meaningful error message is returned when incorrect
    credentials are provided to the login endpoint.
    """
    user = data.User(
        username="admin",
        password_hash=nacl.pwhash.str("admin".encode()).decode(),
        auth_method=AuthMethod.database,
    )
    await user.insert()

    # Invalid username
    result = await client.login(username="test", password="test")
    assert result.code == 401
    assert "Invalid username or password" == result.result["message"]

    # Invalid password
    result = await client.login(username="admin", password="test")
    assert result.code == 401
    assert "Invalid username or password" == result.result["message"]


async def test_ssl_key_encrypted(inmanta_config, server_config, postgres_db, database_name):
    """
    Test that the server produces a cleaner exception if something goes wrong when loading the certificate
    """
    utils.configure_auth(auth=True, ca=False, ssl=True, use_encrypted_ssl_key=True)
    rs = Server()
    with pytest.raises(
        SliceStartupException,
        match="Failed to load ssl certificate. "
        "Please check if you provided the correct certificate/key path and make sure that these files are not encrypted.",
    ):
        await rs.start()
