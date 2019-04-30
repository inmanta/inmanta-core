import logging

import pytest

from agent_server.conftest import (
    get_resource,
    _deploy_resources,
    get_agent,
)
from utils import retry_limited, AsyncClosing, log_contains, log_doesnt_contain


@pytest.mark.asyncio(timeout=150)
async def test_deploy_trigger(
    server, client, resource_container, environment, caplog, no_agent_backoff
):
    """
       Test deployment of empty model
    """
    caplog.set_level(logging.INFO)
    async with AsyncClosing(get_agent(server, environment, "agent1", "agent5")):

        version = 5

        resources = [
            get_resource(version, agent="agent1"),
            get_resource(version, agent="agent2"),
            get_resource(version, agent="agent3"),
        ]

        await _deploy_resources(client, environment, resources, version, False)

        async def verify(
            result,
            a1=0,
            code=200,
            warnings=["Could not reach agents named [agent2,agent3]"],
            agents=["agent1"],
        ):
            assert result.code == code

            def is_deployed():
                return resource_container.Provider.readcount("agent1", "key1") == a1

            await retry_limited(is_deployed, 1)
            log_contains(
                caplog,
                "agent",
                logging.INFO,
                f"Agent agent1 got a trigger to update in environment {environment}",
            )
            log_doesnt_contain(
                caplog,
                "agent",
                logging.INFO,
                f"Agent agent5 got a trigger to update in environment {environment}",
            )

            assert result.result["agents"] == agents
            if warnings:
                assert sorted(result.result["metadata"]["warnings"]) == sorted(warnings)
            caplog.clear()

        async def verify_failed(
            result,
            code=400,
            message="",
            warnings=["Could not reach agents named [agent2,agent3]"],
        ):
            assert result.code == code

            log_doesnt_contain(caplog, "agent", logging.INFO, "got a trigger to update")
            if warnings:
                assert sorted(result.result["metadata"]["warnings"]) == sorted(warnings)
            assert result.result["message"] == message
            caplog.clear()

        # normal
        result = await client.deploy(environment)
        await verify(result, a1=1)

        # only agent1
        result = await client.deploy(environment, agents=["agent1"])
        await verify(result, a1=2, warnings=None)

        # only agent5 (not in model)
        result = await client.deploy(environment, agents=["agent5"])
        await verify_failed(
            result,
            404,
            "No agent could be reached",
            warnings=["Model version 5 does not contain agents named [agent5]"],
        )

        # only agent2 (not alive)
        result = await client.deploy(environment, agents=["agent2"])
        await verify_failed(
            result,
            404,
            "No agent could be reached",
            warnings=["Could not reach agents named [agent2]"],
        )

        # All of it
        result = await client.deploy(environment, agents=["agent1", "agent2", "agent5"])
        await verify(
            result,
            a1=3,
            agents=["agent1"],
            warnings=[
                "Could not reach agents named [agent2]",
                "Model version 5 does not contain agents named [agent5]",
            ],
        )
