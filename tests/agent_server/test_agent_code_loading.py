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
import logging
import os
import py_compile
import tempfile
import uuid
from logging import DEBUG, INFO

import pytest

import inmanta
from inmanta import const
from inmanta.agent import Agent
from inmanta.data import PipConfig
from inmanta.data.model import Notification
from inmanta.protocol import Client
from inmanta.util import get_compiler_version
from utils import LogSequence, log_contains, log_doesnt_contain


async def make_source_structure(
    into: dict, file: str, module: str, source: str, client: Client, byte_code: bool = False, dependencies: list[str] = []
) -> str:
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


async def test_agent_code_loading(
    caplog, server, agent_factory, client, environment: uuid.UUID, monkeypatch, clienthelper
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
    await agent.ensure_code(
        environment=environment,
        version=version_1,
        resource_types=["test::Test", "test::Test2", "test::Test3"],
    )
    # install sources as well
    await agent.ensure_code(environment=environment, version=version_1, resource_types=["test::Test", "test::Test2"])
    # install sources as well
    await agent.ensure_code(environment=environment, version=version_2, resource_types=["test::Test2"])

    # Test 1 is deployed once, as seen by the agent
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, f"Installing handler test::Test version={version_1}").contains(
        "inmanta.agent.agent", DEBUG, f"Installed handler test::Test version={version_1}"
    ).contains("inmanta.agent.agent", DEBUG, f"Code already present for test::Test version={version_1}").assert_not(
        "inmanta", DEBUG, "test::Test "
    )

    # Test 2 is once twice, as seen by the agent
    # But loaded only once
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, f"Installing handler test::Test2 version={version_1}").contains(
        "inmanta.agent.agent", DEBUG, f"Installing handler test::Test2 version={version_2}"
    ).contains("inmanta.loader", DEBUG, f"Not deploying code (hv={hv1}, module=inmanta_plugins.test) because of cache hit")

    # Loader only loads source1 once
    LogSequence(caplog).contains("inmanta.loader", INFO, f"Deploying code (hv={hv1}, module=inmanta_plugins.test)").assert_not(
        "inmanta.loader", INFO, f"Deploying code (hv={hv1}, module=inmanta_plugins.test)"
    )

    # we are now at sources1
    assert getattr(inmanta, "test_agent_code_loading") == 5

    # Install sources2
    await agent.ensure_code(environment=environment, version=version_2, resource_types=["test::Test3"])
    # Test 3 is deployed twice, as seen by the agent and the loader
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, f"Installing handler test::Test3 version={version_1}")
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, f"Installing handler test::Test3 version={version_2}")
    # Loader only loads source2 once
    LogSequence(caplog).contains("inmanta.loader", INFO, f"Deploying code (hv={hv2}, module=inmanta_plugins.tests)").assert_not(
        "inmanta.loader", INFO, f"Deploying code (hv={hv2}, module=inmanta_plugins.tests)"
    )

    # we are now at sources2
    assert getattr(inmanta, "test_agent_code_loading") == 10

    # Loader loads byte code file
    await agent.ensure_code(environment=environment, version=version_3, resource_types=["test::Test4"])
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, f"Installing handler test::Test4 version={version_3}")
    LogSequence(caplog).contains("inmanta.loader", INFO, f"Deploying code (hv={hv3}, module=inmanta_plugins.tests)").assert_not(
        "inmanta.loader", INFO, f"Deploying code (hv={hv3}, module=inmanta_plugins.tests)"
    )

    assert getattr(inmanta, "test_agent_code_loading") == 15

    # Now load the python only version again
    await agent.ensure_code(environment=environment, version=version_4, resource_types=["test::Test4"])
    assert getattr(inmanta, "test_agent_code_loading") == 10


@pytest.mark.slowtest
async def test_agent_installs_dependency_containing_extras(
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

    await agent.ensure_code(
        environment=environment,
        version=version,
        resource_types=["test::Test"],
    )

    assert agent._env.are_installed(["pkg", "dep-a"])
    assert not agent._env.are_installed(["dep-b", "dep-c"])


async def test_warning_message_stale_python_code(
    server,
    client,
    environment,
    agent_factory,
    clienthelper,
    caplog,
    local_module_package_index,
) -> None:
    """
    If a certain module A depends on the plugin code of another module B, then the source of B must either:
      * Be exported to the server (because module B has resources or providers)
      * Or, not be exported and never been exported in any previous version.
    Otherwise there is the possibility that stale code in the code directory of the agent gets picket up,
    instead of the code from the Python package (V2 module) installed in the venv of the agent.

    This test case verifies that a warning message is written the agent's log file when this scenario occurs.
    """

    sources_test_mod = {}
    await make_source_structure(
        into=sources_test_mod,
        file="inmanta_plugins/test/__init__.py",
        module="inmanta_plugins.test",
        source="",
        dependencies=["inmanta-module-minimalv2module"],
        client=client,
    )
    sources_minimalv2module_mod = {}
    await make_source_structure(
        into=sources_minimalv2module_mod,
        file="inmanta_plugins/minimalv2module/__init__.py",
        module="inmanta_plugins.minimalv2module",
        source="",
        dependencies=[],
        client=client,
    )

    version = await clienthelper.get_version()

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=[],
        pip_config=PipConfig(index_url=local_module_package_index),
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    res = await client.upload_code_batched(
        tid=environment,
        id=version,
        resources={"test::Test": sources_test_mod, "minimalv2module::Test": sources_minimalv2module_mod},
    )
    assert res.code == 200

    agent: Agent = await agent_factory(
        environment=environment, agent_map={"agent1": "localhost"}, hostname="host", agent_names=["agent1"], code_loader=True
    )

    await agent.ensure_code(
        environment=uuid.UUID(environment),
        version=version,
        resource_types=["test::Test", "minimalv2module::Test"],
    )

    expected_warning_message = (
        f"The source code for the modules minimalv2module is present in the modules directory of the agent "
        f"({agent._loader.mod_dir})"
    )
    log_doesnt_contain(caplog, "agent", logging.WARNING, expected_warning_message)
    result = await client.list_notifications(tid=environment)
    assert result.code == 200
    assert len(result.result["data"]) == 0

    # Don't upload code for modb anymore in new version
    version = await clienthelper.get_version()

    res = await client.put_version(
        tid=environment,
        version=version,
        resources=[],
        pip_config=PipConfig(index_url=local_module_package_index),
        compiler_version=get_compiler_version(),
    )
    assert res.code == 200

    res = await client.upload_code_batched(tid=environment, id=version, resources={"test::Test": sources_test_mod})
    assert res.code == 200

    await agent.ensure_code(
        environment=uuid.UUID(environment),
        version=version,
        resource_types=["test::Test"],
    )

    log_contains(caplog, "agent", logging.WARNING, expected_warning_message)
    result = await client.list_notifications(tid=environment)
    assert result.code == 200
    assert len(result.result["data"]) == 1
    notification = Notification(**result.result["data"][0])
    assert notification.environment == uuid.UUID(environment)
    assert notification.title == "Stale code in agent's code directory"
    assert expected_warning_message in notification.message
    assert notification.uri is None
    assert notification.severity == const.NotificationSeverity.warning.value
    assert not notification.read
    assert not notification.cleared
