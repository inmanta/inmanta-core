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
import logging
import inspect
import json
import re
from datetime import datetime
from collections import defaultdict
import enum

import tornado
from tornado import gen
from inmanta import const
from inmanta.protocol import methods, common
from inmanta import config as inmanta_config
from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPError
from tornado import httpserver
from typing import Any, Dict, List, Optional, Tuple, Set, Callable  # noqa: F401

LOGGER: logging.Logger = logging.getLogger(__name__)
INMANTA_MT_HEADER = "X-Inmanta-tid"
CONTENT_TYPE = "Content-Type"
JSON_CONTENT = "application/json"

"""

RestServer  => manages tornado/handlers, marshalling, dispatching, and endpoints

ServerSlice => contributes handlers and methods

ServerSlice.server [1] -- RestServer.endpoints [1:]

"""


def authorize_request(auth_data: Dict[str, str], metadata: Dict[str, str], message: str, config: common.UrlMethod) -> None:
    """
        Authorize a request based on the given data
    """
    if auth_data is None:
        return

    # Enforce environment restrictions
    env_key = const.INMANTA_URN + "env"
    if env_key in auth_data:
        if env_key not in metadata:
            raise common.UnauhorizedError("The authorization token is scoped to a specific environment.")

        if metadata[env_key] != "all" and auth_data[env_key] != metadata[env_key]:
            raise common.UnauhorizedError("The authorization token is not valid for the requested environment.")

    # Enforce client_types restrictions
    ok = False
    ct_key = const.INMANTA_URN + "ct"
    for ct in auth_data[ct_key]:
        if ct in config.properties.client_types:
            ok = True

    if not ok:
        raise common.UnauhorizedError(
            "The authorization token does not have a valid client type for this call."
            + " (%s provided, %s expected" % (auth_data[ct_key], config.properties.client_types)
        )


# Shared
class RESTBase(object):
    """
        Base class for REST based client and servers
    """

    _id: str

    def __init__(self) -> None:
        pass

    @property
    def id(self) -> str:
        return self._id

    def _decode(self, body: str) -> Optional[Dict]:
        """
            Decode a response body
        """
        result = None
        if body is not None and len(body) > 0:
            result = json.loads(tornado.escape.to_basestring(body))

        return result

    def return_error_msg(self, status: int = 500, msg="", headers={}):
        body = {"message": msg}
        headers["Content-Type"] = "application/json"
        LOGGER.debug("Signaling error to client: %d, %s, %s", status, body, headers)
        return body, headers, status

    @gen.coroutine
    def _execute_call(self, kwargs, http_method, config: common.UrlMethod, message, request_headers, auth=None):
        headers = {"Content-Type": "application/json"}
        try:
            if kwargs is None or config is None:
                raise Exception("This method is unknown! This should not occur!")

            # create message that contains all arguments (id, query args and body)
            if "id" in kwargs and (message is None or "id" not in message):
                message["id"] = kwargs["id"]

            # validate message against config
            if config.properties.id and "id" not in message:
                return self.return_error_msg(500, "Invalid request. It should contain an id in the url.", headers)

            if config.properties.validate_sid:
                if "sid" not in message:
                    return self.return_error_msg(
                        500, "This is an agent to server call, it should contain an agent session id", headers
                    )

                elif not self.validate_sid(message["sid"]):
                    return self.return_error_msg(500, "The sid %s is not valid." % message["sid"], headers)

            # validate message against the arguments
            argspec = inspect.getfullargspec(config.properties.function)
            args = argspec.args

            if "self" in args:
                args.remove("self")

            all_fields = set(message.keys())
            if argspec.defaults is not None:
                defaults_start = len(args) - len(argspec.defaults)
            else:
                defaults_start = -1

            metadata = {}
            for i in range(len(args)):
                arg = args[i]

                opts = None
                # handle defaults and header mapping
                if arg in config.properties.arg_options:
                    opts: common.ArgOption = config.properties.arg_options[arg]

                    if opts.header:
                        message[arg] = request_headers[opts.header]
                        if opts.reply_header:
                            headers[opts.header] = message[arg]
                    all_fields.add(arg)

                if arg not in message:
                    if defaults_start >= 0 and (i - defaults_start) < len(argspec.defaults):
                        message[arg] = argspec.defaults[i - defaults_start]
                    else:
                        return self.return_error_msg(500, "Invalid request. Field '%s' is required." % arg, headers)

                else:
                    all_fields.remove(arg)

                # validate the type
                if arg in argspec.annotations:
                    arg_type = argspec.annotations[arg]
                    if message[arg] is not None and not isinstance(message[arg], arg_type):
                        try:
                            if arg_type == datetime:
                                message[arg] = datetime.strptime(message[arg], "%Y-%m-%dT%H:%M:%S.%f")

                            elif issubclass(arg_type, enum.Enum):
                                message[arg] = arg_type[message[arg]]

                            elif arg_type == bool:
                                message[arg] = inmanta_config.is_bool(message[arg])

                            else:
                                message[arg] = arg_type(message[arg])

                        except (ValueError, TypeError):
                            error_msg = "Invalid type for argument %s. Expected %s but received %s" % (
                                arg,
                                arg_type,
                                message[arg].__class__,
                            )
                            LOGGER.exception(error_msg)
                            return self.return_error_msg(500, error_msg, headers)

                # execute any getters that are defined
                if opts and opts.getter:
                    try:
                        result = yield opts.getter(message[arg], metadata)
                        message[arg] = result
                    except methods.HTTPException as e:
                        LOGGER.exception("Failed to use getter for arg %s", arg)
                        return self.return_error_msg(e.code, e.message, headers)

            if config.properties.agent_server:
                if "sid" in all_fields:
                    del message["sid"]
                    all_fields.remove("sid")

            if len(all_fields) > 0 and argspec.varkw is None:
                return self.return_error_msg(
                    500,
                    "Request contains fields %s that are not declared in method and no kwargs argument is provided."
                    % all_fields,
                    headers,
                )

            LOGGER.debug(
                "Calling method %s(%s)",
                config.handler,
                ", ".join(["%s='%s'" % (name, common.shorten(str(value))) for name, value in message.items()]),
            )

            if hasattr(config.handler, "__protocol_mapping__"):
                for k, v in config.handler.__protocol_mapping__.items():
                    if v in message:
                        message[k] = message[v]
                        del message[v]

            try:
                authorize_request(auth, metadata, message, config)
            except common.UnauhorizedError as e:
                return self.return_error_msg(403, e.args[0], headers)

            result = yield config.handler(**message)

            if result is None:
                raise Exception(
                    "Handlers for method calls should at least return a status code. %s on %s"
                    % (config.method_name, config.endpoint)
                )

            reply = None
            if isinstance(result, tuple):
                if len(result) == 2:
                    code, reply = result
                else:
                    raise Exception("Handlers for method call can only return a status code and a reply")

            else:
                code = result

            if reply is not None:
                if config.properties.reply:
                    LOGGER.debug("%s returned %d: %s", config.method_name, code, common.shorten(str(reply), 70))
                    return reply, headers, code

                else:
                    LOGGER.warning("Method %s returned a result although it is has not reply!")

            return None, headers, code

        except Exception as e:
            LOGGER.exception("An exception occured during the request.")
            return self.return_error_msg(500, "An exception occured: " + str(e.args), headers)


