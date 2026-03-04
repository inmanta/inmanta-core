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
import socket
import time
import uuid
from typing import Annotated, Any, Callable, Literal, Optional, Tuple
from urllib import parse

import pydantic
from tornado import httpclient, websocket

from inmanta import config as inmanta_config
from inmanta import const, tracing, types, util
from inmanta.data import model
from inmanta.protocol import common, endpoints, rest
from inmanta.protocol.auth import providers

LOGGER = logging.getLogger(__name__)


class Session:
    """A session using websockets"""

    def __init__(
        self,
        environment_id: uuid.UUID,
        session_name: str,
        hostname: str,
        websocket_protocol: "WebsocketFrameDecoder",
    ) -> None:
        self._seen: float = 0
        self._environment_id = environment_id
        self._session_name = session_name
        self._hostname = hostname
        self._closed = False
        self._confirmed = False
        self._id = uuid.uuid4()

        self.websocket_protocol = websocket_protocol

    @property
    def environment(self) -> uuid.UUID:
        return self._environment_id

    @property
    def hostname(self) -> str:
        return self._hostname

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._session_name

    def __repr__(self) -> str:
        return (
            f"Session(id={self._id}, name={self._session_name}, environment={self._environment_id}, "
            f"hostname={self._hostname}, closed={self._closed}, confirmed={self._confirmed})"
        )

    @property
    def active(self) -> bool:
        """Can this session be used? It is confirmed and not closed"""
        return not self._closed and self._confirmed

    def confirm_open(self) -> None:
        self._confirmed = True

    async def open(self) -> None:
        await self.websocket_protocol.write_message(
            OpenSession(
                environment_id=self._environment_id,
                session_name=self._session_name,
                hostname=self._hostname,
            ).model_dump_json()
        )

    @property
    def session_key(self) -> Tuple[uuid.UUID, str]:
        """Return a key that uniquely identifies a session"""
        return self._environment_id, self._session_name

    def seen(self) -> None:
        self._seen = time.monotonic()

    def close_session(self) -> None:
        self._closed = True

    def is_closed(self) -> bool:
        return self._closed

    def get_client(self) -> endpoints.Client:
        """Get a client to communicate with the endpoint on the other side of the session"""
        return _SessionClient(self, False)

    def get_typed_client(self) -> endpoints.TypedClient:
        """Get a typed client to communicate with the endpoint on the other side of the session"""
        return _SessionClient(self, True)

    async def close_connection(self) -> None:
        await self.websocket_protocol.close_connection()


class _SessionClient:
    def __init__(self, session: Session, typed: bool) -> None:
        self._session = session
        self._typed = typed

    def __getattr__(self, name: str) -> Callable[..., Any]:
        """
        Return a function that will call self._call with the correct method properties associated
        """
        method = common.MethodProperties.select_method(name)

        if method is None:
            raise AttributeError("Method with name %s is not defined for this client" % name)

        def wrap(*args: object, **kwargs: object) -> Any:
            assert method
            result = self._session.websocket_protocol.rpc_call(properties=method, args=args, kwargs=kwargs)
            if self._typed:

                async def wait():
                    return common.typed_process_response(method_properties=method, response=await result)

                return wait()

            async def with_properties() -> common.Result:
                r = await result
                r._method_properties = method
                return r

            return common.ClientCall.create(with_properties(), properties=method)

        return wrap


class SessionListener:
    async def session_opened(self, session: Session) -> None:
        pass

    async def session_closed(self, session: Session) -> None:
        pass


class WSMessage(model.BaseModel):
    """A websocket message"""

    action: str


class OpenSession(WSMessage):
    action: Literal["OPEN_SESSION"] = "OPEN_SESSION"
    environment_id: uuid.UUID
    session_name: str
    hostname: str


class SessionOpened(WSMessage):
    action: Literal["SESSION_OPENED"] = "SESSION_OPENED"


class RejectSession(WSMessage):
    """This message is sent when a session is rejected by the server"""

    action: Literal["REJECT_SESSION"] = "REJECT_SESSION"
    reason: str


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
    result: Optional[types.JsonType]
    code: int


type WSMessages = Annotated[
    OpenSession | SessionOpened | RejectSession | CloseSession | RPC_Call | RPC_Reply, pydantic.Field(discriminator="action")
]


