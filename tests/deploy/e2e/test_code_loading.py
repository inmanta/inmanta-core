"""
Copyright 2022 Inmanta

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
import logging
import pathlib
import uuid
from collections.abc import Sequence
from logging import DEBUG

import py
import pytest

from inmanta import data, protocol
from inmanta.agent import executor
from inmanta.agent.agent_new import Agent
from inmanta.agent.code_manager import CodeManager, CouldNotResolveCode
from inmanta.agent.in_process_executor import InProcessExecutorManager
from inmanta.data import AgentModules, InmantaModule, ModuleFiles, PipConfig
from inmanta.data.model import ModuleSourceMetadata
from inmanta.env import process_env
from inmanta.loader import InmantaModule as InmantaModuleDTO
from inmanta.protocol import Client
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.server.server import Server
from inmanta.util import hash_file
from sqlalchemy.dialects.postgresql import insert
from utils import ClientHelper, DummyCodeManager, log_index, retry_limited, wait_until_deployment_finishes

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="function")
async def agent(server, environment, deactive_venv):
    """Construct an agent that can execute using the resource container"""
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    a = Agent(environment)
    loop = asyncio.get_running_loop()
    executor = InProcessExecutorManager(
        environment,
        a._client,
        loop,
        LOGGER,
        a.thread_pool,
        str(pathlib.Path(a._storage["executors"]) / "code"),
        str(pathlib.Path(a._storage["executors"]) / "venvs"),
        True,
    )
    a.executor_manager = executor
    a.scheduler.executor_manager = executor
    a.scheduler.code_manager = DummyCodeManager()

    await a.start()

    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


async def upload_file(client: protocol.Client, content: str) -> str:
    content = content.encode()

    _hash = hash_file(content)
    body = base64.b64encode(content).decode("ascii")

    res = await client.upload_file(id=_hash, content=body)
    assert res.code == 200
    return _hash


@pytest.mark.slowtest
async def test_agent_installs_dependency_containing_extras(
    server_pre_start,
    server,
    client,
    index_with_pkgs_containing_optional_deps: str,
    clienthelper,
    environment,
    agent,
) -> None:
    """
    Test whether the agent code loading works correctly when a python dependency is provided that contains extras.
    """

    source_content = "file_content"
    _hash = await upload_file(client, source_content)

    module_version_info = {
        "test": InmantaModuleDTO(
            name="test",
            version="abc",
            files_in_module=[
                ModuleSourceMetadata(
                    name="inmanta_plugins.test",
                    is_byte_code=False,
                    hash_value=_hash,
                )
            ],
            requirements=["pkg[optional-a]"],
            for_agents=["agent1"],
        )
    }

    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        }
    ]
    res = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        pip_config=PipConfig(index_url=index_with_pkgs_containing_optional_deps),
        module_version_info=module_version_info,
    )
    assert res.code == 200

    codemanager = CodeManager()

    install_spec = await codemanager.get_code(
        environment=uuid.UUID(environment),
        model_version=version,
        agent_name="agent1",
    )

    assert install_spec[0].blueprint.sources[0].source == source_content.encode()
    await agent.executor_manager.get_executor("agent1", "localhost", install_spec)

    installed_packages = process_env.get_installed_packages()

    def check_packages(package_list: Sequence[str], must_contain: set[str], must_not_contain: set[str]) -> None:
        """
        Iterate over <package_list> and check:
         - all elements from <must_contain> are present
         - no element from <must_not_contain> are present
        """
        for package in package_list:
            assert package not in must_not_contain
            if package in must_contain:
                must_contain.remove(package)

        assert not must_contain

    check_packages(package_list=installed_packages, must_contain={"pkg", "dep-a"}, must_not_contain={"dep-b", "dep-c"})


async def test_get_code(
    server,
    client,
) -> None:
    """
    Test the code_manager get_code method.

    1) Set up some data in the agent_modules, inmanta_modules and module_files tables.
    2) Test data retrieval with the get_code method.
    """
    codemanager = CodeManager()

    # Create project
    result = await client.create_project("test_project")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    # Create environment
    result = await client.create_environment(project_id=project_id, name="env_1")
    env_id = result.result["environment"]["id"]
    assert result.code == 200

    clienthelper = ClientHelper(client, env_id)
    v1 = await clienthelper.get_version()
    v2 = await clienthelper.get_version()
    v3 = await clienthelper.get_version()
    await clienthelper.put_version_simple(resources=[], version=v1, wait_for_released=False)
    await clienthelper.put_version_simple(resources=[], version=v2, wait_for_released=False)
    await clienthelper.put_version_simple(resources=[], version=v3, wait_for_released=False)

    agents = ["agent_1", "agent_2"]
    inmanta_modules = ["inmanta_module_1", "inmanta_module_2", "inmanta_module_3"]
    inmanta_module_versions = ["v1.0.0", "v2.0.0", "v3.0.0"]
    model_versions = [v1, v2, v3]
    agent_manager = server.get_slice(SLICE_AGENT_MANAGER)

    env = await data.Environment.get_by_id(env_id)
    for agent_name in agents:
        await agent_manager.ensure_agent_registered(env=env, nodename=agent_name)

    async def upload_files(contents: Sequence[str]) -> list[str]:
        "helper method to upload some files using the file API"
        file_hashes = []
        for file_content in contents:
            content = file_content.encode()
            hash = hash_file(content)
            file_hashes.append(hash)
            body = base64.b64encode(content).decode("ascii")

            result = await client.upload_file(id=hash, content=body)
            assert result.code == 200

        return file_hashes

    file_contents = ["A", "B", "C"]
    files_hashes: Sequence[str]
    files_hashes = await upload_files(file_contents)

    # Setup each module version with a number of file corresponding to its index:
    #  module version:   v1.0.0  v2.0.0  v3.0.0
    #         n_files:      1       2       3
    #         content:      A      A,B    A,B,C

    files_in_module_data = [
        {
            "inmanta_module_name": inmanta_module_name,
            "inmanta_module_version": inmanta_module_version,
            "environment": env_id,
            "file_content_hash": file_hash,
            "python_module_name": python_module_name,
            "is_byte_code": False,
        }
        for inmanta_module_name in inmanta_modules
        for n_files_to_create, inmanta_module_version in enumerate(inmanta_module_versions)
        for python_module_name, file_hash in zip(
            [
                f"inmanta_plugins.{inmanta_module_name}.{py_module}"
                for py_module in [f"top_module{suffix}" for suffix in [".sub" * i for i in range(1 + n_files_to_create)]]
            ],
            files_hashes,
        )
    ]

    module_data = [
        {
            "name": inmanta_module_name,
            "version": inmanta_module_version,
            "environment": env_id,
            "requirements": requirements,
        }
        for inmanta_module_name in inmanta_modules
        for inmanta_module_version in inmanta_module_versions
        for requirements in [[], ["dummy-inmanta-module~=1.0.0"]]
    ]

    # Setup each agent with the following modules:

    #            model version:      1        2       3
    #   inmanta module version:   v1.0.0   v2.0.0  v3.0.0
    #  module list for agent_1:     [1]     [1, 2]   [1, 2, 3]
    #  module list for agent_2:  [1, 2, 3]  [1, 2]   [1]

    modules_for_agent_data = [
        {
            "cm_version": cm_version,
            "environment": env_id,
            "agent_name": agent_name,
            "inmanta_module_name": inmanta_module_name,
            "inmanta_module_version": inmanta_module_version,
        }
        for cm_version, inmanta_module_version, n_modules_in_version in zip(model_versions, inmanta_module_versions, [1, 2, 3])
        for agent_name in agents
        for inmanta_module_name in (
            inmanta_modules[:n_modules_in_version] if agent_name == "agent_1" else inmanta_modules[: 4 - n_modules_in_version]
        )
    ]

    module_stmt = insert(InmantaModule).on_conflict_do_nothing()
    files_in_module_stmt = insert(ModuleFiles).on_conflict_do_nothing()
    modules_for_agent_stmt = insert(AgentModules).on_conflict_do_nothing()

    async with data.get_session() as session, session.begin():
        await session.execute(module_stmt, module_data)
        await session.execute(files_in_module_stmt, files_in_module_data)
        await session.execute(modules_for_agent_stmt, modules_for_agent_data)

    for version in model_versions:
        module_install_specs = await codemanager.get_code(environment=env_id, model_version=version, agent_name="agent_1")
        # Agent 1 is set up to have |version| files per module version and |version| modules per model version:
        assert len(module_install_specs) == version
        expected_content = set(file_contents[:version])
        for spec in module_install_specs:
            assert len(spec.blueprint.sources) == version

            actual_content = set([module_source.source.decode() for module_source in spec.blueprint.sources])
            assert actual_content == expected_content

    for version in model_versions:
        module_install_specs = await codemanager.get_code(environment=env_id, model_version=version, agent_name="agent_2")
        # Agent 2 is set up to have |version| files per module version and (4-|version|) modules per model version:
        assert len(module_install_specs) == (4 - version)
        expected_content = set(file_contents[:version])

        for spec in module_install_specs:
            assert len(spec.blueprint.sources) == version
            actual_content = set([module_source.source.decode() for module_source in spec.blueprint.sources])
            assert actual_content == expected_content


async def test_agent_code_loading_with_failure(
    caplog,
    server: Server,
    agent: Agent,
    client: Client,
    environment: uuid.UUID,
    monkeypatch,
    clienthelper: ClientHelper,
    tmpdir: py.path.local,
) -> None:
    """
    Test goal: make sure that failed resources are correctly returned by `get_code` and `ensure_code` methods.
    The failed resources should have the right exception contained in the returned object.

    """

    caplog.set_level(DEBUG)

    content = "file content".encode()
    hash = hash_file(content)
    body = base64.b64encode(content).decode("ascii")

    module_version_info = {
        "test": InmantaModuleDTO(
            name="test",
            version="abc",
            files_in_module=[ModuleSourceMetadata(name="inmanta_plugins.test.dummy_file", hash_value=hash, is_byte_code=False)],
            requirements=[],
            for_agents=["agent1"],
        )
    }

    res = await client.upload_file(id=hash, content=body)
    assert res.code == 200

    async def get_version() -> int:
        version = await clienthelper.get_version()
        res = await client.put_version(
            tid=environment,
            version=version,
            resources=[
                {
                    "id": "test::Test[agent1,name=test],v=%d" % version,
                    "purged": False,
                    "requires": [],
                    "version": version,
                    "name": "test",
                },
                {
                    "id": "test::Test2[agent1,name=test],v=%d" % version,
                    "purged": False,
                    "requires": [],
                    "version": version,
                    "name": "test",
                },
            ],
            module_version_info=module_version_info,
            pip_config=PipConfig(),
        )
        assert res.code == 200
        return version

    version_1 = await get_version()

    codemanager = CodeManager()

    # We want to test
    nonexistent_version = -1
    with pytest.raises(CouldNotResolveCode):
        _ = await codemanager.get_code(
            environment=environment, model_version=nonexistent_version, agent_name="dummy_agent_name"
        )

    module_install_specs = await codemanager.get_code(environment=environment, model_version=version_1, agent_name="agent1")

    async def _install(blueprint: executor.ExecutorBlueprint) -> None:
        raise Exception("MKPTCH: Unable to load code when agent is started with code loading disabled.")

    monkeypatch.setattr(agent.executor_manager, "_install", _install)

    failed_to_load = await agent.executor_manager.ensure_code(
        code=module_install_specs,
    )
    assert len(failed_to_load) == 1
    assert "test" in failed_to_load
    assert str(failed_to_load["test"]["test"]) == (
        "Failed to install module test version=abc: "
        "MKPTCH: Unable to load code when agent is started with code loading disabled."
    )

    monkeypatch.undo()

    log_index(caplog, "test_code_loading", logging.ERROR, "Failed to install module test version=abc")


@pytest.mark.parametrize("auto_start_agent", [True])
async def test_logging_on_code_loading_failure_missing_code(server, client, environment, clienthelper):
    """
    This test case ensures that if handler code cannot be loaded, this is reported in the resource action log.

    """
    version = await clienthelper.get_version()

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=[
            {
                "id": "test::Test[agent,name=test],v=%d" % version,
                "purged": False,
                "requires": [],
                "version": version,
            }
        ],
        module_version_info={},
    )
    assert res.code == 200

    res = await client.release_version(tid=environment, id=version)
    assert res.code == 200

    await wait_until_deployment_finishes(client, environment, version=version)

    result = await client.get_resource_actions(tid=environment, resource_type="test::Test", agent="agent", log_severity="ERROR")
    assert result.code == 200
    assert any(
        "All resources of type `test::Test` failed to install handler code dependencies" in log_line["msg"]
        for resource_action in result.result["data"]
        for log_line in resource_action["messages"]
    )


@pytest.mark.parametrize("auto_start_agent", [True])
async def test_logging_on_code_loading_error(server, client, environment, clienthelper):
    """
    1) Deploy resources that use broken code
    2) Check the resource action log

    """
    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::ResourceAAA[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key1",
            "value": "value1",
            "id": "test::ResourceBBB[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    content = "syntax error"
    hv1 = await upload_file(client, content)

    module_source_metadata = ModuleSourceMetadata(
        name="inmanta_plugins.test",
        hash_value=hv1,
        is_byte_code=False,
    )

    module_version_info = {
        "test": InmantaModuleDTO(
            name="test",
            version="0.0.0",
            files_in_module=[module_source_metadata],
            requirements=[],
            for_agents=["agent1"],
        )
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        module_version_info=module_version_info,
    )

    assert result.code == 200

    result = await client.release_version(tid=environment, id=version)
    assert result.code == 200

    await wait_until_deployment_finishes(client, environment, version=version, timeout=10)

    expected_error_message = "Agent agent1 failed to load the following modules: test."

    def check_for_message(data, must_be_present: str) -> None:
        """
        Helper method to assert the presence of the must_be_present string
        in the resource action log lines.
        """
        must_be_present_flag = False
        for resource_action in data:
            for log_line in resource_action["messages"]:
                if must_be_present in log_line["msg"]:
                    must_be_present_flag = True
                    break

        assert must_be_present_flag

    result = await client.get_resource_actions(
        tid=environment, resource_type="test::ResourceAAA", agent="agent1", log_severity="ERROR"
    )
    assert result.code == 200
    check_for_message(data=result.result["data"], must_be_present=expected_error_message)

    result = await client.get_resource_actions(
        tid=environment, resource_type="test::ResourceBBB", agent="agent1", log_severity="ERROR"
    )
    assert result.code == 200
    check_for_message(data=result.result["data"], must_be_present=expected_error_message)


async def check_code_for_version(
    version: int,
    environment: str,
    codemanager: CodeManager,
    agent_names: Sequence[str],
    module_name: str,
    expected_source: bytes = b"#The code",
    expected_constraints: str | None = None,
):
    """
    Helper method to check that all agents get the same code
    """
    environment = uuid.UUID(environment)
    for agent_name in agent_names:
        module_install_specs = await codemanager.get_code(environment=environment, model_version=version, agent_name=agent_name)
        for module in module_install_specs:
            if module.module_name == module_name:
                assert len(module.blueprint.sources) == 1
                assert module.blueprint.sources[0].source == expected_source
                assert module.blueprint.project_constraints == expected_constraints
                break
        else:
            assert False, f"Module {module_name} is not registered in version {version}."


@pytest.mark.parametrize("auto_start_agent", [True])
async def test_code_loading_after_partial(server, client, environment, clienthelper):
    """
    Test the following scenario:

    1) Full export of [r1 = ResType_A(agent = X), r2 = ResType_A(agent = Y)]   ---  V1
    2) Partial export of only r1                                               ---  V2

    Assert that agent Y can still get the code to deploy r2 in version V2

    3) Partial export using different module version from the base version should raise an exception

    4) Make sure we can provide during a partial export new agents with already registered code

    5) Make sure we can provide during a partial export new or existing agents with new modules

    6) Make sure we can bypass module version check during partial export with the allow_handler_code_update option


    """
    codemanager = CodeManager()

    version = await clienthelper.get_version()
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::ResType_A[agent_X,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key1",
            "value": "value1",
            "id": "test::ResType_A[agent_Y,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    content = "#The code"
    hv1: str = await upload_file(client, content)

    module_source_metadata1 = ModuleSourceMetadata(
        name="inmanta_plugins.test",
        hash_value=hv1,
        is_byte_code=False,
    )

    module_version_info = {
        "test": InmantaModuleDTO(
            name="test",
            version="0.0.0",
            files_in_module=[module_source_metadata1],
            requirements=[],
            for_agents=["agent_X", "agent_Y"],
            constraints_file_hash=None,
        )
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        module_version_info=module_version_info,
        resource_sets={"test::ResType_A[agent_X,key=key1]": "set-a", "test::ResType_A[agent_Y,key=key1]": "set-b"},
    )

    assert result.code == 200

    await check_code_for_version(
        version=1,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_X", "agent_Y"],
        module_name="test",
        expected_source=b"#The code",
    )

    resources = [
        {
            "key": "key1",
            "value": "value2",
            "id": "test::ResType_A[agent_X,key=key1],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        }
    ]
    resource_sets = {
        "test::ResType_A[agent_X,key=key1]": "set-a",
    }
    result = await client.put_partial(
        tid=environment,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets=resource_sets,
        module_version_info=module_version_info,
    )
    assert result.code == 200
    await check_code_for_version(
        version=2,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_X", "agent_Y"],
        module_name="test",
        expected_source=b"#The code",
    )

    # 3) Partial export using different module version from the base version should raise an exception:

    altered_content = "#The OTHER code"
    hv2: str = await upload_file(client, altered_content)

    module_source_metadata2 = ModuleSourceMetadata(
        name="inmanta_plugins.test",
        hash_value=hv2,
        is_byte_code=False,
    )

    mismatched_module_version_info = {
        "test": InmantaModuleDTO(
            name="test",
            version="1.1.1",
            files_in_module=[module_source_metadata2],
            requirements=[],
            for_agents=["agent_X"],
            constraints_file_hash=None,
        )
    }

    result = await client.put_partial(
        tid=environment,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets=resource_sets,
        module_version_info=mismatched_module_version_info,
    )

    assert result.code == 400
    assert result.result["message"] == (
        "Invalid request: Cannot perform partial export because the source code for module test in this partial version is "
        "different from the currently registered source code. Consider running a full export instead. Alternatively, if you "
        "are sure the new code is compatible and want to forcefully update, you can bypass this version check with the "
        "`--allow-handler-code-update` CLI option."
    )

    await check_code_for_version(
        version=2,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_X", "agent_Y"],
        module_name="test",
        expected_source=b"#The code",
    )

    # 4) Make sure we can provide new agents with already registered code:
    module_version_info = {
        "test": InmantaModuleDTO(
            name="test",
            version="0.0.0",
            files_in_module=[module_source_metadata1],
            requirements=[],
            for_agents=["agent_Z"],
            constraints_file_hash=None,
        )
    }
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::ResType_A[agent_Z,key=key1],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::ResType_A[agent_Z,key=key1]": "set-b",
    }

    result = await client.put_partial(
        tid=environment,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets=resource_sets,
        module_version_info=module_version_info,
    )
    assert result.code == 200

    await check_code_for_version(
        version=3,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_X", "agent_Y", "agent_Z"],
        module_name="test",
        expected_source=b"#The code",
    )

    # 5) Make sure we can provide agents with new modules:

    content = "#Yet some other code"
    hv3: str = await upload_file(client, content)

    module_source_metadata3 = ModuleSourceMetadata(
        name="inmanta_plugins.new_module",
        hash_value=hv3,
        is_byte_code=False,
    )

    module_version_info = {
        "new_module": InmantaModuleDTO(
            name="new_module",
            version="0.0.0",
            files_in_module=[module_source_metadata3],
            requirements=[],
            for_agents=["agent_Z", "agent_A"],
            constraints_file_hash=None,
        )
    }
    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::ResType_A[agent_Z,key=key1],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
        {
            "key": "key1",
            "value": "value1",
            "id": "test::ResType_A[agent_A,key=key1],v=0",
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]
    resource_sets = {
        "test::ResType_A[agent_Z,key=key1]": "set-b",
    }

    result = await client.put_partial(
        tid=environment,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets=resource_sets,
        module_version_info=module_version_info,
    )
    assert result.code == 200

    await check_code_for_version(
        version=4,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_X", "agent_Y", "agent_Z"],
        module_name="test",
        expected_source=b"#The code",
    )
    await check_code_for_version(
        version=4,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_Z", "agent_A"],
        module_name="new_module",
        expected_source=b"#Yet some other code",
    )

    # 6) Make sure we can force code update via the allow_handler_code_update option

    result = await client.put_partial(
        tid=environment,
        resources=resources,
        resource_state={},
        unknowns=[],
        version_info={},
        resource_sets=resource_sets,
        module_version_info=mismatched_module_version_info,
        allow_handler_code_update=True,
    )
    assert result.code == 200
    await check_code_for_version(
        version=5,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_X", "agent_Y", "agent_Z"],
        module_name="test",
        expected_source=b"#The OTHER code",
    )

    await check_code_for_version(
        version=5,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_Z", "agent_A"],
        module_name="new_module",
        expected_source=b"#Yet some other code",
    )


@pytest.mark.parametrize("auto_start_agent", [True])
async def test_project_constraints_in_agent_code_install(server, client, environment, clienthelper):
    """
    Check that registered constraints get propagated into the agents' venv blueprints.

    The test_process_manager test in test_agent_executor.py checks that these constraints
    are taken into account during agent code install.
    """
    codemanager = CodeManager()

    version = await clienthelper.get_version()

    def get_resources(version: int) -> list[dict]:
        resources = [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::ResType_A[agent_X,key=key1],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": [],
            },
            {
                "key": "key1",
                "value": "value1",
                "id": "test::ResType_A[agent_Y,key=key1],v=%d" % version,
                "send_event": False,
                "purged": False,
                "requires": [],
            },
        ]
        return resources

    content = "#The code"
    hv1: str = await upload_file(client, content)

    constraints = "dummy_constraint~=1.2.3\ndummy_constraint<5.5.5"

    module_source_metadata1 = ModuleSourceMetadata(
        name="inmanta_plugins.test",
        hash_value=hv1,
        is_byte_code=False,
    )

    module_version_info_v0 = {
        "test": InmantaModuleDTO(
            name="test",
            version="0.0.0",
            files_in_module=[module_source_metadata1],
            requirements=[],
            for_agents=["agent_X", "agent_Y"],
        )
    }

    result = await client.put_version(
        tid=environment,
        version=version,
        resources=get_resources(version),
        resource_state={},
        unknowns=[],
        version_info={},
        module_version_info=module_version_info_v0,
        resource_sets={"test::ResType_A[agent_X,key=key1]": "set-a", "test::ResType_A[agent_Y,key=key1]": "set-b"},
        project_constraints=constraints,
    )

    assert result.code == 200

    await check_code_for_version(
        version=1,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_X", "agent_Y"],
        module_name="test",
        expected_source=b"#The code",
        expected_constraints=constraints,
    )

    # Partial compiles should use the same constraints as the version they're based on.

    result = await client.put_partial(
        tid=environment,
        resources=get_resources(0),
        resource_state={},
        unknowns=[],
        version_info={},
        module_version_info=module_version_info_v0,
        resource_sets={"test::ResType_A[agent_X,key=key1]": "set-a", "test::ResType_A[agent_Y,key=key1]": "set-b"},
    )
    assert result.code == 200
    await check_code_for_version(
        version=2,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_X", "agent_Y"],
        module_name="test",
        expected_source=b"#The code",
        expected_constraints=constraints,
    )

    module_version_info_v1 = {
        "test": InmantaModuleDTO(
            name="test",
            version="1.0.0",
            files_in_module=[module_source_metadata1],
            requirements=[],
            for_agents=["agent_X", "agent_Y"],
        )
    }

    version = await clienthelper.get_version()
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=get_resources(version),
        resource_state={},
        unknowns=[],
        version_info={},
        module_version_info=module_version_info_v1,
        resource_sets={"test::ResType_A[agent_X,key=key1]": "set-a", "test::ResType_A[agent_Y,key=key1]": "set-b"},
        project_constraints=None,
    )

    assert result.code == 200

    await check_code_for_version(
        version=3,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_X", "agent_Y"],
        module_name="test",
        expected_source=b"#The code",
        expected_constraints=None,
    )
    res = await client.release_version(tid=environment, id=version)
    assert res.code == 200

    result = await client.put_partial(
        tid=environment,
        resources=get_resources(0),
        resource_state={},
        unknowns=[],
        version_info={},
        module_version_info=module_version_info_v1,
        resource_sets={"test::ResType_A[agent_X,key=key1]": "set-a", "test::ResType_A[agent_Y,key=key1]": "set-b"},
    )
    assert result.code == 200
    await check_code_for_version(
        version=4,
        environment=environment,
        codemanager=codemanager,
        agent_names=["agent_X", "agent_Y"],
        module_name="test",
        expected_source=b"#The code",
        expected_constraints=None,
    )
