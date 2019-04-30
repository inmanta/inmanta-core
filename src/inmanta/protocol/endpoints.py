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
from collections import defaultdict

from urllib import parse
from asyncio import Future, ensure_future
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable, Generator  # noqa: F401

from inmanta import config as inmanta_config
from inmanta import util
from inmanta.protocol.common import UrlMethod
from inmanta.types import NoneGen
from . import common
from .rest import client

from tornado import ioloop, gen

LOGGER: logging.Logger = logging.getLogger(__name__)


class CallTarget(object):
    """
        A baseclass for all classes that are target for protocol calls / methods
    """

    def _get_endpoint_metadata(self) -> Dict[str, Tuple[str, Callable]]:
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

    def get_op_mapping(self) -> Dict[str, Dict[str, UrlMethod]]:
        """
            Build a mapping between urls, ops and methods
        """
        url_map: Dict[str, Dict[str, UrlMethod]] = defaultdict(dict)

        # TODO: avoid colliding handlers
        for method, method_handlers in self._get_endpoint_metadata().items():
            properties = method.__method_properties__
            # self.headers.update(properties.get_call_headers())
            url = properties.get_listen_url()
            url_map[url][properties.operation] = UrlMethod(properties, self, method_handlers[1], method_handlers[0])

        return url_map


class Endpoint(object):
    """
        An end-point in the rpc framework
    """

    def __init__(self, name: str):
        self._name: str = name
        self._node_name: str = inmanta_config.nodename.get()
        self._end_point_names: List[str] = []
        self._targets: List[CallTarget] = []

    def add_call_target(self, target: CallTarget) -> None:
        self._targets.append(target)

    @property
    def call_targets(self) -> List[CallTarget]:
        return self._targets

    def add_future(self, future: Future) -> None:
        """
            Add a future to the ioloop to be handled, but do not require the result.
        """

        def handle_result(f: Future) -> None:
            try:
                f.result()
            except Exception as e:
                LOGGER.exception("An exception occurred while handling a future: %s", str(e))

        ioloop.IOLoop.current().add_future(ensure_future(future), handle_result)

    def get_end_point_names(self) -> List[str]:
        return self._end_point_names

    def add_end_point_name(self, name: str) -> None:
        """
            Add an additional name to this endpoint to which it reacts and sends out in heartbeats
        """
        LOGGER.debug("Adding '%s' as endpoint", name)
        self._end_point_names.append(name)

    def clear_end_points(self) -> None:
        """
            Clear all endpoints
        """
        self._end_point_names = []

    name = property(lambda self: self._name)
    end_point_names = property(get_end_point_names)

    def _get_hostname(self) -> str:
        """
            Determine the hostname of this machine
        """
        return socket.gethostname()

    def get_node_name(self) -> str:
        return self._node_name

    node_name = property(get_node_name)


