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
import inspect
import logging
import socket
import uuid
from asyncio import CancelledError, run_coroutine_threadsafe, sleep
from collections import abc, defaultdict
from collections.abc import Coroutine
from enum import Enum
from typing import Any, Callable, Optional
from urllib import parse

import pydantic

from inmanta import config as inmanta_config
from inmanta import const, tracing, types, util
from inmanta.protocol import common, exceptions
from inmanta.util import TaskHandler

from .rest import client

LOGGER: logging.Logger = logging.getLogger(__name__)


class CallTarget:
    """
    A baseclass for all classes that are target for protocol calls / methods
    """

    def _get_endpoint_metadata(self) -> dict[str, list[tuple[str, Callable]]]:
        total_dict = {
            handle_name: method
            for handle_name, method in inspect.getmembers(self)
            if callable(method) and handle_name[0] != "_"
        }

        methods: dict[str, list[tuple[str, Callable]]] = defaultdict(list)
        for handle_name, attr in total_dict.items():
            if hasattr(attr, "__protocol_method__"):
                methods[attr.__protocol_method__.__name__].append((handle_name, attr))

        return methods

    def get_op_mapping(self) -> dict[str, dict[str, common.UrlMethod]]:
        """
        Build a mapping between urls, ops and methods
        """
        url_map: dict[str, dict[str, common.UrlMethod]] = defaultdict(dict)

        # Loop over all methods in this class that have a handler annotation. The handler annotation refers to a method
        # definition. This method definition defines how the handler is invoked.
        for method_name, handler_list in self._get_endpoint_metadata().items():
            for handle_name, fnc in handler_list:
                # Go over all method annotations on the method associated with the handler
                for properties in common.MethodProperties.methods[method_name]:
                    url = properties.get_listen_url()

                    # Associate the method with the handler if:
                    # - the handler does not specific a method version
                    # - the handler specifies a method version and the method version matches the method properties
                    if fnc.__api_version__ is None or (
                        fnc.__api_version__ is not None and properties.api_version == fnc.__api_version__
                    ):
                        # there can only be one
                        if url in url_map and properties.operation in url_map[url]:
                            raise Exception(f"A handler is already registered for {properties.operation} {url}.")

                        url_map[url][properties.operation] = common.UrlMethod(properties, self, fnc, handle_name)
        return url_map


class Endpoint(TaskHandler[None]):
    """
    An end-point in the rpc framework
    """

    def __init__(self, name: str):
        super().__init__()
        self._name: str = name
        self._node_name: str = inmanta_config.nodename.get()
        self._end_point_names: set[str] = set()
        self._targets: list[CallTarget] = []

    def add_call_target(self, target: CallTarget) -> None:
        self._targets.append(target)

    @property
    def call_targets(self) -> list[CallTarget]:
        return self._targets

    def get_end_point_names(self) -> set[str]:
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


