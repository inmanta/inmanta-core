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
import sys
import uuid

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
from forking_agent.ipc_commands import Echo, GetConfig, GetName, TestLoader
from inmanta.agent import executor
from inmanta.agent.executor import ExecutorBlueprint
from inmanta.agent.forking_executor import MPManager
from inmanta.data import PipConfig
from inmanta.data.model import ModuleSourceMetadata
from inmanta.protocol.ipc_light import ConnectionLost
from utils import NOISY_LOGGERS, log_contains, retry_limited


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


async def test_executor_server(set_custom_executor_policy, mpmanager: MPManager, client, environment, caplog):
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
    simplest_blueprint = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=inmanta.data.PipConfig(),
        requirements=[],
        sources=[],
        python_version=sys.version_info[:2],
    )  # No pip
    simplest = await manager.get_executor("agent1", "test", [executor.ModuleInstallSpec("test", "123456", simplest_blueprint)])

    # check communications
    result = await simplest.call(Echo(["aaaa"]))
    assert ["aaaa"] == result
    # check config copying from parent to child
    result = await simplest.call(GetConfig("test", "aaa"))
    assert "bbbb" == result

    # Make a more complete venv
    # Direct: source is sent over directly
    direct_content = """
def test():
   return "DIRECT"
    """.encode(
        "utf-8"
    )
    direct = inmanta.data.model.ModuleSource(
        metadata=ModuleSourceMetadata(
            name="inmanta_plugins.test.testA",
            hash_value=inmanta.util.hash_file(direct_content),
            is_byte_code=False,
        ),
        source=direct_content,
    )
    # Via server: source is sent via server
    server_content = """
def test():
   return "server"
""".encode(
        "utf-8"
    )
    server_content_hash = inmanta.util.hash_file(server_content)
    via_server = inmanta.data.model.ModuleSource(
        metadata=ModuleSourceMetadata(
            name="inmanta_plugins.test.testB",
            hash_value=server_content_hash,
            is_byte_code=False,
        ),
        source=server_content,
    )
    # Upload
    res = await client.upload_file(id=server_content_hash, content=base64.b64encode(server_content).decode("ascii"))
    assert res.code == 200

    # Dummy executor to test executor cap:
    # Create this one first to make sure this is the one being stopped
    # when the cap is reached
    dummy = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=inmanta.data.PipConfig(use_system_config=True),
        requirements=["lorem"],
        sources=[direct],
        python_version=sys.version_info[:2],
    )
    # Full config: 2 source files, one python dependency
    full = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=inmanta.data.PipConfig(use_system_config=True),
        requirements=["lorem"],
        sources=[direct, via_server],
        python_version=sys.version_info[:2],
    )

    # Full runner install requires pip install, this can be slow, so we build it first to prevent the other one from timing out
    oldest_executor = await manager.get_executor("agent2", "internal:", [executor.ModuleInstallSpec("test", 1, dummy)])
    full_runner = await manager.get_executor("agent2", "internal:", [executor.ModuleInstallSpec("test:DDD:Test", 1, full)])

    assert oldest_executor.id in manager.pool

    # assert loaded
    result2 = await full_runner.call(TestLoader())
    assert ["DIRECT", "server"] == result2

    # assert they are distinct
    assert await simplest.call(GetName()) == simplest_blueprint.blueprint_hash()
    assert await full_runner.call(GetName()) == full.blueprint_hash()

    # Request a third executor:
    # The executor cap is reached -> check that the oldest executor got correctly stopped
    dummy = executor.ExecutorBlueprint(
        environment_id=uuid.UUID(environment),
        pip_config=inmanta.data.PipConfig(use_system_config=True),
        requirements=["lorem"],
        sources=[via_server],
        python_version=sys.version_info[:2],
    )

    async def oldest_gone():
        return oldest_executor not in manager.agent_map["agent2"]

    with caplog.at_level(logging.DEBUG):
        _ = await manager.get_executor("agent2", "internal:", [executor.ModuleInstallSpec("test::Test", "1", dummy)])
        assert not oldest_executor.running
        assert full_runner.running
        await retry_limited(oldest_gone, 1)
        log_contains(
            caplog,
            "inmanta.executor",
            logging.DEBUG,
            ("Reached executor cap for agent agent2. Stopping oldest executor "),
        )

    # Assert shutdown and back up
    stopped = await mpmanager.stop_for_agent("agent2")
    # prevent leaking futures
    for x in stopped:
        await x.join()
    await retry_limited(lambda: len(manager.agent_map["agent2"]) == 0, 10)

    full_runner = await manager.get_executor("agent2", "internal:", [executor.ModuleInstallSpec("test::Test", "1", full)])

    await retry_limited(lambda: len(manager.agent_map["agent2"]) == 1, 1)

    await simplest.request_shutdown()
    await simplest.join()

    async def check_connection_lost() -> bool:
        return await simplest.call(GetName()) != simplest_blueprint.blueprint_hash()

    with pytest.raises(ConnectionLost):
        await retry_limited(check_connection_lost, 1)

    with pytest.raises(ImportError):
        # we aren't leaking into this venv
        import lorem  # noqa: F401, F811

    async def check_automatic_clean_up() -> bool:
        return len(manager.agent_map["agent2"]) == 0

    assert len(manager.agent_map["agent2"]) != 0

    with caplog.at_level(logging.DEBUG):
        await retry_limited(check_automatic_clean_up, 10)
        log_contains(
            caplog,
            "inmanta.agent.resourcepool",
            logging.DEBUG,
            ("executor for agent2 will be shutdown because it was inactive for "),
        )

    # We can get `Caught subprocess termination from unknown pid: %d -> %d`
    # When we capture signals from the pip installs
    # Can't happen in real deployment as these things happen in different processes
    utils.assert_no_warning(caplog, NOISY_LOGGERS + ["asyncio"])


