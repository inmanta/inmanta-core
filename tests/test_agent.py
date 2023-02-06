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
import logging
import uuid

import pytest

from inmanta import config, protocol
from inmanta.agent import Agent, reporting
from inmanta.agent.handler import HandlerContext, InvalidOperation
from inmanta.data.model import AttributeStateChange
from inmanta.resources import Id, PurgeableResource
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_SESSION_MANAGER
from inmanta.server.bootloader import InmantaBootloader
from utils import retry_limited

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
    a = Agent(hostname="node1", environment=env_id, agent_map={"agent1": "localhost"}, code_loader=False)
    await a.add_end_point_name("agent1")
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
