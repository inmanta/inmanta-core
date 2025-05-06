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
from inmanta.data.model import AuthMethod
from inmanta.protocol import common, auth
from inmanta.protocol.auth import auth, decorators, policy_engine
from inmanta.protocol.decorators import handle, method, typedmethod
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


async def test_auth_annotation() -> None:
    """
    Validate whether the logic behind the @auth annotation works correctly.
    """

    @decorators.auth(auth_label="label1", read_only=True, environment_param="id")
    @method(path="/test1/<id>", operation="GET")
    def method_1(id: str) -> None:
        pass

    @decorators.auth(auth_label="label2", read_only=False)
    @method(path="/test2", operation="POST", client_types=[const.ClientType.api, const.ClientType.agent])
    def method_2(id: str) -> None:
        pass

    @decorators.auth(auth_label="label3", read_only=True, environment_param="id")
    @typedmethod(path="/test3/<id>", operation="GET")
    def method_3(id: str) -> None:
        pass

    @decorators.auth(auth_label="label4", read_only=False)
    @typedmethod(path="/test4", operation="POST", client_types=[const.ClientType.api, const.ClientType.agent])
    def method_4(id: str) -> None:
        pass

    data: dict[str, object] = common.MethodProperties.get_open_policy_agent_data()
    assert data["endpoints"]["GET /api/v1/test1/<id>"] == {
        "client_types": [const.ClientType.api],
        "auth_label": "label1",
        "read_only": True,
        "environment_param": "id",
    }
    assert data["endpoints"]["POST /api/v1/test2"] == {
        "client_types": [const.ClientType.api, const.ClientType.agent],
        "auth_label": "label2",
        "read_only": False,
        "environment_param": None,
    }
    assert data["endpoints"]["GET /api/v1/test3/<id>"] == {
        "client_types": [const.ClientType.api],
        "auth_label": "label3",
        "read_only": True,
        "environment_param": "id",
    }
    assert data["endpoints"]["POST /api/v1/test4"] == {
        "client_types": [const.ClientType.api, const.ClientType.agent],
        "auth_label": "label4",
        "read_only": False,
        "environment_param": None,
    }
