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

import py
import pytest

import inmanta
from inmanta import config, loader
from inmanta.agent import executor
from inmanta.agent.agent_new import Agent
from inmanta.agent.code_manager import CodeManager, CouldNotResolveCode
from inmanta.agent.in_process_executor import InProcessExecutorManager
from inmanta.const import PLUGINS_PACKAGE
from inmanta.data import PipConfig
from inmanta.env import process_env
from inmanta.loader import PythonModule, SourceInfo
from inmanta.module import ModuleV2
from inmanta.protocol import Client
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.server.server import Server
from inmanta.util import get_compiler_version, hash_file
from packaging.version import Version
from utils import (
    ClientHelper,
    DummyCodeManager,
    PipIndex,
    log_index,
    module_from_template,
    retry_limited,
    wait_until_deployment_finishes,
)

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
    a.scheduler.code_manager = DummyCodeManager(a._client)

    await a.start()

    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


async def make_source_structure(
    into: dict[str, PythonModule],
    file: str,
    module: str,
    source: str,
    client: Client,
    byte_code: bool = False,
    dependencies: list[str] = [],
) -> str:
    """
    :param into: dict to populate:
        # - key = hash value of the file
        # - value = tuple (file_name, module, dependencies)
        - key = module name eg std
        - value = dict{
            module_name eg std -> TODO  can go maybe ?
            module_version
            files_in_module : list [
                dict {
                    path: str
                    fq mod name inmanta_plugins.std.resources',
                    hash: str
                    requires list[str]
                }
            ]
        }

        'module_name': 'std',
        'module_version': '6e929def427efefe814ce4ae0c00a9653628fdcb',
        'files_in_module': [{
                                'path': '/tmp/tmpskd9n7zx/std/plugins/resources.py',
                                'module_name': 'inmanta_plugins.std.resources',
                                'hash': '783979f77d1a40fa9b9c54c445c6f090de5797a1',
                                'requires': ['Jinja2>=3.1,<4', 'email_validator>=1.3,<3', 'pydantic>=1.10,<3',
                                             'inmanta-core>=8.7.0.dev']}, {
                                'path': '/tmp/tmpskd9n7zx/std/plugins/types.py',
                                'module_name': 'inmanta_plugins.std.types',
                                'hash': '4ac629bdc461bf185971b82b4fc3dd457fba3fdd',
                                'requires': ['Jinja2>=3.1,<4', 'email_validator>=1.3,<3', 'pydantic>=1.10,<3',
                                             'inmanta-core>=8.7.0.dev']}, {
                                'path': '/tmp/tmpskd9n7zx/std/plugins/__init__.py',
                                'module_name': 'inmanta_plugins.std',
                                'hash': '835f0e49da1e099d13e87b95d7f296ff68b57348',
                                'requires': ['Jinja2>=3.1,<4', 'email_validator>=1.3,<3', 'pydantic>=1.10,<3',
                                             'inmanta-core>=8.7.0.dev']}]}}

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
            py_file = os.path.join(tmpdirname, "test.py")
            data = source.encode()
            file_name = file

        sha1sum = hashlib.new("sha1")
        sha1sum.update(data)
        hv: str = sha1sum.hexdigest()
        into[module] = PythonModule(
            name=module,
            version=hv,
            files_in_module=[
                SourceInfo(
                    path=file_name,
                    module_name=loader.convert_relative_path_to_module(os.path.join(module, loader.PLUGIN_DIR, "__init__.py")),
                )
            ],
        )
        await client.upload_file(hv, content=base64.b64encode(data).decode("ascii"))

        return hv


@pytest.mark.slowtest
async def test_agent_installs_dependency_containing_extras(
    server_pre_start,
    server,
    client,
    monkeypatch,
    index_with_pkgs_containing_optional_deps: str,
    clienthelper,
    environment,
    agent,
) -> None:
    """
    Test whether the agent code loading works correctly when a python dependency is provided that contains extras.
    """
    content = "file content".encode()
    hash = hash_file(content)
    body = base64.b64encode(content).decode("ascii")

    mocked_module_version_info = {
        "test": PythonModule(
            name="test",
            version="abc",
            files_in_module=[
                {
                    "path": "dummy/path/test/plugins/dummy_file",
                    "module_name": "test",
                    "hash": hash,
                    "content": "file content",
                    "requires": ["pkg[optional-a]"],
                }
            ],
        )
    }

    mocked_type_to_module_data = {
        "test::Resource": ["test"],
    }

    res = await client.upload_file(id=hash, content=body)
    assert res.code == 200

    res = await client.upload_modules(tid=environment, modules_data=mocked_module_version_info)

    assert res.code == 200

    # module_version_info = {module_name: data["version"] for module_name, data in modules_data.items()}
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
        compiler_version=get_compiler_version(),
        module_version_info=mocked_module_version_info,
        type_to_module_data=mocked_type_to_module_data,
    )
    assert res.code == 200

    codemanager = CodeManager(agent._client)

    install_spec = await codemanager.get_code(
        environment=uuid.UUID(environment),
        model_version=version,
        agent_name="agent1",
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
    tmpdir: py.path.local,
) -> None:
    """
    Test goal: make sure that failed resources are correctly returned by `get_code` and `ensure_code` methods.
    The failed resources should have the right exception contained in the returned object.

    TODO: update docstrings of all updated tests
    TODO: remove old transport mechanism parts

    """

    caplog.set_level(DEBUG)

    content = "file content".encode()
    hash = hash_file(content)
    body = base64.b64encode(content).decode("ascii")

    mocked_module_version_info = {
        "test": PythonModule(
            name="test",
            version="abc",
            files_in_module=[
                {
                    "path": "dummy/path/test/plugins/dummy_file",
                    "module_name": "test",
                    "hash": hash,
                    "content": "file content",
                    "requires": [],
                }
            ],
        )
    }

    mocked_type_to_module_data = {
        "test::Test": ["test"],
        "test::Test2": ["test"],
    }

    res = await client.upload_file(id=hash, content=body)
    assert res.code == 200

    res = await client.upload_modules(tid=environment, modules_data=mocked_module_version_info)

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
            module_version_info=mocked_module_version_info,
            type_to_module_data=mocked_type_to_module_data,
            compiler_version=get_compiler_version(),
            pip_config=PipConfig(),
        )
        assert res.code == 200
        return version

    version_1 = await get_version()

    config.Config.set("agent", "executor-mode", "threaded")

    codemanager = CodeManager(agent._client)

    # We want to test
    nonexistent_version = -1
    with pytest.raises(CouldNotResolveCode):
        _ = await codemanager.get_code(
            environment=environment, model_version=nonexistent_version, agent_name="dummy_agent_name"
        )

    module_install_specs_2 = await codemanager.get_code(environment=environment, model_version=version_1, agent_name="agent1")

    async def _install(module_name: str, blueprint: executor.ExecutorBlueprint) -> None:
        raise Exception("MKPTCH: Unable to load code when agent is started with code loading disabled.")

    monkeypatch.setattr(agent.executor_manager, "_install", _install)

    failed_to_load = await agent.executor_manager.ensure_code(
        code=module_install_specs_2,
    )
    assert len(failed_to_load) == 1
    for handler, exception in failed_to_load.items():
        assert str(exception) == (
            f"Failed to install module {handler} version=1: "
            f"MKPTCH: Unable to load code when agent is started with code loading disabled."
        )

    monkeypatch.undo()

    log_index(caplog, "test_code_loading", logging.ERROR, "Failed to install module test version=1")


@pytest.mark.parametrize("auto_start_agent", [True])
async def test_logging_on_code_loading_failure(server, client, environment, clienthelper):
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
        compiler_version=get_compiler_version(),
        module_version_info={},
        type_to_module_data={},
    )
    assert res.code == 200

    res = await client.release_version(tid=environment, id=version)
    assert res.code == 200

    await wait_until_deployment_finishes(client, environment, version=version)

    result = await client.get_resource_actions(tid=environment, resource_type="test::Test", agent="agent", log_severity="ERROR")
    assert result.code == 200
    assert any(
        "All resources of type `test::Test` failed to load handler code or install handler code dependencies" in log_line["msg"]
        for resource_action in result.result["data"]
        for log_line in resource_action["messages"]
    )
