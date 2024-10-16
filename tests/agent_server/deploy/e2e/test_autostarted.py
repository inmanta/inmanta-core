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
import multiprocessing
import os
import time
import uuid
from functools import partial
from uuid import UUID

import psutil
import pytest

from inmanta import config, const, data
from inmanta.agent import Agent
from inmanta.config import Config
from inmanta.const import AGENT_SCHEDULER_ID, AgentAction
from inmanta.server.bootloader import InmantaBootloader
from inmanta.util import get_compiler_version
from utils import _wait_until_deployment_finishes, resource_action_consistency_check, retry_limited

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

    assert len(result.result["agents"]) == 2
    expected_agents = {e["name"] for e in result.result["agents"]}
    assert expected_agents == {const.AGENT_SCHEDULER_ID, "agent1"}


@pytest.mark.parametrize(
    "agent_deploy_interval",
    ["2", "*/2 * * * * * *"],
)
async def test_spontaneous_deploy(
    server,
    client,
    agent,
    resource_container,
    environment,
    clienthelper,
    caplog,
    agent_deploy_interval,
):
    """
    Test that a deploy run is executed every 2 seconds in the new agent
     as specified in the agent_repair_interval (using a cron or not)
    """
    with caplog.at_level(logging.DEBUG):
        resource_container.Provider.reset()

        env_id = UUID(environment)

        Config.set("config", "agent-deploy-interval", agent_deploy_interval)
        Config.set("config", "agent-deploy-splay-time", "2")
        Config.set("config", "agent-repair-interval", "0")

        # This is just so we can reuse the agent from the fixtures with the new config options
        agent._set_deploy_and_repair_intervals()
        agent._enable_time_triggers()

        resource_container.Provider.set_fail("agent1", "key1", 1)

        version = await clienthelper.get_version()

        resources = [
            {
                "key": "key1",
                "value": "value1",
                "id": "test::Resource[agent1,key=key1],v=%d" % version,
                "purged": False,
                "send_event": False,
                "requires": [],
            }
        ]

        await clienthelper.put_version_simple(resources, version)

        # do a deploy
        start = time.time()

        result = await client.release_version(env_id, version, False)
        assert result.code == 200

        assert not result.result["model"]["deployed"]
        assert result.result["model"]["released"]
        assert result.result["model"]["total"] == 1
        assert result.result["model"]["result"] == "deploying"

        result = await client.get_version(env_id, version)
        assert result.code == 200

        await clienthelper.wait_for_deployed()

        await clienthelper.wait_full_success(env_id)

        duration = time.time() - start

        result = await client.get_version(env_id, version)
        assert result.result["model"]["done"] == 1

        assert resource_container.Provider.isset("agent1", "key1")

    # approximate check, the number of heartbeats can vary, but not by a factor of 10
    beats = [message for logger_name, log_level, message in caplog.record_tuples if "Received heartbeat from" in message]
    assert (
        len(beats) < duration * 10
    ), f"Sent {len(beats)} heartbeats over a time period of {duration} seconds, sleep mechanism is broken"


@pytest.mark.parametrize(
    "agent_repair_interval",
    [
        "2",
        "*/2 * * * * * *",
    ],
)
async def test_spontaneous_repair(server, client, agent, resource_container, environment, clienthelper, agent_repair_interval):
    """
    Test that a repair run is executed every 2 seconds in the new agent
     as specified in the agent_repair_interval (using a cron or not)
    """
    resource_container.Provider.reset()
    env_id = environment

    Config.set("config", "agent-repair-interval", agent_repair_interval)
    Config.set("config", "agent-repair-splay-time", "2")
    Config.set("config", "agent-deploy-interval", "0")

    # This is just so we can reuse the agent from the fixtures with the new config options
    agent._set_deploy_and_repair_intervals()
    agent._enable_time_triggers()
    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "purged": False,
            "send_event": False,
            "requires": [],
        },
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    # do a deploy
    result = await client.release_version(env_id, version, True, const.AgentTriggerMethod.push_full_deploy)
    assert result.code == 200
    assert not result.result["model"]["deployed"]
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "deploying"

    result = await client.get_version(env_id, version)
    assert result.code == 200

    await clienthelper.wait_full_success(env_id)

    async def verify_deployment_result():
        result = await client.get_version(env_id, version)
        # A repair run may put one resource from the deployed state to the deploying state.
        assert len(resources) - 1 <= result.result["model"]["done"] <= len(resources)

        assert resource_container.Provider.isset("agent1", "key1")
        assert resource_container.Provider.get("agent1", "key1") == "value1"

    await verify_deployment_result()

    # Manual change
    resource_container.Provider.set("agent1", "key1", "another_value")

    # Wait until repair restores the state
    def repaired() -> bool:
        return resource_container.Provider.get("agent1", "key1") == "value1"

    await retry_limited(repaired, 10)

    await verify_deployment_result()
    await resource_action_consistency_check()