class SessionEndpoint(Endpoint, CallTarget):
    """
    An endpoint for clients that make calls to a server and that receive calls back from the server using long-poll
    """

    _client: "SessionClient"
    _heartbeat_client: "SessionClient"

    def __init__(self, name: str, timeout: int = 120, reconnect_delay: int = 5):
        super().__init__(name)
        self._transport = client.RESTClient
        self._sched = util.Scheduler("session endpoint")

        self._env_id: Optional[uuid.UUID] = None

        self.sessionid: uuid.UUID = uuid.uuid1()
        self.running: bool = True
        self.server_timeout = timeout
        self.reconnect_delay = reconnect_delay
        self.dispatch_delay = 0.01  # keep at least 10 ms between dispatches
        self.add_call_target(self)

        self._client = SessionClient(self.name, self.sessionid, timeout=self.server_timeout)
        self._heartbeat_client = SessionClient(self.name, self.sessionid, timeout=self.server_timeout, force_instance=True)

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

    async def start(self) -> None:
        """
        Connect to the server and use a heartbeat and long-poll for two-way communication
        """
        assert self._env_id is not None
        LOGGER.info("Starting agent for %s", str(self.sessionid))
        await self.start_connected()
        self.add_background_task(self.perform_heartbeat())

    async def stop(self) -> None:
        self._heartbeat_client.close()
        await self._sched.stop()
        await super().stop()

    async def on_reconnect(self) -> None:
        """
        Called when a connection becomes active. i.e. when a first heartbeat is received after startup or
        a first heartbeat after an :py:`on_disconnect`
        """

    async def on_disconnect(self) -> None:
        """
        Called when the connection is lost unexpectedly (not on shutdown)
        """

    async def perform_heartbeat(self) -> None:
        """
        Start a continuous heartbeat call
        """
        if self._heartbeat_client is None or self._client is None:
            raise Exception("AgentEndpoint not started")

        connected: bool = False
        try:
            while True:
                LOGGER.log(3, "sending heartbeat for %s", str(self.sessionid))
                result = await self._heartbeat_client.heartbeat(
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
                            method_calls: list[common.Request] = [
                                common.Request.from_dict(req) for req in result.result["method_calls"]
                            ]
                            # FIXME: reuse transport?
                            transport = self._transport(self)

                            for method_call in method_calls:
                                self.add_background_task(self.dispatch_method(transport, method_call))
                    # Always wait a bit between calls. This encourage call batching.
                    await asyncio.sleep(self.dispatch_delay)
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
            msg = "An error occurred during heartbeat method call ({} {} {}): {}".format(
                method_call.reply_id,
                method_call.method,
                method_call.url,
                "No such method",
            )
            LOGGER.error(msg)
            # if reply_id is none, we don't send the reply
            if method_call.reply_id is not None:
                await self._client.heartbeat_reply(self.sessionid, method_call.reply_id, {"result": msg, "code": 500})
            return

        body = method_call.body or {}
        query_string = parse.urlparse(method_call.url).query
        for key, value in parse.parse_qs(query_string, keep_blank_values=True):
            if len(value) == 1:
                body[key] = value[0].decode("latin-1")
            else:
                body[key] = [v.decode("latin-1") for v in value]

        body.update(kwargs)

        with tracing.attach_context(
            {const.TRACEPARENT: method_call.headers[const.TRACEPARENT]} if const.TRACEPARENT in method_call.headers else {}
        ):
            response: common.Response = await transport._execute_call(config, body, method_call.headers)

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

        # if reply is is none, we don't send the reply
        if method_call.reply_id is not None:
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
        force_instance: bool = False,
    ) -> None:
        super().__init__(name)
        assert isinstance(timeout, int), "Timeout needs to be an integer value."
        LOGGER.debug("Start transport for client %s", self.name)
        if with_rest_client:
            self._transport_instance = client.RESTClient(self, connection_timout=timeout, force_instance=force_instance)
        else:
            self._transport_instance = None
        self._version_match = version_match
        self._exact_version = exact_version

    def close(self):
        """
        Closes the RESTclient instance manually. This is only needed when it is started with force_instance set to true
        """
        self._transport_instance.close()

    async def _call(
        self, method_properties: common.MethodProperties, args: list[object], kwargs: dict[str, object]
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
            return next((m for m in methods if m.api_version == self._exact_version), None)

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


class SyncClient:
    """
    A synchronous client that communicates with end-point based on its configuration
    """

    def __init__(
        self,
        name: Optional[str] = None,
        timeout: int = 120,
        client: Optional[Client] = None,
        ioloop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """
        either name or client is required.
        they can not be used at the same time

        :param name: name of the configuration to use for this endpoint. The config section used is "{name}_rest_transport"
        :param client: the client to use for this sync_client
        :param timeout: http timeout on all requests

        :param ioloop: the specific (running) ioloop to schedule this request on. The loop should run on a different thread
            than the one the client methods are called on. If no ioloop is passed, we assume there is no running ioloop in the
            context where this syncclient is used.
        """
        if (name is None) == (client is None):
            # Exactly one must be set
            raise Exception("Either name or client needs to be provided.")

        self.timeout = timeout
        self._ioloop: Optional[asyncio.AbstractEventLoop] = ioloop
        if client is None:
            assert name is not None  # Make mypy happy
            self.name = name
            self._client = Client(name, self.timeout)
        else:
            self.name = client.name
            self._client = client

    def __getattr__(self, name: str) -> Callable[..., common.Result]:
        def async_call(*args: list[object], **kwargs: dict[str, object]) -> common.Result:
            method: Callable[..., abc.Awaitable[common.Result]] = getattr(self._client, name)
            with_timeout: abc.Awaitable[common.Result] = asyncio.wait_for(method(*args, **kwargs), self.timeout)

            try:
                if self._ioloop is None:
                    # no loop is running: create a loop for this thread if it doesn't exist already and run it
                    return util.ensure_event_loop().run_until_complete(with_timeout)
                else:
                    # loop is running on different thread
                    return run_coroutine_threadsafe(with_timeout, self._ioloop).result()
            except TimeoutError:
                raise ConnectionRefusedError()

        return async_call


class SessionClient(Client):
    """
    A client that communicates with server endpoints over a session.
    """

    def __init__(self, name: str, sid: uuid.UUID, timeout: int = 120, force_instance: bool = False) -> None:
        super().__init__(name, timeout, force_instance=force_instance)
        self._sid = sid

    async def _call(
        self, method_properties: common.MethodProperties, args: list[object], kwargs: dict[str, object]
    ) -> common.Result:
        """
        Execute the rpc call
        """
        if "sid" not in kwargs:
            kwargs["sid"] = self._sid

        result = await self._transport_instance.call(method_properties, args, kwargs)
        return result


class TypedClient(Client):
    """A client that returns typed data instead of JSON"""

    def _raise_exception(self, exception_class: type[exceptions.BaseHttpException], result: Optional[types.JsonType]) -> None:
        """Raise an exception based on the provided status"""
        if result is None:
            raise exception_class()

        message = result.get("message", None)
        details = result.get("error_details", None)

        raise exception_class(message, details)

    def _process_response(self, method_properties: common.MethodProperties, response: common.Result) -> types.ReturnTypes:
        """Convert the response into a proper type and restore exception if any"""
        match response.code:
            case 200:
                # typed methods always require an envelope key
                if response.result is None or method_properties.envelope_key not in response.result:
                    raise exceptions.BadRequest("No data was provided in the body. Make sure to only use typed methods.")

                if method_properties.return_type is None:
                    return None

                try:
                    ta = pydantic.TypeAdapter(method_properties.return_type)
                except common.InvalidMethodDefinition:
                    raise exceptions.BadRequest("Typed client can only be used with typed methods.")

                return ta.validate_python(response.result[method_properties.envelope_key])

            case 400:
                self._raise_exception(exceptions.BadRequest, response.result)

            case 401:
                self._raise_exception(exceptions.UnauthorizedException, response.result)

            case 403:
                self._raise_exception(exceptions.Forbidden, response.result)

            case 404:
                self._raise_exception(exceptions.NotFound, response.result)

            case 409:
                self._raise_exception(exceptions.Conflict, response.result)

            case 500:
                self._raise_exception(exceptions.ServerError, response.result)

            case 503:
                self._raise_exception(exceptions.ShutdownInProgress, response.result)

            case _:
                self._raise_exception(exceptions.ServerError, response.result)

        # make mypy happy, it cannot deduce that all the cases will always raise an exception
        return None

    async def _call(
        self, method_properties: common.MethodProperties, args: list[object], kwargs: dict[str, object]
    ) -> types.ReturnTypes:
        """Execute a call and return the result"""
        return self._process_response(method_properties, await super()._call(method_properties, args, kwargs))