class RESTHandler(tornado.web.RequestHandler):
    """
        A generic class use by the transport
    """

    def initialize(self, transport: "RESTServer", config):
        self._transport = transport
        self._config = config

    def _get_config(self, http_method):
        if http_method.upper() not in self._config:
            allowed = ", ".join(self._config.keys())
            self.set_header("Allow", allowed)
            self._transport.return_error_msg(
                405, "%s is not supported for this url. Supported methods: %s" % (http_method, allowed)
            )
            return

        return self._config[http_method]

    def get_auth_token(self, headers: dict):
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

    def respond(self, body: Optional[Dict[str, Any]], headers: Dict[str, str], status: int) -> None:
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
    def _call(self, kwargs, http_method, call_config):
        """
            An rpc like call
        """
        if call_config is None:
            body, headers, status = self._transport.return_error_msg(404, "This method does not exist.")
            self.respond(body, headers, status)
            return

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

            try:
                auth_token = self.get_auth_token(request_headers)
            except common.UnauhorizedError as e:
                self.respond(*self._transport.return_error_msg(403, "Access denied: " + e.args[0]))
                return

            auth_enabled = inmanta_config.Config.get("server", "auth", False)
            if not auth_enabled or auth_token is not None:
                result = yield self._transport._execute_call(
                    kwargs, http_method, call_config, message, request_headers, auth_token
                )
                self.respond(*result)
            else:
                self.respond(*self._transport.return_error_msg(401, "Access to this resource is unauthorized."))
        except ValueError:
            LOGGER.exception("An exception occured")
            self.respond(*self._transport.return_error_msg(500, "Unable to decode request body"))

        finally:
            self.finish()

    @gen.coroutine
    def head(self, *args, **kwargs):
        yield self._call(http_method="HEAD", call_config=self._get_config("HEAD"), kwargs=kwargs)

    @gen.coroutine
    def get(self, *args, **kwargs):
        yield self._call(http_method="GET", call_config=self._get_config("GET"), kwargs=kwargs)

    @gen.coroutine
    def post(self, *args, **kwargs):
        yield self._call(http_method="POST", call_config=self._get_config("POST"), kwargs=kwargs)

    @gen.coroutine
    def delete(self, *args, **kwargs):
        yield self._call(http_method="DELETE", call_config=self._get_config("DELETE"), kwargs=kwargs)

    @gen.coroutine
    def patch(self, *args, **kwargs):
        yield self._call(http_method="PATCH", call_config=self._get_config("PATCH"), kwargs=kwargs)

    @gen.coroutine
    def put(self, *args, **kwargs):
        yield self._call(http_method="PUT", call_config=self._get_config("PUT"), kwargs=kwargs)

    @gen.coroutine
    def options(self, *args, **kwargs):
        allow_headers = "Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token"
        if len(self._transport.headers):
            allow_headers += ", " + ", ".join(self._transport.headers)

        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "HEAD, GET, POST, PUT, OPTIONS, DELETE, PATCH")
        self.set_header("Access-Control-Allow-Headers", allow_headers)

        self.set_status(200)


