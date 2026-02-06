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
from dataclasses import dataclass
from functools import partial
from typing import Mapping

import pytest

import nacl.pwhash
import utils
from inmanta import config, const, data
from inmanta.data.model import AuthMethod, RoleAssignmentsPerEnvironment
from inmanta.protocol import common, rest
from inmanta.protocol.auth import auth, decorators, policy_engine, providers
from inmanta.protocol.decorators import handle, method, typedmethod
from inmanta.server import config as server_config
from inmanta.server import protocol
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.protocol import Server, SliceStartupException


@pytest.fixture
async def server_with_test_slice(
    tmpdir,
    access_policy: str,
    path_policy_engine_executable: str,
    authorization_provider: server_config.AuthorizationProviderName,
) -> protocol.Server:
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

    # Configure authorization
    config.Config.set("server", "authorization-provider", authorization_provider.value)
    os.mkdir(os.path.join(tmpdir, "policy_engine"))
    access_policy_file = os.path.join(tmpdir, "policy_engine", "policy.rego")
    with open(access_policy_file, "w") as fh:
        fh.write(access_policy)
    policy_engine.policy_file.set(access_policy_file)
    policy_engine.policy_engine_log_level.set("info")
    policy_engine.path_opa_executable.set(path_policy_engine_executable)

    # Define the TestSlice and its API endpoints
    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST, read_only=True)
    @typedmethod(path="/read-only", operation="GET", client_types=[const.ClientType.api, const.ClientType.compiler])
    def read_only_method() -> None:  # NOQA
        pass

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST, read_only=False, environment_param="env")
    @typedmethod(path="/environment-scoped", operation="POST", client_types=[const.ClientType.api])
    def environment_scoped_method(env: uuid.UUID) -> None:  # NOQA
        pass

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST_2, read_only=False, environment_param="env")
    @typedmethod(path="/user-endpoint", operation="POST", client_types=[const.ClientType.api])
    def user_method(env: uuid.UUID) -> None:  # NOQA
        pass

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST_3, read_only=False)
    @typedmethod(path="/admin-only", operation="POST", client_types=[const.ClientType.api])
    def admin_only_method() -> None:  # NOQA
        pass

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST, read_only=False)
    @typedmethod(path="/enforce-auth-disabled", operation="GET", client_types=[const.ClientType.api], enforce_auth=False)
    def enforce_auth_disabled_method() -> None:  # NOQA
        pass

    async def _idempotent_getter(val: uuid.UUID, metadata: dict) -> uuid.UUID:
        """
        Getter that can be passed to the ArgOption constructor that doesn't alter the value.
        """
        return val

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST, read_only=False)
    @typedmethod(
        path="/method-with-call-context",
        operation="GET",
        client_types=[const.ClientType.api],
        arg_options={"tid": common.ArgOption(header=const.INMANTA_MT_HEADER, reply_header=True, getter=_idempotent_getter)},
    )
    def call_context_method(tid: uuid.UUID, arg1: uuid.UUID, arg2: str) -> None:  # NOQA
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

        @handle(enforce_auth_disabled_method)
        async def handle_enforce_auth_disabled(self) -> None:  # NOQA
            return

        @handle(call_context_method, test="arg1")
        async def handle_call_context_method(
            self, call_context: common.CallContext, tid: uuid.UUID, test: uuid.UUID, arg2: str
        ) -> None:  # NOQA
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


async def create_client_for_user(client, username: str, password: str) -> protocol.Client:
    """
    Create a client for the given user that uses a token containing the roles
    the user has at the moment this method is called.
    """
    result = await client.login(username=username, password=password)
    assert result.code == 200
    config.Config.set("client_rest_transport", "token", result.result["data"]["token"])
    return protocol.Client("client")


