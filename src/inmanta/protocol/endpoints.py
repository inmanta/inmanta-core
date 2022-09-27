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
import inspect
import logging
import socket
import uuid
from asyncio import CancelledError, run_coroutine_threadsafe, sleep
from collections import defaultdict
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, Generator, List, Optional, Set, Tuple, Union  # noqa: F401
from urllib import parse

from tornado import ioloop
from tornado.platform.asyncio import BaseAsyncIOLoop

from inmanta import config as inmanta_config
from inmanta import util
from inmanta.protocol.common import UrlMethod
from inmanta.util import TaskHandler

from . import common
from .rest import client

LOGGER: logging.Logger = logging.getLogger(__name__)


class CallTarget(object):
    """
    A baseclass for all classes that are target for protocol calls / methods
    """

    def _get_endpoint_metadata(self) -> Dict[str, List[Tuple[str, Callable]]]:
        total_dict = {
            method_name: method
            for method_name, method in inspect.getmembers(self)
            if callable(method) and method_name[0] != "_"
        }

        methods: Dict[str, List[Tuple[str, Callable]]] = defaultdict(list)
        for name, attr in total_dict.items():
            if hasattr(attr, "__protocol_method__"):
                methods[attr.__protocol_method__.__name__].append((name, attr))

        return methods

    def get_op_mapping(self) -> Dict[str, Dict[str, UrlMethod]]:
        """
        Build a mapping between urls, ops and methods
        """
        url_map: Dict[str, Dict[str, UrlMethod]] = defaultdict(dict)

        # Loop over all methods in this class that have a handler annotation. The handler annotation refers to a method
        # definition. This method definition defines how the handler is invoked.
        for method, handler_list in self._get_endpoint_metadata().items():
            for method_handlers in handler_list:
                # Go over all method annotation on the method associated with the handler
                for properties in common.MethodProperties.methods[method]:
                    url = properties.get_listen_url()

                    # Associate the method with the handler if:
                    # - the handler does not specific a method version
                    # - the handler specifies a method version and the method version matches the method properties
                    if method_handlers[1].__api_version__ is None or (
                        method_handlers[1].__api_version__ is not None
                        and properties.api_version == method_handlers[1].__api_version__
                    ):
                        # there can only be one
                        if url in url_map and properties.operation in url_map[url]:
                            raise Exception(f"A handler is already registered for {properties.operation} {url}. ")

                        url_map[url][properties.operation] = UrlMethod(properties, self, method_handlers[1], method_handlers[0])
        return url_map


class Endpoint(TaskHandler):
    """
    An end-point in the rpc framework
    """

    def __init__(self, name: str):
        super(Endpoint, self).__init__()
        self._name: str = name
        self._node_name: str = inmanta_config.nodename.get()
        self._end_point_names: Set[str] = set()
        self._targets: List[CallTarget] = []

    def add_call_target(self, target: CallTarget) -> None:
        self._targets.append(target)

    @property
    def call_targets(self) -> List[CallTarget]:
        return self._targets

    def get_end_point_names(self) -> Set[str]:
        return self._end_point_names

    async def add_end_point_name(self, name: str) -> None:
        """
        Add an additional name to this endpoint to which it reacts and sends out in heartbeats
        """
        LOGGER.debug("Adding '%s' as endpoint", name)
        self._end_point_names.add(name)

    async def remove_end_point_name(self, name: str) -> None:
        LOGGER.debug("Removing '%s' as endpoint", name)
        self._end_point_names.discard(name)

    def clear_end_points(self) -> None:
        """
        Clear all endpoints
        """
        self._end_point_names = set()

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

    async def stop(self) -> None:
        """Stop this endpoint"""
        await super(Endpoint, self).stop()