@pytest.fixture
def ensure_resource_tracker_is_started() -> None:
    """
    In POSIX, when you spawn a process, a resource tracker is also created so by doing this, we can assert some facts
    such as the number of processes, ...
    """
    context = multiprocessing.get_context("spawn")
    process = context.Process(target=print, args=(None,))
    process.start()
    process.join()
    assert process.exitcode == 0
    process.close()


def retrieve_mapping_process(current_processes: list[psutil.Process]) -> dict[str, list[psutil.Process]]:
    """
    Create a mapping of the current snapshot of processes that have been started by Pytest

    :param current_processes: Current processes
    """
    inmanta_fork_server = []
    inmanta_executor = []
    postgres_processes = []
    python_processes = []
    other_processes = []

    for process in current_processes:
        match process.name():
            case "inmanta: multiprocessing fork server":
                inmanta_fork_server.append(process)
            case executor if "inmanta: executor process" in executor:
                inmanta_executor.append(process)
            case "python":
                python_processes.append(process)
            case "pg_ctl":
                postgres_processes.append(process)
            case _:
                other_processes.append(process)

    return {
        "inmanta fork server": inmanta_fork_server,
        "inmanta executor": inmanta_executor,
        "python": python_processes,
        "pg_ctl": postgres_processes,
        "other": other_processes,
    }


def wait_for_terminated_status(current_children: list[psutil.Process], expected_terminated_process: int = 1) -> bool:
    """
    Check that the number of terminated processes matches the expected ones

    :param current_children: Current processes
    :param expected_terminated_process: How many processes should be "terminated"
    """
    terminated_process = []
    for process in current_children:
        try:
            if process.status() == "terminated":
                terminated_process.append(process)
        except psutil.NoSuchProcess:
            terminated_process.append(None)

    logger.warning(f"{terminated_process} - {current_children}")
    return len(terminated_process) == expected_terminated_process


@pytest.fixture
async def ensure_consistent_starting_point(agent: Agent, ensure_resource_tracker_is_started: None) -> int:
    """
    Make sure that every test that uses this fixture will begin in a consistent, i.e.:
        - 2 processes: a postgres server and the scheduler
        - 3 processes:
            - a postgres server, the scheduler and the resource tracker
            - a postgres server, the scheduler and one inmanta fork server (unrelated to the new scheduler)
        - 4 processes: a postgres server, the scheduler, one inmanta fork server and the resource tracker

    :param agent: The agent fixture (that we want to stop before running the test)
    :param ensure_resource_tracker_is_started: The fixture that creates a Resource Tracker process
    """

    def is_consistent_state(current_processes: list[psutil.Process], process_mapping: dict[str, list[psutil.Process]]) -> bool:
        """
        Returns True if we are in one of the above situation, False otherwise

        :param current_processes: Current processes
        :param process_mapping: Current mapping of processes
        """
        match len(current_processes):
            case 2:
                return len(process_mapping["pg_ctl"]) == 1 and len(process_mapping["python"]) == 1
            case 3:
                return (
                    len(process_mapping["pg_ctl"]) == 1
                    and len(process_mapping["python"]) == 2
                    or len(process_mapping["pg_ctl"]) == 1
                    and len(process_mapping["python"]) == 1
                    and len(process_mapping["inmanta fork server"]) == 1
                )
            case 4:
                return (
                    len(process_mapping["pg_ctl"]) == 1
                    and len(process_mapping["python"]) == 2
                    and len(process_mapping["inmanta fork server"]) == 1
                )
            case _:
                return False

    async def wait_for_consistent_state() -> bool:
        """
        Wait for a consistent state
        """
        pre_start_children = get_process_state(current_pid)
        assert len(pre_start_children) == 1
        assert len(pre_start_children.values()) == 1
        old_children = list(pre_start_children.values())[0]
        mapping_process = retrieve_mapping_process(old_children)

        return is_consistent_state(current_processes=old_children, process_mapping=mapping_process)

    current_pid = os.getpid()
    await agent.stop()
    await retry_limited(wait_for_consistent_state, timeout=10)
    return current_pid


