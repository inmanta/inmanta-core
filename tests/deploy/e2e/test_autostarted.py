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


    All tests related to autostarted agents go here
"""

import asyncio
import json
import logging
import multiprocessing
import os
import uuid
from dataclasses import dataclass, field
from functools import partial

import psutil
import pytest
from psutil import NoSuchProcess, Process

from inmanta import config, const, data
from inmanta.const import AgentAction
from inmanta.server import SLICE_AGENT_MANAGER, SLICE_AUTOSTARTED_AGENT_MANAGER
from inmanta.server.bootloader import InmantaBootloader
from inmanta.util import get_compiler_version
from typing_extensions import Optional
from utils import ClientHelper, retry_limited, wait_until_deployment_finishes

logger = logging.getLogger("inmanta.test.server_agent")


@dataclass(frozen=True, kw_only=True)
class SchedulerChildren:
    """
    Dataclass to represent the different processes related to the Scheduler
    """

    scheduler: Optional[psutil.Process] = None
    fork_server: Optional[psutil.Process] = None
    executors: list[psutil.Process] = field(default_factory=list)

    def __post_init__(self):
        """
        Make sure the fork server / executors cannot be defined if the Scheduler is not defined
        """
        inconsistencies = (self.scheduler is None and self.fork_server != self.scheduler) or (
            self.scheduler is None and len(self.executors) > 0
        )

        if inconsistencies:
            raise TypeError(f"Some fields have been defined even though the Scheduler is not defined: {str(self)}!")

    @property
    def children(self) -> list[psutil.Process]:
        """
        Returns all children related to the Scheduler:
            - The Scheduler, itself (if it exists)
            - The fork server (if it exists)
            - The executors
        """
        children = []
        if self.scheduler is not None:
            children.append(self.scheduler)
        if self.fork_server is not None:
            children.append(self.fork_server)
        children.extend(self.executors)

        return children


@pytest.fixture(scope="function")
async def auto_start_agent():
    # In this file, we allow auto started agents
    return True


async def setup_environment_with_agent(client, project_name):
    """
    1) Create a project with name project_name and create an environment.
    2) Deploy a model which requires one autostarted agent. The agent does not have code so it will mark the version as
       failed.
    3) Wait until the autostarted agent is up.
    """
    create_project_result = await client.create_project(project_name)
    assert create_project_result.code == 200
    project_id = create_project_result.result["project"]["id"]

    create_environment_result = await client.create_environment(project_id=project_id, name="dev")
    assert create_environment_result.code == 200
    env_id = create_environment_result.result["environment"]["id"]
    env = await data.Environment.get_by_id(uuid.UUID(env_id))

    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": ""})
    await env.set(data.AUTO_DEPLOY, True)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    await env.set(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, 0)
    await env.set(data.AUTOSTART_ON_START, True)

    clienthelper = ClientHelper(client, env_id)
    version = await clienthelper.get_version()

    resources = [
        {
            "key": "key1",
            "value": "value1",
            "id": "test::Resource[agent1,key=key1],v=%d" % version,
            "send_event": False,
            "receive_events": False,
            "purged": False,
            "requires": [],
        }
    ]

    result = await client.put_version(
        tid=env_id, version=version, resources=resources, unknowns=[], version_info={}, compiler_version=get_compiler_version()
    )
    assert result.code == 200

    # check deploy
    await wait_until_deployment_finishes(client, env_id)
    result = await client.get_version(env_id, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 1
    assert result.result["model"]["result"] == "failed"

    result = await client.list_agents(tid=env_id)
    assert result.code == 200

    while len([x for x in result.result["agents"] if x["state"] == "up"]) < 1:
        result = await client.list_agents(tid=env_id)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 1
    assert len([x for x in result.result["agents"] if x["state"] == "up"]) == 1

    return project_id, env_id


def _get_inmanta_agent_child_processes(parent_process: psutil.Process) -> list[psutil.Process]:
    def try_get_cmd(p: psutil.Process) -> str:
        try:
            return p.cmdline()
        except Exception:
            logger.warning("A child process is gone! pid=%d", p.pid)
            """If a child process is gone, p.cmdline() raises an exception"""
            return ""

    return [p for p in parent_process.children(recursive=True) if "inmanta.app" in try_get_cmd(p) and "agent" in try_get_cmd(p)]


def ps_diff_inmanta_agent_processes(original: list[psutil.Process], current_process: psutil.Process, diff: int = 0) -> None:
    current = _get_inmanta_agent_child_processes(current_process)

    def is_terminated(proc):
        try:
            Process(proc.pid)
        except NoSuchProcess:
            return True
        except Exception:
            return False
        return False

    if not len(original) + diff == len(current):
        # can be in terminated state apparently
        current = [c for c in current if not is_terminated(c)]
        original = [c for c in original if not is_terminated(c)]

    assert len(original) + diff == len(
        current
    ), """procs found:
        pre:{}
        post:{}""".format(
        original,
        current,
    )


async def test_auto_deploy_no_splay(server, client, clienthelper: ClientHelper, environment):
    """
    Verify that the new scheduler can actually fork
    """
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

    await clienthelper.wait_for_released(version)

    # check deploy
    await wait_until_deployment_finishes(client, environment)

    result = await client.get_version(environment, version)
    assert result.code == 200
    assert result.result["model"]["released"]
    assert result.result["model"]["total"] == 2

    # check if agent 1 is started by the server
    # deploy will fail because handler code is not uploaded to the server
    result = await client.list_agents(tid=environment)
    assert result.code == 200

    while len(result.result["agents"]) == 0 or result.result["agents"][0]["state"] == "down":
        result = await client.list_agents(tid=environment)
        await asyncio.sleep(0.1)

    assert len(result.result["agents"]) == 2
    assert result.result["agents"][0]["name"] == const.AGENT_SCHEDULER_ID


async def test_deploy_no_code(resource_container, client, clienthelper, environment):
    """
    Test retrieving facts from the agent when there is no handler code available. We use an autostarted agent, these
    do not have access to the handler code for the resource_container.
    """
    resource_container.Provider.reset()
    resource_container.Provider.set("agent1", "key", "value")

    # set auto deploy and push
    result = await client.set_setting(environment, data.AUTO_DEPLOY, True)
    assert result.code == 200

    version = await clienthelper.get_version()

    resource_id_wov = "test::Resource[agent1,key=key]"
    resource_id = "%s,v=%d" % (resource_id_wov, version)

    resources = [
        {
            "key": "key",
            "value": "value",
            "id": resource_id,
            "requires": [],
            "purged": False,
            "send_event": False,
            "receive_events": False,
        }
    ]

    await clienthelper.put_version_simple(resources, version, wait_for_released=True)

    async def log_any() -> bool:
        response = await client.get_resource(environment, resource_id, logs=True)
        assert response.code == 200
        result = response.result
        logging.getLogger(__name__).warning("Found results: %s", json.dumps(result["logs"], indent=1))
        return any((is_log_line(line) for line in result["logs"]))

    def is_log_line(log_line):
        return (
            log_line["action"] == "deploy"
            and log_line["status"] == "unavailable"
            and ("failed to load handler code" in log_line["messages"][-1]["msg"])
        )

    await retry_limited(log_any, 1)


@pytest.mark.skip("Test when agent pause PR is in with proper helper functions")
async def test_stop_autostarted_agents_on_environment_removal(server, client, resource_container):
    current_process = psutil.Process()
    inmanta_agent_child_processes: list[psutil.Process] = _get_inmanta_agent_child_processes(current_process)
    resource_container.Provider.reset()
    (project_id, env_id) = await setup_environment_with_agent(client, "proj")

    # One autostarted agent should running as a subprocess
    ps_diff_inmanta_agent_processes(original=inmanta_agent_child_processes, current_process=current_process, diff=1)

    result = await client.delete_environment(id=env_id)
    assert result.code == 200, result.result

    # The autostarted agent should be terminated when its environment is deleted.
    ps_diff_inmanta_agent_processes(original=inmanta_agent_child_processes, current_process=current_process, diff=0)


@pytest.mark.parametrize("delete_project", [True, False])
async def test_autostart_clear_agent_venv_on_delete(
    server, client, resource_container, project_default: str, environment: str, delete_project: bool, clienthelper
) -> None:
    """
    Ensure that the venv of an auto-started agent gets cleaned up when its environment or project is deleted.
    """
    resource_container.Provider.reset()
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await env.set(data.AUTOSTART_AGENT_MAP, {"internal": "", "agent1": ""})
    await env.set(data.AUTO_DEPLOY, True)
    await env.set(data.PUSH_ON_AUTO_DEPLOY, True)
    await env.set(data.AUTOSTART_AGENT_DEPLOY_SPLAY_TIME, 0)
    await env.set(data.AUTOSTART_ON_START, True)

    version = await clienthelper.get_version()
    await clienthelper.put_version_simple(
        [
            {
                "key": "key1",
                "value": "value1",
                "id": f"test::Resource[agent1,key=key1],v={version}",
                "send_event": False,
                "receive_events": False,
                "purged": False,
                "requires": [],
            }
        ],
        version,
    )

    # check deploy
    await wait_until_deployment_finishes(client, environment)

    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
    venv_dir_agent1 = os.path.join(autostarted_agent_manager._get_state_dir_for_agent_in_env(uuid.UUID(environment)))

    assert os.path.exists(venv_dir_agent1)

    result = await client.delete_environment(environment)
    assert result.code == 200

    if delete_project:
        result = await client.delete_project(project_default)
        assert result.code == 200

    assert not os.path.exists(venv_dir_agent1)


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

    return len(terminated_process) == expected_terminated_process


def construct_scheduler_children(current_pid: int) -> SchedulerChildren:
    """
    Retrieve and construct a `SchedulerChildren` instance that will contain processes that are related to the Scheduler
    (more precisely children). This is the list of processes that can be expected depending on if these processes actually
    exist:
        - Scheduler
        - Fork server
        - Executor(s)
    """

    def get_process_children(current_pid: int) -> list[Process]:
        """
        Retrieves the current list of processes running under this process

        :param current_pid: The PID of this process
        """
        for process in psutil.process_iter():
            if process.pid == current_pid:
                return process.children(recursive=True)

    def find_scheduler(children: list[Process]) -> Optional[Process]:
        """
        Find and return the Scheduler. Make sure only one scheduler is running

        :param children: The list of processes that are currently running
        """
        current_scheduler = None

        for child in children:
            match child.name():
                case "python" | "python3":
                    cmd_line_process = " ".join(child.cmdline())
                    if "inmanta.app" in cmd_line_process and "scheduler" in cmd_line_process:
                        assert current_scheduler is None
                        current_scheduler = child
                case _:
                    continue
        return current_scheduler

    def filter_relevant_processes(latest_scheduler: Process) -> SchedulerChildren:
        """
        Filter the list of processes by removing processes not relevant with the Scheduler. The only processes that interest
        us are:
            - inmanta: multiprocessing fork server (if it was started by the Scheduler and not the old agent)
            - inmanta: executor process
        """
        children = latest_scheduler.children(recursive=True)
        fork_server = None
        executors = []

        for child in children:
            match child.name():
                case "inmanta: multiprocessing fork server":
                    fork_server = child
                case executor if "inmanta: executor process" in executor:
                    executors.append(child)
                case "python" | "python3":
                    cmd_line_process = " ".join(child.cmdline())
                    resource_tracker_import = "from multiprocessing.resource_tracker"
                    if resource_tracker_import in cmd_line_process:
                        continue
                case _ as e:
                    assert False, f"Unexpected process: {e}"

        return SchedulerChildren(
            scheduler=latest_scheduler,
            fork_server=fork_server,
            executors=executors,
        )

    children = get_process_children(current_pid)
    latest_scheduler = find_scheduler(children)
    if latest_scheduler is None:
        return SchedulerChildren(
            scheduler=None,
            fork_server=None,
            executors=[],
        )

    return filter_relevant_processes(latest_scheduler)


async def assert_is_paused(client, environment: str, expected_agents: dict[str, bool]) -> None:
    """
    Assert that the provided agents are in the same state to the server
    """
    result = await client.list_agents(tid=environment)
    assert result.code == 200
    assert len(result.result["agents"]) == len(expected_agents)
    assert {e["name"]: e["paused"] for e in result.result["agents"]} == expected_agents


async def wait_for_consistent_children(
    current_pid: int,
    should_scheduler_be_defined: bool,
    should_fork_server_be_defined: bool,
    executor_to_be_defined: int,
) -> None:
    """
    Wait for consistent children for the Scheduler:
        - When the Scheduler is started, it can take some time before every process is actually running
        - This is especially True for the `Executor process`.
        - Besides, when the executor process is created, it can have, for a very short time, the same name as the fork server
            (because it was forked from it).
    """

    async def wait_consistent_scheduler() -> bool:
        # This can occur, when the fork server forks and for a small amount of time, there will be two fork servers
        # even though one of them is actually the executor process (will be shortly renamed)
        current = construct_scheduler_children(current_pid)
        is_scheduler_defined = current.scheduler is not None
        is_fork_server_defined = current.fork_server is not None
        return (
            (is_scheduler_defined == should_scheduler_be_defined)
            and (is_fork_server_defined == should_fork_server_be_defined)
            and (len(current.executors) == executor_to_be_defined)
        )

    await retry_limited(wait_consistent_scheduler, 10)


@pytest.mark.slowtest
@pytest.mark.parametrize(
    "auto_start_agent,should_time_out,time_to_sleep,", [(True, False, 2), (True, True, 120)]
)  # this overrides a fixture to allow the agent to fork!
async def test_halt_deploy(
    snippetcompiler,
    server,
    ensure_resource_tracker_is_started,
    client,
    clienthelper,
    environment,
    auto_start_agent: bool,
    should_time_out: bool,
    time_to_sleep: int,
):
    """
    Verify that the new scheduler can actually halt an ongoing deployment and can resume it when the user requests it
    Two cases are tested:
        - If the deployment gets through before halting the environment
        - If the deployment is taking too much time, the halting of the environment will stop the active deployment. We will
        assert that this deployment is started again once the environment is resumed
    """
    current_pid = os.getpid()

    # First, configure everything
    config.Config.set("config", "environment", environment)
    # Make sure the session with the Scheduler is there
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    assert len(agentmanager.sessions) == 1

    # Retrieve the actual processes before deploying anything
    start_state = construct_scheduler_children(current_pid)
    for child in start_state.children:
        assert child.is_running()

    snippetcompiler.setup_for_snippet(
        f"""
