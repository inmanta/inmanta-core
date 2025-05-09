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

import nacl.pwhash
from inmanta import config, const, data
from inmanta.data.model import AuthMethod
from inmanta.protocol import common
from inmanta.protocol.auth import auth, decorators, policy_engine
from inmanta.protocol.decorators import handle, method, typedmethod
from inmanta.server import protocol


@pytest.fixture
async def server_with_test_slice(tmpdir, access_policy: str, path_policy_engine_executable: str) -> protocol.Server:
    """
    A fixture that returns a server with authentication and authorization enabled
    that has a TestSlice with several different API endpoints that require authorization
    through the policy engine.
    """
    # Configure server
    state_dir = os.path.join(tmpdir, "state")
    log_dir = os.path.join(tmpdir, "logs")
    for directory in [state_dir, log_dir]:
        os.mkdir(directory)

    config.Config.set("server", "auth", "true")
    config.Config.set("server", "enforce-access-policy", "true")
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
    policy_engine.policy_file.set(access_policy_file)
    policy_engine.policy_engine_log_level.set("info")
    policy_engine.path_opa_executable.set(path_policy_engine_executable)

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
    test_slice = TestSlice(name="testslice")
    rs.add_slice(test_slice)
    await rs.start()

    yield rs

    # Stop the server
    await test_slice.stop()
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

    log_dir = config.log_dir.get()
    policy_engine_log_file = os.path.join(log_dir, "policy_engine.log")
    assert os.path.isfile(policy_engine_log_file)
    with open(policy_engine_log_file, "r") as fh:
        assert fh.read(1)


async def test_input_for_policy_engine(server_with_test_slice: protocol.Server, monkeypatch) -> None:
    """
    Verify that the protocol layer correctly composes the JSON document that is fed into the policy
    engine as input for the policy evaluation.
    """
    # Monkeypatch the does_satisfy_access_policy() method of the PolicyEngineSlice so that we can
    # intercept the value of the input_data dictionary.
    input_policy_engine = None
    _old_does_satisfy_access_policy = policy_engine.PolicyEngine.does_satisfy_access_policy

    async def save_input_data(self, input_data: dict[str, object]) -> bool:
        """
        Save the value of the input_data parameter, passed to the PolicyEngineSlice.does_satisfy_access_policy()
        method, into the local input_policy_engine variable.
        """
        nonlocal input_policy_engine
        input_policy_engine = input_data
        return _old_does_satisfy_access_policy(self, input_data)

    monkeypatch.setattr(policy_engine.PolicyEngine, "does_satisfy_access_policy", save_input_data)

    env_id = "11111111-1111-1111-1111-111111111111"
    client = get_client_with_role(env_to_role_dct={env_id: "read-write"}, is_admin=False)
    result = await client.environment_scoped_method(env_id)
    assert result.code == 200
    assert input_policy_engine is not None
    assert "input" in input_policy_engine
    assert "request" in input_policy_engine["input"]
    request = input_policy_engine["input"]["request"]
    assert request == {
        "endpoint_id": "POST /api/v1/environment-scoped",
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
    assert result.code == 200
    assert "input" in input_policy_engine
    assert "request" in input_policy_engine["input"]
    request = input_policy_engine["input"]["request"]
    assert request == {
        "endpoint_id": "GET /api/v1/read-only",
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

    data: dict[str, object] = common.MethodProperties.get_open_policy_agent_data()
    endpoint_id = "GET /api/v1/read-only"
    assert endpoint_id in data["endpoints"]
    read_only_method_metadata = data["endpoints"][endpoint_id]
    assert read_only_method_metadata["auth_label"] == "test"
    assert read_only_method_metadata["read_only"] is True
    assert read_only_method_metadata["client_types"] == ["api"]
    assert read_only_method_metadata["environment_param"] is None

    endpoint_id = "POST /api/v1/read-write"
    assert endpoint_id in data["endpoints"]
    read_write_method_metadata = data["endpoints"][endpoint_id]
    assert read_write_method_metadata["auth_label"] == "other-test"
    assert read_write_method_metadata["read_only"] is False
    assert read_write_method_metadata["client_types"] == ["api", "agent"]
    assert read_write_method_metadata["environment_param"] == "tid"


async def test_missing_auth_annotation() -> None:
    """
    Ensure that the validation logic of the server raises an Exception if an API endpoint
    is missing an @auth annotation.
    """

    @method(path="/test/<id>", operation="GET")
    def missing_auth_annotation(id: str):
        pass

    with pytest.raises(Exception) as excinfo:
        protocol.Server()._validate()

    assert "API endpoint missing_auth_annotation is missing an @auth annotation." in str(excinfo.value)


async def test_auth_annotation_not_required() -> None:
    """
    Verify that no exception is raised if the @auth annotation is missing on endpoints for machine-to-machine
    communication.
    """

    @method(path="/test1/<id>", agent_server=True, operation="GET")
    def method_1(id: str):
        pass

    @method(path="/test2/<id>", client_types=[const.ClientType.agent], operation="GET")
    def method_2(id: str):
        pass

    @method(path="/test3/<id>", client_types=[const.ClientType.compiler], operation="GET")
    def method_3(id: str):
        pass

    @method(
        path="/test4/<id>",
        client_types=[const.ClientType.agent, const.ClientType.compiler],
        operation="GET",
    )
    def method_4(id: str):
        pass

    protocol.Server()._validate()


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
