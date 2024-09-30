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
import logging
import os
import uuid

import psutil
import pytest
from inmanta import config, const

from inmanta import const, data
from utils import _wait_until_deployment_finishes

logger = logging.getLogger("inmanta.test.server_agent")


@pytest.mark.parametrize("auto_start_agent", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_auto_deploy_no_splay(server, client, clienthelper, resource_container, environment, no_agent_backoff):
    """
    Verify that the new scheduler can actually fork
    """
    resource_container.Provider.reset()
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": ""})
    await env.set(data.AUTOSTART_ON_START, True)

    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": ["test::Resource[agent1,key=key2],v=%d" % version],
        },
        {
            "key": "key2",
            "value": "value2",
            "id": "test::Resource[agent1,key=key2],v=%d" % version,
            "send_event": False,
            "purged": False,
            "requires": [],
        },
    ]

    # set auto deploy and push
    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200

    await clienthelper.put_version_simple(resources, version)

    # check deploy
    await _wait_until_deployment_finishes(client, environment, version)
    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 2
    assert result.result["model"]["result"] == "failed"

    # check if agent 1 is started by the server
    # deploy will fail because handler code is not uploaded to the server
    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while len(result.result["agents"]) == 0 or result.result["agents"][0]["state"] == "down":
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == const.AGENT_SCHEDULER_ID


@pytest.mark.parametrize("auto_start_agent", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_halt_deploy(snippetcompiler, server, client, clienthelper, environment, no_agent_backoff):
    """
    Verify that the new scheduler can actually fork
    """
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    agent_name = "agent1"
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", agent_name: ""})
    await env.set(data.AUTOSTART_ON_START, True)

    config.Config.set("config", "environment", environment)
    current_pid = os.getpid()

    start_children = {process: process.children(recursive=True) for process in psutil.process_iter() if process.pid == current_pid}
    breakpoint()
    snippetcompiler.setup_for_snippet(
        """
import minimalv2waitingmodule

a = minimalv2waitingmodule::Sleep(name="test_sleep", agent="agent1")
""",
        autostd=True
    )

    version, res, status = await snippetcompiler.do_export_and_deploy(
        include_status=True
    )
    try:
        await _wait_until_deployment_finishes(client, environment, version)
    except Exception:
        start_exception_children = {process: process.children(recursive=True) for process in psutil.process_iter() if
                          process.pid == current_pid}
        breakpoint()

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 1

    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while len(result.result["agents"]) == 0 or result.result["agents"][0]["state"] == "down":
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == const.AGENT_SCHEDULER_ID

    def get_process_state() -> dict[psutil.Process, list[psutil.Process]]:
        """
        Retrieves the current list of Python processes running under this process
        """
        return {process: process.children(recursive=True) for process in psutil.process_iter() if process.pid == current_pid}

    process_state_before_halting = get_process_state()
    assert len(process_state_before_halting) == 1, "Only one process should be present!"
    for key, value in process_state_before_halting:
        assert len(value) == 2, "Two children should be running: Postgres + Scheduler"
    processes_iter = psutil.process_iter()
    processes = [process for process in processes_iter if process.name() == "python" or process.name() == "python3"]
    for process in psutil.process_iter():
        print(f"Process ID: {process.pid}, Name: {process.name()}")

    children = {process: process.children(recursive=True) for process in processes if process.pid == current_pid}

    result = await client.halt_environment(tid=environment)

    await asyncio.sleep(3)

    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while len(result.result["agents"]) == 0 or result.result["agents"][0]["state"] == "down":
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == const.AGENT_SCHEDULER_ID

    await client.halt_environment(environment)

    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while len(result.result["agents"]) == 0 or result.result["agents"][0]["state"] == "down":
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == const.AGENT_SCHEDULER_ID
    await asyncio.sleep(1)

    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while len(result.result["agents"]) == 0 or result.result["agents"][0]["state"] == "down":
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == const.AGENT_SCHEDULER_ID

    halted_processes_iter = psutil.process_iter()
    halted_processes = [process for process in halted_processes_iter if process.name() == "python" or process.name() == "python3"]
    for process in psutil.process_iter():
        print(f"Process ID: {process.pid}, Name: {process.name()}")

    halted_children = {process: process.children(recursive=True) for process in halted_processes}

    await client.resume_environment(environment)

    resumed_processes_iter = psutil.process_iter()
    resumed_processes = [process for process in resumed_processes_iter if process.name() == "python" or process.name() == "python3"]
    for process in psutil.process_iter():
        print(f"Process ID: {process.pid}, Name: {process.name()}")

    resumed_children = {process: process.children(recursive=True) for process in resumed_processes}
    current_id = os.getpid()
    breakpoint()

    """
    agent_client = server._slices['core.agentmanager'].get_agent_client(tid=environment, endpoint=const.AGENT_SCHEDULER_ID,
                                                 live_agent_only=False)


    result = await agent_client.trigger_read_version(tid=env.id)
    result3 = await agent_client.set_state(agent=const.AGENT_SCHEDULER_ID, enabled=True)
    breakpoint()
    """

# TODO h test scheduler part apart and check that everything holds there
# TODO here we only want to check that request still works
# TODO we need to restart the session -> ensure scheduler
