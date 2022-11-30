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
import logging
import socket
import time
import uuid
from collections import defaultdict
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

import importlib_metadata
from tornado import gen, queues, routing, web
from tornado.ioloop import IOLoop

import inmanta.protocol.endpoints
from inmanta import config as inmanta_config
from inmanta.data.model import ExtensionStatus
from inmanta.protocol import Client, common, endpoints, handle, methods
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
        super(SliceStartupException, self).__init__()
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
        self, method_properties: common.MethodProperties, args: List[object], kwargs: Dict[str, object]
    ) -> common.Result:
        call_spec = method_properties.build_call(args, kwargs)
        try:
            if method_properties.timeout:
                return_value = await self.session.put_call(call_spec, timeout=method_properties.timeout)
            else:
                return_value = await self.session.put_call(call_spec)
        except asyncio.CancelledError:
            return common.Result(code=500, result={"message": "Call timed out"})

        return common.Result(code=return_value["code"], result=return_value["result"])


# Server Side
class Server(endpoints.Endpoint):
    def __init__(self, connection_timout: int = 120) -> None:
        super().__init__("server")
        self._slices: Dict[str, ServerSlice] = {}
        self._slice_sequence: Optional[List[ServerSlice]] = None
        self._handlers: List[routing.Rule] = []
        self.token: Optional[str] = inmanta_config.Config.get(self.id, "token", None)
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

    def get_slices(self) -> Dict[str, "ServerSlice"]:
        return self._slices

    def get_slice(self, name: str) -> "ServerSlice":
        return self._slices[name]

    def get_id(self) -> str:
        """
        Returns a unique id for a transport on an endpoint
        """
        return "server_rest_transport"

    id = property(get_id)

    def _order_slices(self) -> List["ServerSlice"]:
        edges: Dict[str, Set[str]] = defaultdict(set)

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

        await super(Server, self).stop()

        order = list(reversed(self._get_slice_sequence()))

        for endpoint in order:
            LOGGER.debug("Pre Stopping %s", endpoint.name)
            await endpoint.prestop()

        for endpoint in order:
            LOGGER.debug("Stopping %s", endpoint.name)
            await endpoint.stop()


class ServerSlice(inmanta.protocol.endpoints.CallTarget, TaskHandler):
    """
    Base class for server extensions offering zero or more api endpoints

    Extensions developers should override the lifecycle methods:

    * :func:`ServerSlice.prestart`
    * :func:`ServerSlice.start`
    * :func:`ServerSlice.prestop`
    * :func:`ServerSlice.stop`
    * :func:`ServerSlice.get_dependencies`

    To register endpoints that server static content, either use :func:'add_static_handler' or :func:'add_static_content'
    To create endpoints, use the annotation based mechanism

    To schedule recurring tasks, use :func:`schedule` or `self._sched`
    To schedule background tasks, use :func:`add_background_task`
    """

    feature_manager: "FeatureManager"

    def __init__(self, name: str) -> None:
        super().__init__()

        self._name: str = name
        self._handlers: List[routing.Rule] = []
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
        pass

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
        await super(ServerSlice, self).stop()

    def get_dependencies(self) -> List[str]:
        """List of names of slices that must be started before this one."""
        return []

    def get_depended_by(self) -> List[str]:
        """List of names of slices that must be started after this one."""
        return []

    # internal API towards extension framework
    name = property(lambda self: self._name)

    def get_handlers(self) -> List[routing.Rule]:
        """Get the list of"""
        return self._handlers

    # utility methods for extensions developers
    def schedule(
        self, call: TaskMethod, interval: int = 60, initial_delay: Optional[float] = None, cancel_on_stop: bool = True
    ) -> None:
        """
        Schedule a task repeatedly with a given interval. Tasks with the same call and the same schedule are considered the
        same. Clients that wish to be able to delete tasks should make sure to use a unique `call` function.

        :param interval: The interval between executions of the task.
        :param initial_delay: The delay to execute the task for the first time. If not set, interval is used.
        """
        self._sched.add_action(call, IntervalSchedule(float(interval), initial_delay), cancel_on_stop)

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

    def add_static_content(self, path: str, content: str, content_type: str = "application/javascript") -> None:
        self._handlers.append(
            routing.Rule(
                routing.PathMatches(r"%s(.*)" % path),
                server.StaticContentHandler,
                {"transport": self, "content": content, "content_type": content_type},
            )
        )

    def get_extension_status(self) -> Optional[ExtensionStatus]:
        ext_name = self.name.split(".")[0]
        source_package_name = self.__class__.__module__.split(".")[0]
        # workaround for #2586
        package_name = "inmanta-core" if source_package_name == "inmanta" else source_package_name
        try:
            distribution = importlib_metadata.distribution(package_name)
            return ExtensionStatus(name=ext_name, package=ext_name, version=distribution.version)
        except importlib_metadata.PackageNotFoundError:
            LOGGER.info(
                "Package %s of slice %s is not packaged in a distribution. Unable to determine its extension.",
                package_name,
                self.name,
            )
            return None

    @classmethod
    def get_extension_statuses(cls, slices: List["ServerSlice"]) -> List[ExtensionStatus]:
        result = {}
        for server_slice in slices:
            ext_status = server_slice.get_extension_status()
            if ext_status is not None:
                result[ext_status.name] = ext_status
        return list(result.values())

    async def get_status(self) -> Dict[str, ArgumentTypes]:
        """
        Get the status of this slice.
        """
        return {}

    def define_features(self) -> List["Feature[object]"]:
        """Return a list of feature that this slice offers"""
        return []


