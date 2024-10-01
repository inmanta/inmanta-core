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

from inmanta import config, const, data
from inmanta.const import AgentAction
from utils import _wait_until_deployment_finishes, retry_limited

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


@pytest.mark.parametrize(
    "auto_start_agent,should_time_out,time_to_sleep,", [(True, False, 2), (True, True, 120)]
)  # this overrides a fixture to allow the agent to fork!
async def test_halt_deploy(
    snippetcompiler,
    server,
    client,
    clienthelper,
    environment,
    no_agent_backoff,
    auto_start_agent: bool,
    should_time_out: bool,
    time_to_sleep: int,
):
    """
    Verify that the new scheduler can actually fork
    """
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    agent_name = "agent1"
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", agent_name: ""})
    await env.set(data.AUTOSTART_ON_START, True)

    config.Config.set("config", "environment", environment)
    current_pid = os.getpid()

    def get_process_state() -> dict[psutil.Process, list[psutil.Process]]:
        """
        Retrieves the current list of Python processes running under this process
        """
        return {process: process.children(recursive=True) for process in psutil.process_iter() if process.pid == current_pid}

    start_children = get_process_state()
    assert len(start_children) == 1
    assert len(start_children.values()) == 1
    current_children = list(start_children.values())[0]
    assert len(current_children) == 2, "There should be only 2 processes: Pg_ctl and the Server!"
    for children in current_children:
        assert children.is_running()

    snippetcompiler.setup_for_snippet(
        f"""
import minimalv2waitingmodule

a = minimalv2waitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep={time_to_sleep})
""",
        autostd=True,
    )

    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    try:
        await _wait_until_deployment_finishes(client, environment, version)
        assert not should_time_out, f"This was supposed to time out with a deployment sleep set to {time_to_sleep}!"
    except (asyncio.TimeoutError, AssertionError):
        assert should_time_out, f"This wasn't supposed to time out with a deployment sleep set to {time_to_sleep}!"
    finally:
        children_after_deployment = get_process_state()

    assert len(children_after_deployment) == 1
    assert len(children_after_deployment.values()) == 1
    current_children_after_deployment: list[psutil.Process] = list(children_after_deployment.values())[0]
    assert (
        len(current_children_after_deployment) == 5
    ), "There should be only 5 processes: Pg_ctl, the Server, the Scheduler, the fork server and the actual agent!"
    for children in current_children_after_deployment:
        assert children.is_running()

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 1

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == const.AGENT_SCHEDULER_ID

    result = await client.halt_environment(tid=environment)
    assert result.code == 200

    result = await client.list_agents(tid=environment)
    assert result.code == 200

    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == const.AGENT_SCHEDULER_ID

    halted_children = get_process_state()

    assert len(halted_children) == 1
    assert len(halted_children.values()) == 1
    current_halted_children = list(halted_children.values())[0]

    await asyncio.sleep(const.EXECUTOR_GRACE_HARD)
    await retry_limited(lambda: len(current_halted_children) == 4, 2)

    assert len(current_halted_children) == 4, (
        "There should be only 4 processes: Pg_ctl, the Server, the Scheduler and  the fork server. "
        "The agent created by the scheduler should have been killed!"
    )
    for children in current_halted_children:
        assert children.is_running()

    await client.resume_environment(environment)

    resumed_children = get_process_state()

    await asyncio.sleep(5)

    assert len(resumed_children) == 1
    assert len(resumed_children.values()) == 1
    current_resumed_children = list(resumed_children.values())[0]

    await retry_limited(lambda: len(current_resumed_children) == 5, 10)

    assert (
        len(current_resumed_children) == 5
    ), "There should be only 5 processes: Pg_ctl, the Server, the Scheduler, the fork server and the actual agent!"

    await retry_limited(lambda: all([children.is_running() for children in current_resumed_children]), 10)


# TODO h test scheduler part apart and check that everything holds there


@pytest.mark.parametrize("auto_start_agent,", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_pause_agent_deploy(
    snippetcompiler, server, client, clienthelper, environment, no_agent_backoff, auto_start_agent: bool
):
    """
    Verify that the new scheduler can actually fork
    """
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    agent_name = "agent1"
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", agent_name: ""})
    await env.set(data.AUTOSTART_ON_START, True)

    config.Config.set("config", "environment", environment)
    current_pid = os.getpid()

    def get_process_state() -> dict[psutil.Process, list[psutil.Process]]:
        """
        Retrieves the current list of Python processes running under this process
        """
        return {process: process.children(recursive=True) for process in psutil.process_iter() if process.pid == current_pid}

    start_children = get_process_state()
    assert len(start_children) == 1
    assert len(start_children.values()) == 1
    current_children = list(start_children.values())[0]
    assert len(current_children) == 2, "There should be only 2 processes: Pg_ctl and the Server!"
    for children in current_children:
        assert children.is_running()

    snippetcompiler.setup_for_snippet(
        """
import minimalv2waitingmodule

a = minimalv2waitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep=15)
b = minimalv2waitingmodule::Sleep(name="test_sleep2", agent="agent1", time_to_sleep=15)
c = minimalv2waitingmodule::Sleep(name="test_sleep3", agent="agent1", time_to_sleep=15)
""",
        autostd=True,
    )

    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    try:
        await _wait_until_deployment_finishes(client, environment, version)
    except (asyncio.TimeoutError, AssertionError):
        pass
    finally:
        children_after_deployment = get_process_state()

    assert len(children_after_deployment) == 1
    assert len(children_after_deployment.values()) == 1
    current_children_after_deployment: list[psutil.Process] = list(children_after_deployment.values())[0]
    assert (
        len(current_children_after_deployment) == 5
    ), "There should be only 5 processes: Pg_ctl, the Server, the Scheduler, the fork server and the actual agent!"
    for children in current_children_after_deployment:
        assert children.is_running()

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 3

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == const.AGENT_SCHEDULER_ID

    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.pause.value)
    assert result.code == 200

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == const.AGENT_SCHEDULER_ID

    halted_children = get_process_state()

    await asyncio.sleep(15)
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["by_state"]["available"] == 2
    assert summary["by_state"]["deployed"] == 1

    assert len(halted_children) == 1
    assert len(halted_children.values()) == 1
    current_halted_children = list(halted_children.values())[0]

    await asyncio.sleep(const.EXECUTOR_GRACE_HARD)

    def wait_for_terminated_status():
        if len(current_halted_children) == 4:
            # The process has already disappeared
            return True
        elif len(current_halted_children) == 5:
            # Or the process is still there but with a `Terminated` status
            terminated_process = []
            for process in current_halted_children:
                try:
                    if process.status() == "terminated":
                        terminated_process.append(process)
                except psutil.NoSuchProcess:
                    terminated_process.append(None)

            # Only one process should end up in terminated
            return len(terminated_process) == 1
        else:
            # Unhandled case
            return False

    await retry_limited(wait_for_terminated_status, 2)

    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.unpause.value)
    assert result.code == 200
    await asyncio.sleep(18)

    resumed_children = get_process_state()

    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["by_state"]["available"] == 0
    assert summary["by_state"]["deploying"] == 1
    assert summary["by_state"]["deployed"] == 2

    assert len(resumed_children) == 1
    assert len(resumed_children.values()) == 1
    current_resumed_children = list(resumed_children.values())[0]

    await retry_limited(lambda: len(current_resumed_children) == 5, 10)
    await retry_limited(lambda: all([children.is_running() for children in current_resumed_children]), 10)
