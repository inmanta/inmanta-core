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
import ssl
import uuid

from typing import Optional, Dict, List

import tornado
from pyformance import timer
from tornado import gen, httpserver, web, routing

import inmanta.protocol.endpoints
from inmanta import config as inmanta_config, const
from inmanta.protocol import exceptions, common
from inmanta.protocol.rest import LOGGER, CONTENT_TYPE, JSON_CONTENT, RESTBase
from inmanta.types import NoneGen, JsonType


class RESTHandler(tornado.web.RequestHandler):
    """
        A generic class use by the transport
    """

    def initialize(self, transport: "RESTServer", config: Dict[str, common.UrlMethod]) -> None:
        self._transport: "RESTServer" = transport
        self._config = config

    def _get_config(self, http_method: str) -> common.UrlMethod:
        if http_method.upper() not in self._config:
            allowed = ", ".join(self._config.keys())
            self.set_header("Allow", allowed)
            raise exceptions.BaseException(
                405, "%s is not supported for this url. Supported methods: %s" % (http_method, allowed)
            )

        return self._config[http_method]

    def get_auth_token(self, headers: Dict[str, str]) -> Optional[Dict[str, str]]:
        """
            Get the auth token provided by the caller. The token is provided as a bearer token.
        """
        if "Authorization" not in headers:
            return None

        parts = headers["Authorization"].split(" ")
        if len(parts) == 0 or parts[0].lower() != "bearer" or len(parts) > 2 or len(parts) == 1:
            LOGGER.warning(
                "Invalid authentication header, Inmanta expects a bearer token. (%s was provided)", headers["Authorization"]
            )
            return None

        return common.decode_token(parts[1])

    def respond(self, body: Optional[JsonType], headers: Dict[str, str], status: int) -> None:
        if CONTENT_TYPE not in headers:
            headers[CONTENT_TYPE] = JSON_CONTENT
        elif headers[CONTENT_TYPE] != JSON_CONTENT:
            raise Exception("Invalid content type header provided. Only %s is supported" % JSON_CONTENT)

        if body is not None:
            self.write(common.json_encode(body))

        for header, value in headers.items():
            self.set_header(header, value)

        self.set_status(status)

    @gen.coroutine
    def _call(self, kwargs: Dict[str, str], http_method: str, call_config: common.UrlMethod) -> NoneGen:
        """
            An rpc like call
        """
        if call_config is None:
            raise exceptions.NotFound("This method does not exist")

        with timer("rpc." + call_config.method_name).time():
            self._transport.start_request()
            self.set_header("Access-Control-Allow-Origin", "*")
            try:
                message = self._transport._decode(self.request.body)
                if message is None:
                    message = {}

                for key, value in self.request.query_arguments.items():
                    if len(value) == 1:
                        message[key] = value[0].decode("latin-1")
                    else:
                        message[key] = [v.decode("latin-1") for v in value]

                request_headers = self.request.headers
                auth_token = self.get_auth_token(request_headers)

                auth_enabled: bool = inmanta_config.Config.get("server", "auth", False)
                if not auth_enabled or auth_token is not None:
                    result = yield self._transport._execute_call(
                        kwargs, http_method, call_config, message, request_headers, auth_token
                    )
                    self.respond(result.body, result.headers, result.status_code)
                else:
                    raise exceptions.UnauthorizedException("Access to this resource is unauthorized.")

            except ValueError:
                LOGGER.exception("An exception occured")
                self.respond({"message": "Unable to decode request body"}, {}, 400)

            except exceptions.BaseException as e:
                self.respond(e.to_body(), {}, e.to_status())

            finally:
                try:
                    yield self.finish()
                except Exception:
                    LOGGER.exception("An exception occurred responding to %s", self.request.remote_ip)
                self._transport.end_request()

    @gen.coroutine
    def head(self, *args: str, **kwargs: str) -> NoneGen:
        if args:
            raise Exception("Only named groups are support in url patterns")
        yield self._call(http_method="HEAD", call_config=self._get_config("HEAD"), kwargs=kwargs)

    @gen.coroutine
    def get(self, *args: str, **kwargs: str) -> NoneGen:
        if args:
            raise Exception("Only named groups are support in url patterns")
        yield self._call(http_method="GET", call_config=self._get_config("GET"), kwargs=kwargs)

    @gen.coroutine
    def post(self, *args: str, **kwargs: str) -> NoneGen:
        if args:
            raise Exception("Only named groups are support in url patterns")
        yield self._call(http_method="POST", call_config=self._get_config("POST"), kwargs=kwargs)

    @gen.coroutine
    def delete(self, *args: str, **kwargs: str) -> NoneGen:
        if args:
            raise Exception("Only named groups are support in url patterns")
        yield self._call(http_method="DELETE", call_config=self._get_config("DELETE"), kwargs=kwargs)

    @gen.coroutine
    def patch(self, *args: str, **kwargs: str) -> NoneGen:
        if args:
            raise Exception("Only named groups are support in url patterns")
        yield self._call(http_method="PATCH", call_config=self._get_config("PATCH"), kwargs=kwargs)

    @gen.coroutine
    def put(self, *args: str, **kwargs: str) -> NoneGen:
        if args:
            raise Exception("Only named groups are support in url patterns")
        yield self._call(http_method="PUT", call_config=self._get_config("PUT"), kwargs=kwargs)

    def options(self, *args: str, **kwargs: str) -> None:
        if args:
            raise Exception("Only named groups are support in url patterns")

        allow_headers = "Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token, %s" % const.INMANTA_MT_HEADER
        if len(self._transport.headers):
            allow_headers += ", " + ", ".join(self._transport.headers)

        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "HEAD, GET, POST, PUT, OPTIONS, DELETE, PATCH")
        self.set_header("Access-Control-Allow-Headers", allow_headers)

        self.set_status(200)


