"""
    Copyright 2018 Inmanta

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
import uuid
import json
import re
from datetime import datetime
from collections import defaultdict
from urllib import parse
import enum
import io
import gzip
import functools

import tornado
from tornado import gen, web
from inmanta import methods, const, execute, rpc
from inmanta import config as inmanta_config
from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPError
from tornado.ioloop import IOLoop
import jwt
from typing import Any, Dict, Sequence, List, Optional, Union, Tuple, Set, Callable, Awaitable  # noqa: F401


from inmanta.util import Scheduler


LOGGER: logging.Logger = logging.getLogger(__name__)
INMANTA_MT_HEADER = "X-Inmanta-tid"

"""

RestServer  => manages tornado/handlers, marshalling, dispatching, and endpoints

ServerSlice => contributes handlers and methods

ServerSlice.server [1] -- RestServer.endpoints [1:]

"""


# Util functions
def custom_json_encoder(o: object) -> Union[Dict, str, List]:
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


def json_encode(value: object) -> str:
    # see json_encode in tornado.escape
    return json.dumps(value, default=custom_json_encoder).replace("</", "<\\/")


def gzipped_json(value: object) -> Tuple[bool, Union[bytes, str]]:
    value = json_encode(value)
    if len(value) < web.GZipContentEncoding.MIN_LENGTH:
        return False, value

    gzip_value = io.BytesIO()
    gzip_file = gzip.GzipFile(mode="w", fileobj=gzip_value, compresslevel=web.GZipContentEncoding.GZIP_LEVEL)

    gzip_file.write(value.encode())
    gzip_file.close()

    return True, gzip_value.getvalue()


def sh(msg: str, max_len: int=10) -> str:
    if len(msg) < max_len:
        return msg
    return msg[0:max_len - 3] + "..."


def encode_token(client_types: List[str], environment=None, idempotent: bool=False, expire=None):
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


def decode_token(token: str) -> Dict[str, str]:
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


def authorize_request(auth_data: Dict[str, str], metadata: Dict[str, str], message: str, config: List[Dict[str, str]]) -> None:
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


# API
class UnauhorizedError(Exception):
    pass


class Result(object):
    """
        A result of a method call
    """
    def __init__(self, code: int=0, result: Dict[str, Any]=None):
        self._result = result
        self.code = code
        self._callback = None

    def get_result(self):
        """
            Only when the result is marked as available the result can be returned
        """
        if self.available():
            return self._result
        raise Exception("The result is not yet available")

    def set_result(self, value):
        if not self.available():
            self._result = value
            if self._callback:
                self._callback(self)

    def available(self):
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
            Set a callback function that is to be called when the result is ready.
        """
        self._callback = fnc


# Tornado Interface


# Shared
class RESTBase(object):

    def _create_base_url(self, properties: Dict[str, str], msg: Dict[str, str]=None) -> str:
        """
            Create a url for the given protocol properties
        """
        url = "/api/v1"
        if "id" in properties and properties["id"]:
            if msg is None:
                url += "/%s/(?P<id>[^/]+)" % properties["method_name"]
            else:
                url += "/%s/%s" % (properties["method_name"], parse.quote(str(msg["id"]), safe=""))

        elif "index" in properties and properties["index"]:
            url += "/%s" % properties["method_name"]
        else:
            url += "/%s" % properties["method_name"]

        return url

    def _decode(self, body: str) -> Optional[Dict]:
        """
            Decode a response body
        """
        result = None
        if body is not None and len(body) > 0:
            result = json.loads(tornado.escape.to_basestring(body))

        return result

    @gen.coroutine
    def _execute_call(self, kwargs, http_method, config, message, request_headers, auth=None):
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


# Client side
class RESTTransport(RESTBase):
    """"
        A REST (json body over http) transport. Only methods that operate on resource can use all
        HTTP verbs. For other methods the POST verb is used.
    """
    __transport_name__ = "rest"

    def __init__(self, endpoint: "Endpoint", connection_timout: int=120) -> None:
        self.__end_point = endpoint
        self.daemon = True
        self._connected = False
        self.set_connected()
        self._handlers = []
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
        return "%s_%s_transport" % (self.__end_point.name, self.__class__.__transport_name__)

    id = property(get_id)

    def start_client(self):
        """
            Start this transport as client
        """
        self.start()

    def stop_client(self) -> None:
        """
            Stop this transport as client
        """
        self.stop()

    def start(self) -> None:
        """
            Start the transport as a new thread
        """
        pass

    def stop(self) -> None:
        """
            Stop the transport
        """
        self._connected = False

    def set_connected(self) -> None:
        """
            Mark this transport as connected
        """
        LOGGER.debug("Transport %s is connected", self.get_id())
        self._connected = True

    def is_connected(self) -> bool:
        """
            Is this transport connected
        """
        return self._connected

    def create_op_mapping(self) -> Dict[str, Dict[str, Callable]]:
        """
            Build a mapping between urls, ops and methods
        """
        url_map: Dict[str, Dict[str, Callable]] = defaultdict(dict)
        headers = set()
        for method, method_handlers in self.endpoint.__methods__.items():
            properties = method.__protocol_properties__
            call = (self.endpoint, method_handlers[0])

            if "arg_options" in properties:
                for opts in properties["arg_options"].values():
                    if "header" in opts:
                        headers.add(opts["header"])

            url = self._create_base_url(properties)
            url_map[url][properties["operation"]] = (properties, call, method.__wrapped__)

        headers.add("Authorization")
        self.headers = headers
        return url_map

    def match_call(self, url: str, method: str) -> Tuple[Optional[Dict], Optional[Callable]]:
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
    def call(self, properties: rpc.MethodProperties, args: List, kwargs: Dict[str, Any]={}) -> Result:
        url, headers, body = properties.build_call(args, kwargs)

        url_host = self._get_client_config()
        url = url_host + url

        if self.token is not None:
            headers["Authorization"] = "Bearer " + self.token

        if body is not None:
            zipped, body = gzipped_json(body)
            if zipped:
                headers["Content-Encoding"] = "gzip"

        ca_certs = inmanta_config.Config.get(self.id, "ssl_ca_cert_file", None)
        LOGGER.debug("Calling server %s %s", properties.operation, url)

        try:
            request = HTTPRequest(url=url, method=properties.operation, headers=headers, body=body, connect_timeout=self.connection_timout,
                                  request_timeout=self.request_timeout, ca_certs=ca_certs, decompress_response=True)
            client = AsyncHTTPClient()
            response = yield client.fetch(request)
        except HTTPError as e:
            if e.response is not None and e.response.body is not None and len(e.response.body) > 0:
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

    def __init__(self, method: str, **kwargs) -> None:
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