@pytest.mark.parametrize(
    "access_policy",
    ["""
        package policy

        default allow := false

        # Write the information about the endpoint into a variable
        # to make the policy easier to read.
        endpoint_data := data.endpoints[input.request.endpoint_id]

        # The environment used in the request
        request_environment := input.request.parameters[endpoint_data.environment_param] if {
            endpoint_data.environment_param != null
        } else := null

        # Any user can make read-only calls.
        allow if {
            endpoint_data.read_only
        }

        # If the API endpoint is environment-scoped, users can call it if
        # they have the read-write role on that environment.
        allow if {
            request_environment != null
            "read-write" in input.token["urn:inmanta:roles"][request_environment]
        }

        # Users with the test2 role in a given environment can execute API endpoints
        # with auth_label="test2" in that environment.
        allow if {
            endpoint_data.auth_label == "test2"
            request_environment != null
            "user" in input.token["urn:inmanta:roles"][request_environment]
        }

        # Users marked as is-admin can execute any API endpoint.
        allow if {
            input.token["urn:inmanta:is_admin"]
        }
        """.strip()],
)
async def test_policy_evaluation(server_with_test_slice: protocol.Server) -> None:
    """
    Verify that the server correctly takes into account the defined access policy.
    """
    env_id = "11111111-1111-1111-1111-111111111111"

    client = utils.get_auth_client(env_to_role_dct={env_id: ["read-only"]}, is_admin=False)
    result = await client.read_only_method()
    assert result.code == 200
    result = await client.environment_scoped_method(env_id)
    assert result.code == 403
    result = await client.user_method(env_id)
    assert result.code == 403
    result = await client.admin_only_method()
    assert result.code == 403

    client = utils.get_auth_client(env_to_role_dct={env_id: ["read-write"]}, is_admin=False)
    result = await client.read_only_method()
    assert result.code == 200
    result = await client.environment_scoped_method(env_id)
    assert result.code == 200
    result = await client.user_method(env_id)
    assert result.code == 200
    result = await client.admin_only_method()
    assert result.code == 403

    client = utils.get_auth_client(env_to_role_dct={env_id: ["user"]}, is_admin=False)
    result = await client.read_only_method()
    assert result.code == 200
    result = await client.environment_scoped_method(env_id)
    assert result.code == 403
    result = await client.user_method(env_id)
    assert result.code == 200
    result = await client.admin_only_method()
    assert result.code == 403

    client = utils.get_auth_client(env_to_role_dct={}, is_admin=True)
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


@pytest.mark.parametrize(
    "access_policy",
    ["""
        package policy

        default allow := false
        """],
)
async def test_fallback_to_legacy_provider(server_with_test_slice: protocol.Server) -> None:
    """
    Verify that service tokens are not evaluated using the policy engine, but a fallback is done
    to the legacy authorization provider.
    """
    # ClientType == api -> Use policy engine authorization provider
    client = utils.get_auth_client(env_to_role_dct={}, is_admin=False, client_types=[const.ClientType.api])
    result = await client.read_only_method()
    assert result.code == 403

    # ClientType == compiler -> Use legacy authorization provider
    client = utils.get_auth_client(env_to_role_dct={}, is_admin=False, client_types=[const.ClientType.compiler])
    result = await client.read_only_method()
    assert result.code == 200


@pytest.mark.parametrize(
    "authorization_provider, return_code",
    [
        # policy_engine provider -> enforce_auth=False is ignored
        (server_config.AuthorizationProviderName.policy_engine, 401),
        # legacy provider -> enforce_auth=False is taken into account
        (server_config.AuthorizationProviderName.legacy, 200),
    ],
)
async def test_enforce_auth_method_property(
    server_with_test_slice: protocol.Server, authorization_provider: server_config.AuthorizationProviderName, return_code: int
) -> None:
    """
    Ensure that the enforce_auth method property is taken into account by the legacy authorization provider,
    but not by the policy engine authorization provider.
    """
    # Create a client that doesn't include an authorization token in its requests to the server.
    config.Config.get("client_rest_transport", "token", None) is None
    client = protocol.Client("client")
    result = await client.enforce_auth_disabled_method()
    assert result.code == return_code


