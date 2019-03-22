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
import inmanta.protocol.endpoints
from inmanta.types import JsonType, NoneGen
from inmanta.util import Scheduler
from inmanta.protocol import Client, handle, methods
from inmanta.protocol import common, endpoints
from inmanta.protocol.rest import server

from inmanta import config as inmanta_config
from inmanta.server import config as opt, SLICE_SESSION_MANAGER

from tornado import gen, queues, web, routing
from tornado.ioloop import IOLoop

from typing import Dict, Tuple, Callable, Optional, List, Union

import logging
import asyncio
import time
import uuid
import abc
from asyncio.tasks import ensure_future


LOGGER = logging.getLogger(__name__)


class ReturnClient(Client):
    """
        A client that uses a return channel to connect to its destination. This client is used by the server to communicate
        back to clients over the heartbeat channel.
    """

    def __init__(self, name: str, session: "Session") -> None:
        super().__init__(name)
        self.session = session

    @gen.coroutine
    def _call(self, method_properties: common.MethodProperties, args, kwargs) -> common.Result:
        call_spec = method_properties.build_call(args, kwargs)
        try:
            return_value = yield self.session.put_call(call_spec, timeout=method_properties.timeout)
        except gen.TimeoutError:
            return common.Result(code=500, result={"message": "Call timed out"})

        return common.Result(code=return_value["code"], result=return_value["result"])


# Server Side
class Server(endpoints.Endpoint):
    def __init__(self, connection_timout: int = 120) -> None:
        super().__init__("server")

        self._slices: Dict[str, ServerSlice] = {}
        self._handlers: List[routing.Rule] = []
        self.token: Optional[str] = inmanta_config.Config.get(self.id, "token", None)
        self.connection_timout = connection_timout
        self.sessions_handler = SessionManager()
        self.add_slice(self.sessions_handler)

        self._transport = server.RESTServer(self.sessions_handler, self.id)
        self.running = False

    def add_slice(self, slice: "ServerSlice") -> None:
        """
            Add new endpoints to this rest transport
        """
        self._slices[slice.name] = slice

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

    @gen.coroutine
    def start(self) -> NoneGen:
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

        for slice in self.get_slices().values():
            yield slice.prestart(self)

        for slice in self.get_slices().values():
            yield slice.start()
            self._handlers.extend(slice.get_handlers())

        yield self._transport.start(self.get_slices().values(), self._handlers)

    @gen.coroutine
    def stop(self) -> NoneGen:
        """
            Stop the transport.

            The order in which the endpoint are stopped, is reverse compared to the starting order.
            This prevents database connection from being closed too early. This order in which the endpoint
            are started, is hardcoded in the get_server_slices() method in server/bootloader.py
        """
        if not self.running:
            return
        self.running = False
        LOGGER.debug("Stopping Server Rest Endpoint")
        yield self._transport.stop()
        for endpoint in reversed(list(self.get_slices().values())):
            yield endpoint.stop()
        yield self._transport.join()


