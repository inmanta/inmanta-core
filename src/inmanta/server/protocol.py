"""
    Copyright 2018 Inmanta

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
from inmanta.util import Scheduler
from inmanta.protocol import RESTBase, decode_token, json_encode, UnauhorizedError, ReturnClient, handle

from inmanta import config as inmanta_config, methods
from inmanta.server import config as opt, SLICE_SESSION_MANAGER

import tornado.web
from tornado import gen, queues
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer

import logging
import ssl
import time
import uuid
from _collections import defaultdict


LOGGER = logging.getLogger(__name__)


# Server Side
class RESTServer(RESTBase):

    def __init__(self, connection_timout=120):
        self.__end_points = []
        self.__endpoint_dict = {}
        self._handlers = []
        self.token = inmanta_config.Config.get(self.id, "token", None)
        self.connection_timout = connection_timout
        self.headers = set()
        self.sessions_handler = SessionManager(IOLoop.current())
        self.add_endpoint(self.sessions_handler)

    def add_endpoint(self, endpoint: "ServerSlice"):
        self.__end_points.append(endpoint)
        self.__endpoint_dict[endpoint.name] = endpoint

    def get_endpoint(self, name):
        return self.__endpoint_dict[name]

    def validate_sid(self, sid):
        return self.sessions_handler.validate_sid(sid)

    def get_id(self):
        """
            Returns a unique id for a transport on an endpoint
        """
        return "server_rest_transport"

    id = property(get_id)

    def create_op_mapping(self):
        """
            Build a mapping between urls, ops and methods
        """
        url_map = defaultdict(dict)

        # TODO: avoid colliding handlers

        for endpoint in self.__end_points:
            for method, method_handlers in endpoint.__methods__.items():
                properties = method.__protocol_properties__
                call = (endpoint, method_handlers[0])

                if "arg_options" in properties:
                    for opts in properties["arg_options"].values():
                        if "header" in opts:
                            self.headers.add(opts["header"])

                url = self._create_base_url(properties)
                properties["api_version"] = "1"
                url_map[url][properties["operation"]] = (properties, call, method.__wrapped__)
                url = self._create_base_url(properties, versioned=False)
                properties = properties.copy()
                properties["api_version"] = None
                url_map[url][properties["operation"]] = (properties, call, method.__wrapped__)
        return url_map

    def start(self):
        """
            Start the transport
        """
        LOGGER.debug("Starting Server Rest Endpoint")

        for endpoint in self.__end_points:
            endpoint.prestart(self)

        for endpoint in self.__end_points:
            endpoint.start()
            self._handlers.extend(endpoint.get_handlers())

        url_map = self.create_op_mapping()

        for url, configs in url_map.items():
            handler_config = {}
            for op, cfg in configs.items():
                handler_config[op] = cfg

            self._handlers.append((url, RESTHandler, {"transport": self, "config": handler_config}))
            LOGGER.debug("Registering handler(s) for url %s and methods %s" % (url, ", ".join(handler_config.keys())))

        port = 8888
        if self.id in inmanta_config.Config.get() and "port" in inmanta_config.Config.get()[self.id]:
            port = inmanta_config.Config.get()[self.id]["port"]

        application = tornado.web.Application(self._handlers, compress_response=True)

        crt = inmanta_config.Config.get("server", "ssl_cert_file", None)
        key = inmanta_config.Config.get("server", "ssl_key_file", None)

        if(crt is not None and key is not None):
            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(crt, key)

            self.http_server = HTTPServer(application, decompress_request=True, ssl_options=ssl_ctx)
            LOGGER.debug("Created REST transport with SSL")
        else:
            self.http_server = HTTPServer(application, decompress_request=True)

        self.http_server.listen(port)

        LOGGER.debug("Start REST transport")

    def stop(self):
        LOGGER.debug("Stoppin Server Rest Endpoint")
        self.http_server.stop()
        for endpoint in self.__end_points:
            endpoint.stop()

    def return_error_msg(self, status=500, msg="", headers={}):
        body = {"message": msg}
        headers["Content-Type"] = "application/json"
        LOGGER.debug("Signaling error to client: %d, %s, %s", status, body, headers)
        return body, headers, status


class ServerSlice(object):
    """
        An API serving part of the server.
    """

    def __init__(self, io_loop, name):
        self._name = name
        self._io_loop = io_loop

        self.create_endpoint_metadata()
        self._end_point_names = []
        self._handlers = []
        self._sched = Scheduler(self._io_loop)

    def prestart(self, server: RESTServer):
        """Called by the RestServer host prior to start, can be used to collect references to other server slices"""
        pass

    def start(self):
        pass

    def stop(self):
        pass

    name = property(lambda self: self._name)

    def get_handlers(self):
        return self._handlers

    def get_end_point_names(self):
        # TODO: why?
        return self._end_point_names

    def add_end_point_name(self, name):
        """
            Add an additional name to this endpoint to which it reacts and sends out in heartbeats
        """
        LOGGER.debug("Adding '%s' as endpoint", name)
        self._end_point_names.append(name)

    def add_future(self, future):
        """
            Add a future to the ioloop to be handled, but do not require the result.
        """
        def handle_result(f):
            try:
                f.result()
            except Exception as e:
                LOGGER.exception("An exception occurred while handling a future: %s", str(e))

        self._io_loop.add_future(future, handle_result)

    def schedule(self, call, interval=60):
        self._sched.add_action(call, interval)

    def create_endpoint_metadata(self):
        total_dict = {method_name: getattr(self, method_name)
                      for method_name in dir(self) if callable(getattr(self, method_name))}

        methods = {}
        for name, attr in total_dict.items():
            if name[0:2] != "__" and hasattr(attr, "__protocol_method__"):
                if attr.__protocol_method__ in methods:
                    raise Exception("Unable to register multiple handlers for the same method. %s" % attr.__protocol_method__)

                methods[attr.__protocol_method__] = (name, attr)

        self.__methods__ = methods

    def add_static_handler(self, location, path, default_filename=None, start=False):
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

        self._handlers.append((r"%s(.*)" % location, tornado.web.StaticFileHandler, options))
        self._handlers.append((r"%s" % location[:-1], tornado.web.RedirectHandler, {"url": location}))

        if start:
            self._handlers.append((r"/", tornado.web.RedirectHandler, {"url": location}))

    def add_static_content(self, path, content, content_type="application/javascript"):
        self._handlers.append((r"%s(.*)" % path, StaticContentHandler, {"transport": self, "content": content,
                                                                        "content_type": content_type}))


class Session(object):
    """
        An environment that segments agents connected to the server
    """

    def __init__(self, sessionstore, io_loop, sid, hang_interval, timout, tid, endpoint_names, nodename):
        self._sid = sid
        self._interval = hang_interval
        self._timeout = timout
        self._sessionstore = sessionstore
        self._seen = time.time()
        self._callhandle = None
        self.expired = False

        self.tid = tid
        self.endpoint_names = endpoint_names
        self.nodename = nodename

        self._io_loop = io_loop

        self._replies = {}
        self.check_expire()
        self._queue = queues.Queue()

        self.client = ReturnClient(str(sid), self)

    def check_expire(self):
        if self.expired:
            LOGGER.exception("Tried to expire session already expired")
        ttw = self._timeout + self._seen - time.time()
        if ttw < 0:
            self.expire(self._seen - time.time())
        else:
            self._callhandle = self._io_loop.call_later(ttw, self.check_expire)

    def get_id(self):
        return self._sid

    id = property(get_id)

    def expire(self, timeout):
        self.expired = True
        if self._callhandle is not None:
            self._io_loop.remove_timeout(self._callhandle)
        self._sessionstore.expire(self, timeout)

    def seen(self):
        self._seen = time.time()

    def _set_timeout(self, future, timeout, log_message):
        def on_timeout():
            if not self.expired:
                LOGGER.warning(log_message)
            future.set_exception(gen.TimeoutError())

        timeout_handle = self._io_loop.add_timeout(self._io_loop.time() + timeout, on_timeout)
        future.add_done_callback(lambda _: self._io_loop.remove_timeout(timeout_handle))

    def put_call(self, call_spec, timeout=10):
        future = tornado.concurrent.Future()

        reply_id = uuid.uuid4()

        LOGGER.debug("Putting call %s: %s %s for agent %s in queue", reply_id, call_spec["method"], call_spec["url"], self._sid)

        q = self._queue
        call_spec["reply_id"] = reply_id
        q.put(call_spec)
        self._set_timeout(future, timeout, "Call %s: %s %s for agent %s timed out." %
                          (reply_id, call_spec["method"], call_spec["url"], self._sid))
        self._replies[call_spec["reply_id"]] = future

        return future

    @gen.coroutine
    def get_calls(self):
        """
            Get all calls queued for a node. If no work is available, wait until timeout. This method returns none if a call
            fails.
        """
        try:
            q = self._queue
            call_list = []
            call = yield q.get(timeout=self._io_loop.time() + self._interval)
            call_list.append(call)
            while q.qsize() > 0:
                call = yield q.get()
                call_list.append(call)

            return call_list

        except gen.TimeoutError:
            return None

    def set_reply(self, reply_id, data):
        LOGGER.log(3, "Received Reply: %s", reply_id)
        if reply_id in self._replies:
            future = self._replies[reply_id]
            del self._replies[reply_id]
            if not future.done():
                future.set_result(data)
        else:
            LOGGER.debug("Received Reply that is unknown: %s", reply_id)

    def get_client(self):
        return self.client


class SessionListener(object):

    def new_session(self, session: Session):
        pass

    def expire(self, session: Session, timeout):
        pass

    def seen(self, session: Session, endpoint_names: list):
        pass


# Internals
class SessionManager(ServerSlice):
    """
        A service that receives method calls over one or more transports
    """
    __methods__ = {}

    def __init__(self, io_loop):
        super().__init__(io_loop, SLICE_SESSION_MANAGER)

        # Config
        interval = opt.agent_timeout.get()
        hangtime = opt.agent_hangtime.get()

        if hangtime is None:
            hangtime = interval * 3 / 4

        self.hangtime = hangtime
        self.interval = interval

        # Session management
        self._heartbeat_cb = None
        self.agent_handles = {}
        self._sessions = {}

        # Listeners
        self.listeners = []

    def add_listener(self, listener):
        self.listeners.append(listener)

    def stop(self):
        """
            Stop the end-point and all of its transports
        """
        # terminate all sessions cleanly
        for session in self._sessions.copy().values():
            session.expire(0)

    def validate_sid(self, sid):
        if isinstance(sid, str):
            sid = uuid.UUID(sid)
        return sid in self._sessions

    def get_or_create_session(self, sid, tid, endpoint_names, nodename):
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

    def new_session(self, sid, tid, endpoint_names, nodename):
        LOGGER.debug("New session with id %s on node %s for env %s with endpoints %s" % (sid, nodename, tid, endpoint_names))
        return Session(self, self._io_loop, sid, self.hangtime, self.interval, tid, endpoint_names, nodename)

    def expire(self, session: Session, timeout):
        LOGGER.debug("Expired session with id %s, last seen %d seconds ago" % (session.get_id(), timeout))
        for listener in self.listeners:
            listener.expire(session, timeout)
        del self._sessions[session.id]

    def seen(self, session: Session, endpoint_names: list):
        LOGGER.debug("Seen session with id %s" % (session.get_id()))
        session.seen()

    @handle(methods.HeartBeatMethod.heartbeat, env="tid")
    @gen.coroutine
    def heartbeat(self, sid, env, endpoint_names, nodename):
        LOGGER.debug("Received heartbeat from %s for agents %s in %s", nodename, ",".join(endpoint_names), env.id)

        session = self.get_or_create_session(sid, env.id, endpoint_names, nodename)

        LOGGER.debug("Let node %s wait for method calls to become available. (long poll)", nodename)
        call_list = yield session.get_calls()
        if call_list is not None:
            LOGGER.debug("Pushing %d method calls to node %s", len(call_list), nodename)
            return 200, {"method_calls": call_list}
        else:
            LOGGER.debug("Heartbeat wait expired for %s, returning. (long poll)", nodename)

        return 200

    @handle(methods.HeartBeatMethod.heartbeat_reply)
    @gen.coroutine
    def heartbeat_reply(self, sid, reply_id, data):
        try:
            env = self._sessions[sid]
            env.set_reply(reply_id, data)
            return 200
        except Exception:
            LOGGER.warning("could not deliver agent reply with sid=%s and reply_id=%s" % (sid, reply_id), exc_info=True)


class RESTHandler(tornado.web.RequestHandler):
    """
        A generic class use by the transport
    """

    def initialize(self, transport: "RESTServer", config):
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

    def get_auth_token(self, headers: dict):
        """
            Get the auth token provided by the caller. The token is provided as a bearer token.
        """
        if "Authorization" not in headers:
            return None

        parts = headers["Authorization"].split(" ")
        if len(parts) == 0 or parts[0].lower() != "bearer" or len(parts) > 2 or len(parts) == 1:
            LOGGER.warning("Invalid authentication header, Inmanta expects a bearer token. (%s was provided)",
                           headers["Authorization"])
            return None

        return decode_token(parts[1])

    def respond(self, body, headers, status):
        if body is not None:
            self.write(json_encode(body))

        for header, value in headers.items():
            self.set_header(header, value)

        self.set_status(status)

    @gen.coroutine
    def _call(self, kwargs, http_method, call_config):
        """
            An rpc like call
        """
        if call_config is None:
            body, headers, status = self._transport.return_error_msg(404, "This method does not exist.")
            self.respond(body, headers, status)
            return

        self.set_header("Access-Control-Allow-Origin", "*")
        try:
            message = self._transport._decode(self.request.body)
            if message is None:
                message = {}

            for key, value in self.request.query_arguments.items():
                if len(value) == 1:
                    message[key] = value[0].decode("latin-1")
                else:
                    message[key] = [v.decode("latin-1") for v in value]

            request_headers = self.request.headers

            try:
                auth_token = self.get_auth_token(request_headers)
            except UnauhorizedError as e:
                self.respond(*self._transport.return_error_msg(403, "Access denied: " + e.args[0]))
                return

            auth_enabled = inmanta_config.Config.get("server", "auth", False)
            if not auth_enabled or auth_token is not None:
                result = yield self._transport._execute_call(kwargs, http_method, call_config,
                                                             message, request_headers, auth_token)
                self.respond(*result)
            else:
                self.respond(*self._transport.return_error_msg(401, "Access to this resource is unauthorized."))
        except ValueError:
            LOGGER.exception("An exception occured")
            self.respond(*self._transport.return_error_msg(500, "Unable to decode request body"))

    @gen.coroutine
    def head(self, *args, **kwargs):
        yield self._call(http_method="HEAD", call_config=self._get_config("HEAD"), kwargs=kwargs)

    @gen.coroutine
    def get(self, *args, **kwargs):
        yield self._call(http_method="GET", call_config=self._get_config("GET"), kwargs=kwargs)

    @gen.coroutine
    def post(self, *args, **kwargs):
        yield self._call(http_method="POST", call_config=self._get_config("POST"), kwargs=kwargs)

    @gen.coroutine
    def delete(self, *args, **kwargs):
        yield self._call(http_method="DELETE", call_config=self._get_config("DELETE"), kwargs=kwargs)

    @gen.coroutine
    def patch(self, *args, **kwargs):
        yield self._call(http_method="PATCH", call_config=self._get_config("PATCH"), kwargs=kwargs)

    @gen.coroutine
    def put(self, *args, **kwargs):
        yield self._call(http_method="PUT", call_config=self._get_config("PUT"), kwargs=kwargs)

    @gen.coroutine
    def options(self, *args, **kwargs):
        allow_headers = "Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token"
        if len(self._transport.headers):
            allow_headers += ", " + ", ".join(self._transport.headers)

        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "HEAD, GET, POST, PUT, OPTIONS, DELETE, PATCH")
        self.set_header("Access-Control-Allow-Headers", allow_headers)

        self.set_status(200)


class StaticContentHandler(tornado.web.RequestHandler):
    def initialize(self, transport: "RESTServer", content, content_type):
        self._transport = transport
        self._content = content
        self._content_type = content_type

    def get(self, *args, **kwargs):
        self.set_header("Content-Type", self._content_type)
        self.write(self._content)
        self.set_status(200)
