"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io

    This module defines the Impera protocol between components. The protocol is marshaling and
    transport independent. Example support can be json over http and amqp
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

import tornado.web
from tornado import gen, queues
from impera import methods
from impera.config import Config
from tornado.httpserver import HTTPServer
from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPError
from tornado.ioloop import IOLoop


LOGGER = logging.getLogger(__name__)
IMPERA_MT_HEADER = "X-Impera-tid"


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
        This class implements a transport for the Impera protocol.

        :param end_point_name The name of the endpoint to which this transport belongs. This is used
            for logging and configuration purposes
    """
    __data__ = tuple()
    __transport_name__ = None
    __broadcast__ = False
    __network__ = True

    @classmethod
    def create(cls, TransportClass, endpoint=None):
        """
            Create an instance of the transport class
        """
        return TransportClass(endpoint)

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
        A custom json encoder that knows how to encode other types commonly used by Impera
    """
    if isinstance(o, uuid.UUID):
        return str(o)

    if isinstance(o, datetime):
        return o.isoformat()

    raise TypeError(repr(o) + " is not JSON serializable")


def json_encode(value):
    # see json_encode in tornado.escape
    return json.dumps(value, default=custom_json_encoder).replace("</", "<\\/")


class RESTHandler(tornado.web.RequestHandler):
    """
        A generic class use by the transport
    """
    def initialize(self, transport, config):
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

    @gen.coroutine
    def _call(self, kwargs, http_method, config):
        """
            An rpc like call
        """
        self.set_header("Access-Control-Allow-Origin", "*")
        try:
            message = self._transport._decode(self.request.body)
            if message is None:
                message = {}
        except ValueError:
            LOGGER.exception("An exception occured")
            self._transport.return_error_msg(500, "Unable to decode request body")

        for key, value in self.request.query_arguments.items():
            if len(value) == 1:
                message[key] = value[0].decode("latin-1")
            else:
                message[key] = [v.decode("latin-1") for v in value]

        request_headers = self.request.headers
        body, headers, status = yield self._transport._execute_call(kwargs, http_method, config, message, request_headers)

        if body is not None:
            self.write(json_encode(body))

        for header, value in headers.items():
            self.set_header(header, value)

        self.set_status(status)

    @gen.coroutine
    def head(self, *args, **kwargs):
        yield self._call(http_method="HEAD", config=self._get_config("HEAD"), kwargs=kwargs)

    @gen.coroutine
    def get(self, *args, **kwargs):
        yield self._call(http_method="GET", config=self._get_config("GET"), kwargs=kwargs)

    @gen.coroutine
    def post(self, *args, **kwargs):
        yield self._call(http_method="POST", config=self._get_config("POST"), kwargs=kwargs)

    @gen.coroutine
    def delete(self, *args, **kwargs):
        yield self._call(http_method="DELETE", config=self._get_config("DELETE"), kwargs=kwargs)

    @gen.coroutine
    def patch(self, *args, **kwargs):
        yield self._call(http_method="PATCH", config=self._get_config("PATCH"), kwargs=kwargs)

    @gen.coroutine
    def put(self, *args, **kwargs):
        yield self._call(http_method="PUT", config=self._get_config("PUT"), kwargs=kwargs)

    @gen.coroutine
    def options(self, *args, **kwargs):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "HEAD, GET, POST, PUT, OPTIONS, DELETE, PATCH")
        self.set_header("Access-Control-Allow-Headers", "Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token, " +
                        IMPERA_MT_HEADER)

        self.set_status(200)


def sh(msg, max_len=10):
    if len(msg) < max_len:
        return msg
    return msg[0:max_len - 3] + "..."


