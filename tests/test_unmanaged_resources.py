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
from inmanta.agent import agent


async def test_discovery_resource(
    resource_container, server, client, clienthelper, environment, no_agent_backoff, async_finalizer
):
    resource_container.Provider.reset()
    myagent = agent.Agent(
        hostname="node1", environment=environment, agent_map={"agent1": "localhost", "agent2": "localhost"}, code_loader=False
    )
    await myagent.add_end_point_name("agent1")
    await myagent.add_end_point_name("agent2")
    await myagent.start()