class SessionEndpoint(Endpoint, CallTarget):
    """
        An endpoint for clients that make calls to a server and that receive calls back from the server using long-poll
    """

    def __init__(self, name: str, timeout: int = 120, reconnect_delay: int = 5):
        super().__init__(name)
        self._transport = client.RESTClient
        self._client: Optional[SessionClient] = None
        self._sched = util.Scheduler("session endpoint")

        self._env_id: Optional[uuid.UUID] = None

        self.sessionid: uuid.UUID = uuid.uuid1()
        self.running: bool = True
        self.server_timeout = timeout
        self.reconnect_delay = reconnect_delay

        self.add_call_target(self)

    def get_environment(self) -> Optional[uuid.UUID]:
        return self._env_id

    environment = property(get_environment)

    def set_environment(self, environment_id: uuid.UUID) -> None:
        """
            Set the environment of this agent
        """
        if isinstance(environment_id, str):
            self._env_id = uuid.UUID(environment_id)
        else:
            self._env_id = environment_id

    @gen.coroutine
    def start(self) -> NoneGen:
        """
            Connect to the server and use a heartbeat and long-poll for two-way communication
        """
        assert self._env_id is not None
        LOGGER.log(3, "Starting agent for %s", str(self.sessionid))
        self._client = SessionClient(self.name, self.sessionid, timeout=self.server_timeout)
        ioloop.IOLoop.current().add_callback(self.perform_heartbeat)

    @gen.coroutine
    def stop(self) -> NoneGen:
        self._sched.stop()
        self.running = False

    @gen.coroutine
    def on_reconnect(self) -> NoneGen:
        pass

    @gen.coroutine
    def on_disconnect(self) -> NoneGen:
        pass

    @gen.coroutine
    def perform_heartbeat(self) -> NoneGen:
        """
            Start a continuous heartbeat call
        """
        if self._client is None:
            raise Exception("AgentEndpoint not started")

        connected: bool = False
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
                        method_calls: List[common.Request] = [
                            common.Request.from_dict(req) for req in result.result["method_calls"]
                        ]
                        # FIXME: reuse transport?
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
                yield self.on_disconnect()
                yield gen.sleep(self.reconnect_delay)

    def dispatch_method(self, transport: client.RESTClient, method_call: common.Request) -> None:
        if self._client is None:
            raise Exception("AgentEndpoint not started")

        LOGGER.debug("Received call through heartbeat: %s %s %s", method_call.reply_id, method_call.method, method_call.url)
        kwargs, config = transport.match_call(method_call.url, method_call.method)

        if config is None:
            msg = "An error occurred during heartbeat method call (%s %s %s): %s" % (
                method_call.reply_id,
                method_call.method,
                method_call.url,
                "No such method",
            )
            LOGGER.error(msg)
            self.add_future(self._client.heartbeat_reply(self.sessionid, method_call.reply_id, {"result": msg, "code": 500}))

        body = method_call.body or {}
        query_string = parse.urlparse(method_call.url).query
        for key, value in parse.parse_qs(query_string, keep_blank_values=True):
            if len(value) == 1:
                body[key] = value[0].decode("latin-1")
            else:
                body[key] = [v.decode("latin-1") for v in value]

        # FIXME: why create a new transport instance on each call? keep-alive?
        call_result: common.Response = transport._execute_call(kwargs, method_call.method, config, body, method_call.headers)

        def submit_result(future: Future) -> None:
            if future is None:
                return

            response: common.Response = future.result()
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

            self._client.heartbeat_reply(
                self.sessionid, method_call.reply_id, {"result": response.body, "code": response.status_code}
            )

        ioloop.IOLoop.current().add_future(call_result, submit_result)


class Client(Endpoint):
    """
        A client that communicates with end-point based on its configuration
    """

    def __init__(self, name: str, timeout: int = 120) -> None:
        super().__init__(name)
        assert isinstance(timeout, int), "Timeout needs to be an integer value."
        LOGGER.debug("Start transport for client %s", self.name)
        self._transport_instance = client.RESTClient(self, connection_timout=timeout)

    @gen.coroutine
    def _call(self, method_properties: common.MethodProperties, args: List, kwargs: Dict) -> common.Result:
        """
            Execute a call and return the result
        """
        result = yield self._transport_instance.call(method_properties, args, kwargs)
        return result

    def __getattr__(self, name: str) -> Callable:
        """
            Return a function that will call self._call with the correct method properties associated
        """
        if name in common.MethodProperties.methods:
            method = common.MethodProperties.methods[name]

            def wrap(*args: List, **kwargs: Dict) -> common.Result:
                method.function(*args, **kwargs)
                return self._call(method_properties=method, args=args, kwargs=kwargs)

            return wrap

        raise AttributeError("Method with name %s is not defined for this client" % name)


class SyncClient(object):
    """
        A synchronous client that communicates with end-point based on its configuration
    """

    def __init__(self, name: str, timeout: int = 120) -> None:
        self.name = name
        self.timeout = timeout
        self._client = Client(self.name, self.timeout)

    def __getattr__(self, name: str) -> Callable:
        def async_call(*args: List, **kwargs: Dict) -> None:
            method = getattr(self._client, name)

            def method_call() -> None:
                return method(*args, **kwargs)

            try:
                return ioloop.IOLoop.current().run_sync(method_call, self.timeout)
            except TimeoutError:
                raise ConnectionRefusedError()

        return async_call


class SessionClient(Client):
    """
        A client that communicates with server endpoints over a session.
    """
    def __init__(self, name: str, sid: uuid.UUID, timeout: int = 120) -> None:
        super().__init__(name, timeout)
        self._sid = sid

    @gen.coroutine
    def _call(self, method_properties: common.MethodProperties, args: List, kwargs: Dict) -> common.Result:
        """
            Execute the rpc call
        """
        if "sid" not in kwargs:
            kwargs["sid"] = self._sid

        result = yield self._transport_instance.call(method_properties, args, kwargs)
        return result