async def test_executor_server_dirty_shutdown(mpmanager: MPManager, caplog):
    caplog.clear()
    manager = mpmanager

    blueprint = executor.ExecutorBlueprint(
        environment_id=uuid.uuid4(),
        pip_config=inmanta.data.PipConfig(use_system_config=True),
        requirements=[],
        sources=[],
        python_version=sys.version_info[:2],
    )
    child1 = await manager.get(executor.ExecutorId("test", "Test", blueprint))

    result = await child1.call(Echo(["aaaa"]))
    assert ["aaaa"] == result
    print("Child there")

    process_name = psutil.Process(pid=child1.process.process.pid).name()
    assert process_name == f"inmanta: executor process {blueprint.blueprint_hash()} - connected"

    await asyncio.get_running_loop().run_in_executor(None, child1.process.process.kill)
    print("Kill sent")

    try:
        await asyncio.get_running_loop().run_in_executor(None, child1.process.process.join)
    except ValueError:
        # to be expected
        logging.exception("Process already gone!")
    print("Child gone")

    with pytest.raises(ConnectionLost):
        await child1.call(Echo(["aaaa"]))

    utils.assert_no_warning(caplog)


def test_hash_with_duplicates():
    env_id = uuid.uuid4()
    source = inmanta.data.model.ModuleSource(
        metadata=ModuleSourceMetadata(
            name="test",
            hash_value="aaaaa",
            is_byte_code=False,
        ),
        source="foo".encode(),
    )
    requirement = "setuptools"
    simple = ExecutorBlueprint(
        environment_id=env_id,
        pip_config=PipConfig(),
        requirements=[requirement],
        sources=[source],
        python_version=sys.version_info[:2],
    )
    duplicated = ExecutorBlueprint(
        environment_id=env_id,
        pip_config=PipConfig(),
        requirements=[requirement, requirement],
        sources=[source, source],
        python_version=sys.version_info[:2],
    )
    assert duplicated == simple
    assert duplicated.blueprint_hash() == simple.blueprint_hash()
