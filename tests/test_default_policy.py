"""
Copyright 2025 Inmanta

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
import os.path
import pytest

from inmanta import data, const
from inmanta.protocol.auth import auth
from inmanta.data.model import AuthMethod
from inmanta.server.config import AuthorizationProviderName

import utils

def read_file(file_name: str) -> str:
    """
    Returns the config of the given file.
    """
    with open(file_name, "r") as fh:
        return fh.read()

@pytest.mark.parametrize("enable_auth", [True])
@pytest.mark.parametrize("auth_method", [AuthMethod.database])
@pytest.mark.parametrize("authorization_provider", [AuthorizationProviderName.policy_engine])
@pytest.mark.parametrize(
    "access_policy",
    [read_file(os.path.join(os.path.dirname(__file__), "..", "misc", "access-policy", "default_policy.rego"))],
)
async def test_default_policy(server, client) -> None:
    """
    Test the behavior of the default policy.
    """
    # Create a user
    user = data.User(
        username="user",
        password_hash=nacl.pwhash.str("user".encode()).decode(),
        auth_method=AuthMethod.database,
    )
    await user.insert()

    admin_client = utils.get_auth_client(
        env_to_role_dct={},
        is_admin=True,
        client_types=[const.ClientType.api],
    )

    