@pytest.mark.parametrize(
    "access_policy",
    ["""
        package policy

        default allow := false
        """],
)
@pytest.mark.parametrize(
    "authorization_provider",
    [a for a in server_config.AuthorizationProviderName],
)
async def test_authorization_providers(
    server_with_test_slice: protocol.Server, authorization_provider: server_config.AuthorizationProviderName
) -> None:
    """
    Verify the behavior of the different authorization providers.
    """
    client = utils.get_auth_client(env_to_role_dct={}, is_admin=False, client_types=[const.ClientType.api])
    result = await client.read_only_method()
    match server_config.AuthorizationProviderName(authorization_provider.value):
        case server_config.AuthorizationProviderName.legacy:
            assert result.code == 200
        case server_config.AuthorizationProviderName.policy_engine:
            assert result.code == 403
        case _:
            raise Exception(f"Unknown authorization_provider: {authorization_provider.value}")


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
    client = utils.get_auth_client(env_to_role_dct={env_id: ["read-write"]}, is_admin=False)
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
    assert token[const.INMANTA_ROLES_URN] == {env_id: ["read-write"]}
    assert token[const.INMANTA_IS_ADMIN_URN] is False

    client = utils.get_auth_client(env_to_role_dct={}, is_admin=True)
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
    assert token[const.INMANTA_ROLES_URN] == {}
    assert token[const.INMANTA_IS_ADMIN_URN] is True


async def test_policy_engine_data() -> None:
    """
    Verify that the data provided to the policy engine, containing
    authorization metadata about the endpoints, is correct.
    """

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST, read_only=True)
    @typedmethod(path="/read-only", operation="GET", client_types=[const.ClientType.api])
    def test_read_only() -> None:  # NOQA
        pass

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST_2, read_only=False, environment_param="tid")
    @typedmethod(path="/read-write", operation="POST", client_types=[const.ClientType.api, const.ClientType.agent])
    def test_read_write(tid: uuid.UUID) -> None:  # NOQA
        pass

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST_3, read_only=False, environment_param="tid")
    @typedmethod(path="/read-write2/<tid>", operation="POST", client_types=[const.ClientType.api, const.ClientType.agent])
    def test_param(tid: uuid.UUID) -> None:  # NOQA
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
    assert read_write_method_metadata["auth_label"] == "test2"
    assert read_write_method_metadata["read_only"] is False
    assert read_write_method_metadata["client_types"] == ["api", "agent"]
    assert read_write_method_metadata["environment_param"] == "tid"

    endpoint_id = "POST /api/v1/read-write2/<tid>"
    assert endpoint_id in data["endpoints"]
    read_write_method_metadata = data["endpoints"][endpoint_id]
    assert read_write_method_metadata["auth_label"] == "test3"
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

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST, read_only=True, environment_param="id")
    @method(path="/test1/<id>", operation="GET")
    def method_1(id: str) -> None:
        pass

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST_2, read_only=False)
    @method(path="/test2", operation="POST", client_types=[const.ClientType.api, const.ClientType.agent])
    def method_2(id: str) -> None:
        pass

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST_3, read_only=True, environment_param="id")
    @typedmethod(path="/test3/<id>", operation="GET")
    def method_3(id: str) -> None:
        pass

    @decorators.auth(auth_label=const.CoreAuthorizationLabel.TEST_4, read_only=False)
    @typedmethod(path="/test4", operation="POST", client_types=[const.ClientType.api, const.ClientType.agent])
    def method_4(id: str) -> None:
        pass

    data: dict[str, object] = common.MethodProperties.get_open_policy_agent_data()
    assert data["endpoints"]["GET /api/v1/test1/<id>"] == {
        "client_types": ["api"],
        "auth_label": "test",
        "read_only": True,
        "environment_param": "id",
    }
    assert data["endpoints"]["POST /api/v1/test2"] == {
        "client_types": ["api", "agent"],
        "auth_label": "test2",
        "read_only": False,
        "environment_param": None,
    }
    assert data["endpoints"]["GET /api/v1/test3/<id>"] == {
        "client_types": ["api"],
        "auth_label": "test3",
        "read_only": True,
        "environment_param": "id",
    }
    assert data["endpoints"]["POST /api/v1/test4"] == {
        "client_types": ["api", "agent"],
        "auth_label": "test4",
        "read_only": False,
        "environment_param": None,
    }


@dataclass
class CapturedInput:
    """
    Object that contains the output of the `PolicyEngineAuthorizationProvider._get_input_for_policy_engine()` method.
    """

    value: dict[str, object] | None = None