class RESTTransport(Transport):
    """"
        A REST (json body over http) transport. Only methods that operate on resource can use all
        HTTP verbs. For other methods the POST verb is used.
    """
    __data__ = ("message", "blob")
    __transport_name__ = "rest"

    def __init__(self, endpoint):
        super().__init__(endpoint)
        self.set_connected()

    def _create_base_url(self, properties, msg=None):
        """
            Create a url for the given protocol properties
        """
        url = ""
        if "id" in properties and properties["id"]:
            if msg is None:
                url = "/%s/(?P<id>[^/]+)" % properties["method_name"]
            else:
                url = "/%s/%s" % (properties["method_name"], urllib.parse.quote(str(msg["id"]), safe=""))

        elif "index" in properties and properties["index"]:
            url = "/%s" % properties["method_name"]
        else:
            url = "/%s" % properties["method_name"]

        return url

    def create_op_mapping(self):
        """
            Build a mapping between urls, ops and methods
        """
        url_map = defaultdict(dict)
        for method, method_handlers in self.endpoint.__methods__.items():
            properties = method.__protocol_properties__
            call = (self.endpoint, method_handlers[0])

            url = self._create_base_url(properties)
            url_map[url][properties["operation"]] = (properties, call, method.__wrapped__)

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
        return body, headers, status

    @gen.coroutine
    def _execute_call(self, kwargs, http_method, config, message, request_headers):
        headers = {"Content-Type": "application/json"}
        try:
            # create message that contains all arguments (id, query args and body)
            if "id" in kwargs and (message is None or "id" not in message):
                message["id"] = kwargs["id"]

            # validate message against config
            if "id" in config[0] and config[0]["id"] and "id" not in message:
                return self.return_error_msg(500, "Invalid request. It should contain an id in the url.", headers)

            if "mt" in config[0] and config[0]["mt"]:
                if IMPERA_MT_HEADER not in request_headers:
                    return self.return_error_msg(500, "This is multi-tenant method, it should contain a tenant id", headers)

                else:
                    message["tid"] = request_headers[IMPERA_MT_HEADER]
                    if message["tid"] == "":
                        return self.return_error_msg(500, "%s header set without value." % IMPERA_MT_HEADER, headers)

                    headers[IMPERA_MT_HEADER] = message["tid"]

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

            for i in range(len(args)):
                arg = args[i]
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
                            else:
                                message[arg] = arg_type(message[arg])
                        except (ValueError, TypeError):
                            return self.return_error_msg(500, "Invalid type for argument %s. Expected %s but received %s" %
                                                         (arg, arg_type, message[arg].__class__), headers)

            if len(all_fields) > 0 and argspec.varkw is None:
                return self.return_error_msg(500, ("Request contains fields %s " % all_fields) +
                                             "that are not declared in method and no kwargs argument is provided.", headers)

            LOGGER.debug("Calling method %s(%s)", config[1][1], ", ".join(["%s='%s'" % (name, sh(str(value)))
                                                                           for name, value in message.items()]))
            method_call = getattr(config[1][0], config[1][1])

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
            LOGGER.exception("An exception occured")
            return self.return_error_msg(500, "An exception occured: " + str(e.args), headers)

    def start_endpoint(self):
        """
            Start the transport
        """
        url_map = self.create_op_mapping()

        handlers = []
        for url, configs in url_map.items():
            handler_config = {}
            for op, cfg in configs.items():
                handler_config[op] = cfg

            handlers.append((url, RESTHandler, {"transport": self, "config": handler_config}))
            LOGGER.debug("Registering handler(s) for url %s and methods %s" % (url, ", ".join(handler_config.keys())))

        port = 8888
        if self.id in Config.get() and "port" in Config.get()[self.id]:
            port = Config.get()[self.id]["port"]

        application = tornado.web.Application(handlers)
        self.http_server = HTTPServer(application)
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
        port = 8888
        if self.id in Config.get() and "port" in Config.get()[self.id]:
            port = int(Config.get()[self.id]["port"])

        host = "localhost"
        if self.id in Config.get() and "host" in Config.get()[self.id]:
            host = Config.get()[self.id]["host"]

        LOGGER.debug("Using %s:%s", host, port)
        return "http://%s:%d" % (host, port)

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
        if properties["mt"]:
            if "tid" not in msg:
                raise Exception("A multi-tenant method call should contain a tid parameter.")

            headers[IMPERA_MT_HEADER] = str(msg["tid"])
            del msg["tid"]

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
        LOGGER.debug("Calling server %s %s", method, url)

        try:
            if body is not None:
                body = json_encode(body)
            request = HTTPRequest(url=url, method=method, headers=headers, body=body)
            client = AsyncHTTPClient()
            response = yield client.fetch(request)
        except HTTPError as e:
            if e.response is not None and len(e.response.body) > 0:
                try:
                    result = self._decode(e.response.body)
                except ValueError:
                    result = {}
                return Result(code=e.code, result=result)
            return Result(code=e.code, result={"message": e.message})
        except Exception as e:
            return Result(code=500, result={"message": str(e)})

        return Result(code=response.code, result=self._decode(response.body))


