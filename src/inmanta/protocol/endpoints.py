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
import socket
import uuid

from urllib import parse
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable  # noqa: F401

from inmanta import config as inmanta_config
from inmanta import util
from . import common, rest

from tornado import ioloop, gen

LOGGER: logging.Logger = logging.getLogger(__name__)


class Endpoint(object):
    """
        An end-point in the rpc framework
    """

    def __init__(self, name):
        self._name = name
        self._node_name = inmanta_config.nodename.get()
        self._end_point_names = []

    def get_endpoint_metadata(self) -> Dict[str, Callable]:
        total_dict = {
            method_name: getattr(self, method_name) for method_name in dir(self) if callable(getattr(self, method_name))
        }

        methods: Dict[str, Tuple[str, Callable]] = {}
        for name, attr in total_dict.items():
            if name[0:2] != "__" and hasattr(attr, "__protocol_method__"):
                if attr.__protocol_method__ in methods:
                    raise Exception("Unable to register multiple handlers for the same method. %s" % attr.__protocol_method__)

                methods[attr.__protocol_method__] = (name, attr)

        return methods

    def add_future(self, future) -> None:
        """
            Add a future to the ioloop to be handled, but do not require the result.
        """

        def handle_result(f):
            try:
                f.result()
            except Exception as e:
                LOGGER.exception("An exception occurred while handling a future: %s", str(e))

        ioloop.IOLoop.current().add_future(future, handle_result)

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


class AgentEndPoint(Endpoint):
    """
        An endpoint for clients that make calls to a server and that receive calls back from the server using long-poll
    """

    def __init__(self, name, timeout=120, reconnect_delay=5):
        super().__init__(name)
        self._transport = rest.RESTClient
        self._client = None
        self._sched = util.Scheduler()

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
        ioloop.IOLoop.current().add_callback(self.perform_heartbeat)

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
            result = yield self._client.heartbeat(
                sid=str(self.sessionid), tid=str(self._env_id), endpoint_names=self.end_point_names, nodename=self.node_name
            )
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
                LOGGER.warning(
                    "Heartbeat failed with status %d and message: %s, going to sleep for %d s",
                    result.code,
                    result.result,
                    self.reconnect_delay,
                )
                connected = False
                yield gen.sleep(self.reconnect_delay)

    def dispatch_method(self, transport, method_call):
        LOGGER.debug(
            "Received call through heartbeat: %s %s %s", method_call["reply_id"], method_call["method"], method_call["url"]
        )
        kwargs, config = transport.match_call(method_call["url"], method_call["method"])

        if config is None:
            msg = "An error occurred during heartbeat method call (%s %s %s): %s" % (
                method_call["reply_id"],
                method_call["method"],
                method_call["url"],
                "No such method",
            )
            LOGGER.error(msg)
            self.add_future(self._client.heartbeat_reply(self.sessionid, method_call["reply_id"], {"result": msg, "code": 500}))

        body = {}
        if "body" in method_call and method_call["body"] is not None:
            body = method_call["body"]

        query_string = parse.urlparse(method_call["url"]).query
        for key, value in parse.parse_qs(query_string, keep_blank_values=True):
            if len(value) == 1:
                body[key] = value[0].decode("latin-1")
            else:
                body[key] = [v.decode("latin-1") for v in value]

        call_result = self._transport(self)._execute_call(kwargs, method_call["method"], config, body, method_call["headers"])

        def submit_result(future):
            if future is None:
                return

            result_body, _, status = future.result()
            if status == 500:
                msg = ""
                if result_body is not None and "message" in result_body:
                    msg = result_body["message"]
                LOGGER.error(
                    "An error occurred during heartbeat method call (%s %s %s): %s",
                    method_call["reply_id"],
                    method_call["method"],
                    method_call["url"],
                    msg,
                )
            self._client.heartbeat_reply(self.sessionid, method_call["reply_id"], {"result": result_body, "code": status})

        ioloop.IOLoop.current().add_future(call_result, submit_result)


class Client(Endpoint):
    """
        A client that communicates with end-point based on its configuration
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        LOGGER.debug("Start transport for client %s", self.name)
        self._transport_instance = rest.RESTClient(self)

    @gen.coroutine
    def _call(self, method_properties, args, kwargs) -> common.Result:
        """
            Execute a call and return the result
        """
        result = yield self._transport_instance.call(method_properties, args, kwargs)
        return result

    def __getattr__(self, name: str) -> Callable:
        """
            Return a function that will call self._call with the correct method properties associated
        """
        if name in common.MethodProperties._methods:
            method = common.MethodProperties._methods[name]

            def wrap(*args, **kwargs) -> Callable[[List[Any], Dict[str, Any]], common.Result]:
                method.function(*args, **kwargs)
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
                return ioloop.IOLoop.current().run_sync(method_call, self.timeout)
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
        self._transport_instance = rest.RESTClient(self, connection_timout=timeout)

    @gen.coroutine
    def _call(self, method_properties, args, kwargs) -> common.Result:
        """
            Execute the rpc call
        """
        if "sid" not in kwargs:
            kwargs["sid"] = self._sid

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
    def _call(self, method_properties: common.MethodProperties, args, kwargs) -> common.Result:
        url, headers, body = method_properties.build_call(args, kwargs)

        call_spec = {"url": url, "method": method_properties.operation, "headers": headers, "body": body}
        timeout = method_properties.timeout
        try:
            return_value = yield self.session.put_call(call_spec, timeout=timeout)
        except gen.TimeoutError:
            return common.Result(code=500, result={"message": "Call timed out"})

        return common.Result(code=return_value["code"], result=return_value["result"])
