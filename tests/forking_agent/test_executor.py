"""
    Copyright 2024 Inmanta

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

import psutil
import pytest

import inmanta.agent
import inmanta.agent.executor
import inmanta.config
import inmanta.data
import inmanta.loader
import inmanta.protocol.ipc_light
import inmanta.util
import utils
from inmanta.agent import executor
from inmanta.agent.forking_executor import CleanInactiveCommand, MPManager
from inmanta.protocol.ipc_light import ConnectionLost
from utils import retry_limited


class Echo(inmanta.protocol.ipc_light.IPCMethod[list[str], None]):
    def __init__(self, args: list[str]) -> None:
        self.args = args

    async def call(self, ctx) -> list[str]:
        logging.getLogger(__name__).info("Echo ")
        return self.args


class GetConfig(inmanta.protocol.ipc_light.IPCMethod[str, None]):
    def __init__(self, section: str, name: str) -> None:
        self.section = section
        self.name = name

    async def call(self, ctx) -> str:
        return inmanta.config.Config.get(self.section, self.name)


class GetName(inmanta.protocol.ipc_light.IPCMethod[str, None]):
    async def call(self, ctx) -> str:
        return ctx.name


class TestLoader(inmanta.protocol.ipc_light.IPCMethod[list[str], None]):
    """
    Part of assertions for test_executor_server

    Must be module level to be able to pickle it
    """

    async def call(self, ctx) -> list[str]:
        import inmanta_plugins.test.testA
        import inmanta_plugins.test.testB
        import lorem  # noqa: F401

        return [inmanta_plugins.test.testA.test(), inmanta_plugins.test.testB.test()]


@pytest.fixture
def set_custom_executor_policy():
    """
    Fixture to temporarily set the policy for executor management.
    """
    old_cap_value = inmanta.agent.config.executor_cap_per_agent.get()
    inmanta.agent.config.executor_cap_per_agent.set("1")

    old_retention_value = inmanta.agent.config.executor_retention.get()
    inmanta.agent.config.executor_retention.set("5")

    yield

    inmanta.agent.config.executor_cap_per_agent.set(str(old_cap_value))
    inmanta.agent.config.executor_retention.set(str(old_retention_value))


async def test_executor_server(set_custom_executor_policy, mpmanager: MPManager, client):
    """
    Test the MPManager, this includes

    1. copying of config
    2. building up an empty venv
    3. communicate with it
    4. build up venv with requirements, source files, ...
    5. check that code is loaded correctly

    Also test that an executor policy can be set:
        - the executor_cap_per_agent option disallows creating more than N executors.
        - the executor_retention option is used to clean up old executors.
    """
    with pytest.raises(ImportError):
        # make sure lorem isn't installed at the start of the test.
        import lorem  # noqa: F401

    manager = mpmanager
    inmanta.config.Config.set("test", "aaa", "bbbb")

    # Simple empty venv
    simplest = executor.ExecutorBlueprint(pip_config=inmanta.data.PipConfig(), requirements=[], sources=[])  # No pip
    simplest = await manager.get_executor("agent1", "test", [executor.ResourceInstallSpec("test::Test", 5, simplest)])

    # check communications
    result = await simplest.connection.call(Echo(["aaaa"]))
    assert ["aaaa"] == result
    # check config copying from parent to child
    result = await simplest.connection.call(GetConfig("test", "aaa"))
    assert "bbbb" == result

    # Make a more complete venv
    # Direct: source is sent over directly
    direct_content = """
def test():
   return "DIRECT"
    """.encode(
        "utf-8"
    )
    direct = inmanta.loader.ModuleSource(
        "inmanta_plugins.test.testA", inmanta.util.hash_file(direct_content), False, direct_content
    )
    # Via server: source is sent via server
    server_content = """
def test():
   return "server"
""".encode(
        "utf-8"
    )
    server_content_hash = inmanta.util.hash_file(server_content)
    via_server = inmanta.loader.ModuleSource("inmanta_plugins.test.testB", server_content_hash, False)
    # Upload
    res = await client.upload_file(id=server_content_hash, content=base64.b64encode(server_content).decode("ascii"))
    assert res.code == 200

    # Full config: 2 source files, one python dependency
    full = executor.ExecutorBlueprint(
        pip_config=inmanta.data.PipConfig(use_system_config=True), requirements=["lorem"], sources=[direct, via_server]
    )
    full_runner = await manager.get_executor("agent2", "internal:", [executor.ResourceInstallSpec("test::Test", 5, full)])

    # assert loaded
    result2 = await full_runner.connection.call(TestLoader())
    assert ["DIRECT", "server"] == result2

    # assert they are distinct
    assert await simplest.connection.call(GetName()) == "agent1"
    assert await full_runner.connection.call(GetName()) == "agent2"

    # Test executor cap:
    # Dummy config, different enough to require a new executor:
    dummy = executor.ExecutorBlueprint(
        pip_config=inmanta.data.PipConfig(use_system_config=True), requirements=["lorem"], sources=[direct]
    )

    with pytest.raises(Exception) as info:
        await manager.get_executor("agent2", "internal:", [executor.ResourceInstallSpec("test::Test", 5, dummy)])
    expected_output = (
        "Agent agent2 has reached the allowed executor cap of 1. Either retry later when an idle executor"
        " for this agent has been recycled or update the policy to manage executors via the EXECUTOR_CAP_PER_AGENT "
        "and EXECUTOR_RETENTION config options."
    )
    assert expected_output in str(info.value)

    # Assert shutdown and back up
    await mpmanager.stop_for_agent("agent2")
    await retry_limited(lambda: len(manager.agent_map["agent2"]) == 0, 10)

    full_runner = await manager.get_executor("agent2", "internal:", [executor.ResourceInstallSpec("test::Test", 5, full)])

    await retry_limited(lambda: len(manager.agent_map["agent2"]) != 0, 1)

    await simplest.stop()
    await simplest.join(2)
    with pytest.raises(ConnectionLost):
        await simplest.connection.call(GetName())

    with pytest.raises(ImportError):
        # we aren't leaking into this venv
        import lorem  # noqa: F401, F811

    async def perform_clean_up() -> bool:
        try:
            await full_runner.connection.call(CleanInactiveCommand(inmanta.agent.config.executor_retention.get()))
        except inmanta.protocol.ipc_light.ConnectionLost:
            # Executor was cleaned up
            pass
        return len(manager.agent_map["agent2"]) == 0

    await retry_limited(perform_clean_up, 10)


async def test_executor_server_dirty_shutdown(mpmanager: MPManager, caplog):
    manager = mpmanager

    blueprint = executor.ExecutorBlueprint(
        pip_config=inmanta.data.PipConfig(use_system_config=True), requirements=[], sources=[]
    )
    child1 = await manager.make_child_and_connect(executor.ExecutorId("test", "Test", blueprint), None)

    result = await child1.connection.call(Echo(["aaaa"]))
    assert ["aaaa"] == result
    print("Child there")

    process_name = psutil.Process(pid=child1.process.pid).name()
    assert process_name == "inmanta: executor test - connected"

    await asyncio.get_running_loop().run_in_executor(None, child1.process.kill)
    print("Kill sent")

    await asyncio.get_running_loop().run_in_executor(None, child1.process.join)
    print("Child gone")

    with pytest.raises(ConnectionLost):
        await child1.connection.call("echo", ["aaaa"])

    utils.assert_no_warning(caplog)