class handle(object):
    """
        Decorator for subclasses of an endpoint to handle protocol methods

        :param method A subclass of method that defines the method
        :param operation The operation to use (POST, GET, PUT, HEAD, ...)
        :param id Is the special parameter id required
        :param index Does this method handle the index
    """
    def __init__(self, method):
        self.method = method

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

    def add_action(self, action, interval, now=False):
        """
            Add a new action

            :param action A function to call periodically
            :param interval The interval between execution of actions
            :param now Execute the first action now and schedule subsequent invocations
        """
        LOGGER.debug("Scheduling action %s every %d seconds", action, interval)

        def action_function():
            LOGGER.info("Calling %s" % action)
            if action in self._scheduled:
                try:
                    action()
                except Exception:
                    LOGGER.exception("Uncaught exception while executing scheduled action")

                finally:
                    self._io_loop.call_later(interval, action_function)

        self._io_loop.call_later(interval, action_function)
        self._scheduled.add(action)

        if now:
            self._io_loop.add_callback(action)

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
        self._node_name = self.set_node_name()
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
                LOGGER.warning("An exception occurred while handling a future: %s", str(e))

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

    def set_node_name(self):
        """
            This determines the name of the machine this endpoint is running on
        """
        node_name = Config.get("config", "node-name", None)
        if node_name is None:
            node_name = self._get_hostname()

        return node_name

    def _get_hostname(self):
        """
            Determine the hostname of this machine
        """
        return socket.gethostname()

    def get_node_name(self):
        return self._node_name

    node_name = property(get_node_name)


def _set_timeout(io_loop, future, timeout, log_message):
    def on_timeout():
        LOGGER.warning(log_message)
        future.set_exception(gen.TimeoutError())
    timeout_handle = io_loop.add_timeout(io_loop.time() + timeout, on_timeout)
    future.add_done_callback(lambda _: io_loop.remove_timeout(timeout_handle))