class Endpoint(object):
    """
        An end-point in the rpc framework
    """

    def __init__(self, name):
        self._name = name
        self._node_name = inmanta_config.nodename.get()
        self._end_point_names = []

    def add_future(self, future) -> None:
        """
            Add a future to the ioloop to be handled, but do not require the result.
        """
        def handle_result(f):
            try:
                f.result()
            except Exception as e:
                LOGGER.exception("An exception occurred while handling a future: %s", str(e))

        IOLoop.current().add_future(future, handle_result)

    def get_end_point_names(self) -> List[str]:
        return self._end_point_names

    def add_end_point_name(self, name: str) -> None:
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


class AgentEndPoint(Endpoint, metaclass=EndpointMeta):
    """
        An endpoint for clients that make calls to a server and that receive calls back from the server using long-poll
    """

    def __init__(self, name, timeout=120, transport=RESTTransport, reconnect_delay=5):
        super().__init__(name)
        self._transport = transport
        self._client = None
        self._sched = Scheduler()

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
        self._client = AgentClient(self.name, self.sessionid, timeout=self.server_timeout)
        IOLoop.current().add_callback(self.perform_heartbeat)

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

        query_string = parse.urlparse(method_call["url"]).query
        for key, value in parse.parse_qs(query_string, keep_blank_values=True):
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

        IOLoop.current().add_future(call_result, submit_result)


class Client(Endpoint):
    """
        A client that communicates with end-point based on its configuration
    """
    def __init__(self, name: str) -> None:
        super().__init__(name)
        LOGGER.debug("Start transport for client %s", self.name)
        self._transport_instance = RESTTransport(self)

    @gen.coroutine
    def _call(self, method_properties, args, kwargs) -> Result:
        """
            Execute a call and return the result
        """
        result = yield self._transport_instance.call(method_properties, args, kwargs)
        return result

    def __getattr__(self, name: str) -> Callable:
        """
            Return a function that will call self._call with the correct method properties associated
        """
        if name in rpc.MethodProperties._methods:
            method = rpc.MethodProperties._methods[name]

            def wrap(*args, **kwargs) -> Callable[[List[Any], Dict[str, Any]], Result]:
                method.function(self, *args, **kwargs)
                return self._call(method_properties=method, args=args, kwargs=kwargs)

            return wrap

        raise AttributeError("Method with name %s is not defined for this client" % name)


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


class AgentClient(Client):
    """
        A client that communicates with end-point based on its configuration
    """
    def __init__(self, name, sid, timeout=120):
        super().__init__(name)
        self._sid = sid
        self._transport_instance = RESTTransport(self, connection_timout=timeout)

    @gen.coroutine
    def _call(self, method_properties, args, kwargs) -> Result:
        """
            Execute the rpc call
        """
        if 'sid' not in kwargs:
            kwargs['sid'] = self._sid

        result = yield self._transport_instance.call(method_properties, args, kwargs)
        return result


class ReturnClient(Client):
    """
        A client that uses a return channel to connect to its destination. This client is used by the server to communicate
        back to clients over the heartbeat channel.
    """

    def __init__(self, name, session) -> None:
        super().__init__(name)
        self.session = session

    @gen.coroutine
    def _call(self, method_properties: rpc.MethodProperties, args, kwargs) -> Result:
        url, headers, body = method_properties.build_call(args, kwargs)

        call_spec = {"url": url, "method": method_properties.operation, "headers": headers, "body": body}
        timeout = method_properties.timeout
        try:
            return_value = yield self.session.put_call(call_spec, timeout=timeout)
        except gen.TimeoutError:
            return Result(code=500, result="Call timed out")

        return Result(code=return_value["code"], result=return_value["result"])