class Session(object):
    """
    An environment that segments agents connected to the server
    """

    def __init__(
        self,
        sessionstore: "SessionManager",
        sid: uuid.UUID,
        hang_interval: int,
        timout: int,
        tid: uuid.UUID,
        endpoint_names: Set[str],
        nodename: str,
        disable_expire_check: bool = False,
    ) -> None:
        self._sid = sid
        self._interval = hang_interval
        self._timeout = timout
        self._sessionstore: SessionManager = sessionstore
        self._seen: float = time.time()
        self._callhandle = None
        self.expired: bool = False

        self.tid: uuid.UUID = tid
        self.endpoint_names: Set[str] = endpoint_names
        self.nodename: str = nodename

        self._replies: Dict[uuid.UUID, asyncio.Future] = {}

        # Disable expiry in certain tests
        if not disable_expire_check:
            self.check_expire()
        self._queue: queues.Queue[Optional[common.Request]] = queues.Queue()

        self.client = ReturnClient(str(sid), self)

    def check_expire(self) -> None:
        if self.expired:
            LOGGER.exception("Tried to expire session already expired")
        ttw = self._timeout + self._seen - time.time()
        if ttw < 0:
            expire_coroutine = self.expire(self._seen - time.time())
            self._sessionstore.add_background_task(expire_coroutine)
        else:
            self._callhandle = IOLoop.current().call_later(ttw, self.check_expire)

    def get_id(self) -> uuid.UUID:
        return self._sid

    id = property(get_id)

    async def expire(self, timeout: float) -> None:
        if self.expired:
            return
        self.expired = True
        if self._callhandle is not None:
            IOLoop.current().remove_timeout(self._callhandle)
        await self._sessionstore.expire(self, timeout)

    def seen(self, endpoint_names: Set[str]) -> None:
        self._seen = time.time()
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

    def put_call(self, call_spec: common.Request, timeout: int = 10) -> asyncio.Future:
        future = asyncio.Future()

        reply_id = uuid.uuid4()

        LOGGER.debug("Putting call %s: %s %s for agent %s in queue", reply_id, call_spec.method, call_spec.url, self._sid)

        call_spec.reply_id = reply_id
        self._queue.put(call_spec)
        self._sessionstore.add_background_task(
            self._handle_timeout(
                future,
                timeout,
                "Call %s: %s %s for agent %s timed out." % (reply_id, call_spec.method, call_spec.url, self._sid),
            )
        )
        self._replies[reply_id] = future

        return future

    async def get_calls(self, no_hang: bool) -> Optional[List[common.Request]]:
        """
        Get all calls queued for a node. If no work is available, wait until timeout. This method returns none if a call
        fails.
        """
        try:
            call_list: List[common.Request] = []

            if no_hang:
                timeout = IOLoop.current().time() + 0.1
            else:
                timeout = IOLoop.current().time() + self._interval

            call = await self._queue.get(timeout=timeout)
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


class SessionListener(object):
    async def new_session(self, session: Session, endpoint_names_snapshot: Set[str]) -> None:
        """
        Notify that a new session was created.

        :param session: The session that was created
        :param endpoint_names_snapshot: The endpoint_names field of the session object may be updated after this
                                        method was called. This parameter provides a snapshot which will not change.
        """
        pass

    async def expire(self, session: Session, endpoint_names_snapshot: Set[str]) -> None:
        """
        Notify that a session expired.

        :param session: The session that was created
        :param endpoint_names_snapshot: The endpoint_names field of the session object may be updated after this
                                        method was called. This parameter provides a snapshot which will not change.
        """
        pass

    async def seen(self, session: Session, endpoint_names_snapshot: Set[str]) -> None:
        """
        Notify that a heartbeat was received for an existing session.

        :param session: The session that was created
        :param endpoint_names_snapshot: The endpoint_names field of the session object may be updated after this
                                        method was called. This parameter provides a snapshot which will not change.
        """
        pass


