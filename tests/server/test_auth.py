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

from inmanta import config, const
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
