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

import base64
import hashlib
import os
import py_compile
import tempfile
import uuid
from logging import DEBUG, INFO
from typing import Sequence

import pytest

import inmanta
from inmanta import config
from inmanta.agent import Agent
from inmanta.agent.executor import ResourceInstallSpec
from inmanta.data import PipConfig
from inmanta.protocol import Client
from inmanta.util import get_compiler_version
from utils import LogSequence


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


@pytest.fixture(scope="function")
def server_pre_start(server_config, request):
    config.Config.set("agent", "executor-mode", request.param)
    yield config


@pytest.mark.parametrize('server_pre_start', ["threaded"], indirect=True)
async def test_agent_code_loading(
    server_pre_start, caplog, server, agent_factory, client, environment: uuid.UUID, monkeypatch, clienthelper
) -> None:
    """
    Test goals:
    1. ensure the agent doesn't re-load the same code if not required
       1a. because the resource-version is exactly the same
       1b. because the underlying code is the same
    even when loading is done in very short succession
    """

    caplog.set_level(DEBUG)

    codea = """
def test():
    return 10

import inmanta
inmanta.test_agent_code_loading = 5
    """

    codeb = """
def test():
    return 10
def xx():
    pass

import inmanta
inmanta.test_agent_code_loading = 10
    """

    codec = """
import inmanta
inmanta.test_agent_code_loading = 15
    """
    # set a different value to check if the agent has loaded the code.
    # use monkeypatch for cleanup
    monkeypatch.setattr(inmanta, "test_agent_code_loading", 0, raising=False)

    sources = {}
    sources2 = {}
    sources3 = {}
    hv1 = await make_source_structure(sources, "inmanta_plugins/test/__init__.py", "inmanta_plugins.test", codea, client=client)
    hv2 = await make_source_structure(
        sources2, "inmanta_plugins/tests/__init__.py", "inmanta_plugins.tests", codeb, client=client
    )
    hv3 = await make_source_structure(
        sources3, "inmanta_plugins/tests/__init__.py", "inmanta_plugins.tests", codec, byte_code=True, client=client
    )

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
    version_2 = await get_version()
    version_3 = await get_version()
    version_4 = await get_version()

    res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test": sources})
    assert res.code == 200

    # 2 identical versions
    res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test2": sources})
    assert res.code == 200
    res = await client.upload_code_batched(tid=environment, id=version_2, resources={"test::Test2": sources})
    assert res.code == 200

    # two distinct versions
    res = await client.upload_code_batched(tid=environment, id=version_1, resources={"test::Test3": sources})
    assert res.code == 200
    res = await client.upload_code_batched(tid=environment, id=version_2, resources={"test::Test3": sources2})
    assert res.code == 200

    # bytecompile version
    res = await client.upload_code_batched(tid=environment, id=version_3, resources={"test::Test4": sources3})
    assert res.code == 200

    # source version again
    res = await client.upload_code_batched(tid=environment, id=version_4, resources={"test::Test4": sources2})
    assert res.code == 200

    # Try to pull binary file via v1 API, get a 400
    result = await client.get_code(tid=environment, id=version_3, resource="test::Test4")
    assert result.code == 400

    agent: Agent = await agent_factory(
        environment=environment, agent_map={"agent1": "localhost"}, hostname="host", agent_names=["agent1"], code_loader=True
    )

    # Cache test
    # install sources for all three
    resource_install_specs_1: list[ResourceInstallSpec]
    resource_install_specs_2: list[ResourceInstallSpec]
    resource_install_specs_3: list[ResourceInstallSpec]
    resource_install_specs_4: list[ResourceInstallSpec]
    resource_install_specs_5: list[ResourceInstallSpec]
    resource_install_specs_6: list[ResourceInstallSpec]

    resource_install_specs_1, _ = await agent.get_code(
        environment=environment, version=version_1, resource_types=["test::Test", "test::Test2", "test::Test3"]
    )
    await agent.executor_manager.ensure_code(
        code=resource_install_specs_1,
    )
    resource_install_specs_2, _ = await agent.get_code(
        environment=environment, version=version_1, resource_types=["test::Test", "test::Test2"]
    )
    await agent.executor_manager.ensure_code(
        code=resource_install_specs_2,
    )
    resource_install_specs_3, _ = await agent.get_code(
        environment=environment, version=version_2, resource_types=["test::Test2"]
    )
    await agent.executor_manager.ensure_code(
        code=resource_install_specs_3,
    )

    # Test 1 is deployed once, as seen by the agent
    (
        LogSequence(caplog)
        .contains("inmanta.agent.agent", DEBUG, f"Installing handler test::Test version={version_1}")
        .contains("inmanta.agent.agent", DEBUG, f"Installed handler test::Test version={version_1}")
        .contains(
            "inmanta.agent.agent",
            DEBUG,
            f"Cache hit, using existing ResourceInstallSpec for resource_type=test::Test version={version_1}",
        )
        .contains("inmanta.agent.agent", DEBUG, f"Handler code already installed for test::Test version={version_1}")
        .assert_not("inmanta", DEBUG, "test::Test ")
    )

    # Test 2 is deployed one, as seen by the agent
    # and loaded only once
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, f"Installing handler test::Test2 version={version_1}").contains(
        "inmanta.agent.agent", DEBUG, f"Handler code already installed for test::Test2 version={version_2}"
    )
    # Loader only loads source1 once
    LogSequence(caplog).contains("inmanta.loader", INFO, f"Deploying code (hv={hv1}, module=inmanta_plugins.test)").assert_not(
        "inmanta.loader", INFO, f"Deploying code (hv={hv1}, module=inmanta_plugins.test)"
    )

    # we are now at sources1
    assert getattr(inmanta, "test_agent_code_loading") == 5

    resource_install_specs_4, _ = await agent.get_code(
        environment=environment, version=version_2, resource_types=["test::Test3"]
    )
    # Install sources2
    await agent.executor_manager.ensure_code(code=resource_install_specs_4)
    # Test 3 is deployed twice, as seen by the agent and the loader
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, f"Installing handler test::Test3 version={version_1}")
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, f"Installing handler test::Test3 version={version_2}")
    # Loader only loads source2 once
    LogSequence(caplog).contains("inmanta.loader", INFO, f"Deploying code (hv={hv2}, module=inmanta_plugins.tests)").assert_not(
        "inmanta.loader", INFO, f"Deploying code (hv={hv2}, module=inmanta_plugins.tests)"
    )

    # we are now at sources2
    assert getattr(inmanta, "test_agent_code_loading") == 10

    resource_install_specs_5, _ = await agent.get_code(
        environment=environment, version=version_3, resource_types=["test::Test4"]
    )
    # Loader loads byte code file
    await agent.executor_manager.ensure_code(code=resource_install_specs_5)
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, f"Installing handler test::Test4 version={version_3}")
    LogSequence(caplog).contains("inmanta.loader", INFO, f"Deploying code (hv={hv3}, module=inmanta_plugins.tests)").assert_not(
        "inmanta.loader", INFO, f"Deploying code (hv={hv3}, module=inmanta_plugins.tests)"
    )

    assert getattr(inmanta, "test_agent_code_loading") == 15

    resource_install_specs_6, _ = await agent.get_code(
        environment=environment, version=version_4, resource_types=["test::Test4"]
    )
    # Now load the python only version again
    await agent.executor_manager.ensure_code(code=resource_install_specs_6)
    assert getattr(inmanta, "test_agent_code_loading") == 10

    # ensure we clean up on restart
    assert os.path.exists(os.path.join(agent.executor_manager._loader.mod_dir, "tests/plugins/__init__.py"))
    await agent.stop()
    await agent_factory(
        environment=environment, agent_map={"agent1": "localhost"}, hostname="host", agent_names=["agent1"], code_loader=True
    )
    assert not os.path.exists(os.path.join(agent.executor_manager._loader.mod_dir, "tests"))


