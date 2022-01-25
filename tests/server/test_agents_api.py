"""
    Copyright 2021 Inmanta

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
import datetime
import json
import uuid
from operator import itemgetter
from typing import Dict, List, Optional

import pytest
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from inmanta import data
from inmanta.agent import reporting
from inmanta.server import SLICE_AGENT_MANAGER
from inmanta.server.config import get_bind_port


@pytest.fixture
async def env_with_agents(client, environment: str) -> None:
    env_uuid = uuid.UUID(environment)

    async def create_agent(
        name: str,
        paused: bool = False,
        last_failover: Optional[datetime.datetime] = None,
        unpause_on_resume: Optional[bool] = None,
        with_process: bool = False,
    ):
        id_primary = None
        if with_process:
            process_sid = uuid.uuid4()
            await data.AgentProcess(hostname=f"localhost-{name}", environment=env_uuid, sid=process_sid).insert()
            id_primary = uuid.uuid4()
            await data.AgentInstance(id=id_primary, process=process_sid, name=f"{name}-instance", tid=env_uuid).insert()
        await data.Agent(
            environment=env_uuid,
            name=name,
            id_primary=id_primary,
            paused=paused,
            last_failover=last_failover,
            unpause_on_resume=unpause_on_resume,
        ).insert()

    await create_agent(name="first_agent")  # down
    await create_agent(name="agent_with_instance1", with_process=True)  # up
    await create_agent(name="agent_with_instance2", with_process=True)  # up
    await create_agent(name="agent_with_instance3", with_process=True)  # up
    await create_agent(name="paused_agent", paused=True)  # paused
    await create_agent(name="paused_agent_with_instance", paused=True, with_process=True)  # paused
    await create_agent(name="unpause_on_resume", unpause_on_resume=True)  # down
    await create_agent(
        name="failover1", with_process=True, last_failover=(datetime.datetime.now() - datetime.timedelta(minutes=1))
    )  # up
    await create_agent(name="failover2", with_process=True, last_failover=datetime.datetime.now())  # up


@pytest.mark.asyncio
async def test_agent_list_filters(client, environment: str, env_with_agents: None) -> None:
    result = await client.get_agents(environment)
    assert result.code == 200
    assert len(result.result["data"]) == 9

    # Test status filters
    result = await client.get_agents(environment, filter={"status": "down"})
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert all([agent["status"] == "down" for agent in result.result["data"]])

    result = await client.get_agents(environment, filter={"status": "up"})
    assert result.code == 200
    assert len(result.result["data"]) == 5
    assert all([agent["status"] == "up" for agent in result.result["data"]])

    result = await client.get_agents(environment, filter={"status": "paused"})
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert all([agent["status"] == "paused" for agent in result.result["data"]])

    result = await client.get_agents(environment, filter={"status": ["paused", "up"]})
    assert result.code == 200
    assert len(result.result["data"]) == 7
    assert all([agent["status"] == "paused" or agent["status"] == "up" for agent in result.result["data"]])

    result = await client.get_agents(environment, filter={"name": "with_instance"})
    assert result.code == 200
    assert len(result.result["data"]) == 4
    assert all(["with_instance" in agent["name"] for agent in result.result["data"]])

    result = await client.get_agents(environment, filter={"process_name": "failover"})
    assert result.code == 200
    assert len(result.result["data"]) == 2
    assert all(["failover" in agent["name"] for agent in result.result["data"]])

    result = await client.get_agents(environment, filter={"name": "agent", "status": "down"})
    assert result.code == 200
    assert len(result.result["data"]) == 1


def agent_names(agents: List[Dict[str, str]]) -> List[str]:
    return [agent["name"] for agent in agents]


@pytest.mark.parametrize("order_by_column", ["name", "status", "process_name", "last_failover", "paused"])
@pytest.mark.parametrize("order", ["DESC", "ASC"])
@pytest.mark.asyncio
async def test_agents_paging(server, client, env_with_agents: None, environment: str, order_by_column: str, order: str) -> None:
    result = await client.get_agents(
        environment,
        filter={"status": ["paused", "up"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 7
    all_agents = result.result["data"]
    for agent in all_agents:
        if not agent["process_name"]:
            agent["process_name"] = ""
        if not agent["last_failover"]:
            agent["last_failover"] = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        else:
            agent["last_failover"] = datetime.datetime.strptime(agent["last_failover"], "%Y-%m-%dT%H:%M:%S.%f").replace(
                tzinfo=datetime.timezone.utc
            )
    all_agents_in_expected_order = sorted(all_agents, key=itemgetter(order_by_column, "name"), reverse=order == "DESC")
    all_agent_names_in_expected_order = agent_names(all_agents_in_expected_order)

    result = await client.get_agents(
        environment,
        limit=2,
        sort=f"{order_by_column}.{order}",
        filter={"status": ["paused", "up"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 2

    assert agent_names(result.result["data"]) == all_agent_names_in_expected_order[:2]

    assert result.result["metadata"] == {"total": 7, "before": 0, "after": 5, "page_size": 2}
    assert result.result["links"].get("next") is not None
    assert result.result["links"].get("prev") is None

    port = get_bind_port()
    base_url = "http://localhost:%s" % (port,)
    http_client = AsyncHTTPClient()

    # Test link for next page
    url = f"""{base_url}{result.result["links"]["next"]}"""
    assert "limit=2" in url
    assert "filter.status=" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(environment)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    assert agent_names(response["data"]) == all_agent_names_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 7, "before": 2, "after": 3, "page_size": 2}

    # Test link for next page
    url = f"""{base_url}{response["links"]["next"]}"""
    assert "limit=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(environment)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    next_page_agent_names = agent_names(response["data"])
    assert next_page_agent_names == all_agent_names_in_expected_order[4:6]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 7, "before": 4, "after": 1, "page_size": 2}

    # Test link for previous page
    url = f"""{base_url}{response["links"]["prev"]}"""
    assert "limit=2" in url
    request = HTTPRequest(
        url=url,
        headers={"X-Inmanta-tid": str(environment)},
    )
    response = await http_client.fetch(request, raise_error=False)
    assert response.code == 200
    response = json.loads(response.body.decode("utf-8"))
    prev_page_agent_names = agent_names(response["data"])
    assert prev_page_agent_names == all_agent_names_in_expected_order[2:4]
    assert response["links"].get("prev") is not None
    assert response["links"].get("next") is not None
    assert response["metadata"] == {"total": 7, "before": 2, "after": 3, "page_size": 2}

    result = await client.get_agents(
        environment,
        limit=100,
        sort=f"{order_by_column}.{order}",
        filter={"status": ["paused", "up"]},
    )
    assert result.code == 200
    assert len(result.result["data"]) == 7
    assert agent_names(result.result["data"]) == all_agent_names_in_expected_order

    assert result.result["metadata"] == {"total": 7, "before": 0, "after": 0, "page_size": 100}


@pytest.mark.asyncio
async def test_sorting_validation(client, environment: str, env_with_agents: None) -> None:
    sort_status_map = {
        "date.desc": 400,
        "name.asc": 200,
        "state.desc": 400,
        "state.dsc": 400,
        "failover": 400,
        "failover.asc": 400,
        "unpause_on_resume.asc": 400,
    }
    for sort, expected_status in sort_status_map.items():
        result = await client.get_agents(environment, sort=sort)
        assert result.code == expected_status


@pytest.mark.asyncio
async def test_agent_process_details(client, environment: str) -> None:
    env_uuid = uuid.UUID(environment)
    process_sid = uuid.uuid4()
    await data.AgentProcess(
        hostname="localhost-dummy", environment=env_uuid, sid=process_sid, last_seen=datetime.datetime.now()
    ).insert()
    id_primary = uuid.uuid4()
    await data.AgentInstance(id=id_primary, process=process_sid, name="dummy-instance", tid=env_uuid).insert()
    await data.Agent(
        environment=env_uuid,
        name="dummy-agent",
        id_primary=id_primary,
        paused=True,
    ).insert()

    result = await client.get_agent_process_details(environment, process_sid)
    assert result.code == 200
    assert result.result["data"]["state"] is None

    # Get with a random id
    result = await client.get_agent_process_details(environment, uuid.uuid4())
    assert result.code == 404

    # Get with report, but the process is not live
    result = await client.get_agent_process_details(environment, process_sid, report=True)
    assert result.code == 200
    assert result.result["data"]["state"] is None


@pytest.mark.asyncio
async def test_agent_process_details_with_report(server, client, environment: str, agent) -> None:
    agentmanager = server.get_slice(SLICE_AGENT_MANAGER)
    env = await data.Environment.get_by_id(uuid.UUID(environment))
    await agentmanager.ensure_agent_registered(env=env, nodename="agent1")
    result = await client.get_agents(
        environment,
    )
    assert result.code == 200
    process_id = result.result["data"][0]["process_id"]

    result = await client.get_agent_process_details(environment, process_id, report=True)
    assert result.code == 200
    status = result.result["data"]["state"]
    assert status is not None
    for name in reporting.reports.keys():
        assert name in status and status[name] != "ERROR"
