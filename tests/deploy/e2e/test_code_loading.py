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
from typing import Any

import pytest

from inmanta import config
from inmanta.agent import executor
from inmanta.agent.agent_new import Agent
from inmanta.agent.code_manager import CodeManager, CouldNotResolveCode
from inmanta.agent.executor import ResourceInstallSpec, ModuleInstallSpec
from inmanta.agent.in_process_executor import InProcessExecutorManager
from inmanta.data import PipConfig
from inmanta.env import process_env
from inmanta.protocol import Client
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.server.server import Server
from inmanta.util import get_compiler_version
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
    a.scheduler.code_manager = DummyCodeManager(a._client)

    await a.start()

    await retry_limited(lambda: len(agentmanager.sessions) == 1, 10)

    yield a

    await a.stop()


async def make_source_structure(
    into: dict[str, dict[str, str, list[dict[str, Any]]]],
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
            data = source.encode()
            file_name = file

        sha1sum = hashlib.new("sha1")
        sha1sum.update(data)
        hv: str = sha1sum.hexdigest()
        into[module] = {
            "name": module,
            "version": hv,  # only one file: module hash == file hash
            "files_in_module": [
                {
                    "path": file_name,
                    "module_name": module,
                    "hash": hv,
                    "requires": dependencies,
                }
            ],
        }
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

@resource("test::Resource", agent="agent1", id_attribute="key")
class Res(Resource):
    fields = ("agent", "key", "value")

    """

    modules_data = {}
    type_to_module_data = {
        "test::Resource": "inmanta_plugins.test",
    }
    await make_source_structure(
        modules_data,
        "inmanta_plugins/test/__init__.py",
        "inmanta_plugins.test",
        code,
        dependencies=["pkg[optional-a]"],
        client=client,
    )

    res = await client.upload_modules(tid=environment, modules_data=modules_data)
    assert res.code == 200

    module_version_info = {module_name: data["version"] for module_name, data in modules_data.items()}
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
        module_version_info=module_version_info,
        type_to_module_data=type_to_module_data,
    )
    assert res.code == 200

    #
    # res = conn.stat_files(list(code_manager.get_file_hashes()))
    # if res is None or res.code != 200:
    #     raise Exception("Unable to upload handler plugin code to the server (msg: %s)" % res.result)
    #
    # for file in res.result["files"]:
    #     content = code_manager.get_file_content(file)
    #     res = conn.upload_file(id=file, content=base64.b64encode(content).decode("ascii"))
    #     if res is None or res.code != 200:
    #         raise Exception("Unable to upload handler plugin code to the server (msg: %s)" % res.result)
    #
    # def get_modules_data() -> dict[str, PythonModule]:
    #     source_info = code_manager.get_module_source_info()
    #
    #     modules_data = {}
    #     for module_name, files_in_module in source_info.items():
    #         all_files_hashes = [file.hash for file in sorted(files_in_module, key=lambda f: f.hash)]
    #
    #         module_version_hash = hashlib.new("sha1")
    #         for file_hash in all_files_hashes:
    #             module_version_hash.update(file_hash.encode())
    #
    #         module_version = module_version_hash.hexdigest()
    #         modules_data[module_name] = dataclasses.asdict(
    #             PythonModule(
    #                 module_name = module_name,
    #                 module_version = module_version,
    #                 files_in_module = files_in_module,
    #             )
    #         )
    #     return modules_data
    # modules_data = {
    #     "test": {
    #         'module_name': 'test',
    #         "module_version": module_hash,
    #         "files_in_module": [
    #             {
    #                 'path': '/tmp/tmpskd9n7zx/std/plugins/types.py',
    #                 'module_name': 'inmanta_plugins.test',
    #                 'hash': '4ac629bdc461bf185971b82b4fc3dd457fba3fdd',
    #                 'requires': ['pkg[optional-a]'],
    #             }
    #         ]
    #     }
    # }

    # res = client.upload_modules(tid=environment, modules_data=modules_data)
    # if res is None or res.code != 200:
    #     raise Exception("Unable to upload plugin code to the server (msg: %s)" % res.result)

    # Example of what a source_map may look like:
    # Type Name: mymodule::Mytype"
    # Source Files:
    #   /path/to/__init__.py (hash: 'abc123', module: 'inmanta_plugins.mymodule.Mytype')
    #   /path/to/utils.py (hash: 'def456', module: 'inmanta_plugins.mymodule.Mytype')
    #
    # source_map = {
    #    "mymodule::Mytype": {
    #      'abc123': ('/path/to/__init__.py', 'inmanta_plugins.mymodule.Mytype', <requirements if any>),
    #      'def456': ('/path/to/utils.py', 'inmanta_plugins.mymodule.Mytype', <requirements if any>)
    #    },
    # ...other types would be included as well
    # }
    # source_map = {
    #     resource_name: {source.hash: (source.path, source.module_name, source.requires) for source in sources}
    #     for resource_name, sources in code_manager.get_types()
    # }
    #
    # res = conn.upload_code_batched(tid=tid, id=version, resources=source_map)
    # if res is None or res.code != 200:
    #     raise Exception("Unable to upload handler plugin code to the server (msg: %s)" % res.result)

    # res = await client.upload_code_batched(tid=environment, id=version, resources={"test::Test": sources})

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
) -> None:
    """
    Test goal: make sure that failed resources are correctly returned by `get_code` and `ensure_code` methods.
    The failed resources should have the right exception contained in the returned object.

    TODO: update docstrings of all updated tests
    TODO: remove old transport mechanism parts

    """

    caplog.set_level(DEBUG)

    # sources = {}
    #
    # res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test": sources})
    # assert res.code == 200
    #
    # res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test2": sources})
    # assert res.code == 200
    #
    # res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test3": sources})
    #

    res = await client.upload_modules(tid=environment, modules_data={})
    assert res.code == 200

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

    config.Config.set("agent", "executor-mode", "threaded")

    resource_install_specs_1: list[ModuleInstallSpec]
    resource_install_specs_2: list[ModuleInstallSpec]

    codemanager = CodeManager(agent._client)

    # We want to test
    nonexistent_version = -1
    with pytest.raises(CouldNotResolveCode):
        resource_install_specs_1 = await codemanager.get_code(
            environment=environment, model_version=nonexistent_version, agent_name="dummy_agent_name"
        )

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


@pytest.mark.parametrize("auto_start_agent", [True])
async def test_logging_on_code_loading_failure(server, client, environment, clienthelper):
    """
    This test case ensures that if handler code cannot be loaded, this is reported in the resource action log.
    """
    code = """
raise Exception("Fail code loading")
    """

    sources = {}
    await make_source_structure(
        sources,
        "inmanta_plugins/test/__init__.py",
        "inmanta_plugins.test",
        code,
        dependencies=[],
        client=client,
    )

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
        module_version_info={
            "inmanta_plugins.test": "2bf2115acde296712916b76cab9b6b96791ba295",
        },
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
