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

from http import client
import logging
import sched
import socket
import threading
import time
import inspect
import urllib
from collections import defaultdict

import tornado.ioloop
import tornado.web
import tornado.gen
from impera import methods
from impera.config import Config
import uuid
from datetime import datetime
import json


LOGGER = logging.getLogger(__name__)
_clients = {}
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


class Transport(threading.Thread):
    """
        This class implements a transport for the Impera protocol.

        :param end_point_name The name of the endpoint to which this transport belongs. This is used
            for logging and configuration purposes
    """
    __data__ = tuple()
    __transport_name__ = None
    __broadcast__ = False
    __network__ = True

    offline = False

    @classmethod
    def create(cls, TransportClass, endpoint=None):
        """
            Create an instance of the transport class or return None if the transport requires a network but we are operating
            in offline mode
        """
        if cls.offline and TransportClass.__network__:
            return None

        return TransportClass(endpoint)

    def __init__(self, endpoint=None):
        self.__end_point = endpoint
        super().__init__(name=self.id)
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
        super().start()

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

    if isinstance(o, datetime.datetime):
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

    def return_error_msg(self, status=500, msg=""):
        self.write(json_encode({"message": msg}))
        self.set_header("Content-Type", "application/json")
        self.set_status(status, msg)

    def _call(self, args, kwargs, operation):
        """
            An rpc like call
        """
        self.set_header("Access-Control-Allow-Origin", "*")
        if operation.upper() not in self._config:
            allowed = ", ".join(self._config.keys())
            self.set_header("Allow", allowed)
            self.return_error_msg(405, "%s is not supported for this url. Supported methods: %s" % (operation, allowed))
            return

        try:
            # create message that contains all arguments (id, query args and body)
            message = self._transport._decode(self.request.body)
            if message is None:
                message = {}

            for key, value in self.request.query_arguments.items():
                if len(value) == 1:
                    message[key] = value[0].decode("latin-1")
                else:
                    message[key] = [v.decode("latin-1") for v in value]

            if "id" in kwargs and (message is None or "id" not in message):
                message["id"] = kwargs["id"]

            # validate message against config
            config = self._config[operation][0]
            if "id" in config and config["id"] and "id" not in message:
                self.return_error_msg(500, "Invalid request. It should contain an id in the url.")
                return

            if "mt" in config and config["mt"]:
                if IMPERA_MT_HEADER not in self.request.headers:
                    self.return_error_msg(500, "This is multi-tenant method, it should contain a tenant id")
                    return

                else:
                    message["tid"] = self.request.headers[IMPERA_MT_HEADER]
                    if message["tid"] == "":
                        self.return_error_msg(500, "%s header set without value." % IMPERA_MT_HEADER)
                        return

                    self.add_header(IMPERA_MT_HEADER, message["tid"])

            # validate message against the arguments
            argspec = inspect.getfullargspec(self._config[operation][2])
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
                    if (defaults_start >= 0 and (i - defaults_start) < len(argspec.defaults) and
                            argspec.defaults[i - defaults_start] is None):
                        # a default value of none is provided
                        message[arg] = None
                    else:
                        self.return_error_msg(500, "Invalid request. Field '%s' is required." % arg)
                        return
                else:
                    all_fields.remove(arg)

                # validate the type
                if arg in argspec.annotations:
                    arg_type = argspec.annotations[arg]
                    if message[arg] is not None and not isinstance(message[arg], arg_type):
                        try:
                            message[arg] = arg_type(message[arg])
                        except (ValueError, TypeError):
                            self.return_error_msg(500, "Invalid type for argument %s. Expected %s but received %s" %
                                                  (arg, arg_type, message[arg].__class__))
                            return

            if len(all_fields) > 0 and argspec.varkw is None:
                self.return_error_msg(500, ("Request contains fields %s " % all_fields) +
                                      "that are not declared in method and no kwargs argument is provided.")
                return

            LOGGER.debug("Calling method %s on %s" % self._config[operation][1])
            method_call = getattr(self._config[operation][1][0], self._config[operation][1][1])

            result = method_call(**message)
            if result is None:
                raise Exception("Handlers for method calls should at least return a status code.")

            reply = None
            if isinstance(result, tuple):
                if len(result) == 2:
                    code, reply = result
                else:
                    raise Exception("Handlers for method call can only return a status code and a reply")

            else:
                code = result

            if reply is not None:
                if "reply" in self._config[operation][0] and self._config[operation][0]:
                    self.write(json_encode(reply))
                    self.set_header("Content-Type", "application/json")

                else:
                    LOGGER.warn("Method %s returned a result although it is has not reply!")

            self.set_status(code)

        except Exception as e:
            LOGGER.exception("An exception occured")
            self.return_error_msg(500, "An exception occured: " + str(e.args))

        self.finish()

    @tornado.gen.coroutine
    def head(self, *args, **kwargs):
        self._call(operation="HEAD", args=args, kwargs=kwargs)

    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        self._call(operation="GET", args=args, kwargs=kwargs)

    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        self._call(operation="POST", args=args, kwargs=kwargs)

    @tornado.gen.coroutine
    def delete(self, *args, **kwargs):
        self._call(operation="DELETE", args=args, kwargs=kwargs)

    @tornado.gen.coroutine
    def patch(self, *args, **kwargs):
        self._call(operation="PATCH", args=args, kwargs=kwargs)

    @tornado.gen.coroutine
    def put(self, *args, **kwargs):
        self._call(operation="PUT", args=args, kwargs=kwargs)

    @tornado.gen.coroutine
    def options(self, *args, **kwargs):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "HEAD, GET, POST, PUT, OPTIONS, DELETE, PATCH")
        self.set_header("Access-Control-Allow-Headers", "Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token, " +
                        IMPERA_MT_HEADER)

        self.set_status(200)
        self.finish()


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
                url = "/%s/(?P<id>.*)" % properties["method_name"]
            else:
                url = "/%s/%s" % (properties["method_name"], msg["id"])

        elif "index" in properties and properties["index"]:
            url = "/%s" % properties["method_name"]
        else:
            url = "/%s" % properties["method_name"]

        return url

    def start_endpoint(self):
        """
            Start the transport
        """
        url_map = {}
        for method, method_handlers in self.endpoint.__methods__.items():
            properties = method.__protocol_properties__
            call = (self.endpoint, method_handlers[0])

            url = self._create_base_url(properties)

            if url not in url_map:
                url_map[url] = []

            url_map[url].append((properties, call, method.__wrapped__))

            # ##
