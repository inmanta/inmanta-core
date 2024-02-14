"""
    Copyright 2019 Inmanta

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
import concurrent
import hashlib
import logging
import os
import uuid

import pytest

from inmanta import config, data, protocol
from inmanta.agent import Agent, reporting
from inmanta.agent.agent import ExecutorId, ExecutorManager, VirtualEnvironmentManager
from inmanta.agent.handler import HandlerContext, InvalidOperation
from inmanta.data.model import AttributeStateChange, PipConfig
from inmanta.loader import EnvBlueprint, ModuleSource
from inmanta.resources import Id, PurgeableResource
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_SESSION_MANAGER
from inmanta.server.bootloader import InmantaBootloader
from packaging import version
from utils import PipIndex, create_python_package, retry_limited

logger = logging.getLogger(__name__)


@pytest.mark.slowtest
async def test_agent_get_status(server, environment, agent):
    clients = server.get_slice(SLICE_SESSION_MANAGER)._sessions.values()
    assert len(clients) == 1
    clients = [x for x in clients]
    client = clients[0].get_client()
    status = await client.get_status()
    status = status.get_result()
    for name in reporting.reports.keys():
        assert name in status and status[name] != "ERROR"
    assert status.get("env") is None


def test_context_changes():
    """Test registering changes in the handler context"""
    resource = PurgeableResource(Id.parse_id("std::File[agent,path=/test],v=1"))
    ctx = HandlerContext(resource)

    # use attribute change attributes
    ctx.update_changes({"value": AttributeStateChange(current="a", desired="b")})
    assert len(ctx.changes) == 1

    # use dict
    ctx.update_changes({"value": dict(current="a", desired="b")})
    assert len(ctx.changes) == 1
    assert isinstance(ctx.changes["value"], AttributeStateChange)

    # use dict with empty string
    ctx.update_changes({"value": dict(current="", desired="value")})
    assert len(ctx.changes) == 1
    assert ctx.changes["value"].current == ""
    assert ctx.changes["value"].desired == "value"

    # use tuple
    ctx.update_changes({"value": ("a", "b")})
    assert len(ctx.changes) == 1
    assert isinstance(ctx.changes["value"], AttributeStateChange)

    # use wrong arguments
    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": ("a", "b", 3)})

    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": ["a", "b"]})

    with pytest.raises(InvalidOperation):
        ctx.update_changes({"value": "test"})


@pytest.fixture(scope="function")
async def async_started_agent(server_config):
    """
    Start agent with the use_autostart_agent_map option to true.
    agent.start() is executed in the background, since connection to the server will fail.
    """
    config.Config.set("config", "use_autostart_agent_map", "true")

    env_id = uuid.uuid4()
    a = Agent(hostname="node1", environment=env_id, agent_map=None, code_loader=False)
    task = asyncio.ensure_future(a.start())
    yield a
    task.cancel()
    while not task.done():
        # The CancelledError is only thrown on the next invocation of the event loop.
        # Wait until the cancellation has finished.
        await asyncio.sleep(0)


@pytest.fixture(scope="function")
async def startable_server(server_config):
    """
    This fixture returns the bootloader of a server which is not yet started.
    """
    bootloader = InmantaBootloader()
    yield bootloader
    try:
        await bootloader.stop(timeout=15)
    except concurrent.futures.TimeoutError:
        logger.exception("Timeout during stop of the server in teardown")


async def test_agent_cannot_retrieve_autostart_agent_map(async_started_agent, startable_server, caplog):
    """
    When an agent with the config option use_autostart_agent_map set to true, cannot retrieve the autostart_agent_map
    from the server at startup, the process should retry. This test verifies that the retry happens correctly.
    """
    client = protocol.Client("client")

    def retry_occured() -> bool:
        return caplog.text.count("Failed to retrieve the autostart_agent_map setting from the server.") > 2

    # Agent cannot contact server, since server is not started yet.
    await retry_limited(retry_occured, 10)

    # Start server
    await startable_server.start()

    # Create project
    result = await client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    # Create environment
    result = await client.create_environment(project_id=project_id, name="dev", environment_id=async_started_agent.environment)
    assert result.code == 200

    # set agent in agent map
    result = await client.get_setting(tid=async_started_agent.environment, id=data.AUTOSTART_AGENT_MAP)
    assert result.code == 200
    result = await client.set_setting(
        tid=async_started_agent.environment,
        id=data.AUTOSTART_AGENT_MAP,
        value={"agent1": "localhost"} | result.result["value"],
    )
    assert result.code == 200

    # Assert agent managed to establish session with the server
    agent_manager = startable_server.restserver.get_slice(SLICE_AGENT_MANAGER)
    await retry_limited(lambda: (async_started_agent.environment, "agent1") in agent_manager.tid_endpoint_to_session, 10)


async def test_set_agent_map(server, environment, agent_factory):
    """
    This test verifies whether an agentmap is set correct when set via:
        1) The constructor
        2) Via the agent-map configuration option
    """
    env_id = uuid.UUID(environment)
    agent_map = {"agent1": "localhost"}

    # Set agentmap in constructor
    agent1 = await agent_factory(hostname="node1", environment=env_id, agent_map=agent_map)
    assert agent1.agent_map == agent_map

    # Set agentmap via config option
    config.Config.set("config", "agent-map", "agent2=localhost")
    agent2 = await agent_factory(hostname="node2", environment=env_id)
    assert agent2.agent_map == {"agent2": "localhost"}

    # When both are set, the constructor takes precedence
    config.Config.set("config", "agent-map", "agent3=localhost")
    agent3 = await agent_factory(hostname="node3", environment=env_id, agent_map=agent_map)
    assert agent3.agent_map == agent_map


async def test_hostname(server, environment, agent_factory):
    """
    This test verifies whether the hostname of an agent is set correct when set via:
        1) The constructor
        2) Via the agent-names configuration option
    """
    env_id = uuid.UUID(environment)

    # Set hostname in constructor
    agent1 = await agent_factory(hostname="node1", environment=env_id)
    assert list(agent1.get_end_point_names()) == ["node1"]

    # Set hostname via config option
    config.Config.set("config", "agent-names", "test123,test456")
    agent2 = await agent_factory(environment=env_id)
    assert sorted(list(agent2.get_end_point_names())) == sorted(["test123", "test456"])

    # When both are set, the constructor takes precedence
    agent3 = await agent_factory(hostname="node3", environment=env_id)
    assert list(agent3.get_end_point_names()) == ["node3"]


async def test_update_agent_map(server, environment, agent_factory):
    """
    If the URI of an enabled agent changes, it should still be enabled after the change
    """
    env_id = uuid.UUID(environment)
    agent_map = {"node1": "localhost"}

    agent1 = await agent_factory(hostname="node1", environment=env_id, agent_map=agent_map)
    assert agent1.agent_map == agent_map

    agent1.unpause("node1")

    await agent1._update_agent_map({"node1": "localhost2"})

    assert agent1._instances["node1"].is_enabled()


async def test_process_manager(environment, agent_factory, tmpdir) -> None:
    agent: Agent = await agent_factory(
        environment=environment, agent_map={"agent1": "localhost"}, hostname="host", agent_names=["agent1"]
    )

    pip_index = PipIndex(artifact_dir=str(tmpdir))
    create_python_package(
        name="pkg1",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "pkg1"),
        publish_index=pip_index,
    )
    create_python_package(
        name="pkg2",
        pkg_version=version.Version("1.0.0"),
        path=os.path.join(tmpdir, "pkg2"),
        publish_index=pip_index,
    )

    requirements1 = ("pkg1",)
    requirements2 = ("pkg1", "pkg2")
    pip_config = PipConfig(index_url=pip_index.url)

    blueprint1 = EnvBlueprint(pip_config=pip_config, requirements=requirements1)
    blueprint2 = EnvBlueprint(pip_config=pip_config, requirements=requirements2)
    venv_manager = VirtualEnvironmentManager()
    executor_manager = ExecutorManager(agent, venv_manager)

    # Getting a first executor will create it
    executor_1, executor_1_id = await executor_manager.get_executor("agent1", 1, blueprint1)

    assert executor_1

    assert len(executor_manager.executor_map) == 1
    assert ExecutorId("agent1", 1) == executor_1_id
    assert executor_1_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_1_id] == executor_1

    assert len(venv_manager._environment_map) == 1
    assert blueprint1 in venv_manager._environment_map
    assert venv_manager._environment_map[blueprint1] == executor_1.venv

    # Getting it again will reuse the same one
    executor_1, executor_1_id = await executor_manager.get_executor("agent1", 1, blueprint1)

    assert executor_1

    assert len(executor_manager.executor_map) == 1
    assert ExecutorId("agent1", 1) == executor_1_id
    assert executor_1_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_1_id] == executor_1

    assert len(venv_manager._environment_map) == 1
    assert blueprint1 in venv_manager._environment_map
    assert venv_manager._environment_map[blueprint1] == executor_1.venv

    # changing the config_model_version will create a new executor
    # Keeping the same blueprint will not create a new venv: same venv is used.
    executor_2, executor_2_id = await executor_manager.get_executor("agent1", 2, blueprint1)

    assert len(executor_manager.executor_map) == 2
    assert ExecutorId("agent1", 2) == executor_2_id
    assert executor_2_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_2_id] == executor_2

    assert len(venv_manager._environment_map) == 1
    assert blueprint1 in venv_manager._environment_map
    assert venv_manager._environment_map[blueprint1] == executor_2.venv

    # The requirements change: a new venv is needed
    executor_3, executor_3_id = await executor_manager.get_executor("agent1", 3, blueprint2)

    assert len(executor_manager.executor_map) == 3
    assert ExecutorId("agent1", 3) == executor_3_id
    assert executor_3_id in executor_manager.executor_map
    assert executor_manager.executor_map[executor_3_id] == executor_3

    assert len(venv_manager._environment_map) == 2
    assert blueprint2 in venv_manager._environment_map
    assert venv_manager._environment_map[blueprint2] == executor_3.venv