def get_process_state(current_pid: int) -> dict[psutil.Process, list[psutil.Process]]:
    """
    Retrieves the current list of processes running under this process

    :param current_pid: The PID of this process
    """
    return {process: process.children(recursive=True) for process in psutil.process_iter() if process.pid == current_pid}


@pytest.mark.parametrize(
    "auto_start_agent,should_time_out,time_to_sleep,", [(True, False, 2), (True, True, 120)]
)  # this overrides a fixture to allow the agent to fork!
async def test_halt_deploy(
    snippetcompiler,
    server,
    ensure_consistent_starting_point: int,
    client,
    clienthelper,
    environment,
    no_agent_backoff,
    auto_start_agent: bool,
    should_time_out: bool,
    time_to_sleep: int,
):
    """
    Verify that the new scheduler can actually halt an ongoing deployment and can resume it when the user requests it
    """
    current_pid = ensure_consistent_starting_point

    env = await data.Environment.get_by_id(uuid.UUID(environment))
    agent_name = "agent1"
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", agent_name: ""})
    await env.set(data.AUTOSTART_ON_START, True)

    config.Config.set("config", "environment", environment)

    start_children = get_process_state(current_pid)
    assert len(start_children) == 1
    assert len(start_children.values()) == 1
    current_children = list(start_children.values())[0]
    for children in current_children:
        assert children.is_running()

    pre_existent_children = {e.pid for e in current_children}

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

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 1
    assert result.result["agents"][0]["name"] == AGENT_SCHEDULER_ID
    assert result.result["agents"][0]["state"] == "up"
    assert not result.result["agents"][0]["paused"]

    try:
        await _wait_until_deployment_finishes(client, environment, version)
        assert not should_time_out, f"This was supposed to time out with a deployment sleep set to {time_to_sleep}!"
    except (asyncio.TimeoutError, AssertionError):
        result = await client.list_agents(tid=environment)
        assert result.code == 200
        assert should_time_out, f"This wasn't supposed to time out with a deployment sleep set to {time_to_sleep}!"
    finally:
        children_after_deployment = get_process_state(current_pid)

    assert len(children_after_deployment) == 1
    assert len(children_after_deployment.values()) == 1
    current_children_after_deployment: list[psutil.Process] = list(children_after_deployment.values())[0]
    # The resource tracker, the fork server and the new executor should be there
    expected_additional_children_after_deployment = 3
    assert (
        len(current_children_after_deployment) == len(pre_existent_children) + expected_additional_children_after_deployment
    ), (
        "These processes should be present: Pg_ctl, the Server, the Scheduler, the fork server and the actual agent! "
        f"Actual state: {current_children_after_deployment}"
    )
    for children in current_children_after_deployment:
        assert children.is_running()

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 1

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 2
    expected_agents_status = {e["name"]: e["paused"] for e in result.result["agents"]}
    assert set(expected_agents_status.keys()) == {const.AGENT_SCHEDULER_ID, "agent1"}
    assert not expected_agents_status[const.AGENT_SCHEDULER_ID]
    assert not expected_agents_status["agent1"]

    result = await client.halt_environment(tid=environment)
    assert result.code == 200

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 2
    expected_agents_status = {e["name"]: e["paused"] for e in result.result["agents"]}
    assert set(expected_agents_status.keys()) == {const.AGENT_SCHEDULER_ID, "agent1"}
    assert expected_agents_status[const.AGENT_SCHEDULER_ID]
    assert expected_agents_status["agent1"]

    halted_children = get_process_state(current_pid)
    assert len(halted_children) == 1
    assert len(halted_children.values()) == 1
    current_halted_children = list(halted_children.values())[0]

    await retry_limited(
        wait_for_terminated_status, timeout=const.EXECUTOR_GRACE_HARD + 2, current_children=current_children_after_deployment
    )

    assert len(current_halted_children) == len(current_children_after_deployment) - 1, (
        "These processes should be present: Pg_ctl, the Server, the Scheduler and the fork server. "
        "The agent created by the scheduler should have been killed!"
    )
    for children in current_halted_children:
        assert children.is_running()

    await client.resume_environment(environment)

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 2
    expected_agents_status = {e["name"]: e["paused"] for e in result.result["agents"]}
    assert set(expected_agents_status.keys()) == {const.AGENT_SCHEDULER_ID, "agent1"}
    assert not expected_agents_status[const.AGENT_SCHEDULER_ID]
    assert not expected_agents_status["agent1"]

    def testme():
        logger.warning(f"CURRENT: {list(get_process_state(current_pid).values())[0]}")
        logger.warning(f"WAS: {current_children_after_deployment}")
        return len(list(get_process_state(current_pid).values())[0]) == len(current_children_after_deployment)

    await retry_limited(testme, 10)
    await retry_limited(
        lambda: len(list(get_process_state(current_pid).values())[0]) == len(current_children_after_deployment), 10
    )

    resumed_children = get_process_state(current_pid)

    assert len(resumed_children) == 1
    assert len(resumed_children.values()) == 1
    current_resumed_children = list(resumed_children.values())[0]

    await retry_limited(lambda: len(current_resumed_children) == len(current_children_after_deployment), 10)

    assert len(current_resumed_children) == len(
        current_children_after_deployment
    ), "These processes should be present: Pg_ctl, the Server, the Scheduler, the fork server and the actual agent!"

    await retry_limited(lambda: all([children.is_running() for children in current_resumed_children]), 10)
    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 2
    expected_agents_status = {e["name"]: e["paused"] for e in result.result["agents"]}
    assert set(expected_agents_status.keys()) == {const.AGENT_SCHEDULER_ID, "agent1"}
    assert not expected_agents_status[const.AGENT_SCHEDULER_ID]
    assert not expected_agents_status["agent1"]


