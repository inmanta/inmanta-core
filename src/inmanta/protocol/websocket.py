"""
Copyright 2026 Inmanta

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
import json
import logging
import socket
import uuid
from typing import Annotated, Any, Callable, Literal, Optional, Tuple
from urllib import parse

import pydantic
from tornado import httpclient, websocket

from inmanta import config as inmanta_config
from inmanta import const, tracing, types, util
from inmanta.data import model
from inmanta.protocol import common, endpoints, rest
from inmanta.protocol.auth import auth as auth_module
from inmanta.protocol.auth import providers

LOGGER = logging.getLogger(__name__)


class Session:
    """Represents a websocket session between a client (agent) and the server. Each side has an instance
    representing the session.

    A session is uniquely identified by (environment_id, session_name). It goes through the
    following lifecycle:

    1. Created locally (client or server side)
    2. OpenSession message sent over the websocket
    3. Server confirms with SessionOpened → session becomes `active` (confirmed and not closed)
    4. RPC calls can flow in both directions while active
    5. Session is closed via CloseSession message or connection loss

    The session holds a reference to its :class:`WebsocketFrameDecoder`, which provides the
    underlying websocket transport for sending messages and making RPC calls.
    """

    def __init__(
        self,
        environment_id: uuid.UUID,
        session_name: str,
        hostname: str,
        websocket_protocol: "WebsocketFrameDecoder",
    ) -> None:
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
        """Can this session be used? It is confirmed and not closed."""
        return not self._closed and self._confirmed

    def confirm_open(self) -> None:
        """Mark the session as confirmed after receiving a SessionOpened acknowledgment."""
        self._confirmed = True

    async def open(self, token: str | None = None) -> None:
        """Send an OpenSession message to the remote side to initiate the session handshake.

        :param token: Optional JWT bearer token to include in the handshake for authentication.
        """
        await self.websocket_protocol.write_message(
            OpenSession(
                environment_id=self._environment_id,
                session_name=self._session_name,
                hostname=self._hostname,
                token=token,
            ).model_dump_json()
        )

    @property
    def session_key(self) -> Tuple[uuid.UUID, str]:
        """Return a (environment_id, session_name) tuple that uniquely identifies this session."""
        return self._environment_id, self._session_name

    def close_session(self) -> None:
        """Mark the session as closed. This is a local state change only; it does not send a message."""
        self._closed = True

    def is_closed(self) -> bool:
        """Return True if the session has been closed."""
        return self._closed

    def get_client(self) -> endpoints.Client:
        """Get a client to communicate with the endpoint on the other side of the session."""
        return _SessionClient(self.websocket_protocol, False)

    def get_typed_client(self) -> endpoints.TypedClient:
        """Get a typed client to communicate with the endpoint on the other side of the session."""
        return _SessionClient(self.websocket_protocol, True)

    async def close_connection(self) -> None:
        """Close the underlying websocket connection (delegates to the frame decoder)."""
        await self.websocket_protocol.close_connection()


class _SessionClient:
    """A dynamic RPC client that routes method calls through a websocket frame decoder.

    This client is obtained via `Session.get_client` or `Session.get_typed_client`.
    It uses `__getattr__` to intercept attribute access: any method name defined in the protocol's
    `inmanta.protocol.common.MethodProperties` registry can be called as if it were a local
    method. The call is serialized as an `RPC_Call` message and sent over the decoder's
    websocket connection.

    When `typed=True`, the response is deserialized into the method's declared return type.
    When `typed=False`, a raw `inmanta.protocol.common.Result` is returned.
    """

    def __init__(self, decoder: "WebsocketFrameDecoder", typed: bool) -> None:
        self._decoder = decoder
        self._typed = typed

    def __getattr__(self, name: str) -> Callable[..., Any]:
        """Look up the named RPC method and return a callable that dispatches it over the websocket."""
        method = common.MethodProperties.select_method(name)

        if method is None:
            raise AttributeError("Method with name %s is not defined for this client" % name)

        def wrap(*args: object, **kwargs: object) -> Any:
            assert method
            result = self._decoder.rpc_call(properties=method, args=args, kwargs=kwargs)
            if self._typed:

                async def wait():
                    return common.typed_process_response(method_properties=method, response=await result)

                return wait()

            async def with_properties() -> common.Result:
                r = await result
                r.method_properties = method
                return r

            return common.ClientCall.create(with_properties(), properties=method)

        return wrap


class SessionListener:
    """Interface for receiving session lifecycle events.

    Implement this interface to be notified when sessions are opened or closed.
    """

    async def session_opened(self, session: Session) -> None:
        """Called when a new session has been opened and confirmed."""
        pass

    async def session_closed(self, session: Session) -> None:
        """Called when a session has been closed (either gracefully or due to connection loss)."""
        pass


class WSMessage(model.BaseModel):
    """Base class for all websocket protocol messages.

    Each subclass represents a distinct message type in the websocket protocol. Messages are
    discriminated by their `action` field, which is set to a fixed literal value per subclass.
    The `WSMessages` type alias uses Pydantic's discriminated union for efficient parsing.
    """

    action: str


class OpenSession(WSMessage):
    """Sent by the client to request a new session with the server.

    :param environment_id: The environment this session belongs to.
    :param session_name: A unique name for this session within the environment (e.g. the agent name).
    :param hostname: The hostname of the machine initiating the session.
    :param token: Optional JWT bearer token for authentication. When auth is enabled on the server,
                  this token is validated before the session is accepted.
    """

    action: Literal["OPEN_SESSION"] = "OPEN_SESSION"
    environment_id: uuid.UUID
    session_name: str
    hostname: str
    token: str | None = None


class SessionOpened(WSMessage):
    """Sent by the server to confirm that the session has been accepted and is now active."""

    action: Literal["SESSION_OPENED"] = "SESSION_OPENED"


class RejectSession(WSMessage):
    """Sent by the server when it refuses a session request (e.g. duplicate session, server shutting down).

    :param reason: Human-readable explanation for the rejection.
    """

    action: Literal["REJECT_SESSION"] = "REJECT_SESSION"
    reason: str


class CloseSession(WSMessage):
    """Sent by either side to gracefully close the session."""

    action: Literal["CLOSE_SESSION"] = "CLOSE_SESSION"


class RPC_Call(WSMessage):
    """An RPC request sent over the websocket. Can flow in either direction (server→client or client→server).

    :param url: The API endpoint URL (e.g. `/api/v2/resource`). May include query parameters.
    :param method: The HTTP method (GET, POST, PUT, DELETE, etc.).
    :param headers: HTTP headers to pass along (e.g. tracing context, authentication).
    :param body: The JSON request body, or None for bodyless requests.
    :param reply_id: Correlation ID for matching the reply. None for fire-and-forget calls.
    """

    action: Literal["RPC_CALL"] = "RPC_CALL"
    url: str
    method: str
    headers: dict[str, str]
    body: Optional[types.JsonType]
    reply_id: Optional[uuid.UUID] = None


class RPC_Reply(WSMessage):
    """The response to an `RPC_Call`, correlated by `reply_id`.

    :param reply_id: The correlation ID from the original `RPC_Call`.
    :param result: The JSON response body, or None.
    :param code: The HTTP status code of the response.
    """

    action: Literal["RPC_REPLY"] = "RPC_REPLY"
    reply_id: uuid.UUID
    result: Optional[types.JsonType]
    code: int


type WSMessages = Annotated[
    OpenSession | SessionOpened | RejectSession | CloseSession | RPC_Call | RPC_Reply, pydantic.Field(discriminator="action")
]


async def handle_timeout(
    future: asyncio.Future[common.Result],
    timeout: int,
    log_message: str,
    replies: dict[uuid.UUID, "asyncio.Future[common.Result]"],
    reply_id: uuid.UUID,
) -> None:
    """A function that awaits a future until its value is ready or until timeout. When the call times out, a message is
    logged and the future is cancelled. The entry is also removed from the replies dict to prevent a memory leak.

    This method should be called as a background task. Any other exceptions (which should not occur) will be logged in
    the background task.
    """
    try:
        await asyncio.wait_for(future, timeout)
    except asyncio.TimeoutError:
        LOGGER.warning(log_message)
    finally:
        replies.pop(reply_id, None)


class WebsocketFrameDecoder(util.TaskHandler[None]):
    """Handles incoming websocket frames and dispatches them to the appropriate handler.

    This is the core protocol handler for the websocket-based RPC layer. It parses incoming
    messages into typed `WSMessage` objects and processes them according to their type:

    - **Session lifecycle**: `OpenSession` / `SessionOpened` / `RejectSession` / `CloseSession`
      manage the session handshake and teardown.
    - **RPC dispatch**: `RPC_Call` messages are dispatched to registered call targets (the same
      handler methods used by the REST layer). `RPC_Reply` messages resolve pending futures from
      outgoing `rpc_call` invocations.

    Subclasses must implement `write_message` to provide the actual transport. Override
    `on_open_session` and `on_close_session` for session lifecycle hooks.
    """

    def __init__(self) -> None:
        super().__init__()
        self._message_parser = pydantic.TypeAdapter(WSMessages)
        self._session: Optional[Session] = None
        self._call_targets: Optional[list[common.CallTarget]] = None
        self._replies: dict[uuid.UUID, asyncio.Future[common.Result]] = {}
        self._authnz_context: rest.AuthnzInterface | None = None
        self._token: str | None = None

    def set_authnz_context(self, context: rest.AuthnzInterface) -> None:
        """Set the authentication/authorization context used when dispatching incoming RPC calls."""
        self._authnz_context = context

    @property
    def session(self) -> Optional[Session]:
        """The session associated with this decoder, or None if no session has been established yet."""
        return self._session

    def set_call_targets(self, call_targets: list[common.CallTarget]) -> None:
        """Set the call targets that incoming RPC calls will be dispatched to."""
        self._call_targets = call_targets

    def active(self) -> bool:
        """Return True if a session is established and active (confirmed and not closed)."""
        return self._session is not None and self._session.active

    def rpc_call(
        self, properties: common.MethodProperties, args: list[object], kwargs: Optional[dict[str, object]] = None
    ) -> asyncio.Future[common.Result]:
        call_spec = properties.build_call(args=args, kwargs=kwargs)
        call_spec.reply_id = uuid.uuid4() if properties.reply else None
        call_spec.headers.update(tracing.get_context())
        if self._token is not None:
            call_spec.headers["Authorization"] = "Bearer " + self._token
        future = asyncio.Future()

        LOGGER.debug("Putting call %s: %s %s in queue at %s", call_spec.reply_id, call_spec.method, call_spec.url, self)
        # Use the method-defined timeout or a generous default.
        # The timeout covers the full round-trip including handler execution on the remote side.
        timeout = max(properties.timeout or 120, 30)
        if properties.reply:
            self._replies[call_spec.reply_id] = future
            self.add_background_task(
                handle_timeout(
                    future=future,
                    timeout=timeout,
                    log_message=f"Call {call_spec.reply_id}: {call_spec.method} {call_spec.url} timed out.",
                    replies=self._replies,
                    reply_id=call_spec.reply_id,
                )
            )
        else:
            future.set_result(common.Result(code=200, result=None))

        self.add_background_task(self._send_rpc_call(call_spec.reply_id, RPC_Call(**call_spec.to_dict()).model_dump_json()))
        return future

    async def _send_rpc_call(self, reply_id: uuid.UUID | None, message: str) -> None:
        """Send an RPC call message, resolving the pending future with 503 if the write fails."""
        try:
            await self.write_message(message)
        except Exception:
            future = self._replies.pop(reply_id, None)
            if future is not None and not future.done():
                future.set_result(common.Result(code=503, result={"message": "Failed to send RPC call"}))

    async def on_message(self, message: str | bytes) -> None:
        """Parse an incoming websocket frame and dispatch it based on message type."""
        LOGGER.debug("%s got %s", self, message)
        try:
            msg = self._message_parser.validate_json(message)
        except pydantic.ValidationError:
            LOGGER.exception("Invalid message")
            return

        match msg:
            case OpenSession():
                if self._session is not None:
                    LOGGER.warning(
                        "Rejecting duplicate OpenSession on connection that already has session %s",
                        self._session,
                    )
                    await self.write_message(
                        RejectSession(reason="A session is already open on this connection").model_dump_json()
                    )
                    return

                # Validate token if auth is enabled
                if self._authnz_context is not None and self._authnz_context.is_auth_enabled():
                    if msg.token is None:
                        await self.write_message(RejectSession(reason="Authentication required").model_dump_json())
                        return
                    try:
                        auth_module.decode_token(msg.token)
                    except Exception:
                        await self.write_message(RejectSession(reason="Invalid authentication token").model_dump_json())
                        return

                LOGGER.info(
                    "Opening session %s on host %s with environment %s", msg.session_name, msg.hostname, msg.environment_id
                )
                # session open request: normally only initiated by the client and received by the server
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
                LOGGER.warning("Session rejected by server: %s", msg.reason)
                if self._session is not None:
                    self._session.close_session()
                    self._session = None
                await self.close_connection()

            case CloseSession():
                if not self.active():
                    LOGGER.warning("Received a close for %s that is not active on %s.", self._session, self)
                else:
                    self._session.close_session()
                    await self.on_close_session(self._session)

            case RPC_Call():
                if self.active():
                    # A request from the client on the server
                    self.add_background_task(self._handle_call(msg))
                else:
                    LOGGER.warning("Received RPC_Call on inactive session, ignoring: %s", self)

            case RPC_Reply():
                LOGGER.debug("Got a reply on %s with %s", self, msg)
                # A reply to a request sent by the server to the client
                if not self.active():
                    LOGGER.warning("Received RPC_Reply on inactive session, ignoring: %s", self)
                    return

                if msg.reply_id not in self._replies:
                    LOGGER.warning("Received a reply that is unknown: %s", msg.reply_id)
                    return

                future = self._replies[msg.reply_id]
                del self._replies[msg.reply_id]
                if not future.done():
                    future.set_result(common.Result(code=msg.code, result=msg.result))

    async def close_session(self) -> None:
        """Close the session linked with the decoder. Call this method when the connection closes."""
        if self._session is None or self._session.is_closed():
            return

        self._session.close_session()

        # Resolve any pending RPC futures so callers don't hang until timeout
        for reply_id, future in self._replies.items():
            if not future.done():
                future.set_result(common.Result(code=503, result={"message": "Session closed"}))
        self._replies.clear()

        await self.on_close_session(self._session)

    async def _handle_call(self, msg: RPC_Call) -> None:
        if self._call_targets is None:
            LOGGER.error("Cannot dispatch method when no call targets are available.")
            return

        reply = await self.dispatch_method(msg)
        if reply is not None:
            try:
                await self.write_message(reply.model_dump_json())
            except Exception:
                LOGGER.debug("Failed to send RPC reply for %s, connection may already be closed.", msg.reply_id, exc_info=True)

    async def on_open_session(self, session: Session) -> None:
        """Called when a new session is opened.

        Note: On the server side (WebsocketHandler) this runs inline, blocking the message loop.
        On the client side (SessionEndpoint) it runs as a background task via on_message.
        """

    async def on_close_session(self, session: Session) -> None:
        """Called when a session is closed"""

    async def write_message(self, message: str | bytes, binary: bool = False) -> None:
        """Write the message in the correct transport"""

    def create_session(self, environment_id: uuid.UUID, session_name: str) -> None:
        """Create a new local session (client-side). The session is not yet confirmed until the server responds."""
        self._session = Session(
            environment_id=environment_id, session_name=session_name, hostname=socket.gethostname(), websocket_protocol=self
        )

    async def close_connection(self) -> None:
        """Close the connection that belongs to this session and the session itself"""
        if self._session is not None and not self._session.is_closed():
            try:
                await self.write_message(CloseSession().model_dump_json())
            except Exception:
                LOGGER.debug("Failed to send CloseSession message, connection may already be closed.")
        await self.close_session()

    async def dispatch_method(self, msg: RPC_Call) -> Optional[RPC_Reply]:
        """Dispatch a request from the server into the RPC code so the requests gets executed. The call result is sent back
        to the server using a WebSocket reply.
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
                "An error occurred during websocket method call "
                f"({method_call.reply_id} {method_call.method} {method_call.url}): No such method"
            )
            LOGGER.error(error)
            # if reply_id is none, we don't send the reply
            if method_call.reply_id is not None:
                return RPC_Reply(
                    reply_id=msg.reply_id,
                    code=500,
                    result={"message": error},
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
                # Round-trip through json_encode to normalize non-serializable objects
                # (e.g. ValueError in validation error ctx) into plain JSON-compatible dicts.
                body = json.loads(common.json_encode(e.to_body()))
                return RPC_Reply(
                    reply_id=msg.reply_id,
                    code=e.to_status(),
                    result=body,
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
            elif body is not None:
                # Round-trip through json_encode to normalize complex types (e.g. resources.Id, datetime)
                # into plain JSON-compatible dicts, matching the REST path's serialization.
                body = json.loads(common.json_encode(body))
            return RPC_Reply(
                reply_id=msg.reply_id,
                code=response.status_code,
                result=body,
            )


class WebSocketClientConnection(websocket.WebSocketClientConnection):
    """A websocket connection with a disconnect callback for session liveness tracking."""

    def __init__(
        self,
        on_connection_close_callback: Optional[Callable[[], ...]] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._on_connection_close_callback = on_connection_close_callback

    @property
    def closed(self) -> bool:
        return self.protocol is None

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
        self._reconnecting: bool = False
        self.set_call_targets(self.call_targets)
        self.set_authnz_context(self)

        client_id = f"{name}_rest_transport"
        self._token = inmanta_config.Config.get(client_id, "token", None)

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

        return f"{protocol}://{host}:{port}{const.WS_URL_PATH}"

    @property
    def environment(self) -> uuid.UUID:
        return self._env_id

    async def start_connected(self) -> None:
        """Called after sending OpenSession but before receiving SessionOpened confirmation.

        The websocket connection is established but the session is not yet confirmed active.
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
        from inmanta.agent import config as agent_cfg

        ws_ping_interval = agent_cfg.agent_ws_ping_interval.get()
        ws_ping_timeout = agent_cfg.agent_ws_ping_timeout.get()
        if ws_ping_timeout > ws_ping_interval:
            raise Exception(
                f"client.ws-ping-timeout ({ws_ping_timeout}) must not exceed " f"client.ws-ping-interval ({ws_ping_interval})"
            )

        # Clean up old session and connection before creating new ones
        self._reconnecting = True
        try:
            if self._session is not None and not self._session.is_closed():
                await self.close_session()
            if self._ws_client is not None and not self._ws_client.closed:
                self._ws_client.close()

            LOGGER.info("Creating websocket connection to server for %s in environment %s", self.name, self.environment)
            client_id = f"{self.name}_rest_transport"
            ca_certs = inmanta_config.Config.get(client_id, "ssl_ca_cert_file", None)
            conn = WebSocketClientConnection(
                request=httpclient.HTTPRequest(self.get_websocket_url(), connect_timeout=1, ca_certs=ca_certs),
                ping_interval=ws_ping_interval,
                ping_timeout=ws_ping_timeout,
                on_connection_close_callback=self._on_disconnect,
            )

            self._ws_client = await conn.connect_future
            # Create a fresh session for each connection attempt. This ensures a clean state after
            # rejection or disconnection (where the old session may be closed).
            self.create_session(environment_id=self.environment, session_name=self.name)
            await self.session.open(token=self._token)
            await self.start_connected()
        finally:
            self._reconnecting = False

    def _on_disconnect(self) -> None:
        # This fires before close_session() (which happens later in _reconnect). This is intentional:
        # on_disconnect should stop the agent's scheduler promptly rather than waiting for
        # reconnect_delay seconds. The session cleanup happens when _reconnect calls close_session().
        if self.is_running() and not self._reconnecting:
            self.add_background_task(self.on_disconnect())

    async def stop(self) -> None:
        """Stop the endpoint.

        Ordering: super().stop() cancels all background tasks (including _process_messages and any
        in-progress _reconnect), then close_connection() cleanly shuts down the session and websocket.
        """
        LOGGER.info("Stopping session endpoint %s in environment %s", self.name, self.environment)
        await self._sched.stop()
        await super().stop()
        await self.close_connection()

    async def on_reconnect(self) -> None:
        """
        Called when a connection becomes active. i.e. when a first heartbeat is received after startup or
        a first heartbeat after an `on_disconnect`
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
        if self._ws_client is None or self._ws_client.closed:
            raise ConnectionError("WebSocket is closed")
        await self._ws_client.write_message(message, binary)

    async def _process_messages(self) -> None:
        """Process incoming messages from the WebSocket connection.

        This method runs as a long-lived background task for the lifetime of the endpoint.
        It handles the full connection lifecycle: initial connection, message dispatch,
        and reconnection after failures.

        Error handling:
            - Connection failures (refused, DNS, SSL, timeout) in _reconnect() are caught,
              logged, and retried after reconnect_delay seconds.
            - Message processing errors in on_message() are caught and logged without
              dropping the connection.
            - asyncio.CancelledError is allowed to propagate for clean shutdown via stop().
        """
        try:
            while True:
                try:
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
                    raise
                except Exception:
                    LOGGER.exception(
                        "Exception in message loop for %s in environment %s, reconnecting in %s seconds",
                        self.name,
                        self.environment,
                        self.reconnect_delay,
                    )
                    self._ws_client = None
                    await asyncio.sleep(self.reconnect_delay)
        except asyncio.CancelledError:
            pass

    async def close_connection(self) -> None:
        await super().close_connection()
        if self._ws_client:
            self._ws_client.close()
