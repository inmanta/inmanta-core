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

from tornado import websocket

from inmanta import tracing
from inmanta.protocol import common, handle, typedmethod
from inmanta.protocol.rest.server import OpenSession, RPC_Call, RESTServer
from inmanta.server.protocol import Server, ServerSlice, SessionListener

LOGGER = logging.getLogger(__name__)


@typedmethod(path="/server_status", operation="GET")
def get_server_status() -> str:
    """Get the status of the server"""


@typedmethod(path="/agent_status", operation="GET")
def get_agent_status() -> str:
    """Get the status of the agent"""


class WSServer(SessionListener, ServerSlice):
    def __init__(self) -> None:
        ServerSlice.__init__(self, "wsserver")

    @handle(get_server_status)
    async def get_server_status(self) -> str:
        LOGGER.error("Got status call")
        return "server status"


# class WSAgent(WebsocketEndpoint):
#     def __init__(self, name: str, timeout: int = 120, reconnect_delay: int = 5) -> None:
#         super().__init__(name, timeout, reconnect_delay)
#
#     @handle(get_agent_status)
#     async def get_agent_status(self) -> str:
#         return "agent status"


async def _call(method_properties: common.MethodProperties, args: list[object], kwargs: dict[str, object]) -> dict[str, object]:
    with tracing.span(f"return_rpc.{method_properties.function.__name__}"):
        call_spec = method_properties.build_call(args, kwargs)
        call_spec.headers.update(tracing.get_context())

        return call_spec.to_dict()

        expect_reply = method_properties.reply
        try:
            if method_properties.timeout:
                return_value = await self.session.put_call(
                    call_spec, timeout=method_properties.timeout, expect_reply=expect_reply
                )
            else:
                return_value = await self.session.put_call(call_spec, expect_reply=expect_reply)
        except asyncio.CancelledError:
            return common.Result(code=500, result={"message": "Call timed out"})

        return common.Result(code=return_value["code"], result=return_value["result"])


def put_call(call_spec: common.Request, timeout: int = 10, expect_reply: bool = True) -> asyncio.Future:
    reply_id = uuid.uuid4()
    future = asyncio.Future()

    LOGGER.debug("Putting call %s: %s %s for agent %s in queue", reply_id, call_spec.method, call_spec.url, self._sid)

    if expect_reply:
        call_spec.reply_id = reply_id
        _sessionstore.add_background_task(
            _handle_timeout(
                future,
                timeout,
                f"Call {reply_id}: {call_spec.method} {call_spec.url} for agent {self._sid} timed out.",
            )
        )
        _replies[reply_id] = future
    else:
        future.set_result({"code": 200, "result": None})
    _queue.put(call_spec)

    return future


async def test_ws_2way(inmanta_config, server_config) -> None:
    """Test websocket 2-way communication"""
    rs = Server()
    server = WSServer()
    rs.add_slice(server)
    await rs.start()

    # agent = WSAgent("agent")
    # await agent.add_end_point_name("agent")
    # # await agent.start()
    #
    # await asyncio.sleep(1000)

    port = int(server_config.Config.get("server", "bind-port"))

    ws_conn = await websocket.websocket_connect(
        f"ws://localhost:{port}/v2/ws",
        ping_interval=1,
        on_message_callback=None,
    )
    # on_pong exists on the ws_conn class -> subclass and instantiate ourselves if we need the on_pong

    await ws_conn.write_message(
        OpenSession(
            environment_id=uuid.uuid4(), session_name="test", node_name="localhost", endpoint_names=["scheduler"]
        ).model_dump_json()
    )

    # build a call
    method = min(common.MethodProperties.methods["get_server_status"], key=lambda x: x.api_version)
    call_spec = method.build_call([], {})
    call_spec.headers.update(tracing.get_context())

    await ws_conn.write_message(
        RPC_Call(**call_spec.to_dict()).model_dump_json()
    )

    while True:
        msg = await ws_conn.read_message()
        if msg is None:
            break
        else:
            print(msg)
            break

    ws_conn.close()

    await rs.stop()
    # await agent.stop()
