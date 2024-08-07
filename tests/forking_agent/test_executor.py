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
from inmanta.agent.executor import ExecutorBlueprint
from inmanta.agent.forking_executor import MPManager
from inmanta.data import PipConfig
from inmanta.protocol.ipc_light import ConnectionLost
from utils import NOISY_LOGGERS, log_contains, retry_limited


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
def set_custom_executor_policy(server_config):
    """
    Fixture to temporarily set the policy for executor management.
    """
    old_cap_value = inmanta.agent.config.agent_executor_cap.get()

    # Keep only 2 executors per agent
    inmanta.agent.config.agent_executor_cap.set("2")

    old_retention_value = inmanta.agent.config.agent_executor_retention_time.get()
    # Clean up executors after 3s of inactivity
    inmanta.agent.config.agent_executor_retention_time.set("3")

    yield

    inmanta.agent.config.agent_executor_cap.set(str(old_cap_value))
    inmanta.agent.config.agent_executor_retention_time.set(str(old_retention_value))


async def test_executor_server(set_custom_executor_policy, mpmanager: MPManager, client, caplog):
    """
    Test the MPManager, this includes

    1. copying of config
    2. building up an empty venv
    3. communicate with it
    4. build up venv with requirements, source files, ...
    5. check that code is loaded correctly

    Also test that an executor policy can be set:
        - the agent_executor_cap option correctly stops the oldest executor.
        - the agent_executor_retention_time option is used to clean up old executors.
    """

    with pytest.raises(ImportError):
        # make sure lorem isn't installed at the start of the test.
        import lorem  # noqa: F401

    manager = mpmanager
    await manager.start()

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

    # Dummy executor to test executor cap:
    # Create this one first to make sure this is the one being stopped
    # when the cap is reached
    dummy = executor.ExecutorBlueprint(
        pip_config=inmanta.data.PipConfig(use_system_config=True), requirements=["lorem"], sources=[direct]
    )
    # Full config: 2 source files, one python dependency
    full = executor.ExecutorBlueprint(
        pip_config=inmanta.data.PipConfig(use_system_config=True), requirements=["lorem"], sources=[direct, via_server]
    )

    # Full runner install requires pip install, this can be slow, so we build it first to prevent the other one from timing out
    full_runner = await manager.get_executor("agent2", "internal:", [executor.ResourceInstallSpec("test::Test", 5, full)])
    oldest_executor = await manager.get_executor("agent2", "internal:", [executor.ResourceInstallSpec("test::Test", 5, dummy)])

    assert oldest_executor.executor_id in manager.agent_map["agent2"]
    # assert loaded
    result2 = await full_runner.connection.call(TestLoader())
    assert ["DIRECT", "server"] == result2

    # assert they are distinct
    assert await simplest.connection.call(GetName()) == "agent1"
    assert await full_runner.connection.call(GetName()) == "agent2"

    # Request a third executor:
    # The executor cap is reached -> check that the oldest executor got correctly stopped
    dummy = executor.ExecutorBlueprint(
        pip_config=inmanta.data.PipConfig(use_system_config=True), requirements=["lorem"], sources=[via_server]
    )
    with caplog.at_level(logging.DEBUG):
        _ = await manager.get_executor("agent2", "internal:", [executor.ResourceInstallSpec("test::Test", 5, dummy)])
        assert oldest_executor.executor_id not in manager.agent_map["agent2"]
        log_contains(
            caplog,
            "inmanta.agent.forking_executor",
            logging.DEBUG,
            (
                f"Reached executor cap for agent agent2. Stopping oldest executor "
                f"{oldest_executor.executor_id.identity()} to make room for a new one."
            ),
        )

    # Assert shutdown and back up
    await mpmanager.stop_for_agent("agent2")
    await retry_limited(lambda: len(manager.agent_map["agent2"]) == 0, 10)

    full_runner = await manager.get_executor("agent2", "internal:", [executor.ResourceInstallSpec("test::Test", 5, full)])

    await retry_limited(lambda: len(manager.agent_map["agent2"]) == 1, 1)

    await simplest.stop()
    await simplest.join(2)
    with pytest.raises(ConnectionLost):
        await simplest.connection.call(GetName())

    with pytest.raises(ImportError):
        # we aren't leaking into this venv
        import lorem  # noqa: F401, F811

    async def check_automatic_clean_up() -> bool:
        return len(manager.agent_map["agent2"]) == 0

    with caplog.at_level(logging.DEBUG):
        await retry_limited(check_automatic_clean_up, 10)
        log_contains(
            caplog,
            "inmanta.agent.executor",
            logging.DEBUG,
            (
                f"Stopping PoolMember {full_runner.executor_id.identity()} of type {type(full_runner).__name__} "
                "because it was inactive for"
            ),
        )

    # We can get `Caught subprocess termination from unknown pid: %d -> %d`
    # When we capture signals from the pip installs
    # Can't happen in real deployment as these things happen in different processes
    utils.assert_no_warning(caplog, NOISY_LOGGERS + ["asyncio"])


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


def test_hash_with_duplicates():
    source = inmanta.loader.ModuleSource("test", "aaaaa", False, None, None)
    requirement = "setuptools"
    simple = ExecutorBlueprint(pip_config=PipConfig(), requirements=[requirement], sources=[source])
    duplicated = ExecutorBlueprint(pip_config=PipConfig(), requirements=[requirement, requirement], sources=[source, source])
    assert duplicated == simple
    assert duplicated.blueprint_hash() == simple.blueprint_hash()