class Environment(object):
    """
        An environment that segments agents connected to the server
    """
    def __init__(self, io_loop, env_id):
        self._env_id = env_id
        self._agents = set()
        self._agent_node_map = {}
        self._node_queues = defaultdict(lambda: queues.Queue())
        self._io_loop = io_loop
        self._replies = {}
        self.check_expire()

    def check_expire(self):
        # TODO: add expire
        self._io_loop.call_later(1, self.check_expire)

    def get_id(self):
        return self._env_id

    def get_agents(self):
        return self._agents

    id = property(get_id)
    agents = property(get_agents)

    def add_agent(self, node, agent, interval):
        if agent in self._agent_node_map and self._agent_node_map[agent] != node:
            LOGGER.info("Agent %s moved from node %s to node %s", self._agent_node_map[agent], node)

        self._agent_node_map[agent] = node
        self._agents.add(agent)

    def put_call(self, agent, call_spec):
        future = tornado.concurrent.Future()
        if agent in self._agent_node_map:
            LOGGER.debug("Putting call %s %s for agent %s in queue", call_spec["method"], call_spec["url"], agent)
            nodename = self._agent_node_map[agent]
            q = self._node_queues[nodename]
            call_spec["reply_id"] = uuid.uuid4()
            call_spec["agent"] = agent
            q.put(call_spec)

            _set_timeout(self._io_loop, future, int(Config.get("config", "timeout", 5)),
                         "Call %s %s for agent %s timed out." % (call_spec["method"], call_spec["url"], agent))
            self._replies[call_spec["reply_id"]] = future
        else:
            LOGGER.warning("Call for agent %s ignore because it is not known to the server.", agent)
            future.set_exception(Exception())

        return future

    def has_agent(self, agent):
        return agent in self._agents

    @gen.coroutine
    def get_calls(self, nodename, timeout):
        """
            Get all calls queued for a node. If no work is available, wait until timeout. This method returns none if a call
            fails.
        """
        try:
            q = self._node_queues[nodename]
            call_list = []
            call = yield q.get(timeout=self._io_loop.time() + timeout)
            call_list.append(call)
            while q.qsize() > 0:
                call = yield q.get()
                call_list.append(call)

            return call_list

        except gen.TimeoutError:
            return None

    def set_reply(self, reply_id, data):
        if reply_id in self._replies:
            future = self._replies[reply_id]
            del self._replies[reply_id]
            if not future.done():
                future.set_result(data)


class ServerEndpoint(Endpoint, metaclass=EndpointMeta):
    """
        A service that receives method calls over one or more transports
    """
    __methods__ = {}

    def __init__(self, name, io_loop, transport=RESTTransport):
        super().__init__(io_loop, name)
        self._transport = transport
        self._transport_instance = None
        self._sched = Scheduler(self._io_loop)

        self._heartbeat_cb = None
        self._environments = {}

    def schedule(self, call, interval=60):
        self._sched.add_action(call, interval)

    def get_agents(self, env_id):
        assert isinstance(env_id, uuid.UUID)
        env = self.get_env(env_id)
        return env.agents

    def start(self):
        """
            Start this end-point using the central configuration
        """
        LOGGER.debug("Starting transport for endpoint %s", self.name)
        self._transport_instance = Transport.create(self._transport, self)

        if self._transport_instance is not None:
            self._transport_instance.start_endpoint()

    def stop(self):
        """
            Stop the end-point and all of its transports
        """
        if self._transport_instance is not None:
            self._transport_instance.stop_endpoint()
            LOGGER.debug("Stopped %s", self._transport_instance)

    def put_call(self, env_id, agent, call_spec):
        """
            Add a call for the given agent on its work queue. This method returns a future to get the response from the
            agent.
        """
        env = self.get_env(env_id)
        return env.put_call(agent, call_spec)

    def get_agent_client(self, env_id, agent):
        """
            Get a client to do requests on agent. Returns None if the agent is not known
        """
        env = self.get_env(env_id)
        if not env.has_agent(agent):
            return None
        client = ReturnClient("client", self, env_id, agent)
        return client

    def add_heartbeat_callback(self, callback):
        """
            Register a function that adds custom heartbeat handling to the server. The server does not wait for this method to
            return. It will be handed over to the ioloop.
        """
        self._heartbeat_cb = callback

    def get_env(self, env_id):
        if isinstance(env_id, str):
            env_id = uuid.UUID(env_id)

        if env_id not in self._environments:
            self._environments[env_id] = Environment(self._io_loop, env_id)

        return self._environments[env_id]

    @handle(methods.HeartBeatMethod.heartbeat)
    @gen.coroutine
    def heartbeat(self, tid, endpoint_names, nodename, interval):
        LOGGER.debug("Received heartbeat from %s for agents %s in %s (interval=%d)",
                     nodename, ",".join(endpoint_names), tid, interval)

        env = self.get_env(tid)
        for endpoint in endpoint_names:
            env.add_agent(nodename, endpoint, interval)

        if self._heartbeat_cb is not None:
            future = self._heartbeat_cb(tid, endpoint_names, nodename, interval)
            self.add_future(future)

        LOGGER.debug("Let node %s wait for method calls to become available. (long poll)", nodename)
        call_list = yield env.get_calls(nodename, interval)
        if call_list is not None:
            LOGGER.debug("Pushing %d method calls to node %s", len(call_list), nodename)
            return 200, {"method_calls": call_list}
        else:
            LOGGER.debug("Heartbeat wait expired for %s, returning. (long poll)", nodename)

        return 200

    @handle(methods.HeartBeatMethod.heartbeat_reply)
    @gen.coroutine
    def heartbeat_reply(self, tid, reply_id, data):
        env = self.get_env(tid)
        env.set_reply(reply_id, data)
        return 200


