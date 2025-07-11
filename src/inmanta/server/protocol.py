"""
Copyright 2022 Inmanta

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
import importlib.metadata
import itertools
import logging
import re
import socket
import time
import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import timedelta
from typing import TYPE_CHECKING, Callable, Mapping, Optional, Union

from tornado import gen, queues, routing, web

import inmanta.protocol.endpoints
from inmanta import tracing
from inmanta.data.model import ExtensionStatus, ReportedStatus, SliceStatus
from inmanta.protocol import Client, Result, TypedClient, common, endpoints, handle, methods, methods_v2
from inmanta.protocol.exceptions import ShutdownInProgress
from inmanta.protocol.rest import server
from inmanta.server import SLICE_SESSION_MANAGER, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.types import ArgumentTypes, JsonType
from inmanta.util import (
    CronSchedule,
    CycleException,
    IntervalSchedule,
    ScheduledTask,
    Scheduler,
    TaskHandler,
    TaskMethod,
    stable_depth_first,
)

if TYPE_CHECKING:
    from inmanta.server.extensions import Feature, FeatureManager

LOGGER = logging.getLogger(__name__)


class ServerStartFailure(Exception):
    pass


class SliceStartupException(ServerStartFailure):
    def __init__(self, slice_name: str, cause: Exception):
        super().__init__()
        self.__cause__ = cause
        self.in_slice = slice_name

    def __str__(self) -> str:
        return f"Slice {self.in_slice} failed to start because: {str(self.__cause__)}"


class ReturnClient(Client):
    """
    A client that uses a return channel to connect to its destination. This client is used by the server to communicate
    back to clients over the heartbeat channel.
    """

    def __init__(self, name: str, session: "Session") -> None:
        super().__init__(name, with_rest_client=False)
        self.session = session

    async def _call(
        self, method_properties: common.MethodProperties, args: list[object], kwargs: dict[str, object]
    ) -> common.Result:
        with tracing.span(f"return_rpc.{method_properties.function.__name__}"):
            call_spec = method_properties.build_call(args, kwargs)
            call_spec.headers.update(tracing.get_context())
            expect_reply = method_properties.reply
            try:
                if method_properties.timeout:
                    return_value = await self.session.put_call(
                        call_spec, timeout=method_properties.timeout, expect_reply=expect_reply
                    )
                else:
                    return_value = await self.session.put_call(call_spec, expect_reply=expect_reply)
            except asyncio.CancelledError:
                return common.Result(
                    code=500,
                    result={"message": "Call timed out"},
                    client=self._transport_instance,
                    method_properties=method_properties,
                )

            return common.Result(
                code=return_value["code"],
                result=return_value["result"],
                client=self._transport_instance,
                method_properties=method_properties,
            )


# Server Side
class Server(endpoints.Endpoint):
    def __init__(self, connection_timout: int = 120) -> None:
        super().__init__("server")
        self._slices: dict[str, ServerSlice] = {}
        self._slice_sequence: Optional[list[ServerSlice]] = None
        self._handlers: list[routing.Rule] = []
        self.connection_timout = connection_timout
        self.sessions_handler = SessionManager()
        self.add_slice(self.sessions_handler)

        self._transport = server.RESTServer(self.sessions_handler, self.id)
        self.add_slice(TransportSlice(self))
        self.running = False

    def add_slice(self, slice: "ServerSlice") -> None:
        """
        Add new endpoints to this rest transport
        """
        self._slices[slice.name] = slice
        self._slice_sequence = None

    def get_slices(self) -> dict[str, "ServerSlice"]:
        return self._slices

    def get_slice(self, name: str) -> "ServerSlice":
        return self._slices[name]

    def get_id(self) -> str:
        """
        Returns a unique id for a transport on an endpoint
        """
        return "server_rest_transport"

    id = property(get_id)

    def _order_slices(self) -> list["ServerSlice"]:
        edges: dict[str, set[str]] = defaultdict(set)

        for slice in self.get_slices().values():
            edges[slice.name].update(slice.get_dependencies())
            for depby in slice.get_depended_by():
                edges[depby].add(slice.name)

        names = list(edges.keys())
        try:
            order = stable_depth_first(names, {k: list(v) for k, v in edges.items()})
        except CycleException as e:
            raise ServerStartFailure("Dependency cycle between server slices " + ",".join(e.nodes)) from e

        def resolve(name: str) -> Optional["ServerSlice"]:
            if name in self._slices:
                return self._slices[name]
            LOGGER.debug("Slice %s is depended on but does not exist", name)
            return None

        return [s for s in (resolve(name) for name in order) if s is not None]

    def _get_slice_sequence(self) -> Sequence["ServerSlice"]:
        if self._slice_sequence is not None:
            return self._slice_sequence
        self._slice_sequence = self._order_slices()
        return self._slice_sequence

    def _validate(self) -> None:
        """
        Validate whether the server is in a consistent state.
        Raises an exception if an inconsistency is found.
        """
        for method_name, properties_list in common.MethodProperties.methods.items():
            for properties in properties_list:
                # All endpoints used by end-users must have an @auth annotation.
                has_auth_annotation = properties.authorization_metadata is not None
                if (
                    properties.is_external_interface()
                    and not has_auth_annotation
                    and properties.function not in {methods_v2.login, methods_v2.health}
                ):
                    raise Exception(f"API endpoint {method_name} is missing an @auth annotation.")

    async def start(self) -> None:
        """
        Start the transport.

        The order in which the different endpoints are prestarted/started, is determined by the
        order in which they are added to the RESTserver via the add_endpoint(endpoint) method.
        This order is hardcoded in the get_server_slices() method in server/bootloader.py
        """
        if self.running:
            return
        LOGGER.debug("Starting Server Rest Endpoint")
        self._validate()
        self.running = True

        for my_slice in self._get_slice_sequence():
            try:
                LOGGER.debug("Pre Starting %s", my_slice.name)
                await my_slice.prestart(self)
            except Exception as e:
                raise SliceStartupException(my_slice.name, e)

        for my_slice in self._get_slice_sequence():
            try:
                LOGGER.debug("Starting %s", my_slice.name)
                await my_slice.start()
                self._handlers.extend(my_slice.get_handlers())
            except Exception as e:
                raise SliceStartupException(my_slice.name, e)

    async def stop(self) -> None:
        """
        Stop the transport.

        The order in which the endpoint are stopped, is reverse compared to the starting order.
        This prevents database connection from being closed too early. This order in which the endpoint
        are started, is hardcoded in the get_server_slices() method in server/bootloader.py
        """
        if not self.running:
            return
        self.running = False

        await super().stop()

        order = list(reversed(self._get_slice_sequence()))

        pre_stop_exceptions: dict[str, Exception] = {}
        stop_exceptions: dict[str, Exception] = {}

        for endpoint in order:
            try:
                LOGGER.debug("Pre Stopping %s", endpoint.name)
                await endpoint.prestop()
            except Exception as e:
                pre_stop_exceptions[endpoint.name] = e

        for endpoint in order:
            try:
                LOGGER.debug("Stopping %s", endpoint.name)
                await endpoint.stop()
            except Exception as e:
                stop_exceptions[endpoint.name] = e

        if pre_stop_exceptions or stop_exceptions:
            raise BaseExceptionGroup(
                "Uncaught exception occurred during the following slice(s) shutdown %s."
                % str(set(pre_stop_exceptions.keys()).union(set(stop_exceptions.keys()))),
                [exc for exc in itertools.chain(pre_stop_exceptions.values(), stop_exceptions.values())],
            )


class ServerSlice(inmanta.protocol.endpoints.CallTarget, TaskHandler[Result | None]):
    """
    Base class for server extensions offering zero or more api endpoints

    Extensions developers should override the lifecycle methods:

    * :func:`ServerSlice.prestart`
    * :func:`ServerSlice.start`
    * :func:`ServerSlice.prestop`
    * :func:`ServerSlice.stop`
    * :func:`ServerSlice.get_dependencies`

    To register endpoints that serve static content, either use :func:'add_static_handler' or :func:'add_static_content'
    To create endpoints, use the annotation based mechanism

    To schedule recurring tasks, use :func:`schedule` or `self._sched`
    To schedule background tasks, use :func:`add_background_task`
    """

    feature_manager: "FeatureManager"

    # The number of seconds after which the call to the get_status() endpoint of this server slice should time out.
    GET_SLICE_STATUS_TIMEOUT: int = 1

    def __init__(self, name: str) -> None:
        super().__init__()

        self._name: str = name
        self._handlers: list[routing.Rule] = []
        self._sched = Scheduler(f"server slice {name}")
        # is shutdown in progress?
        self._stopping: bool = False

    def is_stopping(self) -> bool:
        """True when prestop has been called."""
        return self._stopping

    async def prestart(self, server: Server) -> None:
        """
        Called by the RestServer host prior to start, can be used to collect references to other server slices
        Dependencies are not up yet.
        """

    async def start(self) -> None:
        """
        Start the server slice.

        This method `blocks` until the slice is ready to receive calls

        Dependencies are up (if present) prior to invocation of this call
        """

    async def prestop(self) -> None:
        """
        Always called before stop

        Stop producing new work:
        - stop timers
        - stop listeners
        - notify shutdown to systems depending on us (like agents)

        sets is_stopping to true

        But remain functional

        All dependencies are up (if present)
        """
        self._stopping = True
        await self._sched.stop()

    async def stop(self) -> None:
        """
        Go down

        All dependencies are up (if present)

        This method `blocks` until the slice is down
        """
        await super().stop()

    def get_dependencies(self) -> list[str]:
        """List of names of slices that must be started before this one."""
        return []

    def get_depended_by(self) -> list[str]:
        """List of names of slices that must be started after this one."""
        return []

    # internal API towards extension framework
    name = property(lambda self: self._name)

    def get_handlers(self) -> list[routing.Rule]:
        """Get the list of"""
        return self._handlers

    # utility methods for extensions developers
    def schedule(
        self,
        call: TaskMethod,
        interval: float = 60,
        initial_delay: Optional[float] = None,
        cancel_on_stop: bool = True,
        quiet_mode: bool = False,
    ) -> None:
        """
        Schedule a task repeatedly with a given interval. Tasks with the same call and the same schedule are considered the
        same. Clients that wish to be able to delete tasks should make sure to use a unique `call` function.

        :param interval: The interval between executions of the task.
        :param initial_delay: The delay to execute the task for the first time. If not set, interval is used.
        :quiet_mode: Set to true to disable logging the recurring notification that the action is being called. Use this to
        avoid polluting the server log for very frequent actions.
        """
        self._sched.add_action(call, IntervalSchedule(interval, initial_delay), cancel_on_stop, quiet_mode)

    def schedule_cron(self, call: TaskMethod, cron: str, cancel_on_stop: bool = True) -> None:
        """
        Schedule a task according to a cron specifier. Tasks with the same call and the same schedule are considered the same.
        Clients that wish to be able to delete tasks should make sure to use a unique `call` function.

        :param cron: The cron specifier to schedule the task by.
        """
        self._sched.add_action(call, CronSchedule(cron=cron), cancel_on_stop)

    def remove_cron(self, call: TaskMethod, cron: str) -> None:
        """
        Remove a cron-scheduled task.
        """
        self._sched.remove(ScheduledTask(action=call, schedule=CronSchedule(cron=cron)))

    def add_static_handler(self, location: str, path: str, default_filename: Optional[str] = None, start: bool = False) -> None:
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

        self._handlers.append(routing.Rule(routing.PathMatches(r"%s(.*)" % location), web.StaticFileHandler, options))
        self._handlers.append(
            routing.Rule(routing.PathMatches(r"%s" % location[:-1]), web.RedirectHandler, {"url": location[1:]})
        )
        if start:
            self._handlers.append((r"/", web.RedirectHandler, {"url": location[1:]}))

    def add_static_content(
        self,
        path: str,
        content: str,
        content_type: str = "application/javascript",
        set_no_cache_header: bool = False,
    ) -> None:
        self._handlers.append(
            routing.Rule(
                routing.PathMatches(r"%s(.*)" % path),
                server.StaticContentHandler,
                {
                    "transport": self,
                    "content": content,
                    "content_type": content_type,
                    "set_no_cache_header": set_no_cache_header,
                },
            )
        )

    def get_extension_status(self) -> Optional[ExtensionStatus]:
        ext_name = self.name.split(".")[0]
        source_package_name = self.__class__.__module__.split(".")[0]
        # workaround for #2586
        package_name = "inmanta-core" if source_package_name == "inmanta" else source_package_name
        try:
            distribution = importlib.metadata.distribution(package_name)
            return ExtensionStatus(name=ext_name, package=ext_name, version=distribution.version)
        except importlib.metadata.PackageNotFoundError:
            LOGGER.info(
                "Package %s of slice %s is not packaged in a distribution. Unable to determine its extension.",
                package_name,
                self.name,
            )
            return None

    @classmethod
    def get_extension_statuses(cls, slices: list["ServerSlice"]) -> list[ExtensionStatus]:
        result = {}
        for server_slice in slices:
            ext_status = server_slice.get_extension_status()
            if ext_status is not None:
                result[ext_status.name] = ext_status
        return list(result.values())

    async def get_status(self) -> Mapping[str, ArgumentTypes | Mapping[str, ArgumentTypes]]:
        """
        Get the status of this slice.
        """
        return {}

    async def get_reported_status(self) -> tuple[ReportedStatus, Optional[str]]:
        """
        Get the reported status of this slice as well as a message if applicable.
        """
        return ReportedStatus.OK, None

    async def get_slice_status(self) -> SliceStatus:
        """
        Get the reported status of this slice
        """
        try:
            status, message = await self.get_reported_status()
            return SliceStatus(
                name=self.name,
                status=await asyncio.wait_for(self.get_status(), self.GET_SLICE_STATUS_TIMEOUT),
                reported_status=status,
                message=message,
            )
        except asyncio.TimeoutError:
            return SliceStatus(
                name=self.name,
                status={
                    "error": f"Timeout on data collection for {self.name}, consult the server log for additional information"
                },
                reported_status=ReportedStatus.Error,
                message="Timeout on data collection",
            )
        except Exception:
            LOGGER.error(
                f"The following error occurred while trying to determine the status of slice {self.name}",
                exc_info=True,
            )
            return SliceStatus(
                name=self.name,
                status={"error": "An unexpected error occurred, reported to server log"},
                reported_status=ReportedStatus.Error,
                message="An unexpected error occurred, reported to server log",
            )

    def define_features(self) -> list["Feature[object]"]:
        """Return a list of feature that this slice offers"""
        return []


class Session:
    """
    An environment that segments agents connected to the server. Should only be created in a context with a running event loop.
    """

    def __init__(
        self,
        sessionstore: "SessionManager",
        sid: uuid.UUID,
        hang_interval: int,
        timout: int,
        tid: uuid.UUID,
        endpoint_names: set[str],
        nodename: str,
        disable_expire_check: bool = False,
    ) -> None:
        self._sid = sid
        self._interval = hang_interval
        self._timeout = timout
        self._sessionstore: SessionManager = sessionstore
        self._seen: float = time.monotonic()
        self._callhandle: Optional[asyncio.TimerHandle] = None
        self.expired: bool = False

        self.last_dispatched_call: float = 0
        self.dispatch_delay = 0.01  # keep at least 10 ms between dispatches

        self.tid: uuid.UUID = tid
        self.endpoint_names: set[str] = endpoint_names
        self.nodename: str = nodename

        self._replies: dict[uuid.UUID, asyncio.Future] = {}

        # Disable expiry in certain tests
        if not disable_expire_check:
            self.check_expire()
        self._queue: queues.Queue[Optional[common.Request]] = queues.Queue()

        self.client = ReturnClient(str(sid), self)

    def check_expire(self) -> None:
        if self.expired:
            LOGGER.exception("Tried to expire session already expired")
        now = time.monotonic()
        ttw = self._timeout + self._seen - now
        if ttw < 0:
            expire_coroutine = self.expire(self._seen - now)
            self._sessionstore.add_background_task(expire_coroutine)
        else:
            self._callhandle = asyncio.get_running_loop().call_later(ttw, self.check_expire)

    def get_id(self) -> uuid.UUID:
        return self._sid

    id = property(get_id)

    async def expire(self, timeout: float) -> None:
        if self.expired:
            return
        self.expired = True
        if self._callhandle is not None:
            self._callhandle.cancel()
        await self._sessionstore.expire(self, timeout)

    def seen(self, endpoint_names: set[str]) -> None:
        self._seen = time.monotonic()
        self.endpoint_names = endpoint_names

    async def _handle_timeout(self, future: asyncio.Future, timeout: int, log_message: str) -> None:
        """A function that awaits a future until its value is ready or until timeout. When the call times out, a message is
        logged. The future itself will be cancelled.

        This method should be called as a background task. Any other exceptions (which should not occur) will be logged in
        the background task.
        """
        try:
            await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            LOGGER.warning(log_message)

    def put_call(self, call_spec: common.Request, timeout: int = 10, expect_reply: bool = True) -> asyncio.Future:
        reply_id = uuid.uuid4()
        future = asyncio.Future()

        LOGGER.debug("Putting call %s: %s %s for agent %s in queue", reply_id, call_spec.method, call_spec.url, self._sid)

        if expect_reply:
            call_spec.reply_id = reply_id
            self._sessionstore.add_background_task(
                self._handle_timeout(
                    future,
                    timeout,
                    f"Call {reply_id}: {call_spec.method} {call_spec.url} for agent {self._sid} timed out.",
                )
            )
            self._replies[reply_id] = future
        else:
            future.set_result({"code": 200, "result": None})
        self._queue.put(call_spec)

        return future

    async def get_calls(self, no_hang: bool) -> Optional[list[common.Request]]:
        """
        Get all calls queued for a node. If no work is available, wait until timeout. This method returns none if a call
        fails.
        """
        try:
            call_list: list[common.Request] = []

            if no_hang:
                timeout = 0.1
            else:
                timeout = self._interval if self._interval > 0.1 else 0.1
                # We choose to have a minimum of 0.1 as timeout as this is also the value used for no_hang.
                # Furthermore, the timeout value cannot be zero as this causes an issue with Tornado:
                # https://github.com/tornadoweb/tornado/issues/3271
            call = await self._queue.get(timeout=timedelta(seconds=timeout))
            if call is None:
                # aborting session
                return None
            call_list.append(call)
            while self._queue.qsize() > 0:
                call = await self._queue.get()
                if call is None:
                    # aborting session
                    return None
                call_list.append(call)

            return call_list

        except gen.TimeoutError:
            return None

    def set_reply(self, reply_id: uuid.UUID, data: JsonType) -> None:
        LOGGER.log(3, "Received Reply: %s", reply_id)
        if reply_id in self._replies:
            future: asyncio.Future = self._replies[reply_id]
            del self._replies[reply_id]
            if not future.done():
                future.set_result(data)
        else:
            LOGGER.debug("Received Reply that is unknown: %s", reply_id)

    def get_client(self) -> ReturnClient:
        return self.client

    def abort(self) -> None:
        "Send poison pill to signal termination."
        self._queue.put(None)

    async def expire_and_abort(self, timeout: float) -> None:
        await self.expire(timeout)
        self.abort()


class SessionListener:
    async def new_session(self, session: Session, endpoint_names_snapshot: set[str]) -> None:
        """
        Notify that a new session was created.

        :param session: The session that was created
        :param endpoint_names_snapshot: The endpoint_names field of the session object may be updated after this
                                        method was called. This parameter provides a snapshot which will not change.
        """

    async def expire(self, session: Session, endpoint_names_snapshot: set[str]) -> None:
        """
        Notify that a session expired.

        :param session: The session that was created
        :param endpoint_names_snapshot: The endpoint_names field of the session object may be updated after this
                                        method was called. This parameter provides a snapshot which will not change.
        """

    async def seen(self, session: Session, endpoint_names_snapshot: set[str]) -> None:
        """
        Notify that a heartbeat was received for an existing session.

        :param session: The session that was created
        :param endpoint_names_snapshot: The endpoint_names field of the session object may be updated after this
                                        method was called. This parameter provides a snapshot which will not change.
        """


# Internals
class TransportSlice(ServerSlice):
    """Slice to manage the listening socket"""

    def __init__(self, server: Server) -> None:
        super().__init__(SLICE_TRANSPORT)
        self.server = server

    def get_dependencies(self) -> list[str]:
        """All Slices with an http endpoint should depend on this one using :func:`get_dependened_by`"""
        return []

    async def start(self) -> None:
        await super().start()
        await self.server._transport.start(self.server.get_slices().values(), self.server._handlers)

    async def prestop(self) -> None:
        await super().prestop()
        LOGGER.debug("Stopping Server Rest Endpoint")
        await self.server._transport.stop()

    async def stop(self) -> None:
        await super().stop()
        await self.server._transport.join()

    async def get_status(self) -> Mapping[str, ArgumentTypes]:
        def format_socket(sock: socket.socket) -> str:
            sname = sock.getsockname()
            return f"{sname[0]}:{sname[1]}"

        sockets = []
        if self.server._transport._http_server._sockets:
            sockets = [
                format_socket(s)
                for s in self.server._transport._http_server._sockets.values()
                if s.family in [socket.AF_INET, socket.AF_INET6]
            ]

        return {
            "inflight": self.server._transport.inflight_counter,
            "running": self.server._transport.running,
            "sockets": sockets,
        }


class SessionManager(ServerSlice):
    """
    A service that receives method calls over one or more transports
    """

    __methods__: dict[str, tuple[str, Callable]] = {}

    def __init__(self) -> None:
        super().__init__(SLICE_SESSION_MANAGER)

        # Config
        interval: int = opt.agent_timeout.get()
        hangtime: Optional[int] = opt.agent_hangtime.get()

        if hangtime is None:
            hangtime = int(interval * 3 / 4)

        self.hangtime: int = hangtime
        self.interval: int = interval

        # Session management
        self._sessions: dict[uuid.UUID, Session] = {}
        self._sessions_lock = asyncio.Lock()

        # Listeners
        self.listeners: list[SessionListener] = []

    async def get_status(self) -> Mapping[str, ArgumentTypes]:
        return {"hangtime": self.hangtime, "interval": self.interval, "sessions": len(self._sessions)}

    def add_listener(self, listener: SessionListener) -> None:
        self.listeners.append(listener)

    async def prestop(self) -> None:
        async with self._sessions_lock:
            # Keep the super call in the session_lock to make sure that no additional sessions are created
            # while the server is shutting down. This call sets the is_stopping() flag to true.
            await super().prestop()
        # terminate all sessions cleanly
        for session in self._sessions.copy().values():
            await session.expire(0)
            session.abort()

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    def validate_sid(self, sid: uuid.UUID) -> bool:
        if isinstance(sid, str):
            sid = uuid.UUID(sid)
        return sid in self._sessions

    async def get_or_create_session(self, sid: uuid.UUID, tid: uuid.UUID, endpoint_names: set[str], nodename: str) -> Session:
        if isinstance(sid, str):
            sid = uuid.UUID(sid)

        async with self._sessions_lock:
            if self.is_stopping():
                raise ShutdownInProgress()
            if sid not in self._sessions:
                session = self.new_session(sid, tid, endpoint_names, nodename)
                self._sessions[sid] = session
                endpoint_names_snapshot = set(session.endpoint_names)
                await asyncio.gather(*[listener.new_session(session, endpoint_names_snapshot) for listener in self.listeners])
            else:
                session = self._sessions[sid]
                self.seen(session, endpoint_names)
                endpoint_names_snapshot = set(session.endpoint_names)
                await asyncio.gather(*[listener.seen(session, endpoint_names_snapshot) for listener in self.listeners])

            return session

    def new_session(self, sid: uuid.UUID, tid: uuid.UUID, endpoint_names: set[str], nodename: str) -> Session:
        LOGGER.debug(f"New session with id {sid} on node {nodename} for env {tid} with endpoints {endpoint_names}")
        return Session(self, sid, self.hangtime, self.interval, tid, endpoint_names, nodename)

    async def expire(self, session: Session, timeout: float) -> None:
        async with self._sessions_lock:
            LOGGER.debug("Expired session with id %s, last seen %d seconds ago" % (session.get_id(), timeout))
            if session.id in self._sessions:
                del self._sessions[session.id]
            endpoint_names_snapshot = set(session.endpoint_names)
            await asyncio.gather(*[listener.expire(session, endpoint_names_snapshot) for listener in self.listeners])

    def seen(self, session: Session, endpoint_names: set[str]) -> None:
        LOGGER.debug("Seen session with id %s; endpoints: %s", session.get_id(), endpoint_names)
        session.seen(endpoint_names)

    @handle(methods.heartbeat, env="tid")
    async def heartbeat(
        self, sid: uuid.UUID, env: "inmanta.data.Environment", endpoint_names: list[str], nodename: str, no_hang: bool = False
    ) -> Union[int, tuple[int, dict[str, str]]]:
        LOGGER.debug("Received heartbeat from %s for agents %s in %s", nodename, ",".join(endpoint_names), env.id)

        session: Session = await self.get_or_create_session(sid, env.id, set(endpoint_names), nodename)

        LOGGER.debug("Let node %s wait for method calls to become available. (long poll)", nodename)

        # keep a minimal timeout between sending out calls to allow them to batch up
        now = time.monotonic()
        wait_time = session.dispatch_delay - (now - session.last_dispatched_call)
        if wait_time > 0:
            await asyncio.sleep(wait_time)

        call_list = await session.get_calls(no_hang=no_hang)

        if call_list is not None:
            LOGGER.debug("Pushing %d method calls to node %s", len(call_list), nodename)
            session.last_dispatched_call = time.monotonic()
            return 200, {"method_calls": call_list}
        else:
            LOGGER.debug("Heartbeat wait expired for %s, returning. (long poll)", nodename)

        return 200

    @handle(methods.heartbeat_reply)
    async def heartbeat_reply(
        self, sid: uuid.UUID, reply_id: uuid.UUID, data: JsonType
    ) -> Union[int, tuple[int, dict[str, str]]]:
        try:
            env = self._sessions[sid]
            env.set_reply(reply_id, data)
            return 200
        except Exception:
            LOGGER.warning(f"could not deliver agent reply with sid={sid} and reply_id={reply_id}", exc_info=True)
            return 500


class LocalClient(TypedClient):
    """A client that calls methods async on the server in the same process"""

    def __init__(self, name: str, server: Server) -> None:
        super().__init__(name, with_rest_client=False)
        self._server = server
        self._op_mapping: dict[str, dict[str, common.UrlMethod]] = {}
        for slice in server.get_slices().values():
            self._op_mapping.update(slice.get_op_mapping())

    def _get_op_mapping(self, url: str, method: str) -> common.UrlMethod:
        """Get the op mapping for the provided url and method"""
        methods = {}
        if url not in self._op_mapping:
            for key, mapping in self._op_mapping.items():
                if re.match(key, url):
                    methods = mapping
                    break
        else:
            methods = self._op_mapping[url]

        if method in methods:
            return methods[method]

        raise Exception(f"No handler defined for {method} {url}")

    async def _call(
        self, method_properties: common.MethodProperties, args: list[object], kwargs: dict[str, object]
    ) -> common.Result:
        spec = method_properties.build_call(args, kwargs)
        method_config = self._get_op_mapping(spec.url, spec.method)
        response = await self._server._transport._execute_call(method_config, spec.body, spec.headers)
        return self._process_response(
            method_properties,
            common.Result(
                code=response.status_code,
                result=response.body,
                client=self._transport_instance,
                method_properties=method_properties,
            ),
        )