import minimalwaitingmodule

a = minimalwaitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep={time_to_sleep})
""",
        autostd=True,
    )

    # Now, let's deploy some resources
    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    async def are_resources_being_deployed() -> bool:
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        deploying = summary["by_state"]["deploying"]
        return deploying == 1

    # Wait for at least one resource to be in deploying
    await retry_limited(are_resources_being_deployed, timeout=5)

    # Let's check the agent table and check that agent1 is present and not paused
    await assert_is_paused(client, environment, {const.AGENT_SCHEDULER_ID: False, "agent1": False})

    # Make sure the children of the scheduler are consistent
    await wait_for_consistent_children(
        current_pid=current_pid,
        should_scheduler_be_defined=True,
        should_fork_server_be_defined=True,
        executor_to_be_defined=1,
    )

    # Wait for something to be deployed
    try:
        await clienthelper.wait_for_deployed(timeout=5)
        assert not should_time_out, f"This was supposed to time out with a deployment sleep set to {time_to_sleep}!"
    except (asyncio.TimeoutError, AssertionError):
        result = await client.list_agents(tid=environment)
        assert result.code == 200
        assert should_time_out, f"This wasn't supposed to time out with a deployment sleep set to {time_to_sleep}!"
    finally:
        # Retrieve the current processes, we should have more processes than `start_children`
        await wait_for_consistent_children(
            current_pid=current_pid,
            should_scheduler_be_defined=True,
            should_fork_server_be_defined=True,
            executor_to_be_defined=1,
        )

    state_after_deployment = construct_scheduler_children(current_pid)
    for child in state_after_deployment.children:
        assert child.is_running()

    # The number of resources for this version should match
    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 1

    # Let's check the agent table and check that agent1 is present and not paused
    await assert_is_paused(client, environment, {const.AGENT_SCHEDULER_ID: False, "agent1": False})

    # Now let's halt the environment
    result = await client.halt_environment(tid=environment)
    assert result.code == 200

    snippetcompiler.setup_for_snippet(
        f"""
    import minimalwaitingmodule

    a = minimalwaitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep={time_to_sleep})
    """,
        autostd=True,
    )
    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    # Let's recheck the agent table and check that the scheduler and agent1 are present and paused
    await assert_is_paused(client, environment, {const.AGENT_SCHEDULER_ID: True, "agent1": True})

    # Let's wait for the executor to die (
    await retry_limited(
        wait_for_terminated_status,
        timeout=const.EXECUTOR_GRACE_HARD + 2,
        current_children=state_after_deployment.children,
        expected_terminated_process=3,
    )

    # Let's recheck the number of processes after pausing the environment
    halted_state = construct_scheduler_children(current_pid)

    assert (
        len(halted_state.children) == 0
    ), "The Scheduler and the fork server and the executor created by the scheduler should have been killed!"

    result = await client.get_agents(environment)
    assert result.code == 200
    actual_data = result.result["data"]
    assert len(actual_data) == 1
    expected_data = {
        "environment": environment,
        "last_failover": actual_data[0]["last_failover"],
        "name": "agent1",
        "paused": True,
        "process_id": actual_data[0]["process_id"],
        "process_name": actual_data[0]["process_name"],
        "status": "paused",
        "unpause_on_resume": True,
    }
    assert actual_data[0] == expected_data

    await client.resume_environment(environment)

    # Let's check the agent table and check that the scheduler and agent1 are present and not paused
    await assert_is_paused(client, environment, {const.AGENT_SCHEDULER_ID: False, "agent1": False})

    if should_time_out:
        # Wait for at least one resource to be in deploying
        await retry_limited(are_resources_being_deployed, timeout=5)
        await wait_for_consistent_children(
            current_pid=current_pid,
            should_scheduler_be_defined=True,
            should_fork_server_be_defined=True,
            executor_to_be_defined=1,
        )
        current_state = construct_scheduler_children(current_pid)
        assert len(current_state.children) == len(state_after_deployment.children)

    else:
        with pytest.raises(AssertionError):  # Nothing should get deployed
            await retry_limited(are_resources_being_deployed, timeout=1)

        await wait_for_consistent_children(
            current_pid=current_pid,
            should_scheduler_be_defined=True,
            should_fork_server_be_defined=False,
            executor_to_be_defined=0,
        )


@pytest.mark.slowtest
@pytest.mark.parametrize("auto_start_agent,", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_pause_agent_deploy(
    snippetcompiler,
    server,
    ensure_resource_tracker_is_started,
    client,
    clienthelper,
    environment,
    auto_start_agent: bool,
):
    """
    Verify that the new scheduler can pause running agent:
        - It will make sure that the agent finishes its current task before being stopped
        - And take the remaining tasks when this agent is resumed
    """
    current_pid = os.getpid()

    # First, configure everything
    config.Config.set("config", "environment", environment)
    # Make sure the session with the Scheduler is there
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    assert len(agentmanager.sessions) == 1

    # Retrieve the actual processes before deploying anything
    start_state = construct_scheduler_children(current_pid)
    for children in start_state.children:
        assert children.is_running()

    snippetcompiler.setup_for_snippet(
        """