class ServerSlice(inmanta.protocol.endpoints.CallTarget):
    """
        An API serving part of the server.
    """

    def __init__(self, name: str) -> None:
        super().__init__()

        self._name: str = name
        self._handlers: List[routing.Rule] = []
        self._sched = Scheduler("server slice")  # FIXME: why has each slice its own scheduler?
        self.running: bool = False  # for debugging

    @abc.abstractmethod
    @gen.coroutine
    def prestart(self, server: Server) -> NoneGen:
        """Called by the RestServer host prior to start, can be used to collect references to other server slices"""

    @gen.coroutine
    @abc.abstractmethod
    def start(self) -> NoneGen:
        """
            Start the server slice.
        """
        self.running = True

    @gen.coroutine
    def stop(self) -> NoneGen:
        self.running = False
        self._sched.stop()

    name = property(lambda self: self._name)

    def get_handlers(self) -> List[routing.Rule]:
        return self._handlers

    def add_future(self, future: asyncio.Future) -> None:
        """
            Add a future to the ioloop to be handled, but do not require the result.
        """

        def handle_result(f: asyncio.Future) -> None:
            try:
                f.result()
            except Exception as e:
                LOGGER.exception("An exception occurred while handling a future: %s", str(e))

        IOLoop.current().add_future(ensure_future(future), handle_result)

    def schedule(self, call: Callable, interval: int = 60) -> None:
        self._sched.add_action(call, interval)

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
        self._handlers.append(routing.Rule(routing.PathMatches(r"%s" % location[:-1]), web.RedirectHandler, {"url": location}))

        if start:
            self._handlers.append((r"/", web.RedirectHandler, {"url": location}))

    def add_static_content(self, path: str, content: str, content_type: str = "application/javascript") -> None:
        self._handlers.append(
            routing.Rule(
                routing.PathMatches(r"%s(.*)" % path),
                server.StaticContentHandler,
                {"transport": self, "content": content, "content_type": content_type},
            )
        )


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
        endpoint_names: List[str],
        nodename: str,
    ) -> None:
        self._sid = sid
        self._interval = hang_interval
        self._timeout = timout
        self._sessionstore: SessionManager = sessionstore
        self._seen: float = time.time()
        self._callhandle = None
        self.expired: bool = False

        self.tid: uuid.UUID = tid
        self.endpoint_names: List[str] = endpoint_names
        self.nodename: str = nodename

        self._replies: Dict[uuid.UUID, asyncio.Future] = {}
        self.check_expire()
        self._queue: queues.Queue[common.Request] = queues.Queue()

        self.client = ReturnClient(str(sid), self)

    def check_expire(self) -> None:
        if self.expired:
            LOGGER.exception("Tried to expire session already expired")
        ttw = self._timeout + self._seen - time.time()
        if ttw < 0:
            self.expire(self._seen - time.time())
        else:
            self._callhandle = IOLoop.current().call_later(ttw, self.check_expire)

    def get_id(self) -> uuid.UUID:
        return self._sid

    id = property(get_id)

    def expire(self, timeout: float) -> None:
        self.expired = True
        if self._callhandle is not None:
            IOLoop.current().remove_timeout(self._callhandle)
        self._sessionstore.expire(self, timeout)

    def seen(self) -> None:
        self._seen = time.time()

    def _set_timeout(self, future: asyncio.Future, timeout: int, log_message: str) -> None:
        def on_timeout():
            if not self.expired:
                LOGGER.warning(log_message)
            future.set_exception(gen.TimeoutError())

        timeout_handle = IOLoop.current().add_timeout(IOLoop.current().time() + timeout, on_timeout)
        future.add_done_callback(lambda _: IOLoop.current().remove_timeout(timeout_handle))

    def put_call(self, call_spec: common.Request, timeout: int = 10) -> asyncio.Future:
        future = asyncio.Future()

        reply_id = uuid.uuid4()

        LOGGER.debug("Putting call %s: %s %s for agent %s in queue", reply_id, call_spec.method, call_spec.url, self._sid)

        call_spec.reply_id = reply_id
        self._queue.put(call_spec)
        self._set_timeout(
            future, timeout, "Call %s: %s %s for agent %s timed out." % (reply_id, call_spec.method, call_spec.url, self._sid)
        )
        self._replies[reply_id] = future

        return future

    @gen.coroutine
    def get_calls(self) -> Optional[List[common.Request]]:
        """
            Get all calls queued for a node. If no work is available, wait until timeout. This method returns none if a call
            fails.
        """
        try:
            call_list: List[common.Request] = []
            call = yield self._queue.get(timeout=IOLoop.current().time() + self._interval)
            if call is None:
                # aborting session
                return None
            call_list.append(call)
            while self._queue.qsize() > 0:
                call = yield self._queue.get()
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

    def abort(self):
        "Send poison pill to signal termination."
        self._queue.put(None)