class SessionEndpoint(Endpoint, CallTarget):
    """
    An endpoint for clients that make calls to a server and that receive calls back from the server using long-poll
    """

    _client: "SessionClient"

    def __init__(self, name: str, timeout: int = 120, reconnect_delay: int = 5):
        super().__init__(name)
        self._transport = client.RESTClient
        self._sched = util.Scheduler("session endpoint")

        self._env_id: Optional[uuid.UUID] = None

        self.sessionid: uuid.UUID = uuid.uuid1()
        self.running: bool = True
        self.server_timeout = timeout
        self.reconnect_delay = reconnect_delay
        self.add_call_target(self)

    def get_environment(self) -> Optional[uuid.UUID]:
        return self._env_id

    @property
    def environment(self) -> Optional[uuid.UUID]:
        return self._env_id

    def set_environment(self, environment_id: uuid.UUID) -> None:
        """
        Set the environment of this agent
        """
        if isinstance(environment_id, str):
            self._env_id = uuid.UUID(environment_id)
        else:
            self._env_id = environment_id

    async def start_connected(self) -> None:
        """
        This method is called after starting the client transport, but before sending the first heartbeat.
        """
        pass

    async def start(self) -> None:
        """
        Connect to the server and use a heartbeat and long-poll for two-way communication
        """
        assert self._env_id is not None
        LOGGER.log(3, "Starting agent for %s", str(self.sessionid))
        self._client = SessionClient(self.name, self.sessionid, timeout=self.server_timeout)
        await self.start_connected()
        self.add_background_task(self.perform_heartbeat())

    async def stop(self) -> None:
        await self._sched.stop()
        await super(SessionEndpoint, self).stop()

    async def on_reconnect(self) -> None:
        """
        Called when a connection becomes active. i.e. when a first heartbeat is received after startup or
        a first hearbeat after an :py:`on_disconnect`
        """
        pass

    async def on_disconnect(self) -> None:
        """
        Called when the connection is lost unexpectedly (not on shutdown)
        """
        pass

    async def perform_heartbeat(self) -> None:
        """
        Start a continuous heartbeat call
        """
        if self._client is None:
            raise Exception("AgentEndpoint not started")

        connected: bool = False
        try:
            while True:
                LOGGER.log(3, "sending heartbeat for %s", str(self.sessionid))
                result = await self._client.heartbeat(
                    sid=str(self.sessionid),
                    tid=str(self._env_id),
                    endpoint_names=list(self.end_point_names),
                    nodename=self.node_name,
                    no_hang=not connected,
                )
                LOGGER.log(3, "returned heartbeat for %s", str(self.sessionid))
                if result.code == 200:
                    if not connected:
                        connected = True
                        self.add_background_task(self.on_reconnect())
                    if result.result is not None:
                        if "method_calls" in result.result:
                            method_calls: List[common.Request] = [
                                common.Request.from_dict(req) for req in result.result["method_calls"]
                            ]
                            # FIXME: reuse transport?
                            transport = self._transport(self)

                            for method_call in method_calls:
                                self.add_background_task(self.dispatch_method(transport, method_call))
                else:
                    LOGGER.warning(
                        "Heartbeat failed with status %d and message: %s, going to sleep for %d s",
                        result.code,
                        result.result,
                        self.reconnect_delay,
                    )
                    connected = False
                    await self.on_disconnect()
                    await sleep(self.reconnect_delay)
        except CancelledError:
            pass

    async def dispatch_method(self, transport: client.RESTClient, method_call: common.Request) -> None:
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
            self.add_background_task(
                self._client.heartbeat_reply(self.sessionid, method_call.reply_id, {"result": msg, "code": 500})
            )

        body = method_call.body or {}
        query_string = parse.urlparse(method_call.url).query
        for key, value in parse.parse_qs(query_string, keep_blank_values=True):
            if len(value) == 1:
                body[key] = value[0].decode("latin-1")
            else:
                body[key] = [v.decode("latin-1") for v in value]

        # FIXME: why create a new transport instance on each call? keep-alive?
        response: common.Response = await transport._execute_call(kwargs, method_call.method, config, body, method_call.headers)

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

        await self._client.heartbeat_reply(
            self.sessionid, method_call.reply_id, {"result": response.body, "code": response.status_code}
        )


class VersionMatch(str, Enum):
    lowest = "lowest"
    """ Select the lowest available version of the method
    """
    highest = "highest"
    """ Select the highest available version of the method
    """
    exact = "exact"
    """ Select the exact version of the method
    """


