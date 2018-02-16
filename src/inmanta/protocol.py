"""
    Copyright 2017 Inmanta

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
import socket
import time
import inspect
import urllib
import uuid
import json
import re
from datetime import datetime
from collections import defaultdict
import enum
import warnings
import io
import gzip

import tornado.web
from tornado import gen, queues, web
from inmanta import methods, const, execute
from inmanta import config as inmanta_config
from tornado.httpserver import HTTPServer
from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPError
from tornado.ioloop import IOLoop
import ssl
import jwt

LOGGER = logging.getLogger(__name__)
INMANTA_MT_HEADER = "X-Inmanta-tid"


class Result(object):
    """
        A result of a method call
    """

    def __init__(self, multiple=False, code=0, result=None):
        self._multiple = multiple
        if multiple:
            self._result = []
            if result is not None:
                self._result.append(result)
        else:
            self._result = result
        self.code = code
        self._callback = None

    def add_result(self, result):
        """
        Add a new result to an instance

        :param result: The result to store
        """
        assert(self._multiple)
        self._result.append(result)
        if self._callback:
            self._callback(self)

    def get_result(self):
        """
            Only when the result is marked as available the result can be returned
        """
        if self.available():
            return self._result
        raise Exception("The result is not yet available")

    def set_result(self, value):
        if not self.available():
            assert(not self._multiple)
            self._result = value
            if self._callback:
                self._callback(self)

    def available(self):
        if self._multiple:
            return len(self._result) > 0 is not None or self.code > 0
        else:
            return self._result is not None or self.code > 0

    def wait(self, timeout=60):
        """
            Wait for the result to become available
        """
        count = 0
        while count < timeout:
            time.sleep(0.1)
            count += 0.1

    result = property(get_result, set_result)

    def callback(self, fnc):
        """
            Set a callback function that is to be called when the result is ready. When multiple
            results are expected, the callback is called for each result.
        """
        self._callback = fnc


class Transport(object):
    """
        This class implements a transport for the Inmanta protocol.

        :param end_point_name: The name of the endpoint to which this transport belongs. This is used
            for logging and configuration purposes
    """
    @classmethod
    def create(cls, transport_class, endpoint=None):
        """
            Create an instance of the transport class
        """
        return transport_class(endpoint)

    def __init__(self, endpoint=None):
        self.__end_point = endpoint
        self.daemon = True
        self._connected = False

    endpoint = property(lambda x: x.__end_point)

    def get_id(self):
        """
            Returns a unique id for a transport on an endpoint
        """
        return "%s_%s_transport" % (self.__end_point.name, self.__class__.__transport_name__)

    id = property(get_id)

    def start_endpoint(self):
        """
            Start the transport as endpoint
        """
        self.start()

    def stop_endpoint(self):
        """
            Stop the transport as endpoint
        """
        self.stop()

    def start_client(self):
        """
            Start this transport as client
        """
        self.start()

    def stop_client(self):
        """
            Stop this transport as client
        """
        self.stop()

    def start(self):
        """
            Start the transport as a new thread
        """

    def stop(self):
        """
            Stop the transport
        """
        self._connected = False

    def call(self, method, destination=None, **kwargs):
        """
            Perform a method call
        """
        raise NotImplementedError()

    def _decode(self, body):
        """
            Decode a response body
        """
        if body is not None and len(body) > 0:
            body = json.loads(tornado.escape.to_basestring(body))
        else:
            body = None

        return body

    def set_connected(self):
        """
            Mark this transport as connected
        """
        LOGGER.debug("Transport %s is connected", self.get_id())
        self._connected = True

    def is_connected(self):
        """
            Is this transport connected
        """
        return self._connected


def custom_json_encoder(o):
    """
        A custom json encoder that knows how to encode other types commonly used by Inmanta
    """
    if isinstance(o, uuid.UUID):
        return str(o)

    if isinstance(o, datetime):
        return o.isoformat()

    if hasattr(o, "to_dict"):
        return o.to_dict()

    if isinstance(o, enum.Enum):
        return o.name

    if isinstance(o, Exception):
        # Logs can push exceptions through RPC. Return a string representation.
        return str(o)

    if isinstance(o, execute.util.Unknown):
        return const.UNKNOWN_STRING

    LOGGER.error("Unable to serialize %s", o)
    raise TypeError(repr(o) + " is not JSON serializable")


def json_encode(value):
    # see json_encode in tornado.escape
    return json.dumps(value, default=custom_json_encoder).replace("</", "<\\/")


def gzipped_json(value):
    value = json_encode(value)
    if len(value) < web.GZipContentEncoding.MIN_LENGTH:
        return False, value

    gzip_value = io.BytesIO()
    gzip_file = gzip.GzipFile(mode="w", fileobj=gzip_value, compresslevel=web.GZipContentEncoding.GZIP_LEVEL)

    gzip_file.write(value.encode())
    gzip_file.close()

    return True, gzip_value.getvalue()


class UnauhorizedError(Exception):
    pass


def encode_token(client_types, environment=None, idempotent=False, expire=None):
    cfg = inmanta_config.AuthJWTConfig.get_sign_config()

    payload = {
        "iss": cfg.issuer,
        "aud": [cfg.audience],
        const.INMANTA_URN + "ct": ",".join(client_types),
    }

    if not idempotent:
        payload["iat"] = int(time.time())

        if cfg.expire > 0:
            payload["exp"] = int(time.time() + cfg.expire)
        elif expire is not None:
            payload["exp"] = int(time.time() + expire)

    if environment is not None:
        payload[const.INMANTA_URN + "env"] = environment

    return jwt.encode(payload, cfg.key, cfg.algo).decode()


def decode_token(token):
    try:
        # First decode the token without verification
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, verify=False)
    except Exception as e:
        raise UnauhorizedError("Unable to decode provided JWT bearer token.")

    if "iss" not in payload:
        raise UnauhorizedError("Issuer is required in token to validate.")

    cfg = inmanta_config.AuthJWTConfig.get_issuer(payload["iss"])
    if cfg is None:
        raise UnauhorizedError("Unknown issuer for token")

    alg = header["alg"].lower()
    if alg == "hs256":
        key = cfg.key
    elif alg == "rs256":
        if "kid" not in header:
            raise UnauhorizedError("A kid is required for RS256")
        kid = header["kid"]
        if kid not in cfg.keys:
            raise UnauhorizedError("The kid provided in the token does not match a known key. Check the jwks_uri or try "
                                   "restarting the server to load any new keys.")

        key = cfg.keys[kid]
    else:
        raise UnauhorizedError("Algorithm %s is not supported." % alg)

    try:
        payload = jwt.decode(token, key, audience=cfg.audience, algorithms=[cfg.algo])
        ct_key = const.INMANTA_URN + "ct"
        payload[ct_key] = [x.strip() for x in payload[ct_key].split(",")]
    except Exception as e:
        raise UnauhorizedError(*e.args)

    return payload


class RESTHandler(tornado.web.RequestHandler):
    """
        A generic class use by the transport
    """

    def initialize(self, transport: Transport, config):
        self._transport = transport
        self._config = config

    def _get_config(self, http_method):
        if http_method.upper() not in self._config:
            allowed = ", ".join(self._config.keys())
            self.set_header("Allow", allowed)
            self._transport.return_error_msg(405, "%s is not supported for this url. Supported methods: %s" %
                                             (http_method, allowed))
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
            LOGGER.warning("Invalid authentication header, Inmanta expects a bearer token. (%s was provided)",
                           headers["Authorization"])
            return None

        return decode_token(parts[1])

    def respond(self, body, headers, status):
        if body is not None:
            self.write(json_encode(body))

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
            except UnauhorizedError as e:
                self.respond(*self._transport.return_error_msg(403, "Access denied: " + e.args[0]))
                return

            auth_enabled = inmanta_config.Config.get("server", "auth", False)
            if not auth_enabled or auth_token is not None:
                result = yield self._transport._execute_call(kwargs, http_method, call_config,
                                                             message, request_headers, auth_token)
                self.respond(*result)
            else:
                self.respond(*self._transport.return_error_msg(401, "Access to this resource is unauthorized."))
        except ValueError:
            LOGGER.exception("An exception occured")
            self.respond(*self._transport.return_error_msg(500, "Unable to decode request body"))

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
    def initialize(self, transport: Transport, content, content_type):
        self._transport = transport
        self._content = content
        self._content_type = content_type

    def get(self, *args, **kwargs):
        self.set_header("Content-Type", self._content_type)
        self.write(self._content)
        self.set_status(200)


def sh(msg, max_len=10):
    if len(msg) < max_len:
        return msg
    return msg[0:max_len - 3] + "..."


def authorize_request(auth_data, metadata, message, config):
    """
        Authorize a request based on the given data
    """
    if auth_data is None:
        return

    # Enforce environment restrictions
    env_key = const.INMANTA_URN + "env"
    if env_key in auth_data:
        if env_key not in metadata:
            raise UnauhorizedError("The authorization token is scoped to a specific environment.")

        if metadata[env_key] != "all" and auth_data[env_key] != metadata[env_key]:
            raise UnauhorizedError("The authorization token is not valid for the requested environment.")

    # Enforce client_types restrictions
    ok = False
    ct_key = const.INMANTA_URN + "ct"
    for ct in auth_data[ct_key]:
        if ct in config[0]["client_types"]:
            ok = True

    if not ok:
        raise UnauhorizedError("The authorization token does not have a valid client type for this call." +
                               " (%s provided, %s expected" % (auth_data[ct_key], config[0]["client_types"]))

    return


class RESTTransport(Transport):
    """"
        A REST (json body over http) transport. Only methods that operate on resource can use all
        HTTP verbs. For other methods the POST verb is used.
    """
    __transport_name__ = "rest"

    def __init__(self, endpoint, connection_timout=120):
        super().__init__(endpoint)
        self.set_connected()
        self._handlers = []
        self.token = inmanta_config.Config.get(self.id, "token", None)
        self.connection_timout = connection_timout
        self.headers = set()

    def _create_base_url(self, properties, msg=None, versioned=True):
        """
            Create a url for the given protocol properties
        """
        url = "/api/v1" if versioned else ""
        if "id" in properties and properties["id"]:
            if msg is None:
                url += "/%s/(?P<id>[^/]+)" % properties["method_name"]
            else:
                url += "/%s/%s" % (properties["method_name"], urllib.parse.quote(str(msg["id"]), safe=""))

        elif "index" in properties and properties["index"]:
            url += "/%s" % properties["method_name"]
        else:
            url += "/%s" % properties["method_name"]

        return url

    def create_op_mapping(self):
        """
            Build a mapping between urls, ops and methods
        """
        url_map = defaultdict(dict)
        headers = set()
        for method, method_handlers in self.endpoint.__methods__.items():
            properties = method.__protocol_properties__
            call = (self.endpoint, method_handlers[0])

            if "arg_options" in properties:
                for opts in properties["arg_options"].values():
                    if "header" in opts:
                        headers.add(opts["header"])

            url = self._create_base_url(properties)
            properties["api_version"] = "1"
            url_map[url][properties["operation"]] = (properties, call, method.__wrapped__)

            url = self._create_base_url(properties, versioned=False)
            properties = properties.copy()
            properties["api_version"] = None
            url_map[url][properties["operation"]] = (properties, call, method.__wrapped__)

        headers.add("Authorization")
        self.headers = headers
        return url_map

    def match_call(self, url, method):
        """
            Get the method call for the given url and http method
        """
        url_map = self.create_op_mapping()
        for url_re, handlers in url_map.items():
            if not url_re.endswith("$"):
                url_re += "$"
            match = re.match(url_re, url)
            if match and method in handlers:
                return match.groupdict(), handlers[method]

        return None, None

    def return_error_msg(self, status=500, msg="", headers={}):
        body = {"message": msg}
        headers["Content-Type"] = "application/json"
        LOGGER.debug("Signaling error to client: %d, %s, %s", status, body, headers)
        return body, headers, status

    @gen.coroutine
    def _execute_call(self, kwargs, http_method, config, message, request_headers, auth=None):
        if "api_version" in config[0] and config[0]["api_version"] is None:
            warnings.warn("Using an unversioned API method will be removed in the next release", DeprecationWarning)
            LOGGER.warning("Using an unversioned API method will be removed in the next release")

        headers = {"Content-Type": "application/json"}
        try:
            if kwargs is None or config is None:
                raise Exception("This method is unknown! This should not occur!")
            # create message that contains all arguments (id, query args and body)
            if "id" in kwargs and (message is None or "id" not in message):
                message["id"] = kwargs["id"]

            # validate message against config
            if "id" in config[0] and config[0]["id"] and "id" not in message:
                return self.return_error_msg(500, "Invalid request. It should contain an id in the url.", headers)

            validate_sid = config[0]["validate_sid"]
            if validate_sid:
                if 'sid' not in message:
                    return self.return_error_msg(500,
                                                 "This is an agent to server call, it should contain an agent session id",
                                                 headers)
                elif not self.validate_sid(message['sid']):
                    return self.return_error_msg(500, "The sid %s is not valid." % message['sid'], headers)

            # validate message against the arguments
            argspec = inspect.getfullargspec(config[2])
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

                opts = {}
                # handle defaults and header mapping
                if arg in config[0]["arg_options"]:
                    opts = config[0]["arg_options"][arg]

                    if "header" in opts:
                        message[arg] = request_headers[opts["header"]]
                        if "reply_header" in opts and opts["reply_header"]:
                            headers[opts["header"]] = message[arg]
                    all_fields.add(arg)

                if arg not in message:
                    if (defaults_start >= 0 and (i - defaults_start) < len(argspec.defaults)):
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
                            error_msg = ("Invalid type for argument %s. Expected %s but received %s" %
                                         (arg, arg_type, message[arg].__class__))
                            LOGGER.exception(error_msg)
                            return self.return_error_msg(500, error_msg, headers)

                # execute any getters that are defined
                if "getter" in opts:
                    try:
                        result = yield opts["getter"](message[arg], metadata)
                        message[arg] = result
                    except methods.HTTPException as e:
                        LOGGER.exception("Failed to use getter for arg %s", arg)
                        return self.return_error_msg(e.code, e.message, headers)

            if config[0]["agent_server"]:
                if 'sid' in all_fields:
                    del message['sid']
                    all_fields.remove('sid')

            if len(all_fields) > 0 and argspec.varkw is None:
                return self.return_error_msg(500, ("Request contains fields %s " % all_fields) +
                                             "that are not declared in method and no kwargs argument is provided.", headers)

            LOGGER.debug("Calling method %s(%s)", config[1][1], ", ".join(["%s='%s'" % (name, sh(str(value)))
                                                                           for name, value in message.items()]))
            method_call = getattr(config[1][0], config[1][1])

            if hasattr(method_call, "__protocol_mapping__"):
                for k, v in method_call.__protocol_mapping__.items():
                    if v in message:
                        message[k] = message[v]
                        del message[v]

            try:
                authorize_request(auth, metadata, message, config)
            except UnauhorizedError as e:
                return self.return_error_msg(403, e.args[0], headers)

            result = yield method_call(**message)

            if result is None:
                raise Exception("Handlers for method calls should at least return a status code. %s on %s" % config[1])

            reply = None
            if isinstance(result, tuple):
                if len(result) == 2:
                    code, reply = result
                else:
                    raise Exception("Handlers for method call can only return a status code and a reply")

            else:
                code = result

            if reply is not None:
                if "reply" in config[0] and config[0]:
                    LOGGER.debug("%s returned %d: %s", config[1][1], code, sh(str(reply), 70))
                    return reply, headers, code

                else:
                    LOGGER.warn("Method %s returned a result although it is has not reply!")

            return None, headers, code

        except Exception as e:
            LOGGER.exception("An exception occured during the request.")
            return self.return_error_msg(500, "An exception occured: " + str(e.args), headers)

    def add_static_handler(self, location, path, default_filename=None, start=False):
        """
            Configure a static handler to serve data from the specified path.
        """
        if location[0] != "/":
            location = "/" + location

        if location[-1] != "/":
            location = location + "/"

        options = {"path": path}
        if default_filename is None:
            options["default_filename"] = "index.html"

        self._handlers.append((r"%s(.*)" % location, tornado.web.StaticFileHandler, options))
        self._handlers.append((r"%s" % location[:-1], tornado.web.RedirectHandler, {"url": location}))

        if start:
            self._handlers.append((r"/", tornado.web.RedirectHandler, {"url": location}))

    def add_static_content(self, path, content, content_type="application/javascript"):
        self._handlers.append((r"%s(.*)" % path, StaticContentHandler, {"transport": self, "content": content,
                                                                        "content_type": content_type}))

    def start_endpoint(self):
        """
            Start the transport
        """
        url_map = self.create_op_mapping()

        for url, configs in url_map.items():
            handler_config = {}
            for op, cfg in configs.items():
                handler_config[op] = cfg

            self._handlers.append((url, RESTHandler, {"transport": self, "config": handler_config}))
            LOGGER.debug("Registering handler(s) for url %s and methods %s" % (url, ", ".join(handler_config.keys())))

        port = 8888
        if self.id in inmanta_config.Config.get() and "port" in inmanta_config.Config.get()[self.id]:
            port = inmanta_config.Config.get()[self.id]["port"]

        application = tornado.web.Application(self._handlers, compress_response=True)

        crt = inmanta_config.Config.get("server", "ssl_cert_file", None)
        key = inmanta_config.Config.get("server", "ssl_key_file", None)

        if(crt is not None and key is not None):
            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(crt, key)

            self.http_server = HTTPServer(application, decompress_request=True, ssl_options=ssl_ctx)
            LOGGER.debug("Created REST transport with SSL")
        else:
            self.http_server = HTTPServer(application, decompress_request=True)

        self.http_server.listen(port)

        LOGGER.debug("Start REST transport")
        super().start()

    def stop_endpoint(self):
        super().stop()
        self.http_server.stop()

    def _get_client_config(self):
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

    def build_call(self, properties, args, kwargs={}):
        """
            Build a call from the given arguments. This method returns the url, headers, method and body for the call.
        """
        method = properties["operation"]

        # create the message
        msg = kwargs

        # map the argument in arg to names
        argspec = inspect.getfullargspec(properties["method"])
        for i in range(len(args)):
            msg[argspec.args[i + 1]] = args[i]

        url = self._create_base_url(properties, msg)

        headers = {}

        for arg_name in list(msg.keys()):
            if isinstance(msg[arg_name], enum.Enum):  # Handle enum values "special"
                msg[arg_name] = msg[arg_name].name

            if arg_name in properties["arg_options"]:
                opts = properties["arg_options"][arg_name]
                if "header" in opts:
                    headers[opts["header"]] = str(msg[arg_name])
                    del msg[arg_name]

        if not (method == "POST" or method == "PUT" or method == "PATCH"):
            qs_map = msg.copy()
            if "id" in qs_map:
                del qs_map["id"]

            # encode arguments in url
            if len(qs_map) > 0:
                url += "?" + urllib.parse.urlencode(qs_map)

            body = None
        else:
            body = msg

        return url, method, headers, body

    @gen.coroutine
    def call(self, properties, args, kwargs={}):
        url, method, headers, body = self.build_call(properties, args, kwargs)

        url_host = self._get_client_config()
        url = url_host + url

        if self.token is not None:
            headers["Authorization"] = "Bearer " + self.token

        if body is not None:
            zipped, body = gzipped_json(body)
            if zipped:
                headers["Content-Encoding"] = "gzip"

        ca_certs = inmanta_config.Config.get(self.id, "ssl_ca_cert_file", None)
        LOGGER.debug("Calling server %s %s", method, url)

        try:
            request = HTTPRequest(url=url, method=method, headers=headers, body=body, connect_timeout=self.connection_timout,
                                  request_timeout=120, ca_certs=ca_certs, decompress_response=True)
            client = AsyncHTTPClient()
            response = yield client.fetch(request)
        except HTTPError as e:
            if e.response is not None and len(e.response.body) > 0:
                try:
                    result = self._decode(e.response.body)
                except ValueError:
                    result = {}
                return Result(code=e.code, result=result)

            return Result(code=e.code, result={"message": str(e)})
        except Exception as e:
            raise e
            return Result(code=500, result={"message": str(e)})

        return Result(code=response.code, result=self._decode(response.body))

    def validate_sid(self, sid):
        return self.endpoint.validate_sid(sid)


class handle(object):  # noqa: H801
    """
        Decorator for subclasses of an endpoint to handle protocol methods

        :param method A subclass of method that defines the method
    """

    def __init__(self, method, **kwargs):
        self.method = method
        self.mapping = kwargs

    def __call__(self, function):
        """
            The wrapping
        """
        class_name = self.method.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
        module = inspect.getmodule(self.method)
        method_class = getattr(module, class_name)

        if not hasattr(method_class, "__method_name__"):
            raise Exception("%s should have a __method_name__ variable." % method_class)

        if "method_name" not in self.method.__protocol_properties__:
            self.method.__protocol_properties__["method_name"] = method_class.__method_name__

        function.__protocol_method__ = self.method
        function.__protocol_mapping__ = self.mapping
        return function


class EndpointMeta(type):
    """
        Meta class to create endpoints
    """
    def __new__(cls, class_name, bases, dct):
        if "__methods__" not in dct:
            dct["__methods__"] = {}

        total_dict = dct.copy()
        for base in bases:
            total_dict.update(base.__dict__)

        methods = {}
        for name, attr in total_dict.items():
            if name[0:2] != "__" and hasattr(attr, "__protocol_method__"):
                if attr.__protocol_method__ in methods:
                    raise Exception("Unable to register multiple handlers for the same method.")

                methods[attr.__protocol_method__] = (name, attr)

        dct["__methods__"] = methods

        return type.__new__(cls, class_name, bases, dct)


class Scheduler(object):
    """
        An event scheduler class
    """

    def __init__(self, io_loop):
        self._scheduled = set()
        self._io_loop = io_loop

    def add_action(self, action, interval, initial_delay=None):
        """
            Add a new action

            :param action A function to call periodically
            :param interval The interval between execution of actions
            :param initial_delay Delay to the first execution, default to interval
        """

        if initial_delay is None:
            initial_delay = interval

        LOGGER.debug("Scheduling action %s every %d seconds with initial delay %d", action, interval, initial_delay)

        def action_function():
            LOGGER.info("Calling %s" % action)
            if action in self._scheduled:
                try:
                    action()
                except Exception:
                    LOGGER.exception("Uncaught exception while executing scheduled action")

                finally:
                    self._io_loop.call_later(interval, action_function)

        self._io_loop.call_later(initial_delay, action_function)
        self._scheduled.add(action)

    def remove(self, action):
        """
            Remove a scheduled action
        """
        if action in self._scheduled:
            self._scheduled.remove(action)


class Endpoint(object):
    """
        An end-point in the rpc framework
    """

    def __init__(self, io_loop, name):
        self._name = name
        self._node_name = inmanta_config.nodename.get()
        self._end_point_names = []
        self._io_loop = io_loop

    def add_future(self, future):
        """
            Add a future to the ioloop to be handled, but do not require the result.
        """
        def handle_result(f):
            try:
                f.result()
            except Exception as e:
                LOGGER.exception("An exception occurred while handling a future: %s", str(e))

        self._io_loop.add_future(future, handle_result)

    def get_end_point_names(self):
        return self._end_point_names

    def add_end_point_name(self, name):
        """
            Add an additional name to this endpoint to which it reacts and sends out in heartbeats
        """
        LOGGER.debug("Adding '%s' as endpoint", name)
        self._end_point_names.append(name)

    def clear_end_points(self):
        """
            Clear all endpoints
        """
        self._end_point_names = []

    name = property(lambda self: self._name)
    end_point_names = property(get_end_point_names)

    def _get_hostname(self):
        """
            Determine the hostname of this machine
        """
        return socket.gethostname()

    def get_node_name(self):
        return self._node_name

    node_name = property(get_node_name)


class Session(object):
    """
        An environment that segments agents connected to the server
    """

    def __init__(self, sessionstore, io_loop, sid, hang_interval, timout, tid, endpoint_names, nodename):
        self._sid = sid
        self._interval = hang_interval
        self._timeout = timout
        self._sessionstore = sessionstore
        self._seen = time.time()
        self._callhandle = None
        self.expired = False

        self.tid = tid
        self.endpoint_names = endpoint_names
        self.nodename = nodename

        self._io_loop = io_loop

        self._replies = {}
        self.check_expire()
        self._queue = queues.Queue()

        self.client = ReturnClient(str(sid), self)

    def check_expire(self):
        if self.expired:
            LOGGER.exception("Tried to expire session already expired")
        ttw = self._timeout + self._seen - time.time()
        if ttw < 0:
            self.expire(self._seen - time.time())
        else:
            self._callhandle = self._io_loop.call_later(ttw, self.check_expire)

    def get_id(self):
        return self._sid

    id = property(get_id)

    def expire(self, timeout):
        self.expired = True
        if self._callhandle is not None:
            self._io_loop.remove_timeout(self._callhandle)
        self._sessionstore.expire(self, timeout)

    def seen(self):
        self._seen = time.time()

    def _set_timeout(self, future, timeout, log_message):
        def on_timeout():
            if not self.expired:
                LOGGER.warning(log_message)
            future.set_exception(gen.TimeoutError())

        timeout_handle = self._io_loop.add_timeout(self._io_loop.time() + timeout, on_timeout)
        future.add_done_callback(lambda _: self._io_loop.remove_timeout(timeout_handle))

    def put_call(self, call_spec, timeout=10):
        future = tornado.concurrent.Future()

        reply_id = uuid.uuid4()

        LOGGER.debug("Putting call %s: %s %s for agent %s in queue", reply_id, call_spec["method"], call_spec["url"], self._sid)

        q = self._queue
        call_spec["reply_id"] = reply_id
        q.put(call_spec)
        self._set_timeout(future, timeout, "Call %s: %s %s for agent %s timed out." %
                          (reply_id, call_spec["method"], call_spec["url"], self._sid))
        self._replies[call_spec["reply_id"]] = future

        return future

    @gen.coroutine
    def get_calls(self):
        """
            Get all calls queued for a node. If no work is available, wait until timeout. This method returns none if a call
            fails.
        """
        try:
            q = self._queue
            call_list = []
            call = yield q.get(timeout=self._io_loop.time() + self._interval)
            call_list.append(call)
            while q.qsize() > 0:
                call = yield q.get()
                call_list.append(call)

            return call_list

        except gen.TimeoutError:
            return None

    def set_reply(self, reply_id, data):
        LOGGER.log(3, "Received Reply: %s", reply_id)
        if reply_id in self._replies:
            future = self._replies[reply_id]
            del self._replies[reply_id]
            if not future.done():
                future.set_result(data)
        else:
            LOGGER.debug("Received Reply that is unknown: %s", reply_id)

    def get_client(self):
        return self.client


class ServerEndpoint(Endpoint, metaclass=EndpointMeta):
    """
        A service that receives method calls over one or more transports
    """
    __methods__ = {}

    def __init__(self, name, io_loop, transport=RESTTransport, interval=60, hangtime=None):
        super().__init__(io_loop, name)
        self._transport = transport

        self._transport_instance = Transport.create(self._transport, self)
        self._sched = Scheduler(self._io_loop)

        self._heartbeat_cb = None
        self.agent_handles = {}
        self._sessions = {}
        self.interval = interval
        if hangtime is None:
            hangtime = interval * 3 / 4
        self.hangtime = hangtime

    def schedule(self, call, interval=60):
        self._sched.add_action(call, interval)

    def start(self):
        """
            Start this end-point using the central configuration
        """
        LOGGER.debug("Starting transport for endpoint %s", self.name)
        if self._transport_instance is not None:
            self._transport_instance.start_endpoint()

    def stop(self):
        """
            Stop the end-point and all of its transports
        """
        if self._transport_instance is not None:
            self._transport_instance.stop_endpoint()
            LOGGER.debug("Stopped %s", self._transport_instance)
        # terminate all sessions cleanly
        for session in self._sessions.copy().values():
            session.expire(0)

    def validate_sid(self, sid):
        if isinstance(sid, str):
            sid = uuid.UUID(sid)
        return sid in self._sessions

    def get_or_create_session(self, sid, tid, endpoint_names, nodename):
        if isinstance(sid, str):
            sid = uuid.UUID(sid)

        if sid not in self._sessions:
            session = self.new_session(sid, tid, endpoint_names, nodename)
            self._sessions[sid] = session
        else:
            session = self._sessions[sid]
            self.seen(session, endpoint_names)

        return session

    def new_session(self, sid, tid, endpoint_names, nodename):
        LOGGER.debug("New session with id %s on node %s for env %s with endpoints %s" % (sid, nodename, tid, endpoint_names))
        return Session(self, self._io_loop, sid, self.hangtime, self.interval, tid, endpoint_names, nodename)

    def expire(self, session: Session, timeout):
        LOGGER.debug("Expired session with id %s, last seen %d seconds ago" % (session.get_id(), timeout))
        del self._sessions[session.id]

    def seen(self, session: Session, endpoint_names: list):
        LOGGER.debug("Seen session with id %s" % (session.get_id()))
        session.seen()

    @handle(methods.HeartBeatMethod.heartbeat, env="tid")
    @gen.coroutine
    def heartbeat(self, sid, env, endpoint_names, nodename):
        LOGGER.debug("Received heartbeat from %s for agents %s in %s", nodename, ",".join(endpoint_names), env.id)

        session = self.get_or_create_session(sid, env.id, endpoint_names, nodename)

        LOGGER.debug("Let node %s wait for method calls to become available. (long poll)", nodename)
        call_list = yield session.get_calls()
        if call_list is not None:
            LOGGER.debug("Pushing %d method calls to node %s", len(call_list), nodename)
            return 200, {"method_calls": call_list}
        else:
            LOGGER.debug("Heartbeat wait expired for %s, returning. (long poll)", nodename)

        return 200

    @handle(methods.HeartBeatMethod.heartbeat_reply)
    @gen.coroutine
    def heartbeat_reply(self, sid, reply_id, data):
        try:
            env = self._sessions[sid]
            env.set_reply(reply_id, data)
            return 200
        except Exception:
            LOGGER.warning("could not deliver agent reply with sid=%s and reply_id=%s" % (sid, reply_id), exc_info=True)


class AgentEndPoint(Endpoint, metaclass=EndpointMeta):
    """
        An endpoint for clients that make calls to a server and that receive calls back from the server using long-poll
    """

    def __init__(self, name, io_loop, timeout=120, transport=RESTTransport, reconnect_delay=5):
        super().__init__(io_loop, name)
        self._transport = transport
        self._client = None
        self._sched = Scheduler(self._io_loop)

        self._env_id = None

        self.sessionid = uuid.uuid1()
        self.running = True
        self.server_timeout = timeout
        self.reconnect_delay = reconnect_delay

    def get_environment(self):
        return self._env_id

    environment = property(get_environment)

    def set_environment(self, environment_id: uuid.UUID):
        """
            Set the environment of this agent
        """
        if isinstance(environment_id, str):
            self._env_id = uuid.UUID(environment_id)
        else:
            self._env_id = environment_id

    def start(self):
        """
            Connect to the server and use a heartbeat and long-poll for two-way communication
        """
        assert self._env_id is not None
        LOGGER.log(3, "Starting agent for %s", str(self.sessionid))
        self._client = AgentClient(self.name, self.sessionid, transport=self._transport, timeout=self.server_timeout)
        self._io_loop.add_callback(self.perform_heartbeat)

    def stop(self):
        self.running = False

    @gen.coroutine
    def on_reconnect(self):
        pass

    @gen.coroutine
    def perform_heartbeat(self):
        """
            Start a continuous heartbeat call
        """
        connected = False
        while self.running:
            LOGGER.log(3, "sending heartbeat for %s", str(self.sessionid))
            result = yield self._client.heartbeat(sid=str(self.sessionid),
                                                  tid=str(self._env_id),
                                                  endpoint_names=self.end_point_names,
                                                  nodename=self.node_name)
            LOGGER.log(3, "returned heartbeat for %s", str(self.sessionid))
            if result.code == 200:
                if not connected:
                    connected = True
                    self.add_future(self.on_reconnect())
                if result.result is not None:
                    if "method_calls" in result.result:
                        method_calls = result.result["method_calls"]
                        transport = self._transport(self)

                        for method_call in method_calls:
                            self.dispatch_method(transport, method_call)
            else:
                LOGGER.warning("Heartbeat failed with status %d and message: %s, going to sleep for %d s",
                               result.code, result.result, self.reconnect_delay)
                connected = False
                yield gen.sleep(self.reconnect_delay)

    def dispatch_method(self, transport, method_call):
        LOGGER.debug("Received call through heartbeat: %s %s %s", method_call[
                     "reply_id"], method_call["method"], method_call["url"])
        kwargs, config = transport.match_call(method_call["url"], method_call["method"])

        if config is None:
            msg = "An error occurred during heartbeat method call (%s %s %s): %s" % (
                method_call["reply_id"], method_call["method"], method_call["url"], "No such method")
            LOGGER.error(msg)
            self.add_future(self._client.heartbeat_reply(self.sessionid, method_call["reply_id"],
                                                         {"result": msg, "code": 500}))

        body = {}
        if "body" in method_call and method_call["body"] is not None:
            body = method_call["body"]

        query_string = urllib.parse.urlparse(method_call["url"]).query
        for key, value in urllib.parse.parse_qs(query_string, keep_blank_values=True):
            if len(value) == 1:
                body[key] = value[0].decode("latin-1")
            else:
                body[key] = [v.decode("latin-1") for v in value]

        call_result = self._transport(self)._execute_call(kwargs, method_call["method"], config, body,
                                                          method_call["headers"])

        def submit_result(future):
            if future is None:
                return

            result_body, _, status = future.result()
            if status == 500:
                msg = ""
                if result_body is not None and "message" in result_body:
                    msg = result_body["message"]
                LOGGER.error("An error occurred during heartbeat method call (%s %s %s): %s",
                             method_call["reply_id"], method_call["method"], method_call["url"], msg)
            self._client.heartbeat_reply(self.sessionid, method_call["reply_id"],
                                         {"result": result_body, "code": status})

        self._io_loop.add_future(call_result, submit_result)


class ClientMeta(type):
    """
        A meta class that programs all protocol method call into the Client class.
    """
    def __new__(cls, class_name, bases, dct):
        classes = methods.Method.__subclasses__()  # @UndefinedVariable

        for mcls in classes:
            for attr in dir(mcls):
                attr_fn = getattr(mcls, attr)
                if attr[0:2] != "__" and hasattr(attr_fn, "__wrapped__"):
                    dct[attr] = attr_fn

        return type.__new__(cls, class_name, bases, dct)


def get_method_name(properties):
    method = properties["method"]
    class_name = method.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
    module = inspect.getmodule(method)
    method_class = getattr(module, class_name)

    if not hasattr(method_class, "__method_name__"):
        raise Exception("%s should have a __method_name__ variable." % method_class)

    return method_class.__method_name__


class Client(Endpoint, metaclass=ClientMeta):
    """
        A client that communicates with end-point based on its configuration
    """

    def __init__(self, name, ioloop=None, transport=RESTTransport):
        if ioloop is None:
            ioloop = IOLoop.current()
        Endpoint.__init__(self, ioloop, name)
        self._transport = transport
        self._transport_instance = None

        LOGGER.debug("Start transport for client %s", self.name)
        tr = Transport.create(self._transport, self)
        self._transport_instance = tr

    @gen.coroutine
    def _call(self, args, kwargs, protocol_properties):
        """
            Execute the rpc call
        """
        protocol_properties["method_name"] = get_method_name(protocol_properties)
        result = yield self._transport_instance.call(protocol_properties, args, kwargs)
        return result


class SyncClient(object):
    """
        A synchronous client that communicates with end-point based on its configuration
    """
    def __init__(self, name, timeout=120):
        self.name = name
        self.timeout = timeout
        self._client = Client(self.name)

    def __getattr__(self, name):
        def async_call(*args, **kwargs):
            method = getattr(self._client, name)

            def method_call():
                return method(*args, **kwargs)

            try:
                return IOLoop.current().run_sync(method_call, self.timeout)
            except TimeoutError:
                raise ConnectionRefusedError()

        return async_call


class AgentClient(Endpoint, metaclass=ClientMeta):
    """
        A client that communicates with end-point based on its configuration
    """

    def __init__(self, name, sid, ioloop=None, transport=RESTTransport, timeout=120):
        if ioloop is None:
            ioloop = IOLoop.current()
        Endpoint.__init__(self, ioloop, name)
        self._transport = transport
        self._transport_instance = None
        self._sid = sid

        LOGGER.debug("Start transport for client %s", self.name)
        tr = self._transport(self, connection_timout=timeout)
        self._transport_instance = tr

    @gen.coroutine
    def _call(self, args, kwargs, protocol_properties):
        """
            Execute the rpc call
        """
        protocol_properties["method_name"] = get_method_name(protocol_properties)

        if 'sid' not in kwargs:
            kwargs['sid'] = self._sid

        result = yield self._transport_instance.call(protocol_properties, args, kwargs)
        return result


class ReturnClient(Client, metaclass=ClientMeta):
    """
        A client that uses a return channel to connect to its destination. This client is used by the server to communicate
        back to clients over the heartbeat channel.
    """

    def __init__(self, name, session):
        super().__init__(name)
        self.session = session

    @gen.coroutine
    def _call(self, args, kwargs, protocol_properties):
        protocol_properties["method_name"] = get_method_name(protocol_properties)
        url, method, headers, body = self._transport_instance.build_call(protocol_properties, args, kwargs)

        call_spec = {"url": url, "method": method, "headers": headers, "body": body}
        timeout = protocol_properties["timeout"]
        try:
            return_value = yield self.session.put_call(call_spec, timeout=timeout)
        except gen.TimeoutError:
            return Result(code=500, result="Call timed out")

        return Result(code=return_value["code"], result=return_value["result"])