class StaticContentHandler(tornado.web.RequestHandler):
    def initialize(self, transport: "RESTServer", content, content_type):
        self._transport = transport
        self._content = content
        self._content_type = content_type

    def get(self, *args, **kwargs):
        self.set_header("Content-Type", self._content_type)
        self.write(self._content)
        self.set_status(200)


class RESTServer(RESTBase):
    """
        A tornado based rest server
    """

    _http_server: httpserver.HTTPServer

    def __init__(self) -> None:
        super().__init__()

    def start(self) -> None:
        """
            Start the server on the current ioloop
        """

    def stop(self) -> None:
        """
            Stop the current server
        """
        LOGGER.debug("Stopping Server Rest Endpoint")
        if self._http_server is None:
            self._http_server.stop()


# Client side
class RESTClient(RESTBase):
    """"
        A REST (json body over http) client transport. Only methods that operate on resource can use all
        HTTP verbs. For other methods the POST verb is used.
    """

    def __init__(self, endpoint: "Endpoint", connection_timout: int = 120) -> None:
        super().__init__()
        self.__end_point = endpoint
        self.daemon = True
        self.token = inmanta_config.Config.get(self.id, "token", None)
        self.connection_timout = connection_timout
        self.headers: Set[str] = set()
        self.request_timeout = inmanta_config.Config.get(self.id, "request_timeout", 120)

    @property
    def endpoint(self):
        return self.__end_point

    def get_id(self):
        """
            Returns a unique id for a transport on an endpoint
        """
        return "%s_rest_transport" % self.__end_point.name

    id = property(get_id)

    def create_op_mapping(self) -> Dict[str, Dict[str, Callable]]:
        """
            Build a mapping between urls, ops and methods
        """
        url_map: Dict[str, Dict[str, Callable]] = defaultdict(dict)
        for method, method_handlers in self.endpoint.get_endpoint_metadata().items():
            properties = method.__method_properties__
            self.headers.update(properties.get_call_headers())

            url = properties.get_listen_url()
            url_map[url][properties.operation] = common.UrlMethod(
                properties, self.endpoint, method_handlers[1], method_handlers[0]
            )

        return url_map

    def match_call(self, url: str, method: str) -> Tuple[Optional[Dict], Optional[Callable]]:
        """
            Get the method call for the given url and http method. This method is used for return calls over long poll
        """
        url_map = self.create_op_mapping()
        for url_re, handlers in url_map.items():
            if not url_re.endswith("$"):
                url_re += "$"
            match = re.match(url_re, url)
            if match and method in handlers:
                return match.groupdict(), handlers[method]

        return None, None

    def _get_client_config(self) -> str:
        """
            Load the configuration for the client
        """
        LOGGER.debug("Getting config in section %s", self.id)

        port = inmanta_config.Config.get(self.id, "port", 8888)
        host = inmanta_config.Config.get(self.id, "host", "localhost")

        if inmanta_config.Config.getboolean(self.id, "ssl", False):
            protocol = "https"
        else:
            protocol = "http"

        return "%s://%s:%d" % (protocol, host, port)

    @gen.coroutine
    def call(self, properties: common.MethodProperties, args: List, kwargs: Dict[str, Any] = {}) -> common.Result:
        url, headers, body = properties.build_call(args, kwargs)

        url_host = self._get_client_config()
        url = url_host + url

        if self.token is not None:
            headers["Authorization"] = "Bearer " + self.token

        if body is not None:
            zipped, body = common.gzipped_json(body)
            if zipped:
                headers["Content-Encoding"] = "gzip"

        ca_certs = inmanta_config.Config.get(self.id, "ssl_ca_cert_file", None)
        LOGGER.debug("Calling server %s %s", properties.operation, url)

        try:
            request = HTTPRequest(
                url=url,
                method=properties.operation,
                headers=headers,
                body=body,
                connect_timeout=self.connection_timout,
                request_timeout=self.request_timeout,
                ca_certs=ca_certs,
                decompress_response=True,
            )
            client = AsyncHTTPClient()
            response = yield client.fetch(request)
        except HTTPError as e:
            if e.response is not None and e.response.body is not None and len(e.response.body) > 0:
                try:
                    result = self._decode(e.response.body)
                except ValueError:
                    result = {}
                return common.Result(code=e.code, result=result)

            return common.Result(code=e.code, result={"message": str(e)})
        except Exception as e:
            return common.Result(code=500, result={"message": str(e)})

        return common.Result(code=response.code, result=self._decode(response.body))

    def validate_sid(self, sid):
        return self.endpoint.validate_sid(sid)
