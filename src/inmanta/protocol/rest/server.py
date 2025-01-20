"""
    Copyright 2019 Inmanta

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
import dataclasses
import enum
import logging
import ssl
import time
import uuid
from asyncio import CancelledError
from collections import defaultdict
from collections.abc import Mapping, MutableMapping, Sequence
from datetime import timedelta
from json import JSONDecodeError
from typing import Annotated, Literal, Optional, Union
from urllib import parse

import pydantic
import tornado
from pyformance import timer
from tornado import httpserver, iostream, routing, web, websocket

import inmanta.protocol.endpoints
from inmanta import config as inmanta_config
from inmanta import const, tracing
from inmanta.data import BaseModel
from inmanta.protocol import common, exceptions, endpoints
from inmanta.protocol.rest import RESTBase
from inmanta.protocol.rest.client import match_call
from inmanta.server import config as opt
from inmanta.server import config as server_config
from inmanta.server.config import server_access_control_allow_origin, server_enable_auth, server_tz_aware_timestamps
from inmanta.types import ArgumentTypes, JsonType, ReturnTypes

LOGGER: logging.Logger = logging.getLogger(__name__)


class RESTHandler(tornado.web.RequestHandler):
    """
    A generic class use by the transport
    """

    def initialize(self, transport: "RESTServer", config: dict[str, common.UrlMethod]) -> None:
        self._transport: "RESTServer" = transport
        self._config = config

    def _get_config(self, http_method: str) -> common.UrlMethod:
        if http_method.upper() not in self._config:
            allowed = ", ".join(self._config.keys())
            self.set_header("Allow", allowed)
            raise exceptions.BaseHttpException(
                405, f"{http_method} is not supported for this url. Supported methods: {allowed}"
            )

        return self._config[http_method]

    def prepare(self) -> None:
        # Setting "Access-Control-Allow-Origin": null can be exploited.
        # better not set it all instead.
        # See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Access-Control-Allow-Origin
        server_origin = server_access_control_allow_origin.get()
        if server_origin is not None:
            self.set_header("Access-Control-Allow-Origin", server_origin)

    def respond(self, body: ReturnTypes, headers: MutableMapping[str, str], status: int) -> None:
        if common.CONTENT_TYPE not in headers:
            headers[common.CONTENT_TYPE] = common.JSON_CONTENT

        if body is not None:
            encoded_body = self._encode_body(body, headers[common.CONTENT_TYPE])
            self.write(encoded_body)

        for header, value in headers.items():
            self.set_header(header, value)

        self.set_status(status)

    def _encode_body(self, body: ReturnTypes, content_type: str) -> Union[str, bytes]:
        if content_type == common.JSON_CONTENT:
            return common.json_encode(body, tz_aware=server_tz_aware_timestamps.get())
        if content_type == common.HTML_CONTENT:
            assert isinstance(body, str)
            return body.encode(common.HTML_ENCODING)
        if content_type == common.HTML_CONTENT_WITH_UTF8_CHARSET:
            assert isinstance(body, str)
            return body.encode(common.UTF8_ENCODING)
        elif not isinstance(body, (str, bytes)):
            raise exceptions.ServerError(
                f"Body should be str or bytes and not {type(body)}."
                " For dict make sure content type is set to {common.JSON_CONTENT}"
            )
        return body

    async def _call(self, kwargs: dict[str, str], call_config: common.UrlMethod) -> None:
        """An rpc like call.

        :param kwargs: The parameters extracted by tornado based on the provided handler template url
        :param call_config: The configuration that belongs to the matched url and http_method combination
        """
        if call_config is None:
            raise exceptions.NotFound("This method does not exist")

        if not self._transport.running:
            return

        with tracing.attach_context(
            {const.TRACEPARENT: self.request.headers[const.TRACEPARENT]} if const.TRACEPARENT in self.request.headers else {}
        ):
            with tracing.span("rpc." + call_config.method_name, _tags=["rpc-call"]):
                with timer("rpc." + call_config.method_name).time():
                    self._transport.start_request()
                    try:
                        message = self._transport._decode(self.request.body)
                        if message is None:
                            message = {}

                        # add any url template arguments
                        if kwargs:
                            message.update(kwargs)

                        # add any url arguments
                        for key, value in self.request.query_arguments.items():
                            if len(value) == 1:
                                message[key] = value[0].decode("latin-1")
                            else:
                                message[key] = [v.decode("latin-1") for v in value]

                        result = await self._transport._execute_call(call_config, message, self.request.headers)
                        self.respond(result.body, result.headers, result.status_code)
                    except JSONDecodeError as e:
                        error_message = f"The request body couldn't be decoded as a JSON: {e}"
                        LOGGER.info(error_message, exc_info=True)
                        self.respond({"message": error_message}, {}, 400)

                    except ValueError:
                        LOGGER.exception("An exception occurred")
                        self.respond({"message": "Unable to decode request body"}, {}, 400)

                    except exceptions.BaseHttpException as e:
                        LOGGER.warning("Received an exception with status code %d and message %s", e.to_status(), e.to_body())
                        self.respond(e.to_body(), {}, e.to_status())

                    except CancelledError:
                        self.respond({"message": "Request is cancelled on the server"}, {}, 500)

                    finally:
                        try:
                            await self.finish()
                        except iostream.StreamClosedError:
                            # The connection has been closed already.
                            pass
                        except Exception:
                            LOGGER.exception("An exception occurred responding to %s", self.request.remote_ip)
                        self._transport.end_request()

    async def head(self, *args: str, **kwargs: str) -> None:
        if args:
            raise Exception("Only named groups are support in url patterns")
        await self._transport.add_background_task(
            self._call(call_config=self._get_config("HEAD"), kwargs=kwargs), cancel_on_stop=False
        )

    async def get(self, *args: str, **kwargs: str) -> None:
        if args:
            raise Exception("Only named groups are support in url patterns")
        await self._transport.add_background_task(
            self._call(call_config=self._get_config("GET"), kwargs=kwargs), cancel_on_stop=False
        )

    async def post(self, *args: str, **kwargs: str) -> None:
        if args:
            raise Exception("Only named groups are support in url patterns")
        await self._transport.add_background_task(
            self._call(call_config=self._get_config("POST"), kwargs=kwargs), cancel_on_stop=False
        )

    async def delete(self, *args: str, **kwargs: str) -> None:
        if args:
            raise Exception("Only named groups are support in url patterns")
        await self._transport.add_background_task(
            self._call(call_config=self._get_config("DELETE"), kwargs=kwargs), cancel_on_stop=False
        )

    async def patch(self, *args: str, **kwargs: str) -> None:
        if args:
            raise Exception("Only named groups are support in url patterns")
        await self._transport.add_background_task(
            self._call(call_config=self._get_config("PATCH"), kwargs=kwargs), cancel_on_stop=False
        )

    async def put(self, *args: str, **kwargs: str) -> None:
        if args:
            raise Exception("Only named groups are support in url patterns")
        await self._transport.add_background_task(
            self._call(call_config=self._get_config("PUT"), kwargs=kwargs), cancel_on_stop=False
        )

    def options(self, *args: str, **kwargs: str) -> None:
        if args:
            raise Exception("Only named groups are support in url patterns")

        allow_headers = "Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token, %s" % const.INMANTA_MT_HEADER
        if len(self._transport.headers):
            allow_headers += ", " + ", ".join(self._transport.headers)
        if server_enable_auth.get():
            allow_headers += ", Authorization"

        self.set_header("Access-Control-Allow-Methods", "HEAD, GET, POST, PUT, OPTIONS, DELETE, PATCH")
        self.set_header("Access-Control-Allow-Headers", allow_headers)

        self.set_status(200)


class StaticContentHandler(tornado.web.RequestHandler):
    def initialize(self, transport: "RESTServer", content: str, content_type: str) -> None:
        self._transport = transport
        self._content = content
        self._content_type = content_type

    def get(self, *args: list[str], **kwargs: dict[str, str]) -> None:
        self.set_header("Content-Type", self._content_type)
        self.write(self._content)
        self.set_status(200)


class WSAction(enum.StrEnum):
    OPEN_SESSION = "OPEN_SESSION"
    CLOSE_SESSION = "CLOSE_SESSION"
    RPC_CALL = "RPC_CALL"
    RPC_REPLY = "RPC_REPLY"


class WSMessage(BaseModel):
    """A websocket message"""

    action: WSAction


class OpenSession(WSMessage):
    action: Literal["OPEN_SESSION"] = "OPEN_SESSION"
    nodename: str
    endpoint_names: list[str]


class CloseSession(WSMessage):
    action: Literal["CLOSE_SESSION"] = "CLOSE_SESSION"


class RPC_Call(WSMessage):
    action: Literal["RPC_CALL"] = "RPC_CALL"
    url: str
    method: str
    headers: dict[str, str]
    body: Optional[JsonType]
    reply_id: Optional[uuid.UUID] = None


class RPC_Reply(WSMessage):
    action: Literal["RPC_REPLY"] = "RPC_REPLY"
    result: ReturnTypes
    code: int


type WSMessages = Annotated[OpenSession | CloseSession | RPC_Call | RPC_Reply, pydantic.Field(discriminator="action")]

message_parser = pydantic.TypeAdapter(WSMessage)


class WebsocketHandler(tornado.websocket.WebSocketHandler):
    """A handler for websocket based 2-way communication"""

    def initialize(self, transport: "RESTServer") -> None:
        LOGGER.debug("Starting websocket handler")
        self._server: "RESTServer" = transport
        self.session_id: Optional[uuid.UUID] = None
        self_environment_id: Optional[uuid.UUID] = None
        self._seen: float = time.monotonic()
        self.endpoint_names: Optional[set[str]] = None
        self.nodename: Optional[str] = None

    async def open(self, *args: str, **kwargs: str) -> None:
        if "session_id" not in kwargs or "env_id" not in kwargs:
            raise exceptions.ServerError("No session and environment id provided.")

        self.session_id = uuid.UUID(kwargs["session_id"])
        self.environment_id = uuid.UUID(kwargs["env_id"])

    async def on_message(self, message: Union[str, bytes]) -> None:
        msg = message_parser.validate_json(message)

        self._seen = time.monotonic()

        match msg:
            case OpenSession():
                self.endpoint_names = msg.endpoint_names
                self.nodename = msg.nodename

            case CloseSession():
                self._server.close_session(self)
                self.close()

            case RPC_Call():
                # A request from the client on the server
                self.add_background_task(self.dispatch_method(msg))

            case RPC_Reply():
                # A reply to a request send by the server to the client
                pass

    async def dispatch_method(self, msg: RPC_Call) -> None:
        """Dispatch a request from the server into the RPC code so the requests gets executed. The call results is send back
        to the server using a heartbeat reply.
        """
        method_call = common.Request(url=msg.url, method=msg.method, headers=msg.headers, body=msg.body, reply_id=msg.reply_id)

        LOGGER.debug("Received call through websocket: %s %s %s", method_call.reply_id, method_call.method, method_call.url)
        kwargs, config = match_call(self._server.endpoint, method_call.url, method_call.method)

        if config is None:
            # We cannot match the call to method on this endpoint. We send a reply to report this + ensure that the session
            # does not time out
            msg = "An error occurred during heartbeat method call ({} {} {}): {}".format(
                method_call.reply_id,
                method_call.method,
                method_call.url,
                "No such method",
            )
            LOGGER.error(msg)
            # if reply_id is none, we don't send the reply
            if method_call.reply_id is not None:
                await self._client.heartbeat_reply(self.sessionid, method_call.reply_id, {"result": msg, "code": 500})
            return

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
            response: common.Response = await self._server._execute_call(config, body, method_call.headers)

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

        if self._client is None:
            raise Exception("AgentEndpoint not started")

        # if reply is none, we don't send the reply
        if method_call.reply_id is not None:
            await self._client.heartbeat_reply(
                self.sessionid, method_call.reply_id, {"result": response.body, "code": response.status_code}
            )

    async def on_ping(self, data: bytes) -> None:
        """Called when we get a ping request from the client. The handler will send a pong back."""
        self._seen = time.monotonic()

    async def on_pong(self, data: bytes) -> None:
        """Called when we get a response to our ping"""
        self._seen = time.monotonic()

    async def on_close(self) -> None:
        self._server.close_session(self)


class RESTServer(RESTBase):
    """A tornado based rest server with websocket based two-way communication support"""

    _http_server: Optional[httpserver.HTTPServer]

    def __init__(self, endpoint: endpoints.Endpoint, id: str) -> None:
        super().__init__()

        self._id = id
        self.headers: dict[str, str] = {}
        self.endpoint = endpoint
        # number of ongoing requests
        self.inflight_counter = 0
        # event indicating no more in flight requests
        self.idle_event = asyncio.Event()
        self.idle_event.set()
        self.running = False
        self._http_server = None

        # Session management
        self._sessions: dict[uuid.UUID, session.Session] = {}

        # Listeners
        self.listeners: list[common.SessionListener] = []

    def start_request(self) -> None:
        self.idle_event.clear()
        self.inflight_counter += 1

    def end_request(self) -> None:
        self.inflight_counter -= 1
        if self.inflight_counter == 0:
            self.idle_event.set()

    def validate_sid(self, sid: uuid.UUID) -> bool:
        return self.session_manager.validate_sid(sid)

    def get_global_url_map(
        self, targets: list[inmanta.protocol.endpoints.CallTarget]
    ) -> dict[str, dict[str, common.UrlMethod]]:
        global_url_map: dict[str, dict[str, common.UrlMethod]] = defaultdict(dict)
        for slice in targets:
            url_map = slice.get_op_mapping()
            for url, configs in url_map.items():
                handler_config = global_url_map[url]
                for op, cfg in configs.items():
                    handler_config[op] = cfg
        return global_url_map

    async def start(
        self, targets: Sequence[inmanta.protocol.endpoints.CallTarget], additional_rules: list[routing.Rule] = []
    ) -> None:
        """
        Start the server on the current ioloop
        """
        global_url_map: dict[str, dict[str, common.UrlMethod]] = self.get_global_url_map(targets)

        rules: list[routing.Rule] = [
            routing.Rule(
                routing.PathMatches("/v2/ws/(?P<env_id>[^/]+)/(?P<session_id>[^/]+)"), WebsocketHandler, {"transport": self}
            )
        ]
        rules.extend(additional_rules)

        for url, handler_config in global_url_map.items():
            rules.append(routing.Rule(routing.PathMatches(url), RESTHandler, {"transport": self, "config": handler_config}))
            LOGGER.debug("Registering handler(s) for url %s and methods %s", url, ", ".join(handler_config.keys()))

        application = web.Application(rules, compress_response=True, websocket_ping_interval=1)

        crt = inmanta_config.Config.get("server", "ssl_cert_file", None)
        key = inmanta_config.Config.get("server", "ssl_key_file", None)

        if crt is not None and key is not None:
            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(crt, key)

            self._http_server = httpserver.HTTPServer(application, decompress_request=True, ssl_options=ssl_ctx)
            LOGGER.debug("Created REST transport with SSL")
        else:
            self._http_server = httpserver.HTTPServer(application, decompress_request=True)

        bind_port = server_config.server_bind_port.get()
        bind_addresses = server_config.server_bind_address.get()

        for bind_addr in bind_addresses:
            self._http_server.listen(bind_port, bind_addr)
            LOGGER.info(f"Server listening on {bind_addr}:{bind_port}")
        self.running = True

        LOGGER.debug("Start REST transport")

    async def stop(self) -> None:
        """
        Stop the current server
        """
        self.running = False
        LOGGER.debug("Stopping Server Rest Endpoint")

        # terminate all sessions cleanly (do we need to hold the lock?)
        for session in self._sessions.copy().values():
            await session.expire(0)
            session.abort()

        if self._http_server is not None:
            self._http_server.stop()

    async def join(self) -> None:
        await self.idle_event.wait()
        if self._http_server is not None:
            await self._http_server.close_all_connections()

    async def get_status(self) -> Mapping[str, ArgumentTypes]:
        return {"hangtime": self.hangtime, "interval": self.interval, "sessions": len(self._sessions)}

    def add_session_listener(self, listener: common.SessionListener) -> None:
        self.listeners.append(listener)


