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

import uuid

from inmanta import data
from inmanta.agent import reporting
from inmanta.server import SLICE_AGENT_MANAGER


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