@pytest.fixture
def capture_input_for_policy_engine(monkeypatch) -> CapturedInput:
    """
    Fixture that monkeypatches the PolicyEngineAuthorizationProvider._get_input_for_policy_engine() method to
    capture its return value. After each invocation of the _get_input_for_policy_engine() method, the value
    is stored in the returned CapturedInput object.
    """
    captured_input = CapturedInput()

    original_get_input_for_policy_engine = providers.PolicyEngineAuthorizationProvider._get_input_for_policy_engine

    def _get_input_for_policy_engine_wrapper(self, call_arguments: rest.CallArguments) -> Mapping[str, object]:
        result = original_get_input_for_policy_engine(self, call_arguments)
        captured_input.value = result
        return result

    monkeypatch.setattr(
        providers.PolicyEngineAuthorizationProvider, "_get_input_for_policy_engine", _get_input_for_policy_engine_wrapper
    )

    return captured_input


async def test_get_input_for_policy_engine(capture_input_for_policy_engine: CapturedInput, server_with_test_slice):
    """
    Verify that the input, provided to the policy engine, looks as expected.
    """
    env_id = str(uuid.uuid4())
    client = utils.get_auth_client(env_to_role_dct={env_id: ["test"]}, is_admin=False, client_types=[const.ClientType.api])

    tid = uuid.uuid4()
    arg1 = uuid.uuid4()
    arg2 = "test"
    assert capture_input_for_policy_engine.value is None
    result = await client.call_context_method(tid=tid, arg1=arg1, arg2=arg2)
    assert result.code == 200
    pe_input = capture_input_for_policy_engine.value
    assert pe_input["input"]["request"]["endpoint_id"] == "GET /api/v1/method-with-call-context"
    assert pe_input["input"]["request"]["parameters"] == {const.INMANTA_MT_HEADER: tid, "arg1": arg1, "arg2": arg2}
    assert pe_input["input"]["token"]["urn:inmanta:ct"] == ["api"]
    assert pe_input["input"]["token"][const.INMANTA_ROLES_URN] == {env_id: ["test"]}
    assert pe_input["input"]["token"][const.INMANTA_IS_ADMIN_URN] is False