import minimalwaitingmodule

a = minimalwaitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep=5)
b = minimalwaitingmodule::Sleep(name="test_sleep2", agent="agent1", time_to_sleep=5)
c = minimalwaitingmodule::Sleep(name="test_sleep3", agent="agent1", time_to_sleep=5)
""",
        autostd=True,
    )

    # Now, let's deploy some resources
    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    async def check_resource_in_state(expected_resources: int = 1, state: str = "deployed") -> bool:
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        nr_res_desired_state = summary["by_state"][state]
        return nr_res_desired_state == expected_resources

    # Wait for at least one resource to be deployed
    await retry_limited(check_resource_in_state, timeout=10)

    # Make sure the children of the scheduler are consistent
    await wait_for_consistent_children(
        current_pid=current_pid,
        should_scheduler_be_defined=True,
        should_fork_server_be_defined=True,
        executor_to_be_defined=1,
    )

    # Retrieve the current processes, we should have more processes than `start_children`
    state_after_deployment = construct_scheduler_children(current_pid)
    for children in state_after_deployment.children:
        assert children.is_running()

    # The number of resources for this version should match
    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 3

    # Let's check the agent table and check that agent1 is present and not paused
    await assert_is_paused(client, environment, {const.AGENT_SCHEDULER_ID: False, "agent1": False})

    # Now let's pause agent1
    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.pause.value)
    assert result.code == 200

    # Let's recheck the agent table and check that agent1 is present and paused
    await assert_is_paused(client, environment, {const.AGENT_SCHEDULER_ID: False, "agent1": True})

    # Let's also check if the state of resources are consistent with what we expect:
    # The agent finished deploying resource n°2 before pausing and resource n°3
    # still needs to be deployed
    await retry_limited(check_resource_in_state, timeout=6, expected_resources=2)
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["total"] == 3, f"Unexpected summary: {summary}"
    assert summary["by_state"]["available"] == 1, f"Unexpected summary: {summary}"
    assert summary["by_state"]["deployed"] == 2, f"Unexpected summary: {summary}"

    # Let's wait for the executor to be cleaned up
    with pytest.raises(AssertionError):
        await retry_limited(check_resource_in_state, state="deploying", timeout=1, interval=0.3)

    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.unpause.value)
    assert result.code == 200

    # Everything should be back online
    await assert_is_paused(client, environment, {const.AGENT_SCHEDULER_ID: False, "agent1": False})

    # Nothing should have changed concerning the state of our resources, yet!
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["total"] == 3, f"Unexpected summary: {summary}"
    assert (summary["by_state"]["available"] == 1 and summary["by_state"]["deploying"] == 0) or (
        summary["by_state"]["available"] == 0 and summary["by_state"]["deploying"] == 1
    ), f"Unexpected summary: {summary}"
    assert summary["by_state"]["deployed"] == 2, f"Unexpected summary: {summary}"

    # Let's wait for the new executor to kick in
    await wait_for_consistent_children(
        current_pid=current_pid,
        should_scheduler_be_defined=True,
        should_fork_server_be_defined=True,
        executor_to_be_defined=1,
    )

    resumed_state = construct_scheduler_children(current_pid)
    for children in resumed_state.children:
        assert children.is_running()

    # Let's make sure that we cannot interact directly with the Scheduler agent!
    result = await client.agent_action(tid=environment, name=const.AGENT_SCHEDULER_ID, action=AgentAction.pause.value)
    assert result.code == 400, result.result
    assert (
        result.result["message"] == "Invalid request: Particular action cannot be directed towards the Scheduler agent: pause"
    ), result.result

    result = await client.get_agents(environment)
    assert result.code == 200
    actual_data = result.result["data"]
    assert len(actual_data) == 1
    expected_data = {
        "environment": environment,
        "last_failover": actual_data[0]["last_failover"],
        "name": "agent1",
        "paused": False,
        "process_id": actual_data[0]["process_id"],
        "process_name": actual_data[0]["process_name"],
        "status": "up",
        "unpause_on_resume": None,
    }
    assert actual_data[0] == expected_data


@pytest.mark.slowtest
@pytest.mark.parametrize("auto_start_agent,", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_agent_paused_scheduler_server_restart(
    snippetcompiler,
    server,
    ensure_resource_tracker_is_started,
    client,
    clienthelper,
    environment,
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
    current_pid = os.getpid()

    # First, configure everything
    config.Config.set("config", "environment", environment)
    # Make sure the session with the Scheduler is there
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    assert len(agentmanager.sessions) == 1

    # Retrieve the actual processes before deploying anything
    start_state = construct_scheduler_children(current_pid)
    for children in start_state.children:
        assert children.is_running()

    snippetcompiler.setup_for_snippet(
        """
