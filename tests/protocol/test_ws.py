"""
Copyright 2025 Inmanta

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
import uuid

from inmanta import const
from inmanta.protocol import SessionEndpoint, handle, typedmethod, websocket
from inmanta.protocol.auth.decorators import auth
from inmanta.server.protocol import Server, ServerSlice

LOGGER = logging.getLogger(__name__)


@auth(auth_label=const.CoreAuthorizationLabel.STATUS_READ, read_only=True)
@typedmethod(path="/server_status", operation="GET")
def get_current_server_status() -> str:
    """Get the status of the server"""


@auth(auth_label=const.CoreAuthorizationLabel.STATUS_READ, read_only=True)
@typedmethod(path="/agent_status", operation="GET")
def get_current_agent_status() -> str:
    """Get the status of the agent"""


class WSServer(websocket.SessionListener, ServerSlice):
    def __init__(self) -> None:
        ServerSlice.__init__(self, "wsserver")

    @handle(get_current_server_status)
    async def get_current_server_status(self) -> str:
        LOGGER.error("Got status call")
        return "server status"


class WSAgent(SessionEndpoint):
    def __init__(self, name: str, timeout: int = 120, reconnect_delay: int = 5) -> None:
        super().__init__(name, uuid.uuid4(), timeout, reconnect_delay)

    @handle(get_current_agent_status)
    async def get_current_agent_status(self) -> str:
        return "agent status"


async def test_ws_2way(inmanta_config, server_config) -> None:
    """Test websocket 2-way communication"""
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    agent = WSAgent("agent")
    await agent.start()

    while not agent.session or not agent.session.active:
        await asyncio.sleep(0.01)

    client_a2s = agent.session.get_typed_client()
    result = await client_a2s.get_current_server_status()
    assert result == "server status"

    client_s2a = rs._transport.get_session(*agent.session.session_key).get_typed_client()
    result = await client_s2a.get_current_agent_status()
    assert result == "agent status"

    await rs.stop()
    await agent.stop()
