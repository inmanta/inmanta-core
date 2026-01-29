"""
Copyright 2019 Inmanta

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

import asyncio
import base64
import functools
import json
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta, timezone
from functools import partial

import pytest
from dateutil import parser
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import config, const, data, loader, resources, util
from inmanta.agent import executor, handler
from inmanta.const import ParameterSource
from inmanta.data import AUTO_DEPLOY, ResourcePersistentState
from inmanta.data.model import AttributeStateChange
from inmanta.deploy import persistence, state
from inmanta.export import upload_code
from inmanta.protocol import Client
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_ORCHESTRATION, SLICE_SERVER
from inmanta.server import config as opt
from inmanta.server.bootloader import InmantaBootloader
from inmanta.types import ResourceIdStr, ResourceVersionIdStr
from inmanta.util import get_compiler_version
from utils import log_contains, log_doesnt_contain, retry_limited

LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize("no_agent", [True])
@pytest.mark.parametrize(
    "n_versions_to_keep, n_versions_to_create",
    [
        (2, 4),
        (4, 2),
        (2, 2),
    ],
)
async def test_create_too_many_versions(client, server, no_agent, n_versions_to_keep, n_versions_to_create):
    """
    - set AVAILABLE_VERSIONS_TO_KEEP environment setting to <n_versions_to_keep>
    - create <n_versions_to_create> versions
    - check the actual number of versions before and after cleanup
    """

    # Create project
    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    # Create environment
    result = await client.create_environment(project_id=project_id, name="env_1")
    env_1_id = result.result["environment"]["id"]
    result = await client.set_setting(tid=env_1_id, id=data.AVAILABLE_VERSIONS_TO_KEEP, value=n_versions_to_keep)
    assert result.code == 200
    # Perform release manually using the release_version() endpoint to prevent race conditions.
    result = await client.set_setting(env_1_id, AUTO_DEPLOY, False)
    assert result.code == 200

    # make a second environment to be sure we don't do cross env deletes
    # as it is empty, if it leaks, it will likely take everything with it on the other one
    await client.create_environment(project_id=project_id, name="env_2")

    # Check value was set
    result = await client.get_setting(tid=env_1_id, id=data.AVAILABLE_VERSIONS_TO_KEEP)
    assert result.code == 200
    assert result.result["value"] == n_versions_to_keep

    for _ in range(n_versions_to_create):
        version = (await client.reserve_version(env_1_id)).result["data"]

        resources = [
            # First one is fixed
            {
                "id": f"std::testing::NullResource[vm1.dev.inmanta.com,name=network],v={version}",
                "owner": "root",
                "path": "/etc/sysconfig/network",
                "permissions": 644,
                "purged": False,
                "requires": [],
            },
            # This one changes ID every version
            {
                "id": f"std::testing::NullResource[vm1.dev.inmanta.com,name=network{version}],v={version}",
                "owner": "root",
                "path": "/etc/sysconfig/network",
                "permissions": 644,
                "purged": False,
                "requires": [],
            },
        ]

        res = await client.put_version(
            tid=env_1_id,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert res.code == 200

        res = await client.release_version(tid=env_1_id, id=version)
        assert res.code == 200

    versions = await client.list_versions(tid=env_1_id)
    assert versions.result["count"] == n_versions_to_create

    prvs = await ResourcePersistentState.get_list()
    assert len(prvs) == n_versions_to_create + 1

    # Ensure we don't clean too much
    await ResourcePersistentState.trim(env_1_id)

    prvs = await ResourcePersistentState.get_list()
    assert len(prvs) == n_versions_to_create + 1

    await server.get_slice(SLICE_ORCHESTRATION)._purge_versions()

    versions = await client.list_versions(tid=env_1_id)
    # Add +1, because the latest released version is not included in the AVAILABLE_VERSIONS_TO_KEEP setting.
    assert versions.result["count"] == min(n_versions_to_keep + 1, n_versions_to_create)

    prvs = await ResourcePersistentState.get_list()
    # 1 variable resource per version + 1 fixed resource per version
    assert len(prvs) == min(n_versions_to_keep + 2, n_versions_to_create + 1)


@pytest.mark.parametrize("has_released_versions", [True, False])
async def test_purge_versions(server, client, environment, has_released_versions: bool, agent_no_state_check) -> None:
    """
    Verify that the `OrchestrationService._purge_versions()` method works correctly and that it doesn't cleanup
    the latest released version.
    """
    result = await client.set_setting(tid=environment, id=data.AUTO_DEPLOY, value="false")
    assert result.code == 200

    versions = []
    for _ in range(5):
        version = (await client.reserve_version(environment)).result["data"]
        versions.append(version)
        res = await client.put_version(
            tid=environment,
            version=version,
            resources=[
                {
                    "id": f"unittest::Resource[internal,name=ok],v={version}",
                    "name": "root",
                    "desired_value": "ok",
                    "send_event": "false",
                    "purged": False,
                    "requires": [],
                }
            ],
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert res.code == 200

    if has_released_versions:
        for v in versions[0:2]:
            result = await client.release_version(environment, id=v)
            assert result.code == 200

    result = await client.set_setting(tid=environment, id=data.AVAILABLE_VERSIONS_TO_KEEP, value=3)
    assert result.code == 200
    await server.get_slice(SLICE_ORCHESTRATION)._purge_versions()

    result = await client.list_versions(environment)
    assert result.code == 200
    assert result.result["count"] == (4 if has_released_versions else 3)
    if has_released_versions:
        assert {v["version"] for v in result.result["versions"]} == {versions[1], *versions[2:]}
    else:
        assert {v["version"] for v in result.result["versions"]} == {*versions[2:]}

    result = await client.set_setting(tid=environment, id=data.AVAILABLE_VERSIONS_TO_KEEP, value=1)
    assert result.code == 200
    await server.get_slice(SLICE_ORCHESTRATION)._purge_versions()

    result = await client.list_versions(environment)
    assert result.code == 200
    assert result.result["count"] == (2 if has_released_versions else 1)
    if has_released_versions:
        assert {v["version"] for v in result.result["versions"]} == {versions[1], *versions[4:]}
    else:
        assert {v["version"] for v in result.result["versions"]} == {*versions[4:]}


async def test_n_versions_env_setting_scope(client, server):
    """
    The AVAILABLE_VERSIONS_TO_KEEP environment setting used to be a global config option.
    This test checks that a specific environment setting can be set for each environment
    """

    n_versions_to_keep_env1 = 5
    n_versions_to_keep_env2 = 2

    n_many_versions = n_versions_to_keep_env1 + n_versions_to_keep_env2

    # Create project
    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    # Create environments
    result = await client.create_environment(project_id=project_id, name="env_1")
    env_1_id = result.result["environment"]["id"]
    result = await client.set_setting(tid=env_1_id, id=data.AVAILABLE_VERSIONS_TO_KEEP, value=n_versions_to_keep_env1)
    assert result.code == 200
    # Make sure we don't have a released version. _purge_versions() always keeps the latest released version.
    result = await client.set_setting(env_1_id, AUTO_DEPLOY, False)
    assert result.code == 200

    result = await client.create_environment(project_id=project_id, name="env_2")
    env_2_id = result.result["environment"]["id"]
    result = await client.set_setting(tid=env_2_id, id=data.AVAILABLE_VERSIONS_TO_KEEP, value=n_versions_to_keep_env2)
    assert result.code == 200
    # Make sure we don't have a released version. _purge_versions() always keeps the latest released version.
    result = await client.set_setting(env_2_id, AUTO_DEPLOY, False)
    assert result.code == 200

    # Create a lot of versions in both environments
    for _ in range(n_many_versions):
        env1_version = (await client.reserve_version(env_1_id)).result["data"]
        env2_version = (await client.reserve_version(env_2_id)).result["data"]

        res = await client.put_version(
            tid=env_1_id,
            version=env1_version,
            resources=[],
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert res.code == 200

        res = await client.put_version(
            tid=env_2_id,
            version=env2_version,
            resources=[],
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert res.code == 200

    # Before cleanup we have too many versions in both envs
    versions = await client.list_versions(tid=env_1_id)
    assert versions.result["count"] == n_many_versions

    versions = await client.list_versions(tid=env_2_id)
    assert versions.result["count"] == n_many_versions

    # Cleanup
    await server.get_slice(SLICE_ORCHESTRATION)._purge_versions()

    # After cleanup each env should have its specific number of version
    versions = await client.list_versions(tid=env_1_id)
    assert versions.result["count"] == n_versions_to_keep_env1

    versions = await client.list_versions(tid=env_2_id)
    assert versions.result["count"] == n_versions_to_keep_env2


@pytest.mark.slowtest
async def test_resource_action_update(server_multi, client_multi, environment_multi, null_agent_multi):
    """
    Test the server to manage the updates on a model during agent deploy
    """
    aclient = null_agent_multi._client
    version = (await client_multi.reserve_version(environment_multi)).result["data"]

    resources = [
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": "std::testing::NullResource[vm1.dev.inmanta.com,name=network],v=%d" % version,
            "owner": "root",
            "path": "/etc/sysconfig/network",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "version": version,
        },
        {
            "group": "root",
            "hash": "b4350bef50c3ec3ee532d4a3f9d6daedec3d2aba",
            "id": "std::testing::NullResource[vm2.dev.inmanta.com,name=motd],v=%d" % version,
            "owner": "root",
            "path": "/etc/motd",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "version": version,
        },
        {
            "group": "root",
            "hash": "3bfcdad9ab7f9d916a954f1a96b28d31d95593e4",
            "id": "std::testing::NullResource[vm1.dev.inmanta.com,name=hostname],v=%d" % version,
            "owner": "root",
            "path": "/etc/hostname",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "version": version,
        },
        {
            "id": "std::Service[vm1.dev.inmanta.com,name=network],v=%d" % version,
            "name": "network",
            "onboot": True,
            "requires": ["std::testing::NullResource[vm1.dev.inmanta.com,name=network],v=%d" % version],
            "state": "running",
            "version": version,
        },
    ]

    res = await client_multi.put_version(
        tid=environment_multi,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    result = await client_multi.list_versions(environment_multi)
    assert result.code == 200
    assert result.result["count"] == 1

    result = await client_multi.release_version(environment_multi, version, False)
    assert result.code == 200

    result = await client_multi.get_version(environment_multi, version)
    assert result.code == 200
    assert result.result["model"]["version"] == version
    assert result.result["model"]["total"] == len(resources)
    assert result.result["model"]["released"]

    action_id = uuid.uuid4()
    now = datetime.now()
    result = await aclient.resource_action_update(
        environment_multi,
        ["std::testing::NullResource[vm1.dev.inmanta.com,name=network],v=%d" % version],
        action_id,
        "deploy",
        now,
        now,
        "deployed",
        [],
        {},
    )

    assert result.code == 200

    result = await client_multi.resource_list(tid=environment_multi, deploy_summary=True)
    assert result.code == 200
    assert result.result["metadata"]["deploy_summary"]["by_state"]["deployed"] == 1

    action_id = uuid.uuid4()
    now = datetime.now()
    result = await aclient.resource_action_update(
        environment_multi,
        ["std::testing::NullResource[vm1.dev.inmanta.com,name=hostname],v=%d" % version],
        action_id,
        "deploy",
        now,
        now,
        "deployed",
        [],
        {},
    )
    assert result.code == 200

    result = await client_multi.resource_list(tid=environment_multi, deploy_summary=True)
    assert result.code == 200
    assert result.result["metadata"]["deploy_summary"]["by_state"]["deployed"] == 2


async def test_get_environment(client, clienthelper, server, environment):
    for i in range(10):
        version = await clienthelper.get_version()

        resources = []
        for j in range(i):
            resources.append(
                {
                    "group": "root",
                    "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
                    "id": "std::testing::NullResource[vm1.dev.inmanta.com,name=file%d],v=%d" % (j, version),
                    "owner": "root",
                    "path": "/tmp/file%d" % j,
                    "permissions": 644,
                    "purged": False,
                    "reload": False,
                    "requires": [],
                    "version": version,
                }
            )

        res = await client.put_version(
            tid=environment,
            version=version,
            resources=resources,
            unknowns=[],
            version_info={},
            compiler_version=get_compiler_version(),
        )
        assert res.code == 200

    result = await client.get_environment(environment, versions=5, resources=1)
    assert result.code == 200
    assert len(result.result["environment"]["versions"]) == 5
    assert len(result.result["environment"]["resources"]) == 9


async def test_resource_update(postgresql_client, client, clienthelper, server, environment, async_finalizer, null_agent):
    """
    Test updating resources and logging
    """

    aclient = null_agent._client

    version = await clienthelper.get_version()

    resources = []
    for j in range(10):
        resources.append(
            {
                "group": "root",
                "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
                "id": "std::testing::NullResource[vm1,name=file%d],v=%d" % (j, version),
                "owner": "root",
                "path": "/tmp/file%d" % j,
                "permissions": 644,
                "purged": False,
                "reload": False,
                "requires": [],
                "version": version,
            }
        )

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    resource_ids = [x["id"] for x in resources]

    # Start the deploy
    action_id = uuid.uuid4()
    now = datetime.now()
    result = await aclient.resource_action_update(
        environment, resource_ids, action_id, "deploy", now, status=const.ResourceState.deploying
    )
    assert result.code == 200

    # Get the status from a resource
    result = await client.get_resource(tid=environment, id=resource_ids[0], logs=True)
    assert result.code == 200
    logs = {x["action"]: x for x in result.result["logs"]}

    assert "deploy" in logs
    assert logs["deploy"]["finished"] is None
    assert logs["deploy"]["messages"] is None
    assert logs["deploy"]["changes"] is None

    # Send some logs
    result = await aclient.resource_action_update(
        environment,
        resource_ids,
        action_id,
        "deploy",
        status=const.ResourceState.deploying,
        messages=[data.LogLine.log(const.LogLevel.INFO, "Test log %(a)s %(b)s", a="a", b="b")],
    )
    assert result.code == 200

    # Get the status from a resource
    result = await client.get_resource(tid=environment, id=resource_ids[0], logs=True)
    assert result.code == 200
    logs = {x["action"]: x for x in result.result["logs"]}

    assert "deploy" in logs
    assert "messages" in logs["deploy"]
    assert len(logs["deploy"]["messages"]) == 1
    assert logs["deploy"]["messages"][0]["msg"] == "Test log a b"
    assert logs["deploy"]["finished"] is None
    assert logs["deploy"]["changes"] is None

    # Finish the deploy
    now = datetime.now()
    changes = {x: {"owner": {"old": "root", "current": "inmanta"}} for x in resource_ids}
    result = await aclient.resource_action_update(environment, resource_ids, action_id, "deploy", finished=now, changes=changes)
    assert result.code == 400

    result = await aclient.resource_action_update(
        environment, resource_ids, action_id, "deploy", status=const.ResourceState.deployed, finished=now, changes=changes
    )
    assert result.code == 200
    assert await clienthelper.done_count() == 10


async def test_get_resource_on_invalid_resource_id(server, client, environment) -> None:
    """
    Verify that a clear error message is returned when the resource version id passed to the
    get_resource() endpoint has an invalid structure.
    """
    invalid_resource_version_id = "invalid resource version id"
    result = await client.get_resource(tid=environment, id=invalid_resource_version_id)
    assert result.code == 400
    assert f"{invalid_resource_version_id} is not a valid resource version id" in result.result["message"]


@pytest.mark.parametrize("no_agent", [True])
async def test_clear_environment(client, server, clienthelper, environment):
    """
    Test clearing out an environment
    """
    version = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment, version=version, resources=[], unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    result = await client.get_environment(id=environment, versions=10)
    assert result.code == 200
    assert len(result.result["environment"]["versions"]) == 1

    # trigger multiple compiles and wait for them to complete in order to test cascade deletion of collapsed compiles (#2350)
    result = await client.notify_change_get(id=environment)
    assert result.code == 200
    result = await client.notify_change_get(id=environment)
    assert result.code == 200
    result = await client.notify_change_get(id=environment)
    assert result.code == 200

    async def compile_done():
        return (await client.is_compiling(environment)).code == 204

    await retry_limited(compile_done, 10)

    # Wait for env directory to appear
    slice = server.get_slice(SLICE_SERVER)
    env_dir = os.path.join(slice._server_storage["server"], environment, "compiler")

    while not os.path.exists(env_dir):
        await asyncio.sleep(0.1)

    result = await client.clear_environment(id=environment)
    assert result.code == 200

    assert not os.path.exists(env_dir)

    result = await client.get_environment(id=environment, versions=10)
    assert result.code == 200
    assert len(result.result["environment"]["versions"]) == 0


async def test_tokens(server_multi, client_multi, environment_multi, request):
    # Test using API tokens

    # Check the parameters of the 'server_multi' fixture
    if request.node.callspec.id in ["SSL", "Normal"]:
        # Generating tokens is not allowed if auth is not enabled
        return

    test_token = client_multi._transport_instance.token
    token = await client_multi.create_token(environment_multi, ["api"], idempotent=True)
    jot = token.result["token"]

    assert jot != test_token

    client_multi._transport_instance.token = jot

    # try to access a non environment call (global)
    result = await client_multi.list_environments()
    assert result.code == 403

    result = await client_multi.list_versions(environment_multi)
    assert result.code == 200

    token = await client_multi.create_token(environment_multi, ["agent"], idempotent=True)
    agent_jot = token.result["token"]

    client_multi._transport_instance.token = agent_jot
    result = await client_multi.list_versions(environment_multi)
    assert result.code == 403


async def test_token_without_auth(server, client, environment):
    """Generating a token when auth is not enabled is not allowed"""
    token = await client.create_token(environment, ["api"], idempotent=True)
    assert token.code == 400


async def test_batched_code_upload(
    server_multi, client_multi, sync_client_multi, environment_multi, agent_multi, snippetcompiler
):
    """Test uploading all code definitions at once"""
    snippetcompiler.setup_for_snippet("""
    import std::testing
    f = std::testing::NullResource(name="test")
    """)
    version, _ = await snippetcompiler.do_export_and_deploy(do_raise=False)

    code_manager = loader.CodeManager()

    for type_name, resource_definition in resources.resource.get_resources():
        code_manager.register_code(type_name, resource_definition)

    for type_name, handler_definition in handler.Commander.get_providers():
        code_manager.register_code(type_name, handler_definition)

    await asyncio.get_event_loop().run_in_executor(
        None, lambda: upload_code(sync_client_multi, environment_multi, version, code_manager)
    )

    for name, source_info in code_manager.get_types():
        assert len(source_info) >= 2
        for info in source_info:
            # fetch the code from the server
            response = await agent_multi._client.get_file(info.hash)
            assert response.code == 200
            source_code = base64.b64decode(response.result["content"])
            assert info.content == source_code


@pytest.mark.parametrize("auto_start_agent", [True])
async def test_resource_action_log(server, client, environment, clienthelper, snippetcompiler):
    await clienthelper.set_auto_deploy()

    snippetcompiler.setup_for_snippet(
        """\
        import std::testing

        std::testing::NullResource(name="network", agentname="internal")
        """,
        autostd=True,
    )

    version, _ = await snippetcompiler.do_export_and_deploy()

    await clienthelper.wait_for_released(version)
    await clienthelper.wait_for_deployed(version)
    resource_action_log = os.path.join(config.log_dir.get(), f"{opt.server_resource_action_log_prefix.get()}{environment}.log")
    print(resource_action_log)
    logging.root.warning("%s", resource_action_log)

    log = os.path.join(config.log_dir.get(), f"agent-{environment}.log")
    with open(log, "r") as fh:
        for line in fh:
            logging.warning(line)

    assert os.path.isfile(resource_action_log)
    assert os.stat(resource_action_log).st_size != 0
    with open(resource_action_log) as f:
        contents = f.read()
        parts = contents.split(" ")
        # Date and time
        parser.parse(f"{parts[0]} {parts[1]}")


async def test_invalid_sid(server, client, environment):
    """
    Verify that API endpoints, that should only be called by an agent, return an HTTP 400
    if they are called without a session id.
    """
    res = await client.discovered_resource_create(
        tid=environment,
        discovered_resource_id="test::Test[agent1,attr=val]",
        discovery_resource_id="test::Test[agent1,attr=other_val]",
    )
    assert res.code == 400
    assert res.result["message"] == "Invalid request: this is an agent to server call, it should contain an agent session id"


@pytest.mark.parametrize("tz_aware_timestamp", [True, False])
async def test_get_param(server, client, environment, tz_aware_timestamp: bool):
    config.Config.set("server", "tz-aware-timestamps", str(tz_aware_timestamp).lower())

    metadata = {"key1": "val1", "key2": "val2"}

    await client.set_param(environment, "param", ParameterSource.user, "val", "", metadata, False)
    await client.set_param(environment, "param2", ParameterSource.user, "val2", "", {"a": "b"}, False)

    res = await client.list_params(tid=environment, query={"key1": "val1"})
    assert res.code == 200

    def check_datetime_serialization(timestamp: str, tz_aware_timestamp):
        """
        Check that the given timestamp was serialized appropriately according to the server.tz-aware-timestamps option.
        """
        expected_format: str = const.TIME_ISOFMT
        if tz_aware_timestamp:
            expected_format += "%z"
        is_aware = datetime.strptime(timestamp, expected_format).tzinfo is not None
        assert is_aware == tz_aware_timestamp

    check_datetime_serialization(res.result["now"], tz_aware_timestamp)

    parameters = res.result["parameters"]
    assert len(parameters) == 1

    metadata_received = parameters[0]["metadata"]
    assert len(metadata_received) == 2
    for k, v in metadata.items():
        assert k in metadata_received
        assert metadata_received[k] == v

    res = await client.list_params(tid=environment, query={})
    assert res.code == 200
    parameters = res.result["parameters"]
    assert len(parameters) == 2


async def test_server_logs_address(server_config, caplog, async_finalizer):
    ibl = InmantaBootloader(configure_logging=True)
    with caplog.at_level(logging.INFO):
        async_finalizer.add(partial(ibl.stop, timeout=15))
        await ibl.start()

        client = Client("client")
        result = await client.create_project("env-test")
        assert result.code == 200
        address = "127.0.0.1"

        log_contains(caplog, "protocol.rest", logging.INFO, f"Server listening on {address}:")


class MockConnection:
    """
    Mock connection class to simulate an asyncpg connection.
    This class includes a close method to mimic closing a database connection.
    """

    async def close(self, timeout: int) -> None:
        return


@pytest.mark.parametrize("db_wait_time", ["20", "0"])
async def test_bootloader_db_wait(monkeypatch, tmpdir, caplog, db_wait_time: str) -> None:
    """
    Tests the Inmanta server bootloader's behavior with respect to waiting for the database to be ready before proceeding
    with the startup, based on the 'db_wait_time' configuration.
    """
    state_dir: str = tmpdir.mkdir("state_dir").strpath
    config.Config.set("database", "wait_time", db_wait_time)
    config.Config.set("config", "state-dir", state_dir)

    state = {"first_connect": True}

    async def mock_asyncpg_connect(*args, **kwargs) -> MockConnection:
        """
        Mock function to replace asyncpg.connect.
        Will raise an Exception on the first invocation.
        """
        if state["first_connect"]:
            state["first_connect"] = False
            raise Exception("Connection failure")
        else:
            return MockConnection()

    async def mock_start(self) -> None:
        """Mocks the call to self.restserver.start()."""
        return

    monkeypatch.setattr("inmanta.server.protocol.Server.start", mock_start)
    monkeypatch.setattr("asyncpg.connect", mock_asyncpg_connect)
    ibl: InmantaBootloader = InmantaBootloader(configure_logging=True)
    caplog.set_level(logging.INFO)
    caplog.clear()
    start_task: asyncio.Task = asyncio.create_task(ibl.start())
    await start_task

    if db_wait_time != "0":
        log_contains(caplog, "inmanta.server.bootloader", logging.INFO, "Waiting for database to be up.")
        log_contains(caplog, "inmanta.server.bootloader", logging.INFO, "Successfully connected to the database.")
    else:
        # If db_wait_time is "0", the wait_for_db method is not called,
        # hence "Successfully connected to the database." log message will not appear.
        log_doesnt_contain(caplog, "inmanta.server.bootloader", logging.INFO, "Successfully connected to the database.")

    log_contains(caplog, "inmanta.server.server", logging.INFO, "Starting server endpoint")

    await ibl.stop(timeout=20)


@pytest.mark.parametrize("db_wait_time", ["2", "0"])
async def test_bootloader_connect_running_db(server_config, postgres_db, caplog, db_wait_time: str):
    """
    Tests that the bootloader can connect to a database and can start for both wait_up values
    """
    config.Config.set("database", "wait_time", db_wait_time)
    ibl: InmantaBootloader = InmantaBootloader(configure_logging=True)
    caplog.clear()
    caplog.set_level(logging.INFO)
    await ibl.start()
    await ibl.stop(timeout=20)

    if db_wait_time != "0":
        log_contains(caplog, "inmanta.server.bootloader", logging.INFO, "Successfully connected to the database.")
    else:
        # If db_wait_time is "0", the wait_for_db method is not called,
        # hence "Successfully connected to the database." log message will not appear.
        log_doesnt_contain(caplog, "inmanta.server.bootloader", logging.INFO, "Successfully connected to the database.")
    log_contains(caplog, "inmanta.server.server", logging.INFO, "Starting server endpoint")


async def test_get_resource_actions(postgresql_client, client, clienthelper, server, environment, null_agent):
    """
    Test querying resource actions via the API
    """
    aclient = null_agent._client

    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    version = await clienthelper.get_version()

    resources = []
    for j in range(10):
        resources.append(
            {
                "group": "root",
                "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
                "id": "std::testing::NullResource[vm1,name=file%d],v=%d" % (j, version),
                "owner": "root",
                "path": "/tmp/file%d" % j,
                "permissions": 644,
                "purged": False,
                "reload": False,
                "requires": [],
                "version": version,
            }
        )

    #  adding a resource action with its change field set to "created" to test the get_resource_actions
    #  filtering on resources with changes

    rvid_r1_v1 = f"std::testing::NullResource[agent1,name=file200],v={version}"
    resources.append(
        {
            "group": "root",
            "hash": "89bf880a0dc5ffc1156c8d958b4960971370ee6a",
            "id": rvid_r1_v1,
            "owner": "root",
            "path": "/tmp/file200",
            "permissions": 644,
            "purged": False,
            "reload": False,
            "requires": [],
            "version": version,
        }
    )

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    resource_ids_nochange = [x["id"] for x in resources[0:-1]]
    resource_ids_created = [resources[-1]["id"]]

    # Start the deploy
    action_id = uuid.uuid4()
    now = datetime.now().astimezone()
    result = await aclient.resource_action_update(
        environment,
        resource_ids_created,
        action_id,
        "deploy",
        now,
        status=const.ResourceState.deploying,
        change=const.Change.created,
    )
    assert result.code == 200

    action_id = uuid.uuid4()
    result = await aclient.resource_action_update(
        environment, resource_ids_nochange, action_id, "deploy", now, status=const.ResourceState.deploying
    )
    assert result.code == 200

    # Get the status from a resource
    result = await client.get_resource_actions(tid=environment)
    assert result.code == 200
    assert len(result.result["data"]) == 3

    result = await client.get_resource_actions(tid=environment, attribute="path")
    assert result.code == 400
    result = await client.get_resource_actions(tid=environment, attribute_value="/tmp/file")
    assert result.code == 400
    result = await client.get_resource_actions(tid=environment, attribute="path", attribute_value="/tmp/file1")
    assert result.code == 200
    assert len(result.result["data"]) == 2
    # Query actions happening earlier than the deploy
    result = await client.get_resource_actions(tid=environment, last_timestamp=now)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["action"] == "store"
    # Query actions happening later than the start of the test case
    result = await client.get_resource_actions(tid=environment, first_timestamp=now - timedelta(minutes=1))
    assert result.code == 200
    assert len(result.result["data"]) == 3
    result = await client.get_resource_actions(tid=environment, first_timestamp=now - timedelta(minutes=1), last_timestamp=now)
    assert result.code == 400
    result = await client.get_resource_actions(tid=environment, action_id=action_id)
    assert result.code == 400
    result = await client.get_resource_actions(tid=environment, first_timestamp=now - timedelta(minutes=1), action_id=action_id)
    assert result.code == 200
    assert len(result.result["data"]) == 3

    exclude_changes = [const.Change.nochange.value, const.Change.created.value]
    result = await client.get_resource_actions(tid=environment, exclude_changes=exclude_changes)
    assert result.code == 200
    assert len(result.result["data"]) == 0

    exclude_changes = []
    result = await client.get_resource_actions(tid=environment, exclude_changes=exclude_changes)
    assert result.code == 200
    assert len(result.result["data"]) == 3

    exclude_changes = [const.Change.nochange.value]
    result = await client.get_resource_actions(tid=environment, exclude_changes=exclude_changes)
    assert result.code == 200
    assert len(result.result["data"]) == 1  # only one of the 3 resource_actions has change != nochange

    exclude_changes = ["error"]
    result = await client.get_resource_actions(tid=environment, exclude_changes=exclude_changes)
    assert result.code == 400
    assert "Failed to validate argument" in result.result["message"]


async def test_resource_action_pagination(postgresql_client, client, clienthelper, server, agent):
    """Test querying resource actions via the API, including the pagination links."""
    project = data.Project(name="test")
    await project.insert()

    env = data.Environment(name="dev", project=project.id, repo_url="", repo_branch="")
    await env.insert()

    # Add multiple versions of model
    for i in range(1, 12):
        cm = data.ConfigurationModel(
            environment=env.id,
            version=i,
            date=datetime.now(),
            total=1,
            version_info={},
            is_suitable_for_partial_compiles=False,
        )
        await cm.insert()
        res1 = data.Resource.new(
            environment=env.id,
            resource_version_id="std::testing::NullResource[agent1,name=motd],v=%s" % str(i),
            status=const.ResourceState.deployed,
            attributes={"attr": [{"a": 1, "b": "c"}], "path": "/etc/motd"},
        )
        await res1.insert()

    # Add resource actions for motd
    motd_first_start_time = datetime.now()
    earliest_action_id = uuid.uuid4()
    resource_action = data.ResourceAction(
        environment=env.id,
        version=1,
        resource_version_ids=[f"std::testing::NullResource[agent1,name=motd],v={1}"],
        action_id=earliest_action_id,
        action=const.ResourceAction.deploy,
        started=motd_first_start_time - timedelta(minutes=1),
    )
    await resource_action.insert()
    resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=1)])
    await resource_action.save()

    action_ids_with_the_same_timestamp = []
    for i in range(2, 7):
        action_id = uuid.uuid4()
        action_ids_with_the_same_timestamp.append(action_id)
        resource_action = data.ResourceAction(
            environment=env.id,
            version=i,
            resource_version_ids=[f"std::testing::NullResource[agent1,name=motd],v={i}"],
            action_id=action_id,
            action=const.ResourceAction.deploy,
            started=motd_first_start_time,
        )
        await resource_action.insert()
        resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=i)])
        await resource_action.save()
    action_ids_with_the_same_timestamp = sorted(action_ids_with_the_same_timestamp, reverse=True)
    later_action_id = uuid.uuid4()
    resource_action = data.ResourceAction(
        environment=env.id,
        version=6,
        resource_version_ids=[f"std::testing::NullResource[agent1,name=motd],v={6}"],
        action_id=later_action_id,
        action=const.ResourceAction.deploy,
        started=motd_first_start_time + timedelta(minutes=6),
    )
    await resource_action.insert()
    resource_action.add_logs([data.LogLine.log(logging.INFO, "Successfully stored version %(version)d", version=6)])
    await resource_action.save()

    result = await client.get_resource_actions(
        tid=env.id,
        resource_type="std::testing::NullResource",
        attribute="path",
        attribute_value="/etc/motd",
        last_timestamp=motd_first_start_time + timedelta(minutes=7),
        limit=2,
    )
    assert result.code == 200
    resource_actions = result.result["data"]
    expected_action_ids = [later_action_id] + action_ids_with_the_same_timestamp[:1]
    assert [uuid.UUID(resource_action["action_id"]) for resource_action in resource_actions] == expected_action_ids

    # Use the next link for pagination
    next_page = result.result["links"]["next"]
    port = opt.server_bind_port.get()
    base_url = f"http://localhost:{port}"
    url = f"{base_url}{next_page}"
    client = AsyncHTTPClient()
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(env.id)},
    )
    response = await client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    second_page_action_ids = [uuid.UUID(resource_action["action_id"]) for resource_action in response["data"]]
    assert second_page_action_ids == action_ids_with_the_same_timestamp[1:3]
    next_page = response["links"]["next"]
    url = f"{base_url}{next_page}"
    request.url = url
    response = await client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    third_page_action_ids = [uuid.UUID(resource_action["action_id"]) for resource_action in response["data"]]
    assert third_page_action_ids == action_ids_with_the_same_timestamp[3:5]
    # Go back to the previous page
    prev_page = response["links"]["prev"]
    url = f"{base_url}{prev_page}"
    request.url = url
    response = await client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    action_ids = [uuid.UUID(resource_action["action_id"]) for resource_action in response["data"]]
    assert action_ids == second_page_action_ids
    # And back to the third
    prev_page = response["links"]["next"]
    url = f"{base_url}{prev_page}"
    request.url = url
    response = await client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    action_ids = [uuid.UUID(resource_action["action_id"]) for resource_action in response["data"]]
    assert action_ids == third_page_action_ids


@pytest.mark.parametrize("no_agent", [True])
@pytest.mark.parametrize("method_to_use", ["send_in_progress", "resource_action_update"])
async def test_send_in_progress(server, client, environment, agent, method_to_use: str):
    """
    Ensure that the `ToDbUpdateManager.send_in_progress()` method and the `resource_action_update()` API endpoint do the same
    when a new deployment is reported.
    """
    env_id = uuid.UUID(environment)

    model_version = 1
    cm = data.ConfigurationModel(
        environment=env_id,
        version=model_version,
        date=datetime.now().astimezone(),
        total=1,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    model_version = 1
    rvid_r1 = "std::testing::NullResource[agent1,name=file1]"
    rvid_r2 = "std::testing::NullResource[agent1,name=file2]"
    rvid_r3 = "std::testing::NullResource[agent1,name=file3]"
    rvid_r1_v1 = f"{rvid_r1},v={model_version}"
    rvid_r2_v1 = f"{rvid_r2},v={model_version}"
    rvid_r3_v1 = f"{rvid_r3},v={model_version}"

    async def make_resource_with_last_non_deploying_status(
        status: const.ResourceState,
        last_non_deploying_status: const.NonDeployingResourceState,
        resource_version_id: str,
        attributes: dict[str, object],
        version: int,
    ) -> None:
        r1 = data.Resource.new(
            environment=env_id,
            status=status,
            resource_version_id=resource_version_id,
            attributes=attributes,
        )
        await r1.insert()
        await data.ResourcePersistentState.populate_for_version(environment=uuid.UUID(environment), model_version=version)
        await r1.update_persistent_state(last_deploy=datetime.now(tz=UTC), last_non_deploying_status=last_non_deploying_status)

    await make_resource_with_last_non_deploying_status(
        status=const.ResourceState.skipped,
        last_non_deploying_status=const.NonDeployingResourceState.skipped,
        resource_version_id=rvid_r1_v1,
        attributes={"purge_on_delete": False, "requires": [rvid_r2, rvid_r3]},
        version=model_version,
    )
    await make_resource_with_last_non_deploying_status(
        status=const.ResourceState.deployed,
        last_non_deploying_status=const.NonDeployingResourceState.deployed,
        resource_version_id=rvid_r2_v1,
        attributes={"purge_on_delete": False, "requires": []},
        version=model_version,
    )
    await make_resource_with_last_non_deploying_status(
        status=const.ResourceState.failed,
        last_non_deploying_status=const.NonDeployingResourceState.failed,
        resource_version_id=rvid_r3_v1,
        attributes={"purge_on_delete": False, "requires": []},
        version=model_version,
    )

    action_id = uuid.uuid4()

    if method_to_use == "send_in_progress":
        update_manager = persistence.ToDbUpdateManager(client, env_id)
        await update_manager.send_in_progress(action_id, resources.Id.parse_id(rvid_r1_v1))
    else:
        await agent._client.resource_action_update(
            tid=env_id,
            resource_ids=[rvid_r1_v1],
            action_id=action_id,
            action=const.ResourceAction.deploy,
            started=datetime.now().astimezone(),
            status=const.ResourceState.deploying,
        )

    # Ensure that both API calls result in the same behavior
    result = await client.get_resource_actions(tid=env_id)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    resource_action = result.result["data"][0]
    assert resource_action["environment"] == str(env_id)
    assert resource_action["version"] == model_version
    assert resource_action["resource_version_ids"] == [rvid_r1_v1]
    assert resource_action["action_id"] == str(action_id)
    assert resource_action["action"] == const.ResourceAction.deploy
    assert resource_action["started"] is not None
    assert resource_action["finished"] is None
    assert resource_action["status"] == const.ResourceState.deploying
    assert resource_action["changes"] is None
    assert resource_action["change"] is None


async def test_send_in_progress_action_id_conflict(server, client, environment, agent):
    """
    Ensure proper error handling when the same action_id is provided twice to the `ToDbUpdateManager.send_in_progress()` method.
    """
    env_id = uuid.UUID(environment)

    model_version = 1
    cm = data.ConfigurationModel(
        environment=env_id,
        version=model_version,
        date=datetime.now().astimezone(),
        total=1,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    model_version = 1
    rvid_r1_v1 = ResourceVersionIdStr(f"std::testing::NullResource[agent1,name=file1],v={model_version}")

    await data.Resource.new(
        environment=env_id,
        status=const.ResourceState.skipped,
        resource_version_id=rvid_r1_v1,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()

    action_id = uuid.uuid4()
    update_manager = persistence.ToDbUpdateManager(client, env_id)

    async def execute_send_in_progress(expect_exception: bool, resulting_nr_resource_actions: int) -> None:
        try:
            await update_manager.send_in_progress(action_id, resources.Id.parse_id(rvid_r1_v1))
        except ValueError:
            assert expect_exception
        else:
            assert not expect_exception

        result = await client.get_resource_actions(tid=env_id)
        assert result.code == 200
        assert len(result.result["data"]) == resulting_nr_resource_actions

    await execute_send_in_progress(expect_exception=False, resulting_nr_resource_actions=1)
    await execute_send_in_progress(expect_exception=True, resulting_nr_resource_actions=1)


@pytest.mark.parametrize(
    "method_to_use",
    ["send_deploy_done", "resource_action_update"],
)
async def test_send_deploy_done(server, client, environment, null_agent, caplog, method_to_use, clienthelper):
    """
    Ensure that the `send_deploy_done` method behaves in the same way as the `resource_action_update` endpoint
    when the finished field is not None.
    """
    result = await client.set_setting(environment, "auto_deploy", True)
    assert result.code == 200

    env_id = uuid.UUID(environment)
    model_version = await clienthelper.get_version()
    rid_r1 = ResourceIdStr("std::testing::NullResource[agent1,name=file1]")
    rvid_r1_v1 = ResourceVersionIdStr(f"{rid_r1},v={model_version}")
    attributes_r1 = {
        "name": "file1",
        "id": f"std::testing::NullResource[agent1,name=file1],v={model_version}",
        "version": model_version,
        "purge_on_delete": False,
        "purged": True,
        "requires": [],
    }
    await clienthelper.put_version_simple(resources=[attributes_r1], version=model_version, wait_for_released=True)

    # Add parameter for resource
    parameter_id = "test_param"
    result = await client.set_param(
        tid=env_id,
        id=parameter_id,
        source=const.ParameterSource.user,
        value="val",
        resource_id="std::testing::NullResource[agent1,name=file1]",
    )
    assert result.code == 200

    update_manager = persistence.ToDbUpdateManager(client, env_id)
    action_id = uuid.uuid4()
    await update_manager.send_in_progress(action_id, resources.Id.parse_id(rvid_r1_v1))

    # Assert initial state
    result = await client.get_resource_actions(tid=env_id)
    assert result.code == 200, result.result
    deploy_resource_actions = [r for r in result.result["data"] if r["action"] == const.ResourceAction.deploy.value]
    assert len(deploy_resource_actions) == 1
    resource_action = deploy_resource_actions[0]
    assert resource_action["environment"] == str(env_id)
    assert resource_action["version"] == model_version
    assert resource_action["resource_version_ids"] == [rvid_r1_v1]
    assert resource_action["action_id"] == str(action_id)
    assert resource_action["action"] == const.ResourceAction.deploy
    assert resource_action["started"] is not None
    assert resource_action["finished"] is None
    assert resource_action["status"] == const.ResourceState.deploying
    assert resource_action["changes"] is None
    assert resource_action["change"] is None

    result = await client.get_resource(tid=env_id, id=rvid_r1_v1)
    assert result.code == 200, result.result

    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        # Mark deployment as done
        now = datetime.now().astimezone()
        messages = [
            data.LogLine.log(level=const.LogLevel.DEBUG, msg="message", timestamp=now, keyword=123, none=None),
            data.LogLine.log(level=const.LogLevel.INFO, msg="test", timestamp=now),
        ]
        if method_to_use == "send_deploy_done":
            await update_manager.send_deploy_done(
                attribute_hash=util.make_attribute_hash(resource_id=rid_r1, attributes=attributes_r1),
                result=executor.DeployReport(
                    rvid=rvid_r1_v1,
                    action_id=action_id,
                    resource_state=const.HandlerResourceState.deployed,
                    messages=messages,
                    changes={"attr1": AttributeStateChange(current=None, desired="test")},
                    change=const.Change.purged,
                ),
                state=state.ResourceState(
                    compliance=state.Compliance.COMPLIANT,
                    last_deploy_result=state.DeployResult.DEPLOYED,
                    blocked=state.Blocked.NOT_BLOCKED,
                    last_deployed=now,
                ),
                started=now,
                finished=now,
            )
        else:
            result = await null_agent._client.resource_action_update(
                tid=env_id,
                resource_ids=[rvid_r1_v1],
                action_id=action_id,
                action=const.ResourceAction.deploy,
                started=None,
                finished=now,
                status=const.ResourceState.deployed,
                messages=messages,
                changes={rvid_r1_v1: {"attr1": AttributeStateChange(current=None, desired="test")}},
                change=const.Change.purged,
                send_events=True,
            )
            assert result.code == 200, result.result

    result = await client.get_resource_actions(tid=env_id)
    assert result.code == 200, result.result
    deploy_resource_actions = [r for r in result.result["data"] if r["action"] == const.ResourceAction.deploy.value]
    assert len(deploy_resource_actions) == 1
    resource_action = deploy_resource_actions[0]
    assert resource_action["environment"] == str(env_id)
    assert resource_action["version"] == model_version
    assert resource_action["resource_version_ids"] == [rvid_r1_v1]
    assert resource_action["action_id"] == str(action_id)
    assert resource_action["action"] == const.ResourceAction.deploy
    assert resource_action["started"] is not None
    assert resource_action["finished"] is not None

    expected_timestamp: str
    if opt.server_tz_aware_timestamps.get():
        expected_timestamp = now.astimezone().isoformat(timespec="microseconds")
    else:
        expected_timestamp = now.astimezone(timezone.utc).replace(tzinfo=None).isoformat()

    expected_resource_action_messages = [
        {
            "level": const.LogLevel.DEBUG.name,
            "msg": "message",
            "args": [],
            "kwargs": {"keyword": 123, "none": None},
            "timestamp": expected_timestamp,
        },
        {
            "level": const.LogLevel.INFO.name,
            "msg": "test",
            "args": [],
            "kwargs": {},
            "timestamp": expected_timestamp,
        },
    ]
    assert resource_action["messages"] == expected_resource_action_messages
    assert resource_action["status"] == const.ResourceState.deployed
    assert resource_action["changes"] == {rvid_r1_v1: {"attr1": AttributeStateChange(current=None, desired="test").dict()}}
    assert resource_action["change"] == const.Change.purged.value

    result = await client.resource_details(tid=env_id, rid=rid_r1)
    assert result.code == 200, result.result
    assert result.result["data"]["status"] == const.ResourceState.deployed

    result = await client.get_version(tid=env_id, id=1)
    assert result.code == 200, result.result

    # parameter was deleted due to purge operation
    result = await client.list_params(tid=env_id)
    assert result.code == 200
    assert len(result.result["parameters"]) == 0

    # A new send_deploy_done call for the same action_id should result in a ValueError
    with pytest.raises(ValueError):
        await update_manager.send_deploy_done(
            attribute_hash=util.make_attribute_hash(resource_id=rid_r1, attributes=attributes_r1),
            result=executor.DeployReport(
                rvid=rvid_r1_v1,
                action_id=action_id,
                resource_state=const.HandlerResourceState.deployed,
                messages=[],
                changes={"attr1": AttributeStateChange(current="test", desired="test2")},
                change=const.Change.created,
            ),
            state=state.ResourceState(
                compliance=state.Compliance.COMPLIANT,
                last_deploy_result=state.DeployResult.DEPLOYED,
                blocked=state.Blocked.NOT_BLOCKED,
                last_deployed=datetime.now().astimezone(),
            ),
            started=datetime.now().astimezone(),
            finished=datetime.now().astimezone(),
        )


async def test_send_deploy_done_error_handling(server, client, environment, agent):
    env_id = uuid.UUID(environment)
    update_manager = persistence.ToDbUpdateManager(client, uuid.UUID(environment))

    model_version = 1
    cm = data.ConfigurationModel(
        environment=env_id,
        version=model_version,
        date=datetime.now().astimezone(),
        total=1,
        version_info={},
        is_suitable_for_partial_compiles=False,
    )
    await cm.insert()

    rvid_r1_v1 = ResourceVersionIdStr(f"std::testing::NullResource[agent1,name=file1],v={model_version}")

    # Resource doesn't exist
    with pytest.raises(ValueError) as exec_info:
        await update_manager.send_deploy_done(
            attribute_hash="",
            result=executor.DeployReport(
                rvid=rvid_r1_v1,
                action_id=uuid.uuid4(),
                resource_state=const.HandlerResourceState.deployed,
                messages=[],
                changes={},
                change=const.Change.nochange,
            ),
            state=state.ResourceState(
                compliance=state.Compliance.COMPLIANT,
                last_deploy_result=state.DeployResult.DEPLOYED,
                blocked=state.Blocked.NOT_BLOCKED,
                last_deployed=datetime.now().astimezone(),
            ),
            started=datetime.now().astimezone(),
            finished=datetime.now().astimezone(),
        )
    assert "The resource with the given id does not exist in the given environment" in str(exec_info.value)

    # Create resource
    await data.Resource.new(
        environment=env_id,
        status=const.ResourceState.available,
        resource_version_id=rvid_r1_v1,
        attributes={"purge_on_delete": False, "requires": []},
    ).insert()

    # Resource action doesn't exist
    with pytest.raises(ValueError) as exec_info:
        await update_manager.send_deploy_done(
            attribute_hash="",
            result=executor.DeployReport(
                rvid=rvid_r1_v1,
                action_id=uuid.uuid4(),
                resource_state=const.HandlerResourceState.deployed,
                messages=[],
                changes={},
                change=const.Change.nochange,
            ),
            state=state.ResourceState(
                compliance=state.Compliance.COMPLIANT,
                last_deploy_result=state.DeployResult.DEPLOYED,
                blocked=state.Blocked.NOT_BLOCKED,
                last_deployed=datetime.now().astimezone(),
            ),
            started=datetime.now().astimezone(),
            finished=datetime.now().astimezone(),
        )
    assert "No resource action exists for action_id" in str(exec_info.value)


async def test_start_location_no_redirect(server):
    """
    Ensure that there is no redirection for the "start" location. (issue #3497)
    """
    port = opt.server_bind_port.get()
    base_url = f"http://localhost:{port}/"
    http_client = AsyncHTTPClient()
    request = HTTPRequest(
        url=base_url,
    )
    response = await http_client.fetch(request, raise_error=False)
    assert base_url == response.effective_url


@pytest.mark.parametrize("path", ["", "/", "/test"])
async def test_redirect_dashboard_to_console(server, path):
    """
    Ensure that there is a redirection from the dashboard to the webconsole
    """
    port = opt.server_bind_port.get()
    base_url = f"http://localhost:{port}/dashboard{path}"
    result_url = f"http://localhost:{port}/console{path}"
    http_client = AsyncHTTPClient()
    request = HTTPRequest(
        url=base_url,
    )
    response = await http_client.fetch(request, raise_error=False)
    assert result_url == response.effective_url


@pytest.mark.parametrize("env1_halted", [True, False])
@pytest.mark.parametrize("env2_halted", [True, False])
async def test_cleanup_old_agents(server, client, env1_halted, env2_halted):
    """
    This test is testing the functionality of cleaning up old agents in the database.
    The test creates 2 environments and adds agents with various properties (some used in a version
    and some with the primary ID set), and then tests that the cleanup function correctly removes
    only the agents that meet the criteria for deletion. Also verifies that only agents in envs that
    are not halted are cleaned up
    """

    project = data.Project(name="test")
    await project.insert()

    env1 = data.Environment(name="env1", project=project.id)
    await env1.insert()
    env2 = data.Environment(name="env2", project=project.id)
    await env2.insert()

    if env1_halted:
        result = await client.halt_environment(env1.id)
        assert result.code == 200
    if env2_halted:
        result = await client.halt_environment(env2.id)
        assert result.code == 200

    process_sid = uuid.uuid4()
    await data.AgentProcess(hostname="localhost-dummy", environment=env1.id, sid=process_sid, last_seen=datetime.now()).insert()

    id_primary = uuid.uuid4()
    await data.AgentInstance(id=id_primary, process=process_sid, name="dummy-instance", tid=env1.id).insert()

    version = 1
    await data.ConfigurationModel(
        environment=env1.id,
        version=version,
        date=datetime.now(),
        total=1,
        released=True,
        version_info={},
        is_suitable_for_partial_compiles=False,
    ).insert()

    name = "file1"
    resource_id = f"std::testing::NullResource[agent4,name={name}]"

    await data.Resource.new(
        environment=env1.id, resource_version_id=ResourceVersionIdStr(f"{resource_id},v={version}"), attributes={"name": name}
    ).insert()

    # should get purged
    await data.Agent(
        environment=env1.id,
        name="agent1",
        paused=False,
        id_primary=None,
    ).insert()
    # should not get purged as the id_primary is set -> not down
    await data.Agent(environment=env1.id, name="agent2", paused=False, id_primary=id_primary).insert()
    # should not get purged as it is used in a version of the ConfigurationModel
    await data.Agent(
        environment=env1.id,
        name="agent4",
        paused=False,
        id_primary=None,
    ).insert()
    # agent with "agent2" as name but in another env will get purged:
    await data.Agent(
        environment=env2.id,
        name="agent2",
        paused=False,
        id_primary=None,
    ).insert()
    # agent with "agent1" as name but in another env will get purged:
    await data.Agent(
        environment=env2.id,
        name="agent1",
        paused=False,
        id_primary=None,
    ).insert()

    agents_before_purge = await data.Agent.get_list()
    assert len(agents_before_purge) == 5

    await server.get_slice(SLICE_ORCHESTRATION)._purge_versions()

    agents_after_purge = [(agent.environment, agent.name) for agent in await data.Agent.get_list()]
    number_agents_env1_after_purge = 3 if env1_halted else 2
    number_agents_env2_after_purge = 2 if env2_halted else 0
    assert len(agents_after_purge) == number_agents_env1_after_purge + number_agents_env2_after_purge
    if not (env1_halted or env2_halted):
        expected_agents_after_purge = [
            (env1.id, "agent2"),
            (env1.id, "agent4"),
        ]
        assert sorted(agents_after_purge) == sorted(expected_agents_after_purge)


async def test_serialization_attributes_of_resource_to_api(client, server, environment, clienthelper, null_agent) -> None:
    """
    Due to a bug, the version of a resource was always included in the attribute dictionary.
    This issue has been patched in the database, but at the API boundary we still serve the version
    field in the attributes dictionary for backwards compatibility. This test verifies that behavior.
    """
    version = await clienthelper.get_version()
    resource_id = "test::Resource[agent1,key=key1]"
    resources = [
        {
            "id": f"{resource_id},v={version}",
            "att": "val",
            "version": version,
            "send_event": False,
            "purged": False,
            "requires": [],
        }
    ]
    attributes_on_api = {k: v for k, v in resources[0].items() if k != "id"}
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=get_compiler_version(),
    )
    assert result.code == 200

    result = await client.release_version(tid=environment, id=version)
    assert result.code == 200

    # Verify that the version field is not present in the attributes dictionary in the database.
    result = await data.Resource.get_list()
    assert len(result) == 1
    resource_dao = result[0]
    assert "version" not in resource_dao.attributes

    # Ensure that the serialization of the resource DAO contains the version field in the attributes dictionary
    resource_dto = resource_dao.to_dto()
    assert resource_dto.attributes["version"] == version
    resource_dct = resource_dao.to_dict()
    assert resource_dct["attributes"]["version"] == version

    # Retrieve the resource via the API and ensure that the version field is present in the attributes dictionary
    result = await client.resource_history(environment, resource_id)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0]["attributes"] == attributes_on_api

    result = await client.versioned_resource_details(tid=environment, version=version, rid=resource_id)
    assert result.code == 200
    assert result.result["data"]["attributes"] == attributes_on_api, result.result["data"]

    result = await client.resource_details(tid=environment, rid=resource_id)
    assert result.code == 200
    assert result.result["data"]["attributes"] == attributes_on_api


@pytest.mark.parametrize("v1_partial,v2_partial", [(False, False), (False, True)])
# the other two cases require a race condition to trigger
# as put_partial determines its own version number
async def test_put_stale_version(client, server, environment, clienthelper, caplog, v1_partial, v2_partial):
    """Put a version in with auto deploy on that is already stale"""
    await client.set_setting(environment, AUTO_DEPLOY, True)

    v0 = await clienthelper.get_version()
    v1 = await clienthelper.get_version()
    v2 = await clienthelper.get_version()

    async def put_version(version: int) -> int:
        partial = (version == v1 and v1_partial) or (version == v2 and v2_partial)

        if partial:
            version = 0

        resource_id = "test::Resource[agent1,key=key1]"
        resources = [
            {
                "id": f"{resource_id},v={version}",
                "att": "val",
                "version": version,
                "send_event": False,
                "purged": False,
                "requires": [],
            }
        ]

        if partial:
            result = await client.put_partial(
                tid=environment,
                resources=resources,
                unknowns=[],
                version_info={},
            )
            assert result.code == 200
            return result.result["data"]
        else:
            result = await client.put_version(
                tid=environment,
                version=version,
                resources=resources,
                unknowns=[],
                version_info={},
                compiler_version=get_compiler_version(),
            )
            assert result.code == 200
            return version

    v0 = await put_version(v0)
    await retry_limited(functools.partial(clienthelper.is_released, v0), timeout=1, interval=0.05)
    v2 = await put_version(v2)
    await retry_limited(functools.partial(clienthelper.is_released, v2), timeout=1, interval=0.05)
    v1 = await put_version(v1)
    # give it time to attempt to be release
    await asyncio.sleep(0.1)
    assert not await clienthelper.is_released(v1)


async def test_set_fact_v2(
    server,
    client,
    clienthelper,
    environment,
):
    """
    Test the set_fact endpoint. First create a fact with expires set to true.
    Then set expires to false for the same fact.
    """
    version = await clienthelper.get_version()
    resource_id = "test::MyDiscoveryResource[discovery_agent,key=key1]"
    resource_version_id = f"{resource_id},v={version}"

    resources = [
        {
            "key": "key1",
            "id": resource_version_id,
            "send_event": True,
            "purged": False,
            "requires": [],
        }
    ]

    # Put a new version containing a resource with id=resource_id, to make sure the fact is not cleaned up.
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        unknowns=[],
        version_info={},
        compiler_version=util.get_compiler_version(),
    )
    assert result.code == 200

    result = await client.set_fact(
        tid=environment,
        name="test",
        source=ParameterSource.fact.value,
        value="value1",
        resource_id="test::MyDiscoveryResource[discovery_agent,key=key1]",
    )

    assert result.code == 200
    fact = result.result["data"]
    assert fact["expires"] is True

    result = await client.get_facts(
        tid=environment,
        rid="test::MyDiscoveryResource[discovery_agent,key=key1]",
    )
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0] == fact

    result = await client.set_fact(
        tid=environment,
        name="test",
        source=ParameterSource.fact.value,
        value="value1",
        resource_id="test::MyDiscoveryResource[discovery_agent,key=key1]",
        expires=False,
    )
    assert result.code == 200
    fact = result.result["data"]
    assert fact["expires"] is False

    result = await client.get_facts(
        tid=environment,
        rid="test::MyDiscoveryResource[discovery_agent,key=key1]",
    )
    assert result.code == 200
    assert len(result.result["data"]) == 1
    assert result.result["data"][0] == fact


async def test_set_param_v2(server, client, environment):
    """
    Test the set_parameter endpoint. Create a parameters and verify that expires is set to false.
    Also test we can modify it and create a second one.
    """

    result = await client.set_parameter(
        tid=environment,
        name="param",
        source=ParameterSource.user,
        value="val",
        metadata={"key1": "val1", "key2": "val2"},
        recompile=False,
    )

    assert result.code == 200

    res = await client.list_params(tid=environment, query={})
    assert res.code == 200
    parameters = res.result["parameters"]
    assert len(parameters) == 1
    assert parameters[0]["name"] == "param"
    assert parameters[0]["value"] == "val"
    assert parameters[0]["expires"] is False

    await client.set_parameter(
        tid=environment,
        name="param",
        source=ParameterSource.user,
        value="val2",
        metadata={"key1": "val1", "key2": "val2"},
        recompile=False,
    )
    assert result.code == 200

    res = await client.list_params(tid=environment, query={})
    assert res.code == 200
    parameters = res.result["parameters"]
    assert len(parameters) == 1
    assert parameters[0]["name"] == "param"
    assert parameters[0]["value"] == "val2"
    assert parameters[0]["expires"] is False

    await client.set_parameter(
        tid=environment, name="param2", source=ParameterSource.user, value="val3", metadata={}, recompile=False
    )
    assert result.code == 200

    res = await client.list_params(tid=environment, query={})
    assert res.code == 200
    parameters = res.result["parameters"]
    assert len(parameters) == 2


async def test_delete_active_version(client, clienthelper, server, environment, null_agent):
    """
    Test that the active version cannot be deleted
    """
    version = await clienthelper.get_version()
    assert version == 1
    res1 = "test::Resource[agent1,key=key1]"
    res2 = "test::Resource[agent1,key=key2]"
    resources = [
        {"key": "key1", "value": "value", "id": f"{res1},v={version}", "requires": [], "purged": False, "send_event": False},
        {"key": "key2", "value": "value", "id": f"{res2},v={version}", "requires": [], "purged": False, "send_event": False},
    ]

    await clienthelper.put_version_simple(resources, version)

    result = await client.release_version(
        environment, version, push=False, agent_trigger_method=const.AgentTriggerMethod.push_full_deploy
    )
    assert result.code == 200

    # Remove version 1
    result = await client.delete_version(tid=environment, id=version)
    assert result.code == 400
    assert result.result["message"] == "Invalid request: Cannot delete the active version"