class SessionListener(object):
    def new_session(self, session: Session) -> None:
        pass

    def expire(self, session: Session, timeout: float) -> None:
        pass

    def seen(self, session: Session, endpoint_names: List[str]) -> None:
        pass


# Internals
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

        # Listeners
        self.listeners: List[SessionListener] = []

    def add_listener(self, listener: SessionListener) -> None:
        self.listeners.append(listener)

    @gen.coroutine
    def prestart(self, server: Server) -> None:
        """Called by the RestServer host prior to start, can be used to collect references to other server slices"""

    @gen.coroutine
    def start(self) -> None:
        """
            Start the server slice.
        """
        yield super().start()

    @gen.coroutine
    def stop(self) -> None:
        """
            Stop the end-point and all of its transports
        """
        yield super().stop()
        # terminate all sessions cleanly
        for session in self._sessions.copy().values():
            session.expire(0)
            session.abort()

    def validate_sid(self, sid: uuid.UUID) -> bool:
        if isinstance(sid, str):
            sid = uuid.UUID(sid)
        return sid in self._sessions

    def get_or_create_session(self, sid: uuid.UUID, tid: uuid.UUID, endpoint_names: List[str], nodename: str) -> Session:
        if isinstance(sid, str):
            sid = uuid.UUID(sid)

        if sid not in self._sessions:
            session = self.new_session(sid, tid, endpoint_names, nodename)
            self._sessions[sid] = session
            for listener in self.listeners:
                listener.new_session(session)
        else:
            session = self._sessions[sid]
            self.seen(session, endpoint_names)
            for listener in self.listeners:
                listener.seen(session, endpoint_names)

        return session

    def new_session(self, sid: uuid.UUID, tid: uuid.UUID, endpoint_names: List[str], nodename: str) -> Session:
        LOGGER.debug("New session with id %s on node %s for env %s with endpoints %s" % (sid, nodename, tid, endpoint_names))
        return Session(self, sid, self.hangtime, self.interval, tid, endpoint_names, nodename)

    def expire(self, session: Session, timeout: float) -> None:
        LOGGER.debug("Expired session with id %s, last seen %d seconds ago" % (session.get_id(), timeout))
        for listener in self.listeners:
            listener.expire(session, timeout)
        del self._sessions[session.id]

    def seen(self, session: Session, endpoint_names: List[str]) -> None:
        LOGGER.debug("Seen session with id %s" % (session.get_id()))
        session.seen()

    @handle(methods.heartbeat, env="tid")
    @gen.coroutine
    def heartbeat(
        self, sid: uuid.UUID, env: "inmanta.data.Environment", endpoint_names, nodename
    ) -> Union[int, Tuple[int, Dict[str, str]]]:
        LOGGER.debug("Received heartbeat from %s for agents %s in %s", nodename, ",".join(endpoint_names), env.id)

        session: Session = self.get_or_create_session(sid, env.id, endpoint_names, nodename)

        LOGGER.debug("Let node %s wait for method calls to become available. (long poll)", nodename)
        call_list = yield session.get_calls()
        if call_list is not None:
            LOGGER.debug("Pushing %d method calls to node %s", len(call_list), nodename)
            return 200, {"method_calls": call_list}
        else:
            LOGGER.debug("Heartbeat wait expired for %s, returning. (long poll)", nodename)

        return 200

    @handle(methods.heartbeat_reply)
    @gen.coroutine
    def heartbeat_reply(
        self, sid: uuid.UUID, reply_id: uuid.UUID, data: JsonType
    ) -> Union[int, Tuple[int, Dict[str, str]]]:
        try:
            env = self._sessions[sid]
            env.set_reply(reply_id, data)
            return 200
        except Exception:
            LOGGER.warning("could not deliver agent reply with sid=%s and reply_id=%s" % (sid, reply_id), exc_info=True)
            return 500
