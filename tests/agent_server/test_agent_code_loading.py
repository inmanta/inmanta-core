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
import py_compile
import tempfile
import uuid
from asyncio import gather
from logging import DEBUG, INFO

import inmanta
from inmanta.agent import Agent
from utils import LogSequence


async def test_agent_code_loading(caplog, server, agent_factory, client, environment: uuid.UUID, monkeypatch) -> None:
    """
    Test goals:
    1. ensure the agent doesn't re-load the same code if not required
       1a. because the resource-version is exactly the same
       1b. because the underlying code is the same
    even when loading is done in very short succession
    """

    caplog.set_level(DEBUG)

    async def make_source_structure(into: dict, file: str, module: str, source: str, byte_code: bool = False) -> str:
        if byte_code:
            fd, source_file = tempfile.mkstemp(suffix=".py")
            with open(fd, "w+") as fh:
                fh.write(source)
            py_compile.compile(source_file, cfile=source_file + "c")

            with open(source_file + "c", "rb") as fh:
                data = fh.read()
            file_name = source_file + "c"
        else:
            data = source.encode()
            file_name = file

        sha1sum = hashlib.new("sha1")
        sha1sum.update(data)
        hv: str = sha1sum.hexdigest()
        into[hv] = (file_name, module, [])
        await client.upload_file(hv, content=base64.b64encode(data).decode("ascii"))
        return hv

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
    # set a different value to check if the agent has loaded the code. use setattr to avoid type complaints
    monkeypatch.setattr(inmanta, "test_agent_code_loading", 0, raising=False)

    sources = {}
    sources2 = {}
    sources3 = {}
    hv1 = await make_source_structure(sources, "inmanta_plugins/test/__init__.py", "inmanta_plugins.test", codea)
    hv2 = await make_source_structure(sources2, "inmanta_plugins/tests/__init__.py", "inmanta_plugins.tests", codeb)
    hv3 = await make_source_structure(
        sources3, "inmanta_plugins/tests/__init__.py", "inmanta_plugins.tests", codec, byte_code=True
    )

    res = await client.upload_code_batched(tid=environment, id=5, resources={"test::Test": sources})
    assert res.code == 200

    # 2 identical versions
    res = await client.upload_code_batched(tid=environment, id=5, resources={"test::Test2": sources})
    assert res.code == 200
    res = await client.upload_code_batched(tid=environment, id=6, resources={"test::Test2": sources})
    assert res.code == 200

    # two distinct versions
    res = await client.upload_code_batched(tid=environment, id=5, resources={"test::Test3": sources})
    assert res.code == 200
    res = await client.upload_code_batched(tid=environment, id=6, resources={"test::Test3": sources2})
    assert res.code == 200

    # bytecompile version
    res = await client.upload_code_batched(tid=environment, id=7, resources={"test::Test4": sources3})
    assert res.code == 200

    # source version again
    res = await client.upload_code_batched(tid=environment, id=8, resources={"test::Test4": sources2})
    assert res.code == 200

    agent: Agent = await agent_factory(
        environment=environment, agent_map={"agent1": "localhost"}, hostname="host", agent_names=["agent1"], code_loader=True
    )

    # Cache test
    # install sources for all three
    await agent.ensure_code(
        environment=environment,
        version=5,
        resource_types=["test::Test", "test::Test2", "test::Test3"],
    )
    # install sources as well
    await agent.ensure_code(environment=environment, version=5, resource_types=["test::Test", "test::Test2"])
    # install sources as well
    await agent.ensure_code(environment=environment, version=6, resource_types=["test::Test2"])

    # Test 1 is deployed once, as seen by the agent
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, "Installing handler test::Test version=5").contains(
        "inmanta.agent.agent", DEBUG, "Installed handler test::Test version=5"
    ).contains("inmanta.agent.agent", DEBUG, "Code already present for test::Test version=5").assert_not(
        "inmanta", DEBUG, "test::Test "
    )

    # Test 2 is once twice, as seen by the agent
    # But loaded only once
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, "Installing handler test::Test2 version=5").contains(
        "inmanta.agent.agent", DEBUG, "Installing handler test::Test2 version=6"
    ).contains("inmanta.loader", DEBUG, f"Not deploying code (hv={hv1}, module=inmanta_plugins.test) because of cache hit")

    # Loader only loads source1 once
    LogSequence(caplog).contains("inmanta.loader", INFO, f"Deploying code (hv={hv1}, module=inmanta_plugins.test)").assert_not(
        "inmanta.loader", INFO, f"Deploying code (hv={hv1}, module=inmanta_plugins.test)"
    )

    # we are now at sources1
    assert getattr(inmanta, "test_agent_code_loading") == 5

    # Install sources2
    await agent.ensure_code(environment=environment, version=6, resource_types=["test::Test3"])
    # Test 3 is deployed twice, as seen by the agent and the loader
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, "Installing handler test::Test3 version=5")
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, "Installing handler test::Test3 version=6")
    # Loader only loads source2 once
    LogSequence(caplog).contains("inmanta.loader", INFO, f"Deploying code (hv={hv2}, module=inmanta_plugins.tests)").assert_not(
        "inmanta.loader", INFO, f"Deploying code (hv={hv2}, module=inmanta_plugins.tests)"
    )

    # we are now at sources2
    assert getattr(inmanta, "test_agent_code_loading") == 10

    # Loader loads byte code file
    await agent.ensure_code(environment=environment, version=7, resource_types=["test::Test4"])
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, "Installing handler test::Test4 version=7")
    LogSequence(caplog).contains("inmanta.loader", INFO, f"Deploying code (hv={hv3}, module=inmanta_plugins.tests)").assert_not(
        "inmanta.loader", INFO, f"Deploying code (hv={hv3}, module=inmanta_plugins.tests)"
    )

    assert getattr(inmanta, "test_agent_code_loading") == 15

    # Now load the python only version again
    await agent.ensure_code(environment=environment, version=8, resource_types=["test::Test4"])
    assert getattr(inmanta, "test_agent_code_loading") == 10
