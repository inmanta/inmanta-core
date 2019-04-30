import logging
import time

from agent_server.conftest import get_resource, get_agent
from inmanta import config
import pytest

from utils import retry_limited, log_index


@pytest.mark.asyncio
async def test_agent_disconnect(
    resource_container, environment, server, client, async_finalizer, caplog
):
    caplog.set_level(logging.INFO)
    config.Config.set("config", "server-timeout", "1")
    config.Config.set("config", "agent-reconnect-delay", "1")
    config.Config.set("config", "agent-deploy-interval", "0")
    config.Config.set("config", "agent-repair-interval", "0")

    version = int(time.time())
    result = await client.put_version(
        tid=environment,
        version=version,
        resources=[get_resource(version)],
        unknowns=[],
        version_info={},
    )
    assert result.code == 200

    result = await client.release_version(environment, version, False)
    assert result.code == 200

    agent = await get_agent(server, environment, "agent1")
    async_finalizer.add(agent.stop)

    await server.stop()

    def disconnected():
        return not agent._instances["agent1"]._enabled

    await retry_limited(disconnected, 1)

    i = log_index(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.INFO,
        "Agent assuming primary role for agent1",
    )
    i = log_index(
        caplog,
        "inmanta.agent.agent",
        logging.WARNING,
        "Connection to server lost, taking agents offline",
        i,
    )
    log_index(
        caplog,
        "inmanta.agent.agent.agent1",
        logging.INFO,
        "Agent agent1 stopped because Connection to server lost",
        i,
    )