class Client(Endpoint):
    """
    A client that communicates with end-point based on its configuration
    """

    def __init__(
        self,
        name: str,
        timeout: int = 120,
        version_match: VersionMatch = VersionMatch.lowest,
        exact_version: int = 0,
        with_rest_client: bool = True,
    ) -> None:
        super().__init__(name)
        assert isinstance(timeout, int), "Timeout needs to be an integer value."
        LOGGER.debug("Start transport for client %s", self.name)
        if with_rest_client:
            self._transport_instance = client.RESTClient(self, connection_timout=timeout)
        else:
            self._transport_instance = None
        self._version_match = version_match
        self._exact_version = exact_version

    async def _call(
        self, method_properties: common.MethodProperties, args: List[object], kwargs: Dict[str, object]
    ) -> common.Result:
        """
        Execute a call and return the result
        """
        result = await self._transport_instance.call(method_properties, args, kwargs)
        return result

    def _select_method(self, name) -> Optional[common.MethodProperties]:
        if name not in common.MethodProperties.methods:
            return None

        methods = common.MethodProperties.methods[name]

        if self._version_match is VersionMatch.lowest:
            return min(methods, key=lambda x: x.api_version)
        elif self._version_match is VersionMatch.highest:
            return max(methods, key=lambda x: x.api_version)
        elif self._version_match is VersionMatch.exact:
            for method in methods:
                if method.api_version == self._exact_version:
                    return method

        return None

    def __getattr__(self, name: str) -> Callable[..., Coroutine[Any, Any, common.Result]]:
        """
        Return a function that will call self._call with the correct method properties associated
        """
        method = self._select_method(name)

        if method is None:
            raise AttributeError("Method with name %s is not defined for this client" % name)

        def wrap(*args: object, **kwargs: object) -> Coroutine[Any, Any, common.Result]:
            assert method
            method.function(*args, **kwargs)
            return self._call(method_properties=method, args=args, kwargs=kwargs)

        return wrap


class SyncClient(object):
    """
    A synchronous client that communicates with end-point based on its configuration
    """

    def __init__(
        self,
        name: Optional[str] = None,
        timeout: int = 120,
        client: Optional[Client] = None,
        ioloop: Optional[ioloop.IOLoop] = None,
    ) -> None:
        """
        either name or client is required.
        they can not be used at the same time

        :param name: name of the configuration to use for this endpoint. The config section used is "{name}_rest_transport"
        :param client: the client to use for this sync_client
        :param timeout: http timeout on all requests

        :param ioloop: the specific (running) ioloop to schedule this request on.
        if no ioloop is passed,we assume there is no running ioloop in the context where this syncclient is used.
        """
        if (name is None) == (client is None):
            # Exactly one must be set
            raise Exception("Either name or client needs to be provided.")

        self.timeout = timeout
        self._ioloop = ioloop
        if client is None:
            assert name is not None  # Make mypy happy
            self.name = name
            self._client = Client(name, self.timeout)
        else:
            self.name = client.name
            self._client = client

    def __getattr__(self, name: str) -> Callable[..., common.Result]:
        def async_call(*args: List[object], **kwargs: Dict[str, object]) -> common.Result:
            method: Callable[..., Coroutine[Any, Any, common.Result]] = getattr(self._client, name)

            def method_call() -> Coroutine[Any, Any, common.Result]:
                return method(*args, **kwargs)

            try:
                if self._ioloop is None:
                    # No specific IOLoop if given, so we assume we can start one in this context
                    return ioloop.IOLoop.current().run_sync(method_call, self.timeout)
                else:
                    # a specific IOloop is passed
                    # we unwrap the tornado loop to get the native python loop
                    # and safely tap into it using run_coroutine_threadsafe
                    assert isinstance(self._ioloop, BaseAsyncIOLoop)  # make mypy happy
                    return run_coroutine_threadsafe(method_call(), self._ioloop.asyncio_loop).result(self.timeout)
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

    async def _call(
        self, method_properties: common.MethodProperties, args: List[object], kwargs: Dict[str, object]
    ) -> common.Result:
        """
        Execute the rpc call
        """
        if "sid" not in kwargs:
            kwargs["sid"] = self._sid

        result = await self._transport_instance.call(method_properties, args, kwargs)
        return result