class AgentEndPoint(Endpoint, metaclass=EndpointMeta):
    """
        An endpoint for clients that make calls to a server and that receive calls back from the server using long-poll
    """
    def __init__(self, name, io_loop, heartbeat_interval=10, transport=RESTTransport):
        super().__init__(io_loop, name)
        self._transport = transport
        self._client = None
        self._heart_beat_interval = heartbeat_interval
        self._sched = Scheduler(self._io_loop)

        self._env_id = None

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
        self._client = Client(self.name, self._transport)
        # self._sched.add_action(self.perform_heartbeat, self._heart_beat_interval, True)
        self._io_loop.add_callback(self.perform_heartbeat)

    def stop(self):
        pass

    @gen.coroutine
    def perform_heartbeat(self):
        """
            Start a continuous heartbeat call
        """
        while True:
            result = yield self._client.heartbeat(tid=str(self._env_id), endpoint_names=self.end_point_names,
                                                  nodename=self.node_name, interval=self._heart_beat_interval)
            if result.code == 200:
                if result.result is not None:
                    if "method_calls" in result.result:
                        method_calls = result.result["method_calls"]
                        transport = self._transport(self)

                        for method_call in method_calls:
                            LOGGER.debug("Received call through heartbeat: %s %s", method_call["method"], method_call["url"])
                            kwargs, config = transport.match_call(method_call["url"], method_call["method"])
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
                                result_body, _, status = future.result()
                                if status == 500:
                                    LOGGER.error("An error occurred during heartbeat method call (%s %s): %s",
                                                 method_call["method"], method_call["url"], result_body["message"])
                                self._client.heartbeat_reply(self._env_id, method_call["reply_id"],
                                                             {"result": result_body, "code": status})

                            self._io_loop.add_future(call_result, submit_result)
            else:
                LOGGER.warning("Heartbeat failed with status %d and message: %s", result.code, result.result)

            yield gen.sleep(1)


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

    def get_method_name(self, properties):
        method = properties["method"]
        class_name = method.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
        module = inspect.getmodule(method)
        method_class = getattr(module, class_name)

        if not hasattr(method_class, "__method_name__"):
            raise Exception("%s should have a __method_name__ variable." % method_class)

        return method_class.__method_name__

    @gen.coroutine
    def _call(self, args, kwargs, protocol_properties):
        """
            Execute the rpc call
        """
        protocol_properties["method_name"] = self.get_method_name(protocol_properties)
        result = yield self._transport_instance.call(protocol_properties, args, kwargs)
        return result


class ReturnClient(Client, metaclass=ClientMeta):
    """
        A client that uses a return channel to connect to its destination. This client is used by the server to communicate
        back to clients over the heartbeat channel.
    """
    def __init__(self, name, server, tid, agent):
        super().__init__(name)
        self._server = server
        self._tid = tid
        self._agent = agent

    @gen.coroutine
    def _call(self, args, kwargs, protocol_properties):
        protocol_properties["method_name"] = self.get_method_name(protocol_properties)
        url, method, headers, body = self._transport_instance.build_call(protocol_properties, args, kwargs)

        call_spec = {"url": url, "method": method, "headers": headers, "body": body}
        return_value = yield self._server.put_call(self._tid, self._agent, call_spec)

        return Result(code=return_value["code"], result=return_value["result"])