#             argspec = inspect.getfullargspec(method_handlers[1])
#             args = argspec.args
#             if "id" in args:
#                 args.remove("id")
#             if "self" in args:
#                 args.remove("self")
#             print(properties["operation"], url, args, method_handlers[1])
            # ##

        handlers = []
        for url, configs in url_map.items():
            handler_config = {}
            for cfg in configs:
                handler_config[cfg[0]["operation"]] = cfg

            handlers.append((url, RESTHandler, {"transport": self, "config": handler_config}))
            LOGGER.debug("Registering handler(s) for url %s and methods %s" % (url, ", ".join(handler_config.keys())))

        port = 8888
        if self.id in Config.get() and "port" in Config.get()[self.id]:
            port = Config.get()[self.id]["port"]

        application = tornado.web.Application(handlers)
        application.listen(port)
        super().start()

    def run(self):
        LOGGER.debug("Starting tornado IOLoop")
        tornado.ioloop.IOLoop.instance().start()

    def stop_endpoint(self):
        super().stop()
        tornado.ioloop.IOLoop.instance().stop()

    def start_client(self):
        pass

    def stop_client(self):
        pass

    def _get_client_config(self):
        """
            Load the configuration for the client
        """
        LOGGER.debug("Getting config in section %s", self.id)
        port = 8888
        if self.id in Config.get() and "port" in Config.get()[self.id]:
            port = Config.get()[self.id]["port"]

        host = "localhost"
        if self.id in Config.get() and "host" in Config.get()[self.id]:
            host = Config.get()[self.id]["host"]

        LOGGER.debug("Using %s:%s", host, port)
        return (host, port)

    def call(self, properties, args, kwargs={}):
        host, port = self._get_client_config()
        conn = client.HTTPConnection(host, port)

        operation = properties["operation"]

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

            headers[IMPERA_MT_HEADER] = msg["tid"]
            del msg["tid"]

        if not (operation == "POST" or operation == "PUT" or operation == "PATCH"):
            qs_map = msg.copy()
            if "id" in qs_map:
                del qs_map["id"]

            # encode arguments in url
            if len(qs_map) > 0:
                url += "?" + urllib.parse.urlencode(qs_map)

            body = ""
        else:
            body = json_encode(msg)

        LOGGER.debug("Calling server with url %s", url)

        try:
            conn.request(operation, url, body, headers)
            res = conn.getresponse()
        except Exception as e:
            return Result(code=500, result=str(e))

        return Result(code=res.status, result=self._decode(res.read()))