async def handle_timeout(future: asyncio.Future, timeout: int, log_message: str) -> None:
    """A function that awaits a future until its value is ready or until timeout. When the call times out, a message is
    logged. The future itself will be cancelled.

    This method should be called as a background task. Any other exceptions (which should not occur) will be logged in
    the background task.
    """
    try:
        await asyncio.wait_for(future, timeout)
    except asyncio.TimeoutError:
        LOGGER.warning(log_message)


class WebsocketFrameDecoder(util.TaskHandler[None]):
    """A close that offers an on_message to handle websocket frames and calls handlers for each event"""

    def __init__(self) -> None:
        super().__init__()
        self._message_parser = pydantic.TypeAdapter(WSMessages)
        self._session: Optional[Session] = None
        self._call_targets: Optional[list[common.CallTarget]] = None
        self._replies: dict[uuid.UUID, asyncio.Future[common.Result]] = {}
        self._authnz_context: rest.AuthnzInterface | None = None

    def set_authnz_context(self, context: rest.AuthnzInterface) -> None:
        self._authnz_context = context

    @property
    def session(self) -> Optional[Session]:
        return self._session

    def set_call_targets(self, call_targets: list[common.CallTarget]) -> None:
        self._call_targets = call_targets

    def seen(self) -> None:
        """Bump the liveliness of the session"""
        if self._session:
            self._session.seen()

    def active(self) -> bool:
        """Is the session set and active?"""
        return self._session is not None and self._session.active

    def rpc_call(
        self, properties: common.MethodProperties, args: list[object], kwargs: Optional[dict[str, object]] = None
    ) -> asyncio.Future[common.Result]:
        call_spec = properties.build_call(args=args, kwargs=kwargs)
        call_spec.reply_id = uuid.uuid4()
        call_spec.headers.update(tracing.get_context())
        future = asyncio.Future()

        LOGGER.debug("Putting call %s: %s %s in queue at %s", call_spec.reply_id, call_spec.method, call_spec.url, self)
        # Use the method-defined timeout or a generous default.
        # The timeout covers the full round-trip including handler execution on the remote side.
        timeout = max(properties.timeout or 120, 30)
        if properties.reply:
            self.add_background_task(
                handle_timeout(
                    future=future,
                    timeout=timeout,
                    log_message=f"Call {call_spec.reply_id}: {call_spec.method} {call_spec.url} for timed out.",  # TODO
                )
            )
            self._replies[call_spec.reply_id] = future
        else:
            future.set_result(common.Result(code=200, result=None))

        self.add_background_task(self.write_message(RPC_Call(**call_spec.to_dict()).model_dump_json()))
        return future

    async def on_message(self, message: str | bytes) -> None:
        LOGGER.debug("%s got %s", self, message)
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
                LOGGER.info(
                    "Opening session %s on host %s with environment %s", msg.session_name, msg.hostname, msg.environment_id
                )
                # session open request: normally only initiated by the client and received by the server
                # TODO: handle duplicate sessions
                self._session = Session(
                    environment_id=msg.environment_id,
                    session_name=msg.session_name,
                    hostname=msg.hostname,
                    websocket_protocol=self,
                )
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
                    # Run on_open_session as a background task so the message processing loop is not blocked.
                    # on_reconnect may send RPC calls that require processing incoming replies.
                    self.add_background_task(self.on_open_session(self._session))

            case RejectSession():
                # the server rejected the session: for example when the same session already exists or when the server
                # is shutting down
                # TODO: implement
                pass

            case CloseSession():
                if not self.active():
                    LOGGER.warning("Received a close for %s that is not active on %s.", self._session, self)
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
                LOGGER.debug("Got a reply on %s with %s", self, msg)
                # A reply to a request send by the server to the client
                if not self.active():
                    # TODO: if not valid
                    return

                self._session.seen()
                if msg.reply_id not in self._replies:
                    LOGGER.warning("Received a reply that is unknown: %s", msg.reply_id)
                    return

                future = self._replies[msg.reply_id]
                del self._replies[msg.reply_id]
                if not future.done():
                    future.set_result(common.Result(code=msg.code, result=msg.result))

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

        reply = await self.dispatch_method(msg)
        if reply is not None:
            await self.write_message(common.json_encode(reply))

    async def on_open_session(self, session: Session) -> None:
        """Called when a new session is opened"""

    async def on_close_session(self, session: Session) -> None:
        """Called when a session is closed"""

    async def write_message(self, message: str | bytes, binary: bool = False) -> None:
        """Write the message in the correct transport"""

    def create_session(self, environment_id: uuid.UUID, session_name: str) -> None:
        self._session = Session(
            environment_id=environment_id, session_name=session_name, hostname=socket.gethostname(), websocket_protocol=self
        )

    async def close_connection(self) -> None:
        """Close the connection that belongs to this session and the session itself"""
        await self.close_session()
        await self.write_message(CloseSession().model_dump_json())

    async def dispatch_method(self, msg: RPC_Call) -> Optional[RPC_Reply]:
        """Dispatch a request from the server into the RPC code so the requests gets executed. The call results is send back
        to the server using a heartbeat reply.
        """
        parsed_url = parse.urlparse(msg.url)
        method_call = common.Request(
            url=parsed_url.path, method=msg.method, headers=msg.headers, body=msg.body, reply_id=msg.reply_id
        )

        LOGGER.debug("Received call through websocket: %s %s %s", method_call.reply_id, method_call.method, method_call.url)
        kwargs, config = rest.match_call(self._call_targets, method_call.url, method_call.method)

        if config is None:
            # We cannot match the call to method on this endpoint. We send a reply to report this + ensure that the session
            # does not time out
            error = (
                "An error occurred during heartbeat method call "
                f"({method_call.reply_id} {method_call.method} {method_call.url}): No such method"
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
        for key, value in parse.parse_qs(parsed_url.query, keep_blank_values=True).items():
            if len(value) == 1:
                body[key] = value[0]
            else:
                body[key] = value

        body.update(kwargs)

        from inmanta.protocol.exceptions import BaseHttpException

        try:
            with tracing.attach_context(
                {const.TRACEPARENT: method_call.headers[const.TRACEPARENT]} if const.TRACEPARENT in method_call.headers else {}
            ):
                # do the dispatch
                response: common.Response = await rest.execute_call(self._authnz_context, config, body, method_call.headers)
        except BaseHttpException as e:
            LOGGER.warning(
                "Received an exception with status code %d for websocket call (%s %s %s): %s",
                e.to_status(),
                method_call.reply_id,
                method_call.method,
                method_call.url,
                e.to_body(),
            )
            if method_call.reply_id is not None:
                return RPC_Reply(
                    reply_id=msg.reply_id,
                    code=e.to_status(),
                    result=e.to_body(),
                )
            return None
        except Exception as e:
            LOGGER.exception(
                "An exception occurred during websocket call (%s %s %s)",
                method_call.reply_id,
                method_call.method,
                method_call.url,
            )
            if method_call.reply_id is not None:
                return RPC_Reply(
                    reply_id=msg.reply_id,
                    code=500,
                    result={"message": str(e)},
                )
            return None

        # report the result back
        if response.status_code == 500:
            error_msg = ""
            if isinstance(response.body, dict) and "message" in response.body:
                error_msg = response.body["message"]
            LOGGER.error(
                "An error occurred during websocket method call (%s %s %s): %s",
                method_call.reply_id,
                method_call.method,
                method_call.url,
                error_msg,
            )

        # if reply is none, we don't send the reply
        if method_call.reply_id is not None:
            body = response.body
            if body is not None and not isinstance(body, dict):
                body = {"message": str(body)}
            return RPC_Reply(
                reply_id=msg.reply_id,
                code=response.status_code,
                result=body,
            )


class WebSocketClientConnection(websocket.WebSocketClientConnection):
    """A websocket connection with on_ping and on_pong handlers that we use to register session liveness"""

    def __init__(
        self,
        on_pong_callback: Optional[Callable[[], ...]] = None,
        on_connection_close_callback: Optional[Callable[[], ...]] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._on_pong_cb = on_pong_callback
        self._on_connection_close_callback = on_connection_close_callback

    @property
    def closed(self) -> bool:
        return self.protocol is None

    def on_pong(self, data: bytes) -> None:
        if self._on_pong_cb:
            self._on_pong_cb()

    def on_connection_close(self) -> None:
        super().on_connection_close()
        if self._on_connection_close_callback:
            self._on_connection_close_callback()


class SessionEndpoint(endpoints.Endpoint, common.CallTarget, WebsocketFrameDecoder, rest.AuthnzInterface):
    """
    An endpoint for clients that make calls to a server and that receive calls back from the server using websockets.
    """

    def __init__(self, name: str, environment: uuid.UUID, timeout: int = 120, reconnect_delay: int = 5):
        """
        :param name: The name of the session. This has to be unique per environment
        :param environment: The environment this session is for
        :param: timeout: The connect timeout
        :param reconnect_delay: How long to wait after a disconnect or a closed session to reconnect
        """
        endpoints.Endpoint.__init__(self, name)
        WebsocketFrameDecoder.__init__(self)
        LOGGER.debug("Start transport for client %s", name)

        self._sched = util.Scheduler("session endpoint")

        self._env_id: uuid.UUID = environment

        self.running: bool = True
        self.server_timeout = timeout
        self.reconnect_delay = reconnect_delay
        self.add_call_target(self)

        self._ws_client: Optional[WebSocketClientConnection] = None
        self.set_call_targets(self.call_targets)
        self.set_authnz_context(self)

        self.create_session(
            environment_id=self.environment,
            session_name=self.name,
        )

    def is_auth_enabled(self) -> bool:
        """
        Return True iff authentication is enabled.
        """
        return False

    def get_authorization_provider(self) -> providers.AuthorizationProvider | None:
        """
        Returns the authorization provider or None if we are not running on the server.
        """
        return None

    def get_environment(self) -> uuid.UUID:
        return self._env_id

    def get_websocket_url(self) -> str:
        """Build the websocket url based on the configuration file"""
        client_id = f"{self.name}_rest_transport"
        port: int = inmanta_config.Config.get(client_id, "port", 8888)
        host: str = inmanta_config.Config.get(client_id, "host", "localhost")

        if inmanta_config.Config.getboolean(client_id, "ssl", False):
            protocol = "wss"
        else:
            protocol = "ws"

        return f"{protocol}://{host}:{port}/v2/ws"

    @property
    def environment(self) -> uuid.UUID:
        return self._env_id

    async def start_connected(self) -> None:
        """
        This method is called after starting the client transport, but before establishing the websocket connection.
        """

    async def start(self) -> None:
        """
        Connect to the server using a websocket for bidirectional communication.
        """
        assert self._env_id is not None
        LOGGER.info("Starting session endpoint %s in environment %s", self.name, self.environment)
        self.add_background_task(self._process_messages())

    async def _reconnect(self) -> None:
        """Connect (again) to the websocket on the server"""
        LOGGER.info("Creating websocket connection from server for %s in environment %s", self.name, self.environment)
        conn = WebSocketClientConnection(
            request=httpclient.HTTPRequest(self.get_websocket_url(), connect_timeout=1),
            ping_interval=1,
            ping_timeout=0.5,
            on_pong_callback=self.seen,
            on_connection_close_callback=self._on_disconnect,
        )

        self._ws_client = await conn.connect_future
        await self.session.open()
        await self.start_connected()

    def _on_disconnect(self) -> None:
        if self.is_running():
            self.add_background_task(self.on_disconnect())

    async def stop(self) -> None:
        LOGGER.info("Stopping session endpoint %s in environment %s", self.name, self.environment)
        await self._sched.stop()
        await super().stop()
        await self.close_connection()

    async def on_reconnect(self) -> None:
        """
        Called when a connection becomes active. i.e. when a first heartbeat is received after startup or
        a first heartbeat after an :py:`on_disconnect`
        """
        LOGGER.info("Session %s in environment %s is connected", self.name, self.environment)

    async def on_disconnect(self) -> None:
        """
        Called when the connection is lost unexpectedly (not on shutdown)
        """
        LOGGER.info("Connection to server for session %s in environment %s is disconnected", self.name, self.environment)

    async def on_open_session(self, session: Session) -> None:
        """Called when a new session is opened"""
        await self.on_reconnect()

    async def on_close_session(self, session: Session) -> None:
        """Called when a session is closed"""

    async def write_message(self, message: str | bytes, binary: bool = False) -> None:
        try:
            if self._ws_client is not None and not self._ws_client.closed:
                await self._ws_client.write_message(message, binary)
        except websocket.WebSocketClosedError:
            LOGGER.warning("Tried writing into a closed websocket.")

    async def _process_messages(self) -> None:
        """Process incoming messages"""
        try:
            while True:
                if self._ws_client is not None and not self._ws_client.closed:
                    msg = await self._ws_client.read_message()
                    if msg is None:
                        # we are disconnected. We wait and try to connect. If it fails, we will retry next iteration.
                        await asyncio.sleep(self.reconnect_delay)
                        await self._reconnect()
                    else:
                        await self.on_message(msg)
                else:
                    # There is no connection (probably because we just started). Connect to the server.
                    await self._reconnect()

        except asyncio.CancelledError:
            pass

    async def close_connection(self) -> None:
        await super().close_connection()
        if self._ws_client:
            self._ws_client.close()
