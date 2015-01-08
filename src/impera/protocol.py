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

    Contect: bart@impera.io

    This module defines the Impera protocol between components. The protocol is marshaling and
    transport independent. Example support can be json over http and amqp
"""

from http import client
import logging
import sched
import socket
import threading
import time
import uuid

import amqp
import tornado.ioloop
from tornado.web import HTTPError
import tornado.web
from impera import methods
from impera.config import Config


LOGGER = logging.getLogger(__name__)


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
    __type__ = None
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
            body = tornado.escape.json_decode(body)
        else:
            body = None

        return body

    def set_connected(self):
        """
            Mark this transport as connected
        """
        self._connected = True

    def is_connected(self):
        """
            Is this transport connected
        """
        return self._connected


class AMQPTransport(Transport):
    """
        An amqp based transport.
    """
    __type__ = "message"
    __data__ = ("message",)
    __transport_name__ = "amqp"
    __broadcast__ = True

    def __init__(self, endpoint):
        super().__init__(endpoint)

        self._conn = None
        self._channel = None
        self._run = True
        self._exchange_name = None
        self._queue_name = None

        # TODO: prune these replies!!!
        self._replies = {}

    def stop(self):
        super().stop()
        self._run = False
        if self._conn is not None and self._channel is not None:
            self._channel.close()
            LOGGER.debug("Closed channel")
            self._conn.close()
            LOGGER.debug("Closed connection")

    def _subscribe(self, routing_key):
        self._channel.queue_bind(exchange=self._exchange_name, queue=self._queue_name,
                                 routing_key=routing_key)
        LOGGER.debug("Subscribing to routing key '%s' on queue %s at exchange %s" %
                     (routing_key, self._queue_name, self._exchange_name))

    def _connect(self):
        """
            Connect to AMQP and subscribe
        """
        LOGGER.info("Connecting to AMQP server")

        if self.id not in Config.get():
            LOGGER.error("Unable to get AMQP configuration for %s" % self.id)
            return

        cfg = Config.get()[self.id]

        try:
            self._conn = amqp.Connection(host=cfg["host"], userid=cfg["user"], password=cfg["password"],
                                         virtual_host=cfg["virtualhost"], connect_timeout=5)

            self._exchange_name = cfg["exchange"]

            self._channel = self._conn.channel()
            self._channel.exchange_declare(exchange=self._exchange_name, type="topic")

            # create a queue for us
            result = self._channel.queue_declare(exclusive=True, auto_delete=True)
            queue_name = result[0]
            self._queue_name = queue_name

            # subscribe messages to the queue
            self._subscribe("all")
            self._subscribe("host.%s" % self.endpoint.role)
            for h in self.endpoint.end_point_names:
                self._subscribe("host.%s.%s" % (self.endpoint.role, h))

            # start munching from the queue
            self._channel.basic_consume(queue=queue_name, callback=self.on_message, no_ack=True)
            LOGGER.info("AMQP transport connected")

            self.set_connected()

        except OSError:
            # this means the connection failed
            LOGGER.warning("AMQP connection failed, retrying in 10s")
            time.sleep(10)

    def on_message(self, msg):
        """
            Called when an amqp message is received

            :param msg The message from the amqp library
        """
        if "content_type" not in msg.properties or msg.properties["content_type"] != "application/json":
            LOGGER.error("Only application/json content is supported by the AMQP transport")
            return

        message = tornado.escape.json_decode(msg.body)

        if "method" not in message or "operation" not in message:
            LOGGER.error("No method or operation in message")
            return

        # this is a reply to an outstanding request
        if "correlation_id" in msg.properties and "reply_to" not in msg.properties:
            corr_id = msg.properties["correlation_id"]
            if corr_id not in self._replies:
                LOGGER.warn("Received a reply to a message we are no longer waiting for")
            else:
                self._replies[corr_id].add_result(message)
                self._replies[corr_id].code = message["code"]

        if hasattr(self.endpoint, "__methods__"):
            if message["method"] in self.endpoint.__methods__:
                method_call = getattr(self.endpoint, message["method"])
                operation = message["operation"]
                if operation == "POST":
                    operation = None

                result = method_call(operation=operation, body=message)
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

                method = method_call.__protocol_method__
                if method.__reply__:
                    if "reply_to" not in msg.properties or "correlation_id" not in msg.properties:
                        LOGGER.warn("Unable to send reply because of missing reply_to or correlation_id")
                        return

                    if reply is None:
                        body = {}
                    else:
                        body = reply

                    body["method"] = message["method"]
                    body["operation"] = "POST"
                    body["source"] = self.endpoint.end_point_names
                    body["code"] = code

                    reply_msg = amqp.Message(tornado.escape.json_encode(body))
                    reply_msg.properties["content_type"] = "application/json"
                    reply_msg.properties["correlation_id"] = msg.properties["correlation_id"]
                    LOGGER.debug("Replying to message with correlation_id %s on queue %s" %
                                 (msg.properties["correlation_id"], msg.properties["reply_to"]))

                    self._channel.basic_publish(reply_msg, exchange="", routing_key=msg.properties["reply_to"])

                elif reply is not None:
                    LOGGER.warn("Method %s returned a result although it is has not reply!" % self._method_type)

    def run(self):
        """
            This method does the actual workmessage
        """
        while self._run:
            try:
                self._do_connect()
            except Exception:
                LOGGER.exception("Something strange happened")
                pass

            time.sleep(10)

    def _do_connect(self):
        # try to connect
        while self._conn is None:
            self._connect()

        while self._channel.callbacks and self._run:
            try:
                self._channel.wait()

            except Exception:
                if self._conn is None or not self._conn.connected:
                    LOGGER.warning("Connection to server lost, reconnecting")
                    conn = self._conn
                    self._conn = None
                    conn.close()
                else:
                    LOGGER.exception("Received exception in MQ handler")

    def call(self, method, destination=None, **kwargs):
        if not self.is_connected():
            LOGGER.error("The transport is not yet connected")
            return

        key = None
        if destination == "*":
            key = "all"

        elif destination.startswith("host."):
            key = destination

        else:
            raise Exception("Unable to determine routing key based on destination")

        body = kwargs
        body["method"] = method.__method_name__
        body["operation"] = "POST"
        body["source"] = self.endpoint.end_point_names

        msg = amqp.Message(tornado.escape.json_encode(body))
        msg.properties["content_type"] = "application/json"

        result = None
        if method.__reply__:
            corr_id = str(uuid.uuid4())
            msg.properties["reply_to"] = self._queue_name
            msg.properties["correlation_id"] = corr_id
            result = Result(multiple=True)
            self._replies[corr_id] = result

        self._channel.basic_publish(msg, exchange=self._exchange_name, routing_key=key)
        return result


class RESTHandler(tornado.web.RequestHandler):
    """
        A generic class use by the transport
    """
    def initialize(self, transport, method_type, method_name):
        self._transport = transport
        self._method_name = method_name
        self._method_type = method_type

    def _call(self, args, kwargs, operation=None):
        """
            An rpc like call
        """
        self.set_header("Access-Control-Allow-Origin", "*")

        # can we support this operation
        if operation is not None and operation != "POST":
            if not self._method_type.__resource__:
                raise HTTPError(501, log_message="%s not supported for non resource methods" % operation)

        try:
            endpoint = self._transport.endpoint
            if not hasattr(endpoint, self._method_name):
                raise HTTPError(404, log_message="%s method does not exist on endpoint" % self._method_name)

            body = self._transport._decode(self.request.body)

            if "id" in kwargs and (body is None or "id" not in body):
                if body is None:
                    body = {}
                body["id"] = kwargs["id"]

            method_call = getattr(endpoint, self._method_name)
            result = method_call(operation=operation, body=body)
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
                if self._method_type.__reply__:
                    self.write(tornado.escape.json_encode(reply))
                    self.set_header("Content-Type", "application/json")
                else:
                    LOGGER.warn("Method %s returned a result although it is has not reply!" % self._method_type)

            self.set_status(code)
        except Exception:
            LOGGER.exception("An exception occured")
            self.set_status(500)

    def head(self, *args, **kwargs):
        self._call(operation="HEAD", args=args, kwargs=kwargs)

    def get(self, *args, **kwargs):
        self._call(operation="GET", args=args, kwargs=kwargs)

    def post(self, *args, **kwargs):
        self._call(args=args, kwargs=kwargs)

    def delete(self, *args, **kwargs):
        self._transport.message(operation="DELETE", args=args, kwargs=kwargs)

    def put(self, *args, **kwargs):
        self._call(operation="PUT", args=args, kwargs=kwargs)

    def options(self, *args, **kwargs):
        self._call(operation="OPTIONS", args=args, kwargs=kwargs)


class RESTTransport(Transport):
    """"
        A REST (json body over http) transport. Only methods that operate on resource can use all
        HTTP verbs. For other methods the POST verb is used.
    """
    __type__ = "rpc"
    __data__ = ("message", "blob")
    __transport_name__ = "rest"

    def __init__(self, endpoint):
        super().__init__(endpoint)
        self.set_connected()

    def start_endpoint(self):
        """
            Start the transport
        """
        handlers = []

        for name, method in self.endpoint.__methods__.items():
            if method.__resource__:
                handlers.append((
                    "/%s/(?P<id>.*)" % method.__method_name__, RESTHandler,
                    {"transport": self, "method_type": method, "method_name": name}
                ))

                if method.__index__:
                    handlers.append(("/%s" % method.__method_name__, RESTHandler,
                                     {"transport": self, "method_type": method, "method_name": name}))
            else:
                handlers.append(("/%s" % method.__method_name__, RESTHandler,
                                 {"transport": self, "method_type": method, "method_name": name}))

        port = 8888
        if self.id in Config.get() and "port" in Config.get()[self.id]:
            port = Config.get()[self.id]["port"]

        application = tornado.web.Application(handlers)
        application.listen(port)
        super().start()

    def run(self):
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
        port = 8888
        if self.id in Config.get() and "port" in Config.get()[self.id]:
            port = Config.get()[self.id]["port"]

        host = "localhost"
        if self.id in Config.get() and "host" in Config.get()[self.id]:
            host = Config.get()[self.id]["host"]

        return (host, port)

    def call(self, method, destination=None, **kwargs):
        if destination is not None:
            raise Exception("The REST transport can only communication with a single end-point")

        host, port = self._get_client_config()
        conn = client.HTTPConnection(host, port)

        if "operation" in kwargs:
            operation = kwargs["operation"]
        else:
            operation = "POST"

        if "id" in kwargs:
            url = "/%s/%s" % (method.__method_name__, kwargs["id"])
        else:
            url = "/%s" % method.__method_name__

        body = tornado.escape.json_encode(kwargs)

        conn.request(operation, url, body)
        res = conn.getresponse()

        return Result(code=res.status, result=self._decode(res.read()))


class DirectTransport(Transport):
    """
        Communicate directly within the same python process
    """
    __type__ = "rpc"
    __data__ = ("message", "blob")
    __transport_name__ = "direct"
    __network__ = False
    __broadcast__ = True

    _transports = {}
    connections = []

    @classmethod
    def register_transport(cls, transport):
        cls._transports[transport.endpoint.name] = transport

    def __init__(self, endpoint=None):
        super().__init__(endpoint)
        self.__class__.register_transport(self)
        self.set_connected()

    def call(self, method, destination=None, **kwargs):
        # select the correct transport
        target = None
        for conn in self.connections:
            if conn[0] == self.endpoint.name:
                if conn[1] in self._transports:
                    target = self._transports[conn[1]]

        if target is None:
            raise Exception("Unable to find a direct transport to use.")

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
                return

            result = method_call(operation=operation, body=kwargs)

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

            if method.__reply__:
                if reply is None:
                    body = {}
                else:
                    body = reply

                return Result(code=code, result=body)
            elif reply is not None:
                LOGGER.warn("Method %s returned a result although it is has not reply!" % self._method_type)


class handle(object):
    """
        Decorator for subclasses of an endpoint to handle protocol methods
    """
    def __init__(self, method):
        self.method = method

    def __call__(self, function):
        """
            The wrapping
        """
        function.__protocol_method__ = self.method
        return function


class EndpointMeta(type):
    """
        Meta class to create endpoints
    """
    def __new__(cls, class_name, bases, dct):
        if "__methods__" not in dct:
            dct["__methods__"] = {}

        for name, attr in dct.items():
            if name[0:2] != "__" and hasattr(attr, "__protocol_method__"):
                dct["__methods__"][name] = attr.__protocol_method__

        return type.__new__(cls, class_name, bases, dct)


class Scheduler(threading.Thread):
    """
        An event scheduler class
    """
    def __init__(self):
        super().__init__(name="Scheduler", daemon=True)
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
        LOGGER.debug("Scheduling action every %d seconds", interval)

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

    def __init__(self, name, role):
        super().__init__(name, role)
        self._transports = []
        self._sched = Scheduler()

    def schedule(self, call, interval=60):
        self._sched.add_action(call, interval)

    def start(self):
        """
            Start this end-point using the central configuration
        """
        LOGGER.debug("Starting transports for endpoint %s", self.name)
        for transport in self.__class__.__transports__:
            tr = Transport.create(transport, self)
            if tr is not None:
                tr.start_endpoint()
                self._transports.append(tr)

        LOGGER.debug("Starting scheduler")
        self._sched.start()

    def stop(self):
        """
            Stop the end-point and all of its transports
        """
        for transport in self._transports:
            transport.stop_endpoint()
            LOGGER.debug("Stopped %s", transport)

        self._sched.stop()


class ServerClientEndpoint(ServerEndpoint):
    """
        A server end point that also connects to an AMQP transport as a client and sends out
        regular heartbeats
    """
    def __init__(self, name, role):
        super().__init__(name, role)
        self._client = Client("%s_client" % name, role="client", transports=[AMQPTransport, RESTTransport, DirectTransport])
        self._heartbeat_interval = int(Config.get("config", "heartbeat-interval", 60))

        self.running = True

    def send_heartbeat(self):
        """
            Send a heartbeat message
        """
        self._client.call(methods.HeartBeatMethod, destination="*", endpoint_names=self.end_point_names,
                          nodename=self.node_name, role=self.role, interval=self._heartbeat_interval)

    def start(self, wait_func=None):
        """
            Start the client and schedule a heartbeat
        """
        super().start()

        # start an amqp client
        self._client.start()

        # start the heartbeat
        self.schedule(self.send_heartbeat, self._heartbeat_interval)

        while self.running:
            try:
                if wait_func is not None:
                    wait_func()
                else:
                    time.sleep(1)
            except KeyboardInterrupt:
                super().stop()
                break

    def stop(self):
        """
            Stop this instance
        """
        super().stop()
        self.running = False


class Client(Endpoint):
    """
        A client that communicates with end-point based on its configuration
    """
    def __init__(self, name, role, transports):
        super().__init__(name, role)
        self._transport_list = transports
        self._transports = []

    def start(self):
        """
            Start the transports of this client
        """
        LOGGER.debug("Start transports for client %s", self.name)
        for transport in self._transport_list:
            tr = Transport.create(transport, self)
            if tr is not None:
                tr.start_client()
                self._transports.append(tr)

    def stop(self):
        """
            Stop the transports of this client
        """
        LOGGER.debug("Stop transports of for client %s", self.name)
        for transport in self._transports:
            transport.stop()

    def select_transport(self, multiple_destinations=False, blob=False):
        """
            Select a transport to use based on the given criteria
        """
        for transport in self._transports:
            if ((transport.__class__.__broadcast__ == multiple_destinations or not multiple_destinations) and
                    (not blob or "blob" in transport.__class__.__data__)):

                return transport

        return None

    def all_transports_connected(self):
        """
            Check if all transports are connected
        """
        for tr in self._transports:
            if not tr.is_connected():
                return False

        return True

    def call(self, method, destination=None, async=False, **kwargs):
        """
            Execute a method call
        """
        blob = method.__data_type__ == "blob"

        transport = self.select_transport(destination is not None, blob)

        if transport is None:
            LOGGER.debug("No transport available")
            return

        result = transport.call(method, destination, **kwargs)

        if result is None:
            return
        elif result.available():
            return result
        elif async:
            return result
        else:
            # wait for it to become available
            while not result.available():
                time.sleep(0.01)

            return result