@pytest.mark.parametrize(
    "access_policy",
    ["""
        package policy

        # Write the information about the endpoint into a variable
        # to make the policy easier to read.
        endpoint_data := data.endpoints[input.request.endpoint_id]

        # The environment used in the request
        request_environment := input.request.parameters[endpoint_data.environment_param] if {
            endpoint_data.environment_param != null
        } else := null

        default allow := false

        # Allow access if the user has the role a_role.
        allow if {
            "a_role" in input.token["urn:inmanta:roles"][request_environment]
        }

        # Allow access to admin user.
        allow if {
            input.token["urn:inmanta:is_admin"]
        }
        """],
)
@pytest.mark.parametrize("authentication_method", [AuthMethod.database])
@pytest.mark.parametrize("enable_auth", [True])
async def test_role_assignment(server: protocol.Server, client) -> None:
    """
    Verify that roles set for a user can be used in the access policy.
    """
    env1_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    env2_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    # Create client with admin privileges, that can update role assignment.
    admin_client = utils.get_auth_client(env_to_role_dct={}, is_admin=True)

    result = await admin_client.project_create(name="proj")
    assert result.code == 200
    project_id = result.result["data"]["id"]
    for env_id in [env1_id, env2_id]:
        result = await admin_client.environment_create(project_id=project_id, name=f"env-{env_id}", environment_id=env_id)
        assert result.code == 200

    # Create users
    username1 = "user1"
    username2 = "user2"
    password = "password"
    for username in [username1, username2]:
        user = data.User(
            username=username,
            password_hash=nacl.pwhash.str(password.encode()).decode(),
            auth_method=AuthMethod.database,
        )
        await user.insert()

    async def verify_role_assignment(username: str, expected_assignments: RoleAssignmentsPerEnvironment) -> None:
        result = await admin_client.list_roles_for_user(username=username)
        assert result.code == 200
        assert {
            uuid.UUID(env_id): roles for env_id, roles in result.result["data"]["assignments"].items()
        } == expected_assignments.assignments

    async def verify_roles_on_list_user(expected_assignments: dict[str, RoleAssignmentsPerEnvironment]) -> None:
        """
        Assert that the role assignments returned by the list_users API endpoint correspond to the
        role assignments given in expected_assignments.

        :param expected_assignments: The expected role assignments. Maps the username to the list of role assignments.
        """
        result = await admin_client.list_users()
        assert result.code == 200
        actual_assignments = {
            user["username"]: RoleAssignmentsPerEnvironment(assignments=user["roles"]) for user in result.result["data"]
        }
        assert expected_assignments == actual_assignments

    # Verify initial state
    for username in [username1, username2]:
        result = await admin_client.list_roles_for_user(username=username)
        assert result.code == 200
        assert not result.result["data"]["assignments"]

        client_for_user = await create_client_for_user(client, username, password)
        for env_id in [env1_id, env2_id]:
            result = await client_for_user.environment_get(env_id)
            assert result.code == 403

    result = await admin_client.list_roles()
    assert result.code == 200
    assert not result.result["data"]

    # Create role
    result = await admin_client.create_role(name="a_role")
    assert result.code == 200

    result = await admin_client.list_roles()
    assert result.code == 200
    assert result.result["data"] == ["a_role"]

    # Assign roles
    result = await admin_client.assign_role(username=username1, environment=env1_id, role="a_role")
    assert result.code == 200
    result = await admin_client.assign_role(username=username1, environment=env2_id, role="a_role")
    assert result.code == 200
    result = await admin_client.assign_role(username=username2, environment=env1_id, role="a_role")
    assert result.code == 200

    # Verify role assignment
    expected_role_assignments_username1 = RoleAssignmentsPerEnvironment(assignments={env1_id: ["a_role"], env2_id: ["a_role"]})
    await verify_role_assignment(username=username1, expected_assignments=expected_role_assignments_username1)
    expected_role_assignments_username2 = RoleAssignmentsPerEnvironment(assignments={env1_id: ["a_role"]})
    await verify_role_assignment(username=username2, expected_assignments=expected_role_assignments_username2)
    await verify_roles_on_list_user(
        expected_assignments={username1: expected_role_assignments_username1, username2: expected_role_assignments_username2}
    )

    user1_client = await create_client_for_user(client, username=username1, password=password)
    for env_id in [env1_id, env2_id]:
        result = await user1_client.list_notifications(tid=env_id)
        assert result.code == 200
    user2_client = await create_client_for_user(client, username=username2, password=password)
    for env_id in [env1_id, env2_id]:
        result = await user2_client.list_notifications(tid=env_id)
        assert result.code == (200 if env_id == env1_id else 403)

    # Unassign role
    result = await admin_client.unassign_role(username=username1, environment=env2_id, role="a_role")
    assert result.code == 200
    result = await admin_client.unassign_role(username=username2, environment=env1_id, role="a_role")
    assert result.code == 200

    # Verify role assignment
    expected_role_assignments_username1 = RoleAssignmentsPerEnvironment(assignments={env1_id: ["a_role"]})
    await verify_role_assignment(username=username1, expected_assignments=expected_role_assignments_username1)
    expected_role_assignments_username2 = RoleAssignmentsPerEnvironment(assignments={})
    await verify_role_assignment(username=username2, expected_assignments=expected_role_assignments_username2)
    await verify_roles_on_list_user(
        expected_assignments={username1: expected_role_assignments_username1, username2: expected_role_assignments_username2}
    )

    result = await admin_client.list_roles()
    assert result.code == 200
    assert result.result["data"] == ["a_role"]

    user1_client = await create_client_for_user(client, username=username1, password=password)
    for env_id in [env1_id, env2_id]:
        result = await user1_client.list_notifications(tid=env_id)
        assert result.code == (200 if env_id == env1_id else 403)
    user2_client = await create_client_for_user(client, username=username2, password=password)
    for env_id in [env1_id, env2_id]:
        result = await user2_client.list_notifications(tid=env_id)
        assert result.code == 403

    # Remove last role assignment for role a_role
    result = await admin_client.unassign_role(username=username1, environment=env1_id, role="a_role")
    assert result.code == 200
    # Remove role a_role
    result = await admin_client.delete_role(name="a_role")
    assert result.code == 200

    result = await admin_client.list_roles()
    assert result.code == 200
    assert not result.result["data"]