@pytest.mark.parametrize("auto_start_agent,", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_pause_agent_deploy(
    snippetcompiler,
    server,
    ensure_consistent_starting_point,
    client,
    clienthelper,
    environment,
    no_agent_backoff,
    auto_start_agent: bool,
):
    """
    Verify that the new scheduler can pause running agent:
        - It will make sure that the agent finishes its current task before being stopped
        - And take the remaining tasks when this agent is resumed
    """
    current_pid = ensure_consistent_starting_point

    env = await data.Environment.get_by_id(uuid.UUID(environment))
    agent_name = "agent1"
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", agent_name: ""})
    await env.set(data.AUTOSTART_ON_START, True)

    config.Config.set("config", "environment", environment)

    start_children = get_process_state(current_pid)
    assert len(start_children) == 1
    assert len(start_children.values()) == 1
    current_children = list(start_children.values())[0]
    for children in current_children:
        assert children.is_running()

    pre_existent_children = {e.pid for e in current_children}

    snippetcompiler.setup_for_snippet(
        """
import minimalv2waitingmodule

a = minimalv2waitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep=5)
b = minimalv2waitingmodule::Sleep(name="test_sleep2", agent="agent1", time_to_sleep=5)
c = minimalv2waitingmodule::Sleep(name="test_sleep3", agent="agent1", time_to_sleep=5)
""",
        autostd=True,
    )

    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    async def are_resources_deployed(deployed_resources: int = 1) -> bool:
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        deployed = summary["by_state"]["deployed"]
        logging.warning(f"SUMMARY {summary}")
        return deployed == deployed_resources

    await retry_limited(are_resources_deployed, timeout=10)
    children_after_deployment = get_process_state(current_pid)

    assert len(children_after_deployment) == 1
    assert len(children_after_deployment.values()) == 1
    current_children_after_deployment: list[psutil.Process] = list(children_after_deployment.values())[0]
    # The resource tracker, the fork server and the new executor should be there
    expected_additional_children_after_deployment = 3
    assert (
        len(current_children_after_deployment) == len(pre_existent_children) + expected_additional_children_after_deployment
    ), "These processes should be present: Pg_ctl, the Server, the Scheduler, the fork server and the actual agent!"
    for children in current_children_after_deployment:
        assert children.is_running()

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 3

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 2
    expected_agents_status = {e["name"]: e["paused"] for e in result.result["agents"]}
    assert set(expected_agents_status.keys()) == {const.AGENT_SCHEDULER_ID, "agent1"}

    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.pause.value)
    assert result.code == 200

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 2
    expected_agents_status = {e["name"]: e["paused"] for e in result.result["agents"]}
    assert set(expected_agents_status.keys()) == {const.AGENT_SCHEDULER_ID, "agent1"}
    assert not expected_agents_status[const.AGENT_SCHEDULER_ID]
    assert expected_agents_status["agent1"]

    await retry_limited(are_resources_deployed, timeout=6, deployed_resources=2)
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["total"] == 3, f"Unexpected summary: {summary}"
    assert summary["by_state"]["available"] == 1, f"Unexpected summary: {summary}"
    assert summary["by_state"]["deployed"] == 2, f"Unexpected summary: {summary}"

    await retry_limited(wait_for_terminated_status, timeout=6, interval=1, current_children=current_children_after_deployment)

    halted_children = get_process_state(current_pid)
    assert len(halted_children) == 1
    assert len(halted_children.values()) == 1
    current_halted_children = list(halted_children.values())[0]
    assert len(current_halted_children) == len(current_children_after_deployment) - 1

    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.unpause.value)
    assert result.code == 200

    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["total"] == 3, f"Unexpected summary: {summary}"
    assert (summary["by_state"]["available"] == 1 and summary["by_state"]["deploying"] == 0) or (
        summary["by_state"]["available"] == 0 and summary["by_state"]["deploying"] == 1
    ), f"Unexpected summary: {summary}"
    assert summary["by_state"]["deployed"] == 2, f"Unexpected summary: {summary}"

    resumed_children = get_process_state(current_pid)
    assert len(resumed_children) == 1
    assert len(resumed_children.values()) == 1
    current_resumed_children: list[psutil.Process] = list(resumed_children.values())[0]

    # The scheduler and the new executor should at least be there. Depending on if the inmanta fork server was already running,
    # we might have another process
    assert (
        len(current_resumed_children) == len(pre_existent_children) + expected_additional_children_after_deployment
    ), "These processes should be present: Pg_ctl, the Server, the Scheduler, the fork server and the actual agent!"
    for children in current_resumed_children:
        assert children.is_running()


