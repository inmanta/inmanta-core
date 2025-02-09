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
import enum
import logging
import time
import uuid
from typing import Annotated, Literal, Optional
from urllib import parse

import pydantic
from tornado import websocket

from inmanta import const, tracing, types, util
from inmanta.data import model
from inmanta.protocol import common, endpoints, rest

LOGGER = logging.getLogger(__name__)


class WSMessage(model.BaseModel):
    """A websocket message"""

    action: str


class OpenSession(WSMessage):
    action: Literal["OPEN_SESSION"] = "OPEN_SESSION"
    environment_id: uuid.UUID
    session_name: str
    node_name: str
    endpoint_names: list[str]


class SessionOpened(WSMessage):
    action: Literal["SESSION_OPENED"] = "SESSION_OPENED"


class CloseSession(WSMessage):
    action: Literal["CLOSE_SESSION"] = "CLOSE_SESSION"


class RPC_Call(WSMessage):
    action: Literal["RPC_CALL"] = "RPC_CALL"
    url: str
    method: str
    headers: dict[str, str]
    body: Optional[types.JsonType]
    reply_id: Optional[uuid.UUID] = None


class RPC_Reply(WSMessage):
    action: Literal["RPC_REPLY"] = "RPC_REPLY"
    reply_id: uuid.UUID
    result: types.ReturnTypes
    code: int


type WSMessages = Annotated[
    OpenSession | SessionOpened | CloseSession | RPC_Call | RPC_Reply, pydantic.Field(discriminator="action")
]


async def dispatch_method(call_targets: list[common.CallTarget], msg: RPC_Call) -> Optional[RPC_Reply]:
    """Dispatch a request from the server into the RPC code so the requests gets executed. The call results is send back
    to the server using a heartbeat reply.
    """
    method_call = common.Request(url=msg.url, method=msg.method, headers=msg.headers, body=msg.body, reply_id=msg.reply_id)

    LOGGER.debug("Received call through websocket: %s %s %s", method_call.reply_id, method_call.method, method_call.url)
    kwargs, config = rest.match_call(call_targets, method_call.url, method_call.method)

    if config is None:
        # We cannot match the call to method on this endpoint. We send a reply to report this + ensure that the session
        # does not time out
        error = "An error occurred during heartbeat method call ({} {} {}): {}".format(
            method_call.reply_id,
            method_call.method,
            method_call.url,
            "No such method",
        )
        LOGGER.error(error)
        # if reply_id is none, we don't send the reply
        if method_call.reply_id is not None:
            return RPC_Reply(
                reply_id=msg.reply_id,
                code=500,
                result={"error": error},  # TODO verify if this is the correct key to report the error
            )
        return None

    # rebuild a request so that the RPC layer can process it as if it came from a proper HTTP call
    body = method_call.body or {}
    query_string = parse.urlparse(method_call.url).query
    for key, value in parse.parse_qs(query_string, keep_blank_values=True):
        if len(value) == 1:
            body[key] = value[0].decode("latin-1")
        else:
            body[key] = [v.decode("latin-1") for v in value]

    body.update(kwargs)

    with tracing.attach_context(
        {const.TRACEPARENT: method_call.headers[const.TRACEPARENT]} if const.TRACEPARENT in method_call.headers else {}
    ):
        # do the dispatch
        response: common.Response = await rest.execute_call(config, body, method_call.headers)

    # report the result back
    if response.status_code == 500:
        msg = ""
        if response.body is not None and "message" in response.body:
            msg = response.body["message"]
        LOGGER.error(
            "An error occurred during heartbeat method call (%s %s %s): %s",
            method_call.reply_id,
            method_call.method,
            method_call.url,
            msg,
        )

    # if reply is none, we don't send the reply
    if method_call.reply_id is not None:
        return RPC_Reply(
            reply_id=msg.reply_id,
            code=response.status_code,
            result=response.body,
        )


class WebsocketFrameDecoder(util.TaskHandler[None]):
    """A close that offers an on_message to handle websocket frames and calls handlers for each event"""

    def __init__(self) -> None:
        super().__init__()
        self._message_parser = pydantic.TypeAdapter(WSMessages)
        self._session: Optional[common.Session] = None
        self._call_targets: Optional[list[common.CallTarget]] = None
        self._replies: dict[uuid.UUID, asyncio.Future[RPC_Reply]] = {}

    def set_call_targets(self, call_targets: list[common.CallTarget]) -> None:
        self._call_targets = call_targets

    def seen(self) -> None:
        """Bump the liveliness of the session"""
        if self._session:
            self._session.seen()

    def active(self) -> bool:
        """Is the session set and active?"""
        return self._session is not None and self._session.active

    def get_client(self) -> endpoints.Client:
        pass

    async def on_message(self, message: str | bytes) -> None:
        try:
            msg = self._message_parser.validate_json(message)
        except pydantic.ValidationError:
            # TODO log this
            LOGGER.exception("Invalid message")
            return

        if self._session:
            self._session.seen()

        match msg:
            case OpenSession():
                # session open request: normally only initiated by the client and received by the server
                self._session = common.Session(msg.environment_id, msg.session_name, msg.node_name, msg.endpoint_names)
                await self.on_open_session(self._session)
                self._session.confirm_open()
                await self.write_message(SessionOpened().model_dump_json())

            case SessionOpened():
                # confirmation that the session is open: server responds to the client. This opens the session to start
                # sending requests (in both directions)
                if self._session is None:
                    LOGGER.error("Received a session open for a session that is not opened yet.")
                else:
                    self._session.confirm_open()

            case CloseSession():
                if not self.active():
                    LOGGER.warning("Received a close for a session that is not active.")
                else:
                    self._session.close_session()
                    await self.on_close_session(self._session)

            case RPC_Call():
                if self.active():
                    self._session.seen()
                    # A request from the client on the server
                    self.add_background_task(self._handle_call(msg))
                # TODO: if not valid

            case RPC_Reply():
                # A reply to a request send by the server to the client
                if self.active():
                    # TODO: if not valid
                    return

                self._session.seen()
                if msg.reply_id not in self._replies:
                    LOGGER.warning("Received a reply that is unknown: %s", msg.reply_id)
                    return

                future = self._replies[msg.reply_id]
                del self._replies[msg.reply_id]
                if not future.done():
                    future.set_result(msg)

    async def close_session(self):
        """Close the session linked with the decoder. Call this method when the connection closes."""
        if self._session is None or self._session.is_closed():
            return

        self._session.close_session()
        await self.on_close_session(self._session)

    async def _handle_call(self, msg: RPC_Call) -> None:
        if self._call_targets is None:
            LOGGER.error("Cannot dispatch method when no call targets are available.")
            return

        reply = await dispatch_method(self._call_targets, msg)
        await self.write_message(reply.model_dump_json())

    async def on_open_session(self, session: common.Session) -> None:
        """Called when a new session is opened"""

    async def on_close_session(self, session: common.Session) -> None:
        """Called when a session is closed"""

    async def write_message(self, message: str | bytes, binary: bool = False) -> None:
        """Write the message in the correct transport"""


class WebSocketClientConnection(websocket.WebSocketClientConnection):
    """A websocket connection with on_ping and on_pong handlers that we use to register session liveness"""