# Internals
class TransportSlice(ServerSlice):
    """Slice to manage the listening socket"""

    def __init__(self, server: Server) -> None:
        super(TransportSlice, self).__init__(SLICE_TRANSPORT)
        self.server = server

    def get_dependencies(self) -> List[str]:
        """All Slices with an http endpoint should depend on this one using :func:`get_dependened_by`"""
        return []

    async def start(self) -> None:
        await super(TransportSlice, self).start()
        await self.server._transport.start(self.server.get_slices().values(), self.server._handlers)

    async def prestop(self) -> None:
        await super(TransportSlice, self).prestop()
        LOGGER.debug("Stopping Server Rest Endpoint")
        await self.server._transport.stop()

    async def stop(self) -> None:
        await super(TransportSlice, self).stop()
        await self.server._transport.join()

    async def get_status(self) -> Dict[str, ArgumentTypes]:
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

    __methods__: Dict[str, Tuple[str, Callable]] = {}

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
        self._sessions: Dict[uuid.UUID, Session] = {}
        self._sessions_lock = asyncio.Lock()

        # Listeners
        self.listeners: List[SessionListener] = []

    async def get_status(self) -> Dict[str, ArgumentTypes]:
        return {"hangtime": self.hangtime, "interval": self.interval, "sessions": len(self._sessions)}

    def add_listener(self, listener: SessionListener) -> None:
        self.listeners.append(listener)

    async def prestop(self) -> None:
        async with self._sessions_lock:
            # Keep the super call in the session_lock to make sure that no additional sessions are created
            # while the server is shutting down. This call sets the is_stopping() flag to true.
            await super(SessionManager, self).prestop()
        # terminate all sessions cleanly
        for session in self._sessions.copy().values():
            await session.expire(0)
            session.abort()

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    def validate_sid(self, sid: uuid.UUID) -> bool:
        if isinstance(sid, str):
            sid = uuid.UUID(sid)
        return sid in self._sessions

    async def get_or_create_session(self, sid: uuid.UUID, tid: uuid.UUID, endpoint_names: Set[str], nodename: str) -> Session:
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

    def new_session(self, sid: uuid.UUID, tid: uuid.UUID, endpoint_names: Set[str], nodename: str) -> Session:
        LOGGER.debug("New session with id %s on node %s for env %s with endpoints %s" % (sid, nodename, tid, endpoint_names))
        return Session(self, sid, self.hangtime, self.interval, tid, endpoint_names, nodename)

    async def expire(self, session: Session, timeout: float) -> None:
        async with self._sessions_lock:
            LOGGER.debug("Expired session with id %s, last seen %d seconds ago" % (session.get_id(), timeout))
            if session.id in self._sessions:
                del self._sessions[session.id]
            endpoint_names_snapshot = set(session.endpoint_names)
            await asyncio.gather(*[listener.expire(session, endpoint_names_snapshot) for listener in self.listeners])

    def seen(self, session: Session, endpoint_names: Set[str]) -> None:
        LOGGER.debug("Seen session with id %s; endpoints: %s", session.get_id(), endpoint_names)
        session.seen(endpoint_names)

    @handle(methods.heartbeat, env="tid")
    async def heartbeat(
        self, sid: uuid.UUID, env: "inmanta.data.Environment", endpoint_names: List[str], nodename: str, no_hang: bool = False
    ) -> Union[int, Tuple[int, Dict[str, str]]]:
        LOGGER.debug("Received heartbeat from %s for agents %s in %s", nodename, ",".join(endpoint_names), env.id)

        session: Session = await self.get_or_create_session(sid, env.id, set(endpoint_names), nodename)

        LOGGER.debug("Let node %s wait for method calls to become available. (long poll)", nodename)
        call_list = await session.get_calls(no_hang=no_hang)
        if call_list is not None:
            LOGGER.debug("Pushing %d method calls to node %s", len(call_list), nodename)
            return 200, {"method_calls": call_list}
        else:
            LOGGER.debug("Heartbeat wait expired for %s, returning. (long poll)", nodename)

        return 200

    @handle(methods.heartbeat_reply)
    async def heartbeat_reply(
        self, sid: uuid.UUID, reply_id: uuid.UUID, data: JsonType
    ) -> Union[int, Tuple[int, Dict[str, str]]]:
        try:
            env = self._sessions[sid]
            env.set_reply(reply_id, data)
            return 200
        except Exception:
            LOGGER.warning("could not deliver agent reply with sid=%s and reply_id=%s" % (sid, reply_id), exc_info=True)
            return 500
