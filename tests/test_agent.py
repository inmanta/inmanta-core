"""
    Copyright 2016 Inmanta

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
from inmanta import agent
import pytest
from utils import retry_limited
from inmanta.agent import reporting


@pytest.mark.slowtest
@pytest.mark.gen_test
def test_agent_get_status(io_loop, server, environment):
    myagent = agent.Agent(io_loop, hostname="node1", environment=environment, agent_map={"agent1": "localhost"},
                          code_loader=False)
    myagent.add_end_point_name("agent1")
    myagent.start()

    yield retry_limited(lambda: len(server._sessions) == 1, 0.5)
    clients = server._sessions.values()
    assert len(clients) == 1
    clients = [x for x in clients]
    client = clients[0].get_client()
    status = yield client.get_status()
    status = status.get_result()
    for name in reporting.reports.keys():
        assert name in status and status[name] != "ERROR"