@pytest.mark.parametrize("auto_start_agent,", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_agent_paused_scheduler_crash(
    snippetcompiler,
    server,
    ensure_consistent_starting_point,
    client,
    clienthelper,
    environment,
    no_agent_backoff,
    auto_start_agent: bool,
    async_finalizer,
):
    """
    Verify that the new scheduler does not alter the state of agent after a restart:
        - The agent is deploying something that takes a lot of time
        - The agent is paused
        - The server (and thus the scheduler) is (are) restarted
        - The agent should remain paused (the Scheduler shouldn't do anything after the restart)
    """
    current_pid = ensure_consistent_starting_point

    env = await data.Environment.get_by_id(uuid.UUID(environment))
    agent_name = "agent1"
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", agent_name: ""})
    await env.set(data.AUTOSTART_ON_START, True)

    config.Config.set("config", "environment", environment)

    start_children = get_process_state(current_pid)
    assert len(start_children) == 1
    assert len(start_children.values()) == 1
    current_children = list(start_children.values())[0]
    for children in current_children:
        assert children.is_running()

    pre_existent_children = {e.pid for e in current_children}

    snippetcompiler.setup_for_snippet(
        """
import minimalv2waitingmodule

a = minimalv2waitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep=120)
""",
        autostd=True,
    )

    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    async def are_resources_deploying(deployed_resources: int = 1) -> bool:
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        deployed = summary["by_state"]["deploying"]
        return deployed == deployed_resources

    await retry_limited(are_resources_deploying, 5)

    children_after_deployment = get_process_state(current_pid)
    assert len(children_after_deployment) == 1
    assert len(children_after_deployment.values()) == 1
    current_children_after_deployment: list[psutil.Process] = list(children_after_deployment.values())[0]

    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.pause.value)
    assert result.code == 200

    await asyncio.wait_for(server.stop(), timeout=20)
    ibl = InmantaBootloader(configure_logging=False)
    async_finalizer.add(partial(ibl.stop, timeout=15))
    await ibl.start()

    async def wait_for_scheduler() -> bool:
        current_children_mapping = get_process_state(current_pid)
        assert len(current_children_mapping) == 1
        assert len(current_children_mapping.values()) == 1
        current_children: list[psutil.Process] = list(current_children_mapping.values())[0]
        return len(current_children) == 3

    await retry_limited(wait_for_scheduler, 5)

    children_after_restart = get_process_state(current_pid)
    assert len(children_after_restart) == 1
    assert len(children_after_restart.values()) == 1
    current_children_children_after_restart: list[psutil.Process] = list(children_after_restart.values())[0]

    assert (
        len(current_children_children_after_restart) == len(pre_existent_children)
        and len(current_children_children_after_restart) == len(current_children_after_deployment) - 3
    ), "These processes should be present: Pg_ctl, the Server, the Scheduler and the fork server!"
    for children in current_children_children_after_restart:
        assert children.is_running()

    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["total"] == 1, f"Unexpected summary: {summary}"
    # FIXME this should be fixed -> old resource is still in deploying state, should be available
    # Uncomment this once fixed, see https://github.com/inmanta/inmanta-core/issues/8216
    # assert summary["by_state"]["available"] == 1, f"Unexpected summary: {summary}"