class StaticContentHandler(tornado.web.RequestHandler):
    def initialize(self, transport: "RESTServer", content: str, content_type: str) -> None:
        self._transport = transport
        self._content = content
        self._content_type = content_type

    def get(self, *args: List[str], **kwargs: Dict[str, str]) -> None:
        self.set_header("Content-Type", self._content_type)
        self.write(self._content)
        self.set_status(200)


class RESTServer(RESTBase):
    """
        A tornado based rest server
    """

    _http_server: httpserver.HTTPServer

    def __init__(self, session_manager: common.SessionManagerInterface, id: str) -> None:
        super().__init__()

        self._id = id
        self.headers: Dict[str, str] = {}
        self.session_manager = session_manager
        # number of ongoing requests
        self.inflight_counter = 0
        # event indicating no more in flight requests
        self.idle_event = asyncio.Event()
        self.idle_event.set()

    def start_request(self):
        self.idle_event.clear()
        self.inflight_counter += 1

    def end_request(self):
        self.inflight_counter -= 1
        if self.inflight_counter == 0:
            self.idle_event.set()

    def validate_sid(self, sid: uuid.UUID) -> bool:
        return self.session_manager.validate_sid(sid)

    @gen.coroutine
    def start(self, targets: List[inmanta.protocol.endpoints.CallTarget], additional_rules: List[routing.Rule] = []) -> NoneGen:
        """
            Start the server on the current ioloop
        """
        rules: List[routing.Rule] = []
        rules.extend(additional_rules)

        for slice in targets:
            url_map = slice.get_op_mapping()

            for url, configs in url_map.items():
                handler_config = {}
                for op, cfg in configs.items():
                    handler_config[op] = cfg

                rules.append(routing.Rule(routing.PathMatches(url), RESTHandler, {"transport": self, "config": handler_config}))
                LOGGER.debug("Registering handler(s) for url %s and methods %s" % (url, ", ".join(handler_config.keys())))

        port = 8888
        if self.id in inmanta_config.Config.get() and "port" in inmanta_config.Config.get()[self.id]:
            port = inmanta_config.Config.get()[self.id]["port"]

        application = web.Application(rules, compress_response=True)

        crt = inmanta_config.Config.get("server", "ssl_cert_file", None)
        key = inmanta_config.Config.get("server", "ssl_key_file", None)

        if crt is not None and key is not None:
            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(crt, key)

            self._http_server = httpserver.HTTPServer(application, decompress_request=True, ssl_options=ssl_ctx)
            LOGGER.debug("Created REST transport with SSL")
        else:
            self._http_server = httpserver.HTTPServer(application, decompress_request=True)
        self._http_server.listen(port)

        LOGGER.debug("Start REST transport")

    async def stop(self) -> None:
        """
            Stop the current server
        """
        LOGGER.debug("Stopping Server Rest Endpoint")
        if self._http_server is not None:
            self._http_server.stop()

    @gen.coroutine
    def join(self) -> NoneGen:
        yield self.idle_event.wait()
        yield self._http_server.close_all_connections()