@pytest.mark.slowtest
@pytest.mark.parametrize('server_pre_start', ["forking"], indirect=True)
async def test_agent_installs_dependency_containing_extras(
    server_pre_start,
    server,
    client,
    environment,
    agent_factory,
    monkeypatch,
    index_with_pkgs_containing_optional_deps: str,
    clienthelper,
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

    agent: Agent = await agent_factory(
        environment=environment, agent_map={"agent1": "localhost"}, hostname="host", agent_names=["agent1"], code_loader=True
    )
    install_spec, _ = await agent.get_code(
        environment=environment,
        version=version,
        resource_types=["test::Test"],
    )
    executor = await agent.executor_manager.get_executor("agent1", "localhost", install_spec)

    installed_packages = executor.executor_virtual_env.get_installed_packages()

    def check_packages(
        package_list: Sequence[str], must_contain: Sequence[str] | None, must_not_contain: Sequence[str] | None
    ) -> None:
        """
        Iterate over <package_list> and check:
         - all elements from <must_contain> are present
         - no element from <must_not_contain> are present
        """
        must_contain = list(must_contain) if must_contain else []
        for package in package_list:
            assert package not in must_not_contain
            if package in must_contain:
                must_contain.remove(package)

        assert not must_contain

    check_packages(package_list=installed_packages, must_contain=["pkg", "dep-a"], must_not_contain=["dep-b", "dep-c"])
