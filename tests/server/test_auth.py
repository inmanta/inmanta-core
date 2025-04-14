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

import os
import uuid

import pytest

from inmanta import config, const
from inmanta.protocol import common
from inmanta.protocol.auth import auth, decorators
from inmanta.protocol.decorators import handle, typedmethod
from inmanta.server import protocol
from inmanta.server.services import policy_engine_service

@pytest.fixture
async def server_with_test_slice(tmpdir, access_policy: str) -> protocol.Server:
    """
    A fixture that returns a server with auth enabled that has a TestSlice
    with several different API endpoints that require authorization through
    the policy engine.
    """
    # Configure server
    state_dir = os.path.join(tmpdir, "state")
    log_dir = os.path.join(tmpdir, "logs")
    for directory in [state_dir, log_dir]:
        os.mkdir(directory)

    config.Config.set("server", "auth", "true")
    config.Config.set("server", "auth_method", "database")
    config.Config.set("auth_jwt_default", "algorithm", "HS256")
    config.Config.set("auth_jwt_default", "sign", "true")
    config.Config.set("auth_jwt_default", "client_types", "agent,compiler,api")
    config.Config.set("auth_jwt_default", "key", "eciwliGyqECVmXtIkNpfVrtBLutZiITZKSKYhogeHMM")
    config.Config.set("auth_jwt_default", "expire", "0")
    config.Config.set("auth_jwt_default", "issuer", "https://localhost:8888/")
    config.Config.set("auth_jwt_default", "audience", "https://localhost:8888/")
    config.Config.set("config", "state-dir", state_dir)
    config.Config.set("config", "log-dir", log_dir)
    config.state_dir.set(str(tmpdir))

    os.mkdir(os.path.join(tmpdir, "policy_engine"))
    access_policy_file = os.path.join(tmpdir, "policy_engine", "policy.rego")
    with open(access_policy_file, "w") as fh:
        fh.write(access_policy)
    policy_engine_service.policy_file.set(access_policy_file)

    # Define the TestSlice and its API endpoints
    @decorators.auth(auth_label="test", read_only=True)
    @typedmethod(path="/read-only", operation="GET", client_types=["api"])
    def read_only_method() -> None:  # NOQA
        pass

    @decorators.auth(auth_label="test", read_only=False, environment_param="env")
    @typedmethod(path="/environment-scoped", operation="POST", client_types=["api"])
    def environment_scoped_method(env: uuid.UUID) -> None:  # NOQA
        pass

    @decorators.auth(auth_label="user", read_only=False, environment_param="env")
    @typedmethod(path="/user-endpoint", operation="POST", client_types=["api"])
    def user_method(env: uuid.UUID) -> None:  # NOQA
        pass

    @decorators.auth(auth_label="admin", read_only=False)
    @typedmethod(path="/admin-only", operation="POST", client_types=["api"])
    def admin_only_method() -> None:  # NOQA
        pass

    class TestSlice(protocol.ServerSlice):
        @handle(read_only_method)
        async def handle_read_only_method(self) -> None:  # NOQA
            return

        @handle(environment_scoped_method)
        async def handle_environment_scoped_method(self, env: uuid.UUID) -> None:  # NOQA
            return

        @handle(user_method)
        async def handle_user_method(self, env: uuid.UUID) -> None:  # NOQA
            return

        @handle(admin_only_method)
        async def handle_admin_only_method(self, context: common.CallContext) -> None:  # NOQA
            return

    # Start the server
    rs = protocol.Server()
    policy_engine_slice = policy_engine_service.PolicyEngineSlice()
    test_slice = TestSlice(name="testslice")
    for current_slice in [policy_engine_slice, test_slice]:
        rs.add_slice(current_slice)
    await rs.start()

    yield rs

    # Stop the server
    await test_slice.stop()
    await policy_engine_slice.stop()
    await rs.stop()


def get_client_with_role(env_to_role_dct: dict[str, str], is_admin: bool) -> protocol.Client:
    """
    Returns a client that uses an access token for the given role.
    """
    token = auth.encode_token(
        client_types=[str(const.ClientType.api.value)],
        expire=None,
        custom_claims={
            f"{const.INMANTA_URN}roles": env_to_role_dct,
            f"{const.INMANTA_URN}is-admin": is_admin,
        },
    )
    config.Config.set("client_rest_transport", "token", token)
    return protocol.Client("client")