class DirectTransport(Transport):
    """
        Communicate directly within the same python process
    """
    __data__ = ("message", "blob")
    __transport_name__ = "direct"
    __network__ = False
    __broadcast__ = True

    _transports = defaultdict(list)
    connections = []

    @classmethod
    def register_transport(cls, transport):
        cls._transports[transport.endpoint.name].append(transport)

    def __init__(self, endpoint=None):
        super().__init__(endpoint)
        self.__class__.register_transport(self)
        self.set_connected()

    def call(self, method, destination=None, **kwargs):
        # select the correct transport
        targets = []
        for conn in self.connections:
            if conn[0] == self.endpoint.name:
                if conn[1] in self._transports:
                    targets.extend(self._transports[conn[1]])

        if targets is None or len(targets) == 0:
            raise Exception("Unable to find a direct transport to use.")

        # ##
        results = []
        for target in targets:
            if hasattr(target.endpoint, "__methods__"):
                method_call = None
                for method_name, method_class in target.endpoint.__methods__.items():
                    if method_class == method:
                        method_call = getattr(target.endpoint, method_name)
                        break

                operation = None
                if "operation" in kwargs:
                    operation = kwargs["operation"]

                if operation == "POST":
                    operation = None

                if method_call is None:
                    LOGGER.warning("Cannot find method call for operation.")
                    continue

                result = method_call(operation=operation, body=kwargs)

                if result is None:
                    LOGGER.error("Handlers for method calls should at least return a status code.")
                    continue

                reply = None
                if isinstance(result, tuple):
                    if len(result) == 2:
                        code, reply = result
                    else:
                        LOGGER.error("Handlers for method call can only return a status code and a reply")
                        continue

                else:
                    code = result

                if method.__reply__:
                    if reply is None:
                        body = {}
                    else:
                        body = reply

                    results.append((code, body))
                elif reply is not None:
                    LOGGER.warn("Method %s returned a result although it is has not reply!" % self._method_type)

        end_result = None
        if len(results) > 1:
            end_result = Result(multiple=True)
            for res in results:
                end_result.add_result(res)

        elif len(results) == 1:
            end_result = Result(code=results[0][0], result=results[0][1])

        return end_result


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

        methods = {}
        for name, attr in dct.items():
            if name[0:2] != "__" and hasattr(attr, "__protocol_method__"):
                if attr.__protocol_method__ in methods:
                    raise Exception("Unable to register multiple handlers for the same method.")

                methods[attr.__protocol_method__] = (name, attr)

        dct["__methods__"] = methods

        return type.__new__(cls, class_name, bases, dct)


class Scheduler(threading.Thread):
    """
        An event scheduler class
    """
    def __init__(self, daemon=True):
        super().__init__(name="Scheduler", daemon=daemon)
        self._sched = sched.scheduler()
        self._scheduled = set()
        self._running = True

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
                    self._sched.enter(interval, 1, action_function)

        self._sched.enter(interval, 1, action_function)
        self._scheduled.add(action)

        if now:
            action()

    def remove(self, action):
        """
            Remove a scheduled action
        """
        if action in self._scheduled:
            self._scheduled.remove(action)

    def run(self):
        while self._running:
            self._sched.run(blocking=True)
            time.sleep(0.1)

    def stop(self):
        self._running = False


class Endpoint(object):
    """
        An end-point in the rpc framework
    """
    def __init__(self, name, role):
        self._name = name
        self._role = role
        self._node_name = self.set_node_name()
        self._end_point_names = []

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
    role = property(lambda self: self._role)
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


class ServerEndpoint(Endpoint, metaclass=EndpointMeta):
    """
        A service that receives method calls over one or more transports
    """
    __methods__ = {}

    def __init__(self, name, role, transport=RESTTransport):
        super().__init__(name, role)
        self._transport = transport
        self._transport_instance = None
        self._sched = Scheduler()

        self.running = True

    def schedule(self, call, interval=60):
        self._sched.add_action(call, interval)

    def start(self):
        """
            Start this end-point using the central configuration
        """
        LOGGER.debug("Starting transport for endpoint %s", self.name)
        self._transport_instance = Transport.create(self._transport, self)

        if self._transport_instance is not None:
            self._transport_instance.start_endpoint()

        LOGGER.debug("Starting scheduler")
        self._sched.start()

        while self.running:
            try:
                time.sleep(0.1)
            except KeyboardInterrupt:
                self.stop()

    def stop(self):
        """
            Stop the end-point and all of its transports
        """
        self.running = False
        if self._transport_instance is not None:
            self._transport_instance.stop_endpoint()
            LOGGER.debug("Stopped %s", self._transport_instance)

        self._sched.stop()


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
    def __init__(self, name, role, transport=RESTTransport):
        Endpoint.__init__(self, name, role)
        self._transport = transport
        self._transport_instance = None

        LOGGER.debug("Start transports for client %s", self.name)
        tr = Transport.create(self._transport, self)
        self._transport_instance = tr

    def is_transport_connected(self):
        """
            Check if all transports are connected
        """
        if self._transport_instance is None:
            return False

        return self._transport_instance.is_connected()

    def _call(self, args, kwargs, protocol_properties):
        """
            Execute the rpc call
        """
        method = protocol_properties["method"]
        class_name = method.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
        module = inspect.getmodule(method)
        method_class = getattr(module, class_name)

        if not hasattr(method_class, "__method_name__"):
            raise Exception("%s should have a __method_name__ variable." % method_class)

        protocol_properties["method_name"] = method_class.__method_name__

        return self._transport_instance.call(protocol_properties, args, kwargs)