import minimalwaitingmodule

a = minimalwaitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep=120)
""",
        autostd=True,
    )

    # Now, let's deploy a resource
    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    async def are_resources_deploying(deployed_resources: int = 1) -> bool:
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        deployed = summary["by_state"]["deploying"]
        return deployed == deployed_resources

    # Wait for this resource to be deployed
    await retry_limited(are_resources_deploying, 5)

    # Executors are reporting to be deploying before deploying the first executor, we need to wait for them to be sure that
    # something is moving
    await wait_for_consistent_children(
        current_pid=current_pid,
        should_scheduler_be_defined=True,
        should_fork_server_be_defined=True,
        executor_to_be_defined=1,
    )

    # Retrieve the current processes, we should have more processes than `start_children`
    children_after_deployment = construct_scheduler_children(current_pid)
    for children in children_after_deployment.children:
        assert children.is_running()

    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.pause.value)
    assert result.code == 200

    # Let's pretend that the server crashes
    await asyncio.wait_for(server.stop(), timeout=20)
    ibl = InmantaBootloader(configure_logging=False)
    async_finalizer.add(partial(ibl.stop, timeout=20))
    # Let's restart the server
    await ibl.start()

    # Wait for the scheduler
    await wait_for_consistent_children(
        current_pid=current_pid,
        should_scheduler_be_defined=True,
        should_fork_server_be_defined=False,
        executor_to_be_defined=0,
    )

    # Everything should be consistent in DB: the agent should still be paused
    await assert_is_paused(client, environment, {const.AGENT_SCHEDULER_ID: False, "agent1": True})

    # Let's recheck the number of processes after restarting the server
    state_after_restart = construct_scheduler_children(current_pid)
    for children in state_after_restart.children:
        assert children.is_running()

    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["total"] == 1, f"Unexpected summary: {summary}"
    assert summary["by_state"]["unavailable"] == 1, f"Unexpected summary: {summary}"


@pytest.mark.slowtest
@pytest.mark.parametrize("auto_start_agent,", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_agent_paused_should_remain_paused_after_environment_resume(
    snippetcompiler,
    server,
    ensure_resource_tracker_is_started,
    client,
    clienthelper,
    environment,
    auto_start_agent: bool,
):
    """
    Verify that the new scheduler does not alter the state of agent after resuming the environment (if the agent was flag to
        not be impacted by such event)
    """
    current_pid = os.getpid()

    # First, configure everything
    config.Config.set("config", "environment", environment)
    # Make sure the session with the Scheduler is there
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    assert len(agentmanager.sessions) == 1

    # Retrieve the actual processes before deploying anything
    start_state = construct_scheduler_children(current_pid)
    for children in start_state.children:
        assert children.is_running()

    snippetcompiler.setup_for_snippet(
        """
