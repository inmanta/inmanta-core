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
import hashlib
from asyncio import gather
from logging import DEBUG, INFO

from inmanta.agent import Agent
from utils import LogSequence


async def test_agent_code_loading(caplog, server, agent_factory, client, environment):
    """
    Test goals:
    1. ensure the agent doesn't re-load the same code if not required
       1a. because the resource-version is exactly the same
       1b. because the underlying code is the same
    even when loading is done in very short succession
    """

    caplog.set_level(DEBUG)

    def make_source_structure(into, file, module, source):
        sha1sum = hashlib.new("sha1")
        sha1sum.update(source.encode())
        hv: str = sha1sum.hexdigest()
        into[hv] = [file, module, source, []]
        return hv

    codea = """
def test():
    return 10
    """

    codeb = """
def test():
    return 10
def xx():
    pass
    """

    sources = {}
    sources2 = {}
    hv1 = make_source_structure(sources, "inmanta_plugins/test/__init__.py", "inmanta_plugins.test", codea)
    hv2 = make_source_structure(sources2, "inmanta_plugins/tests/__init__.py", "inmanta_plugins.tests", codeb)

    res = await client.upload_code(tid=environment, id=5, resource="test::Test", sources=sources)
    assert res.code == 200

    # 2 identical versions
    res = await client.upload_code(tid=environment, id=5, resource="test::Test2", sources=sources)
    assert res.code == 200
    res = await client.upload_code(tid=environment, id=6, resource="test::Test2", sources=sources)
    assert res.code == 200

    # two distinct versions
    res = await client.upload_code(tid=environment, id=5, resource="test::Test3", sources=sources)
    assert res.code == 200
    res = await client.upload_code(tid=environment, id=6, resource="test::Test3", sources=sources2)
    assert res.code == 200

    agent: Agent = await agent_factory(
        environment=environment, agent_map={"agent1": "localhost"}, hostname="host", agent_names=["agent1"], code_loader=True
    )

    r1 = agent.ensure_code(
        environment=environment,
        version=5,
        resource_types=["test::Test", "test::Test2", "test::Test3"],
    )

    r2 = agent.ensure_code(environment=environment, version=5, resource_types=["test::Test", "test::Test2"])

    r3 = agent.ensure_code(environment=environment, version=6, resource_types=["test::Test2", "test::Test3"])

    await gather(r1, r2, r3)

    # Test 1 is deployed once, as seen by the agent
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, "Installing handler test::Test 5").contains(
        "inmanta.agent.agent", DEBUG, "Installed handler test::Test 5"
    ).contains("inmanta.agent.agent", DEBUG, "Code already present for test::Test 5").assert_not(
        "inmanta", DEBUG, "test::Test "
    )

    # Test 2 is deployed twice, as seen by the agent
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, "Installing handler test::Test2 5")
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, "Installing handler test::Test2 6")

    # Loader only loads source1 once
    LogSequence(caplog).contains("inmanta.loader", INFO, f"Deploying code (hv={hv1}, module=inmanta_plugins.test)").assert_not(
        "inmanta.loader", INFO, f"Deploying code (hv={hv1}, module=inmanta_plugins.test)"
    )

    # Loader only loads source1 once
    LogSequence(caplog).contains("inmanta.loader", INFO, f"Deploying code (hv={hv2}, module=inmanta_plugins.tests)").assert_not(
        "inmanta.loader", INFO, f"Deploying code (hv={hv2}, module=inmanta_plugins.tests)"
    )

    # Test 3 is deployed twice, as seen by the agent and the loader
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, "Installing handler test::Test3 5")
    LogSequence(caplog).contains("inmanta.agent.agent", DEBUG, "Installing handler test::Test3 6")
