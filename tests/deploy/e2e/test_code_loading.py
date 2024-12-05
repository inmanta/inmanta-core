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
import hashlib
import logging
import os
import pathlib
import py_compile
import tempfile
import uuid
from collections.abc import Sequence
from logging import DEBUG

import pytest

from inmanta import config
from inmanta.agent import executor
from inmanta.agent.agent_new import Agent
from inmanta.agent.code_manager import CodeManager
from inmanta.agent.executor import ResourceInstallSpec
from inmanta.agent.in_process_executor import InProcessExecutorManager
from inmanta.data import PipConfig
from inmanta.env import process_env
from inmanta.protocol import Client
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.server.server import Server
from inmanta.util import get_compiler_version
from utils import ClientHelper, DummyCodeManager, log_index, retry_limited

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="function")
async def agent(server, environment, deactive_venv):
    """Construct an agent that can execute using the resource container"""
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)

    a = Agent(environment)

    executor = InProcessExecutorManager(
        environment,
        a._client,
        asyncio.get_event_loop(),
        LOGGER,
        a.thread_pool,
        str(pathlib.Path(a._storage["executors"]) / "code"),
        str(pathlib.Path(a._storage["executors"]) / "venvs"),
        True,
    )
    a.executor_manager = executor
    a.scheduler.executor_manager = executor
    a.scheduler.code_manager = DummyCodeManager(a._client)

    await a.start()

    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


async def make_source_structure(
    into: dict[str, tuple[str, str, list[str]]],
    file: str,
    module: str,
    source: str,
    client: Client,
    byte_code: bool = False,
    dependencies: list[str] = [],
) -> str:
    """
    :param into: dict to populate:
        - key = hash value of the file
        - value = tuple (file_name, module, dependencies)
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        if byte_code:
            py_file = os.path.join(tmpdirname, "test.py")
            pyc_file = os.path.join(tmpdirname, "test.pyc")
            with open(py_file, "w+") as fh:
                fh.write(source)
            py_compile.compile(py_file, cfile=pyc_file)
            with open(pyc_file, "rb") as fh:
                data = fh.read()
            file_name = pyc_file
        else:
            data = source.encode()
            file_name = file

        sha1sum = hashlib.new("sha1")
        sha1sum.update(data)
        hv: str = sha1sum.hexdigest()
        into[hv] = (file_name, module, dependencies)
        await client.upload_file(hv, content=base64.b64encode(data).decode("ascii"))
        return hv


@pytest.mark.slowtest
async def test_agent_installs_dependency_containing_extras(
    server_pre_start,
    server,
    client,
    environment,
    monkeypatch,
    index_with_pkgs_containing_optional_deps: str,
    clienthelper,
    agent,
) -> None:
    """
    Test whether the agent code loading works correctly when a python dependency is provided that contains extras.
    """
    code = """
def test():
    return 10
    """

    sources = {}
    await make_source_structure(
        sources,
        "inmanta_plugins/test/__init__.py",
        "inmanta_plugins.test",
        code,
        dependencies=["pkg[optional-a]"],
        client=client,
    )

    version = await clienthelper.get_version()

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=[],
        pip_config=PipConfig(index_url=index_with_pkgs_containing_optional_deps),
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    res = await client.upload_code_batched(tid=environment, id=version, resources={"test::Test": sources})
    assert res.code == 200

    codemanager = CodeManager(agent._client)

    install_spec, _ = await codemanager.get_code(
        environment=environment,
        version=version,
        resource_types=["test::Test"],
    )
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


async def test_agent_code_loading_with_failure(
    caplog,
    server: Server,
    agent: Agent,
    client: Client,
    environment: uuid.UUID,
    monkeypatch,
    clienthelper: ClientHelper,
) -> None:
    """
    Test goal: make sure that failed resources are correctly returned by `get_code` and `ensure_code` methods.
    The failed resources should have the right exception contained in the returned object.
    """

    caplog.set_level(DEBUG)

    sources = {}

    async def get_version() -> int:
        version = await clienthelper.get_version()
        res = await client.put_version(
            tid=environment,
            version=version,
            resources=[],
            pip_config=PipConfig(),
            compiler_version=get_compiler_version(),
        )
        assert res.code == 200
        return version

    version_1 = await get_version()

    res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test": sources})
    assert res.code == 200

    res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test2": sources})
    assert res.code == 200

    res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test3": sources})
    assert res.code == 200

    config.Config.set("agent", "executor-mode", "threaded")

    resource_install_specs_1: list[ResourceInstallSpec]
    resource_install_specs_2: list[ResourceInstallSpec]

    codemanager = CodeManager(agent._client)

    # We want to test
    nonexistent_version = -1
    resource_install_specs_1, invalid_resources_1 = await codemanager.get_code(
        environment=environment, version=nonexistent_version, resource_types=["test::Test", "test::Test2", "test::Test3"]
    )
    assert len(invalid_resources_1.keys()) == 3
    for resource_type, exception in invalid_resources_1.items():
        assert (
            "Failed to get source code for " + resource_type + " version=-1, result={'message': 'Request or "
            "referenced resource does not exist: The version of the code does not exist. "
            + resource_type
            + ", "
            + str(nonexistent_version)
            + "'}"
        ) == str(exception)

    await agent.executor_manager.ensure_code(
        code=resource_install_specs_1,
    )

    resource_install_specs_2, _ = await codemanager.get_code(
        environment=environment, version=version_1, resource_types=["test::Test", "test::Test2"]
    )

    async def _install(blueprint: executor.ExecutorBlueprint) -> None:
        raise Exception("MKPTCH: Unable to load code when agent is started with code loading disabled.")

    monkeypatch.setattr(agent.executor_manager, "_install", _install)

    failed_to_load = await agent.executor_manager.ensure_code(
        code=resource_install_specs_2,
    )
    assert len(failed_to_load) == 2
    for handler, exception in failed_to_load.items():
        assert str(exception) == (
            f"Failed to install handler {handler} version=1: "
            f"MKPTCH: Unable to load code when agent is started with code loading disabled."
        )

    monkeypatch.undo()

    idx1 = log_index(
        caplog,
        "inmanta.agent.code_manager",
        logging.ERROR,
        "Failed to get source code for test::Test2 version=-1",
    )

    log_index(caplog, "test_code_loading", logging.ERROR, "Failed to install handler test::Test version=1", idx1)

    log_index(caplog, "test_code_loading", logging.ERROR, "Failed to install handler test::Test2 version=1", idx1)
