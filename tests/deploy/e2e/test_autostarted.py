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
import os
import uuid

import psutil
import pytest
from psutil import NoSuchProcess, Process

from inmanta import const, data
from inmanta.server import SLICE_AUTOSTARTED_AGENT_MANAGER
from inmanta.util import get_compiler_version
from utils import ClientHelper, retry_limited, wait_until_deployment_finishes

logger = logging.getLogger("inmanta.test.server_agent")


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
    await wait_until_deployment_finishes(client, env_id, version)
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
    await wait_until_deployment_finishes(client, environment, version)

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
    await wait_until_deployment_finishes(client, environment, version)

    autostarted_agent_manager = server.get_slice(SLICE_AUTOSTARTED_AGENT_MANAGER)
    venv_dir_agent1 = os.path.join(
        autostarted_agent_manager._get_state_dir_for_agent_in_env(uuid.UUID(environment)), "agent", "env"
    )

    assert os.path.exists(venv_dir_agent1)

    result = await client.delete_environment(environment)
    assert result.code == 200

    if delete_project:
        result = await client.delete_project(project_default)
        assert result.code == 200

    assert not os.path.exists(venv_dir_agent1)