@pytest.mark.parametrize("authentication_method", [AuthMethod.database])
@pytest.mark.parametrize("enable_auth", [True])
async def test_multiple_roles_assigned(server: protocol.Server, client) -> None:
    """
    Verify that all roles are correctly set into the token.
    """
    env_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    # Create client with admin privileges, that can update role assignment.
    admin_client = utils.get_auth_client(env_to_role_dct={}, is_admin=True)

    result = await admin_client.project_create(name="proj")
    assert result.code == 200
    project_id = result.result["data"]["id"]
    result = await admin_client.environment_create(project_id=project_id, name="env", environment_id=env_id)
    assert result.code == 200

    # Create users
    username = "username"
    password = "password"
    user = data.User(
        username=username,
        password_hash=nacl.pwhash.str(password.encode()).decode(),
        auth_method=AuthMethod.database,
    )
    await user.insert()

    result = await admin_client.create_role(name="role1")
    assert result.code == 200
    result = await admin_client.create_role(name="role2")
    assert result.code == 200

    result = await admin_client.assign_role(username=username, environment=env_id, role="role1")
    assert result.code == 200
    result = await admin_client.assign_role(username=username, environment=env_id, role="role2")
    assert result.code == 200

    result = await client.login(username=username, password=password)
    assert result.code == 200
    token = result.result["data"]["token"]
    claims, _ = auth.decode_token(token)
    assert set(claims[const.INMANTA_ROLES_URN][str(env_id)]) == {"role1", "role2"}
    assert not claims[const.INMANTA_IS_ADMIN_URN]

    # Verify roles returned by the list_users API endpoint
    result = await admin_client.list_users()
    assert result.code == 200
    assert len(result.result["data"]) == 1
    actual_role_assignments = {uuid.UUID(env_id): roles for env_id, roles in result.result["data"][0]["roles"].items()}
    expected_role_assignments = {env_id: ["role1", "role2"]}
    assert actual_role_assignments == expected_role_assignments


@pytest.mark.parametrize("enable_auth", [True])
async def test_roles_failure_scenarios(server: protocol.Server, client, environment) -> None:
    """
    Test the failure scenario's when manipulating roles and role assignments.
    """
    result = await client.add_user(username="user", password="useruser")
    assert result.code == 200

    # Create role that already exists
    result = await client.create_role(name="role")
    assert result.code == 200
    result = await client.create_role(name="role")
    assert result.code == 400
    assert "Role role already exists." in result.result["message"]

    # Delete non-existing role
    result = await client.delete_role(name="missing")
    assert result.code == 400
    assert "Role missing doesn't exist" in result.result["message"]

    # Delete role still assigned to user
    result = await client.assign_role(username="user", environment=environment, role="role")
    assert result.code == 200
    result = await client.delete_role(name="role")
    assert result.code == 400
    assert "Role role cannot be delete because it's still assigned to a user." in result.result["message"]

    # Assign role: user doens't exist
    result = await client.assign_role(username="missing", environment=environment, role="role")
    assert result.code == 400
    assert (
        "Cannot assign role role to user missing."
        f" Role role, environment {environment} or user missing doesn't exist." in result.result["message"]
    )

    # Assign role: role doesn't exist
    result = await client.assign_role(username="user", environment=environment, role="missing")
    assert result.code == 400
    assert (
        "Cannot assign role missing to user user."
        f" Role missing, environment {environment} or user user doesn't exist." in result.result["message"]
    )

    # Assign role: environment doesn't exist
    id_non_existing_env = uuid.uuid4()
    result = await client.assign_role(username="user", environment=id_non_existing_env, role="role")
    assert result.code == 400
    assert (
        "Cannot assign role role to user user."
        f" Role role, environment {id_non_existing_env} or user user doesn't exist." in result.result["message"]
    )

    # Unassign role: user doesn't exist
    result = await client.unassign_role(username="missing", environment=environment, role="role")
    assert result.code == 400
    assert f"Role role (environment={environment}) is not assigned to user missing" in result.result["message"]

    # Unassign role: role doesn't exist
    result = await client.unassign_role(username="user", environment=environment, role="missing")
    assert result.code == 400
    assert f"Role missing (environment={environment}) is not assigned to user user" in result.result["message"]

    # Unassign role: environment doesn't exist
    result = await client.unassign_role(username="user", environment=id_non_existing_env, role="role")
    assert result.code == 400
    assert f"Role role (environment={id_non_existing_env}) is not assigned to user user" in result.result["message"]


