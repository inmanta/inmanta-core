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
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Mapping, Optional

from tornado import routing, web

from inmanta.data.model import ExtensionStatus, ReportedStatus, SliceStatus
from inmanta.protocol import Client, Result, TypedClient, common, endpoints, handle, methods, methods_v2
from inmanta.protocol.rest import server
from inmanta.server import SLICE_TRANSPORT
from inmanta.types import ArgumentTypes
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


# Server Side
class Server(endpoints.Endpoint):
    def __init__(self, connection_timout: int = 120) -> None:
        super().__init__("server")
        self._slices: dict[str, ServerSlice] = {}
        self._slice_sequence: Optional[list[ServerSlice]] = None
        self._handlers: list[routing.Rule] = []
        self.connection_timout = connection_timout

        self._transport = server.RESTServer(self, self.id)
        self.add_slice(TransportSlice(self))
        self.running = False

    def add_slice(self, slice: "ServerSlice") -> None:
        """
        Add new endpoints to this rest transport
        """
        self._slices[slice.name] = slice
        self._slice_sequence = None
        self.add_call_target(slice)

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


class ServerSlice(common.CallTarget, TaskHandler[Result | None]):
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
        response = await inmanta.protocol.rest.execute_call(method_config, spec.body, spec.headers)
        return common.typed_process_response(method_properties, common.Result(code=response.status_code, result=response.body))