import minimalwaitingmodule

a = minimalwaitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep=5)
b = minimalwaitingmodule::Sleep(name="test_sleep2", agent="agent1", time_to_sleep=5)
c = minimalwaitingmodule::Sleep(name="test_sleep3", agent="agent1", time_to_sleep=5)
""",
        autostd=True,
    )

    # Now, let's deploy some resources
    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    async def are_resources_deployed(deployed_resources: int = 1) -> bool:
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        deployed = summary["by_state"]["deployed"]
        return deployed == deployed_resources

    # Wait for at least one resource to be deployed
    await retry_limited(are_resources_deployed, timeout=10)

    # Make sure the children of the scheduler are consistent
    await wait_for_consistent_children(
        current_pid=current_pid,
        should_scheduler_be_defined=True,
        should_fork_server_be_defined=True,
        executor_to_be_defined=1,
    )

    # Retrieve the current processes, we should have more processes than `start_children`
    state_after_deployment = construct_scheduler_children(current_pid)
    for children in state_after_deployment.children:
        assert children.is_running()

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 3

    # Let's check the agent table and check that agent1 is present and not paused
    await assert_is_paused(client, environment, {const.AGENT_SCHEDULER_ID: False, "agent1": False})

    result = await client.agent_action(tid=environment, name="agent1", action=AgentAction.pause.value)
    assert result.code == 200

    # Let's check the agent table and check that agent1 is present and paused
    await assert_is_paused(client, environment, {const.AGENT_SCHEDULER_ID: False, "agent1": True})

    # Wait for the current deployment of the agent to end
    await retry_limited(are_resources_deployed, timeout=6, interval=1, deployed_resources=2)

    # Let's make sure there is only one resource left to deploy
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["total"] == 3, f"Unexpected summary: {summary}"
    assert summary["by_state"]["available"] == 1, f"Unexpected summary: {summary}"
    assert summary["by_state"]["deployed"] == 2, f"Unexpected summary: {summary}"

    # Let's wait for the executor to be cleaned up
    await retry_limited(wait_for_terminated_status, timeout=10, current_children=state_after_deployment.children)

    # Let's halt the environment to be able to set `keep_paused_on_resume` flag on agent1
    result = await client.halt_environment(tid=environment)
    assert result.code == 200

    result = await client.agent_action(environment, name="agent1", action=AgentAction.keep_paused_on_resume.value)
    assert result.code == 200

    await assert_is_paused(client, environment, {const.AGENT_SCHEDULER_ID: True, "agent1": True})

    await retry_limited(
        wait_for_terminated_status,
        timeout=const.EXECUTOR_GRACE_HARD + 2,
        current_children=state_after_deployment.children,
        expected_terminated_process=3,
    )

    # Let's recheck the number of processes after pausing the environment
    halted_state = construct_scheduler_children(current_pid)
    assert (
        len(halted_state.children) == 0
    ), "The Scheduler and the fork server and the executor created by the scheduler should have been killed!"

    await client.resume_environment(environment)

    # Let's resume everything and check that the executor is not being created again
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

    # Make sure the children of the scheduler are consistent
    await wait_for_consistent_children(
        current_pid=current_pid,
        should_scheduler_be_defined=True,
        should_fork_server_be_defined=False,
        executor_to_be_defined=0,
    )

    resumed_state = construct_scheduler_children(current_pid)
    assert len(resumed_state.children) == 1, (
        "This process should be present: the Scheduler. "
        "The fork server and the executor created by the scheduler should have been killed and the agent is still paused!"
    )
    for children in resumed_state.children:
        assert children.is_running()


@pytest.mark.slowtest
@pytest.mark.parametrize("auto_start_agent,", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_pause_unpause_all_agents_deploy(
    snippetcompiler,
    server,
    ensure_resource_tracker_is_started,
    client,
    clienthelper,
    environment,
    auto_start_agent: bool,
):
    """
    Verify that the new scheduler can pause and unpause all agents
    """
    # First, configure everything
    config.Config.set("config", "environment", environment)
    # Make sure the session with the Scheduler is there
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    assert len(agentmanager.sessions) == 1

    snippetcompiler.setup_for_snippet(
        """