@pytest.mark.parametrize(
    "access_policy",
    [
        """
        package policy

        default allowed := false

        # Write the information about the endpoint into a variable
        # to make the policy easier to read.
        endpoint_data := data.endpoints[input.request.endpoint_id]

        # The environment used in the request
        request_environment := input.request.parameters[endpoint_data.environment_param] if {
            endpoint_data.environment_param != null
        } else := null

        # Any user can make read-only calls.
        allowed if {
            endpoint_data.read_only
        }

        # If the API endpoint is environment-scoped, users can call it if
        # they have the read-write role on that environment.
        allowed if {
            request_environment != null
            input.token["urn:inmanta:roles"][request_environment] == "read-write"
        }

        # Users with the user role in a given environment can execute API endpoints
        # with auth_label="user" in that environment.
        allowed if {
            endpoint_data.auth_label == "user"
            request_environment != null
            input.token["urn:inmanta:roles"][request_environment] == "user"
        }

        # Users marked as is-admin can execute any API endpoint.
        allowed if {
            input.token["urn:inmanta:is-admin"]
        }
        """.strip()
    ],
)
async def test_policy_evaluation(server_with_test_slice: protocol.Server) -> None:
    """
    Verify that the server correctly takes into account the defined access policy.
    """
    env_id = "11111111-1111-1111-1111-111111111111"

    client = get_client_with_role(env_to_role_dct={env_id: "read-only"}, is_admin=False)
    result = await client.read_only_method()
    assert result.code == 200
    result = await client.environment_scoped_method(env_id)
    assert result.code == 403
    result = await client.user_method(env_id)
    assert result.code == 403
    result = await client.admin_only_method()
    assert result.code == 403

    client = get_client_with_role(env_to_role_dct={env_id: "read-write"}, is_admin=False)
    result = await client.read_only_method()
    assert result.code == 200
    result = await client.environment_scoped_method(env_id)
    assert result.code == 200
    result = await client.user_method(env_id)
    assert result.code == 200
    result = await client.admin_only_method()
    assert result.code == 403

    client = get_client_with_role(env_to_role_dct={env_id: "user"}, is_admin=False)
    result = await client.read_only_method()
    assert result.code == 200
    result = await client.environment_scoped_method(env_id)
    assert result.code == 403
    result = await client.user_method(env_id)
    assert result.code == 200
    result = await client.admin_only_method()
    assert result.code == 403

    client = get_client_with_role(env_to_role_dct={}, is_admin=True)
    result = await client.read_only_method()
    assert result.code == 200
    result = await client.environment_scoped_method(env_id)
    assert result.code == 200
    result = await client.user_method(env_id)
    assert result.code == 200
    result = await client.admin_only_method()
    assert result.code == 200


async def test_input_for_policy_engine(server_with_test_slice: protocol.Server, monkeypatch) -> None:
    """
    Verify that the protocol layer correctly composes the JSON document that is fed into the policy
    engine as input for the policy evaluation.
    """
    # Monkeypatch the does_satisfy_access_policy() method of the PolicyEngineSlice so that we can
    # intercept the value of the input_data dictionary.
    input_policy_engine = None
    _old_does_satisfy_access_policy = policy_engine_service.PolicyEngineSlice.does_satisfy_access_policy

    async def save_input_data(self, input_data: dict[str, object]) -> bool:
        """
        Save the value of the input_data parameter, passed to the PolicyEngineSlice.does_satisfy_access_policy()
        method, into the local input_policy_engine variable.
        """
        nonlocal input_policy_engine
        input_policy_engine = input_data
        return _old_does_satisfy_access_policy(self, input_data)

    monkeypatch.setattr(policy_engine_service.PolicyEngineSlice, "does_satisfy_access_policy", save_input_data)

    env_id = "11111111-1111-1111-1111-111111111111"
    client = get_client_with_role(env_to_role_dct={env_id: "read-write"}, is_admin=False)
    result = await client.environment_scoped_method(env_id)
    assert input_policy_engine is not None
    assert "input" in input_policy_engine
    assert "request" in input_policy_engine["input"]
    request = input_policy_engine["input"]["request"]
    assert request == {
        "endpoint_id": "POST /environment-scoped",
        "parameters": {
            "env": uuid.UUID(env_id),
        },
    }
    assert "token" in input_policy_engine["input"]
    token = input_policy_engine["input"]["token"]
    assert token["urn:inmanta:ct"] == ["api"]
    assert token["urn:inmanta:roles"] == {env_id: "read-write"}
    assert token["urn:inmanta:is-admin"] is False

    client = get_client_with_role(env_to_role_dct={}, is_admin=True)
    input_policy_engine = None
    result = await client.read_only_method()
    assert "input" in input_policy_engine
    assert "request" in input_policy_engine["input"]
    request = input_policy_engine["input"]["request"]
    assert request == {
        "endpoint_id": "GET /read-only",
        "parameters": {},
    }
    assert "token" in input_policy_engine["input"]
    token = input_policy_engine["input"]["token"]
    assert token["urn:inmanta:ct"] == ["api"]
    assert token["urn:inmanta:roles"] == {}
    assert token["urn:inmanta:is-admin"] is True


async def test_policy_engine_data() -> None:
    """
    Verify that the data provided to the policy engine, containing
    authorization metadata about the endpoints, is correct.
    """

    @decorators.auth(auth_label="test", read_only=True)
    @typedmethod(path="/read-only", operation="GET", client_types=["api"])
    def test_read_only() -> None:  # NOQA
        pass

    @decorators.auth(auth_label="other-test", read_only=False, environment_param="tid")
    @typedmethod(path="/read-write", operation="POST", client_types=["api", "agent"])
    def test_read_write(tid: uuid.UUID) -> None:  # NOQA
        pass

    data: dict[str, object] = decorators.AuthorizationMetadata.get_open_policy_agent_data()
    endpoint_id = "GET /read-only"
    assert endpoint_id in data["endpoints"]
    read_only_method_metadata = data["endpoints"][endpoint_id]
    assert read_only_method_metadata["auth_label"] == "test"
    assert read_only_method_metadata["read_only"] is True
    assert read_only_method_metadata["client_types"] == ["api"]
    assert read_only_method_metadata["environment_param"] is None

    endpoint_id = "POST /read-write"
    assert endpoint_id in data["endpoints"]
    read_write_method_metadata = data["endpoints"][endpoint_id]
    assert read_write_method_metadata["auth_label"] == "other-test"
    assert read_write_method_metadata["read_only"] is False
    assert read_write_method_metadata["client_types"] == ["api", "agent"]
    assert read_write_method_metadata["environment_param"] == "tid"