@pytest.mark.parametrize("auto_start_agent,", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_agent_paused_should_remain_paused_after_environment_resume(
    snippetcompiler,
    server,
    ensure_consistent_starting_point,
    client,
    clienthelper,
    environment,
    no_agent_backoff,
    auto_start_agent: bool,
):
    """
    Verify that the new scheduler does not alter the state of agent after resuming the environment (if the agent was flag to
        not be impacted by such event)
    """
    current_pid = ensure_consistent_starting_point

    env = await data.Environment.get_by_id(uuid.UUID(environment))
    agent_name = "agent1"
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", agent_name: ""})
    await env.set(data.AUTOSTART_ON_START, True)

    config.Config.set("config", "environment", environment)

    start_children = get_process_state(current_pid)
    assert len(start_children) == 1
    assert len(start_children.values()) == 1
    current_children = list(start_children.values())[0]
    for children in current_children:
        assert children.is_running()

    pre_existent_children = {e.pid for e in current_children}

    snippetcompiler.setup_for_snippet(
        """
import minimalv2waitingmodule

a = minimalv2waitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep=5)
b = minimalv2waitingmodule::Sleep(name="test_sleep2", agent="agent1", time_to_sleep=5)
c = minimalv2waitingmodule::Sleep(name="test_sleep3", agent="agent1", time_to_sleep=5)
""",
        autostd=True,
    )

    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    async def are_resources_deployed(deployed_resources: int = 1) -> bool:
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        deployed = summary["by_state"]["deployed"]
        return deployed == deployed_resources

    await retry_limited(are_resources_deployed, timeout=10)
    children_after_deployment = get_process_state(current_pid)

    assert len(children_after_deployment) == 1
    assert len(children_after_deployment.values()) == 1
    current_children_after_deployment: list[psutil.Process] = list(children_after_deployment.values())[0]
    # The resource tracker, the fork server and the new executor should be there
    expected_additional_children_after_deployment = 3
    assert (
        len(current_children_after_deployment) == len(pre_existent_children) + expected_additional_children_after_deployment
    ), "These processes should be present: Pg_ctl, the Server, the Scheduler, the fork server and the actual agent!"
    for children in current_children_after_deployment:
        assert children.is_running()

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 3

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 2
    expected_agents_status = {e["name"]: e["paused"] for e in result.result["agents"]}
    assert set(expected_agents_status.keys()) == {const.AGENT_SCHEDULER_ID, "agent1"}

    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.pause.value)
    assert result.code == 200

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 2
    expected_agents_status = {e["name"]: e["paused"] for e in result.result["agents"]}
    assert set(expected_agents_status.keys()) == {const.AGENT_SCHEDULER_ID, "agent1"}
    assert expected_agents_status["agent1"]
    assert not expected_agents_status[const.AGENT_SCHEDULER_ID]

    await retry_limited(are_resources_deployed, timeout=6, interval=1, deployed_resources=2)
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["total"] == 3, f"Unexpected summary: {summary}"
    assert summary["by_state"]["available"] == 1, f"Unexpected summary: {summary}"
    assert summary["by_state"]["deployed"] == 2, f"Unexpected summary: {summary}"

    await retry_limited(wait_for_terminated_status, timeout=10, current_children=current_children_after_deployment)

    result = await client.halt_environment(tid=environment)
    assert result.code == 200

    result = await client.agent_action(environment, name="agent1", action=AgentAction.keep_paused_on_resume.value)
    assert result.code == 200

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 2
    expected_agents_status = {e["name"]: e["paused"] for e in result.result["agents"]}
    assert set(expected_agents_status.keys()) == {const.AGENT_SCHEDULER_ID, "agent1"}

    halted_children = get_process_state(current_pid)
    assert len(halted_children) == 1
    assert len(halted_children.values()) == 1
    current_halted_children = list(halted_children.values())[0]

    await retry_limited(
        wait_for_terminated_status, timeout=const.EXECUTOR_GRACE_HARD + 2, current_children=current_children_after_deployment
    )

    assert len(current_halted_children) == len(current_children_after_deployment) - 1, (
        "These processes should be present: Pg_ctl, the Server, the Scheduler and the fork server. "
        "The agent created by the scheduler should have been killed!"
    )
    for children in current_halted_children:
        assert children.is_running()

    await client.resume_environment(environment)

    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["total"] == 3, f"Unexpected summary: {summary}"
    assert summary["by_state"]["available"] == 1, f"Unexpected summary: {summary}"
    assert summary["by_state"]["deployed"] == 2, f"Unexpected summary: {summary}"

    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == 2
    expected_agents_status = {e["name"]: e["paused"] for e in result.result["agents"]}
    assert set(expected_agents_status.keys()) == {const.AGENT_SCHEDULER_ID, "agent1"}
    assert expected_agents_status["agent1"]
    assert not expected_agents_status[const.AGENT_SCHEDULER_ID]

    resumed_children = get_process_state(current_pid)
    assert len(resumed_children) == 1
    assert len(resumed_children.values()) == 1
    current_resumed_children = list(resumed_children.values())[0]
    assert len(current_halted_children) == len(current_resumed_children), (
        "These processes should be present: Pg_ctl, the Server, the Scheduler and the fork server. "
        "The agent created by the scheduler should have been killed!"
    )
    for children in current_resumed_children:
        assert children.is_running()