import minimalwaitingmodule

a = minimalwaitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep=5)
b = minimalwaitingmodule::Sleep(name="test_sleep2", agent="agent2", time_to_sleep=5)
c = minimalwaitingmodule::Sleep(name="test_sleep3", agent="agent3", time_to_sleep=5)
""",
        autostd=True,
    )

    # Now, let's deploy some resources
    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    async def check_resource_in_state(expected_resources: int = 1, state: str = "deployed") -> bool:
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        nr_res_desired_state = summary["by_state"][state]
        return nr_res_desired_state == expected_resources

    # Wait for at least one resource to be deployed
    await retry_limited(check_resource_in_state, expected_resources=3, state="deploying", timeout=10)

    result = await client.list_versions(tid=environment)
    assert result.code == 200
    assert len(result.result["versions"]) == 1
    assert result.result["versions"][0]["total"] == 3

    # Let's check the agent table and check that all agents are presents and not paused
    await assert_is_paused(
        client, environment, {const.AGENT_SCHEDULER_ID: False, "agent1": False, "agent2": False, "agent3": False}
    )

    await client.all_agents_action(tid=environment, action=AgentAction.pause.value)
    assert result.code == 200

    # Let's check the agent table and check that all agents are presents and paused
    await assert_is_paused(
        client, environment, {const.AGENT_SCHEDULER_ID: True, "agent1": True, "agent2": True, "agent3": True}
    )
    result = await client.get_agents(environment)
    assert result.code == 200
    actual_data = result.result["data"]
    assert len(actual_data) == 3
    expected_data = [
        {
            "environment": environment,
            "last_failover": actual_data[0]["last_failover"],
            "name": "agent1",
            "paused": True,
            "process_id": actual_data[0]["process_id"],
            "process_name": actual_data[0]["process_name"],
            "status": "paused",
            "unpause_on_resume": None,
        },
        {
            "environment": environment,
            "last_failover": actual_data[1]["last_failover"],
            "name": "agent2",
            "paused": True,
            "process_id": actual_data[1]["process_id"],
            "process_name": actual_data[1]["process_name"],
            "status": "paused",
            "unpause_on_resume": None,
        },
        {
            "environment": environment,
            "last_failover": actual_data[2]["last_failover"],
            "name": "agent3",
            "paused": True,
            "process_id": actual_data[2]["process_id"],
            "process_name": actual_data[2]["process_name"],
            "status": "paused",
            "unpause_on_resume": None,
        },
    ]
    assert actual_data == expected_data
    assert (actual_data[0]["process_id"] == actual_data[1]["process_id"]) and (
        actual_data[0]["process_id"] == actual_data[2]["process_id"]
    )
    assert (actual_data[0]["process_name"] == actual_data[1]["process_name"]) and (
        actual_data[0]["process_name"] == actual_data[2]["process_name"]
    )

    await client.all_agents_action(tid=environment, action=AgentAction.unpause.value)
    assert result.code == 200

    # Let's check the agent table and check that all agents are presents and not paused
    await assert_is_paused(
        client, environment, {const.AGENT_SCHEDULER_ID: False, "agent1": False, "agent2": False, "agent3": False}
    )

    result = await client.get_agents(environment)
    assert result.code == 200
    actual_data = result.result["data"]
    assert len(actual_data) == 3
    expected_data = [
        {
            "environment": environment,
            "last_failover": actual_data[0]["last_failover"],
            "name": "agent1",
            "paused": False,
            "process_id": actual_data[0]["process_id"],
            "process_name": actual_data[0]["process_name"],
            "status": "up",
            "unpause_on_resume": None,
        },
        {
            "environment": environment,
            "last_failover": actual_data[1]["last_failover"],
            "name": "agent2",
            "paused": False,
            "process_id": actual_data[1]["process_id"],
            "process_name": actual_data[1]["process_name"],
            "status": "up",
            "unpause_on_resume": None,
        },
        {
            "environment": environment,
            "last_failover": actual_data[2]["last_failover"],
            "name": "agent3",
            "paused": False,
            "process_id": actual_data[2]["process_id"],
            "process_name": actual_data[2]["process_name"],
            "status": "up",
            "unpause_on_resume": None,
        },
    ]
    assert actual_data == expected_data


@pytest.mark.slowtest
@pytest.mark.parametrize("auto_start_agent,", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_scheduler_killed(
    snippetcompiler,
    server,
    ensure_resource_tracker_is_started,
    client,
    clienthelper,
    environment,
    auto_start_agent: bool,
    async_finalizer,
):
    """
    Verify that the AgentView is updated accordingly to the state of the Scheduler:
        - If the scheduler was to crash, the agent view should reflect this on the view -> usage of down status
        - If the scheduler come back online, it will override inconsistent resource states
    """
    current_pid = os.getpid()

    # First, configure everything
    config.Config.set("config", "environment", environment)
    # Make sure the session with the Scheduler is there
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    assert len(agentmanager.sessions) == 1

    # Retrieve the actual processes before deploying anything
    start_state = construct_scheduler_children(current_pid)
    for children in start_state.children:
        assert children.is_running()

    snippetcompiler.setup_for_snippet(
        """