@pytest.mark.parametrize(
    "access_policy",
    ["""
        package policy

        roles := ["role_a", "role_b"]

        default allow := true
        """],
)
@pytest.mark.parametrize("authentication_method", [AuthMethod.database])
@pytest.mark.parametrize("enable_auth", [True])
async def test_synchronization_roles_with_db(server: protocol.Server, client, async_finalizer) -> None:
    """
    Verify that the roles defined in the access policy are correctly synchronized into the database.
    """
    result = await client.list_roles()
    assert result.code == 200
    assert result.result["data"] == ["role_a", "role_b"]

    # Ensure that updates to the roles list are correctly reflected into the database.
    await server.stop()
    policy_file = policy_engine.policy_file.get()
    with open(policy_file, "w") as fh:
        fh.write("""
        package policy

        roles := ["role_a", "role_c"]

        default allow := true
        """)
    ibl = InmantaBootloader(configure_logging=False)
    async_finalizer.add(partial(ibl.stop, timeout=20))
    await ibl.start()

    result = await client.list_roles()
    assert result.code == 200
    assert result.result["data"] == ["role_a", "role_b", "role_c"]

    # Ensure that the absence of the roles list doesn't update anything in the database.
    await ibl.stop()
    with open(policy_file, "w") as fh:
        fh.write("""
        package policy

        default allow := true
        """)
    ibl = InmantaBootloader(configure_logging=False)
    async_finalizer.add(partial(ibl.stop, timeout=20))
    await ibl.start()

    result = await client.list_roles()
    assert result.code == 200
    assert result.result["data"] == ["role_a", "role_b", "role_c"]


@pytest.mark.parametrize(
    "access_policy",
    ["""
        package policy

        default allow := false

        # Users marked as is-admin can execute any API endpoint.
        allow if {
            input.token["urn:inmanta:is_admin"]
        }
        """.strip()],
)
@pytest.mark.parametrize("authentication_method", [AuthMethod.database])
@pytest.mark.parametrize("enable_auth", [True])
async def test_is_admin_role(server: protocol.Server, client: protocol.Client) -> None:
    admin_user = "admin"
    regular_user = "user"
    for username in [admin_user, regular_user]:
        user = data.User(
            username=username,
            password_hash=nacl.pwhash.str(username.encode()).decode(),
            auth_method=AuthMethod.database,
            is_admin=(username == "admin"),
        )
        await user.insert()

    admin_client = await create_client_for_user(client, username=admin_user, password=admin_user)

    user_client = await create_client_for_user(client, username=regular_user, password=regular_user)
    result = await user_client.environment_list()
    assert result.code == 403

    result = await admin_client.set_is_admin(username=regular_user, is_admin=True)
    assert result.code == 200

    user_client = await create_client_for_user(client, username=regular_user, password=regular_user)
    result = await user_client.environment_list()
    assert result.code == 200

    result = await admin_client.set_is_admin(username=regular_user, is_admin=False)
    assert result.code == 200

    user_client = await create_client_for_user(client, username=regular_user, password=regular_user)
    result = await user_client.environment_list()
    assert result.code == 403

    result = await admin_client.set_is_admin(username="non_existing_user", is_admin=True)
    assert result.code == 400


@pytest.mark.parametrize("authentication_method", [AuthMethod.database])
@pytest.mark.parametrize("enable_auth", [True])
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
        "Please check if you provided the correct certificate/key path and make sure that these files are not encrypted",
    ):
        await rs.start()