import minimalwaitingmodule

a = minimalwaitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep=120)
""",
        autostd=True,
    )

    # Now, let's deploy a resource
    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    async def are_resources_deploying(deployed_resources: int = 1) -> bool:
        result = await client.resource_list(environment, deploy_summary=True)
        assert result.code == 200
        summary = result.result["metadata"]["deploy_summary"]
        deployed = summary["by_state"]["deploying"]
        return deployed == deployed_resources

    # Wait for this resource to be deployed
    await retry_limited(are_resources_deploying, 5)

    # Executors are reporting to be deploying before deploying the first executor, we need to wait for them to be sure that
    # something is moving
    await wait_for_consistent_children(
        current_pid=current_pid,
        should_scheduler_be_defined=True,
        should_fork_server_be_defined=True,
        executor_to_be_defined=1,
    )

    # Retrieve the current processes, we should have more processes than `start_children`
    children_after_deployment = construct_scheduler_children(current_pid)
    for children in children_after_deployment.children:
        assert children.is_running()

    # We want to simulate a crash
    children_after_deployment.scheduler.kill()

    # We are only waiting for the scheduler to die. The executor should be cleaned up
    await retry_limited(
        wait_for_terminated_status,
        timeout=const.EXECUTOR_GRACE_HARD + 2,
        current_children=children_after_deployment.children,
        expected_terminated_process=1,
    )

    async def wait_for_down_status() -> bool:
        """
        Wait for the down status of Agent1
        """
        result = await client.get_agents(environment)
        assert result.code == 200
        actual_data = result.result["data"]
        if len(actual_data) != 1:
            return False
        return actual_data[0]["status"] == "down"

    await retry_limited(
        wait_for_down_status,
        timeout=5,
    )

    result = await client.get_agents(environment)
    assert result.code == 200
    actual_data = result.result["data"]
    assert len(actual_data) == 1
    expected_data = {
        "environment": environment,
        "last_failover": actual_data[0]["last_failover"],
        "name": "agent1",
        "paused": False,
        "process_id": actual_data[0]["process_id"],
        "process_name": actual_data[0]["process_name"],
        "status": "down",
        "unpause_on_resume": None,
    }
    assert actual_data[0] == expected_data

    await client.all_agents_action(tid=environment, action=AgentAction.pause.value)

    snippetcompiler.setup_for_snippet(
        """
    import minimalwaitingmodule

a = minimalwaitingmodule::Sleep(name="test_sleep", agent="agent1", time_to_sleep=120)
    """,
        autostd=True,
    )
    version, res, status = await snippetcompiler.do_export_and_deploy(include_status=True)
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200

    # Let's resume everything and check that the executor is not being created again
    result = await client.resource_list(environment, deploy_summary=True)
    assert result.code == 200
    summary = result.result["metadata"]["deploy_summary"]
    assert summary["by_state"]["available"] == 1, f"Unexpected summary: {summary}"
