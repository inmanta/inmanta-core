"""
    Copyright 2024 Inmanta

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


    Remote executor framework:
    - spawns executor processes, each for a specific set of code
    - each executor process can run several executors

    Major components:
    - IPC mechanism based on inmanta.protocol.ipc_light
       - ExecutorContext is the remote state store, keeps track of the different executors and connection to the server
       - ExecutorServer main driver of the remote process:
            - handles IPC,
            - manages the connection
             - controls the remote process shutdown
       - ExecutorClient agent side handle of the IPC connection, also receives logs from the remote side
       - Commands: every IPC command has its own class

    - Client side pool management, based on inmanta.agent.resourcepool
        - MPExecutor: agent side representation of
            - an execturor
            - dispaches calls and ensure it inhibits shutdown if calls are in flight
            - implements the external executor.Executor interface
        - MPProcess: agent side representation of
            - it handles a multi-processing process that runs an ExecutorServer
            - it handles the ExecutorClient that connects to the ExecutorServer
            - it ensure proper shutdown and cleanup of the process
            - it handles a pool of MPExecutor
            - if the pool becomes empty, it shuts itself down
            - if the connection drops, it closes all MPExecutors
        - MPPool: agent side representation of
            - pool of MPProcess
            - handles the integration with multi-processing
            - handles the boot-up of MPProcess
            - boots the process into the IPC
        - MPManager: agent side representation of
            - uses a MPPool to hand out MPExecutors
            - implements the external interface executor.ExecutorManager
            - it shuts down old MPExecutors
            - it keeps the number of executor per agent below a certain number

      A mock up of this structure is in `test_resource_pool_stacking`
"""

import asyncio
import collections
import concurrent.futures
import concurrent.futures.thread
import datetime
import functools
import logging
import logging.config
import multiprocessing
import os
import pathlib
import socket
import threading
import typing
import uuid
from asyncio import Future, transports
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable

import inmanta.agent.cache
import inmanta.agent.config
import inmanta.agent.executor
import inmanta.agent.in_process_executor
import inmanta.config
import inmanta.const
import inmanta.env
import inmanta.loader
import inmanta.logging
import inmanta.protocol
import inmanta.protocol.ipc_light
import inmanta.signals
import inmanta.types
import inmanta.util
from inmanta import const, tracing
from inmanta.agent import executor, resourcepool
from inmanta.agent.resourcepool import PoolManager, PoolMember, TPoolID
from inmanta.data.model import ResourceType
from inmanta.protocol.ipc_light import (
    FinalizingIPCClient,
    IPCMethod,
    IPCReplyFrame,
    IPCServer,
    LogReceiver,
    LogShipper,
    ReturnType,
)
from inmanta.util import join_threadpools
from setproctitle import setproctitle

LOGGER = logging.getLogger(__name__)


class ExecutorContext:
    """The context object used by the executor to expose state to the incoming calls"""

    client: typing.Optional[inmanta.protocol.SessionClient]
    venv: typing.Optional[inmanta.env.VirtualEnv]
    environment: uuid.UUID
    executors: dict[str, "inmanta.agent.in_process_executor.InProcessExecutor"] = {}

    def __init__(self, server: "ExecutorServer", environment: uuid.UUID) -> None:
        self.server = server
        self.threadpool = concurrent.futures.thread.ThreadPoolExecutor()
        self.environment = environment
        self.name = server.name

    def get(self, name: str) -> "inmanta.agent.in_process_executor.InProcessExecutor":
        return self.executors[name]

    # We have no join here yet, don't know if we need it
    async def init_for(self, name: str, uri: str) -> None:
        LOGGER.info("Starting for %s", name)
        if name in self.executors:
            LOGGER.info("Waiting for old executor %s to shutdown", name)
            # We existed before
            old_one = self.executors[name]
            # But were stopped
            assert old_one.is_stopped()
            # Make sure old one is down
            finalizer: list[ThreadPoolExecutor] = []
            old_one.join(finalizer)
            await join_threadpools(finalizer)

        loop = asyncio.get_running_loop()
        parent_logger = logging.getLogger("agent.executor")
        assert self.client  # mypy
        # Setup agent instance
        executor = inmanta.agent.in_process_executor.InProcessExecutor(
            agent_name=name,
            agent_uri=uri,
            environment=self.environment,
            client=self.client,
            eventloop=loop,
            parent_logger=parent_logger,
        )
        self.executors[name] = executor

    async def stop_for(self, name: str) -> None:
        try:
            LOGGER.info("Stopping for %s", name)
            self.get(name).stop()
        except Exception:
            LOGGER.exception("Stop failed for %s", name)

    async def stop(self) -> None:
        """Request the executor to stop"""
        for my_executor in self.executors.values():
            my_executor.stop()
        # TODO: no join here either
        # threadpool finalizer is not used, we expect threadpools to be terminated with the process
        # self.executor.join([])
        await self.server.stop()


class ExecutorServer(IPCServer[ExecutorContext]):
    """The IPC server running on the executor

    When connected, this server will capture all logs and transport them to the remote side

    Shutdown sequence and responses

    1. Client: send stop to serverside
    2. Server: drop the connection (will drain the buffer)
    3a. Server: connection_lost is called, drop out of ioloop, exit process
    3b. Client: connection_lost calls into force_stop
    4.  Client: send term / join with timeout of grace_time / send kill / join
    5.  Client: clean up process

    Scenarios
    Server side stops: go to 3b immediately
    Client side stops: ?
    Pipe break: go to 3a and 3b
    """

    def __init__(self, name: str, environment: uuid.UUID, logger: logging.Logger, take_over_logging: bool = True) -> None:
        """
        :param take_over_logging: when we are connected and are able to stream logs, do we remove all other log handlers?
        """
        super().__init__(name)
        self.environment = environment

        # State machine
        self.stopping = False
        self.stopped = asyncio.Event()

        # logging
        self.log_transport: typing.Optional[LogShipper] = None
        self.take_over_logging = take_over_logging
        self.logger = logger

        # sub executors
        self.ctx = ExecutorContext(self, environment)

        # venc keep alive
        # This interval and this task will be initialized when the InitCommand is received, see usage of `venv_cleanup_task`.
        # We set this to `None` as this field will be used to ensure that the InitCommand is only called once
        self.timer_venv_scheduler_interval: typing.Optional[float] = None
        # We keep a reference to the periodic cleanup task to prevent it
        # from disappearing mid-execution https://docs.python.org/3.11/library/asyncio-task.html#creating-tasks
        self.venv_cleanup_task: typing.Optional[asyncio.Task[None]] = None

    def ainit(self, timer_venv_scheduler_interval: float) -> None:
        """Second stage init, once the eventloop is present"""
        self.timer_venv_scheduler_interval = timer_venv_scheduler_interval
        self.venv_cleanup_task = asyncio.create_task(self.start_timer_venv_checkup())

    def set_status(self, status: str) -> None:
        """Update the process name to reflect the identity and status of this executor"""
        set_executor_status(self.name, status)

    def connection_made(self, transport: transports.Transport) -> None:
        super().connection_made(transport)

        # Second stage logging setup
        # Take over logger to ship to remote
        if self.take_over_logging:
            # Remove all loggers
            root_logger = logging.root
            for handler in root_logger.handlers:
                root_logger.removeHandler(handler)

        self.log_transport = LogShipper(self, asyncio.get_running_loop())
        logging.getLogger().addHandler(self.log_transport)
        self.logger.info(f"Started executor with PID: {os.getpid()}")
        self.set_status("connected")

    def _detach_log_shipper(self) -> None:
        # Once connection is lost, we want to detach asap to keep the logging clean and efficient
        if self.log_transport:
            logging.getLogger().removeHandler(self.log_transport)

    def get_context(self) -> ExecutorContext:
        return self.ctx

    async def stop(self) -> None:
        """Perform shutdown"""
        # shutdown children
        self._sync_stop()

    def _sync_stop(self) -> None:
        """Actual shutdown, not async"""
        if not self.stopping:
            # detach logger
            self._detach_log_shipper()
            self.logger.info("Stopping")
            self.stopping = True
            assert self.transport is not None  # Mypy
            self.transport.close()

    def connection_lost(self, exc: Exception | None) -> None:
        """We lost connection to the controler, bail out"""
        self._detach_log_shipper()
        self.logger.info("Connection lost", exc_info=exc)
        self.set_status("disconnected")
        # We don't shutdown the sub-executors, but we just drop dead.
        self._sync_stop()
        self.stopped.set()
        self.log_transport = None

    async def start_timer_venv_checkup(self) -> None:
        if self.timer_venv_scheduler_interval is None:
            return

        while not self.stopping:
            await self.touch_inmanta_venv_status()
            if not self.stopping:
                await asyncio.sleep(self.timer_venv_scheduler_interval)

    async def touch_inmanta_venv_status(self) -> None:
        """
        Touch the `inmanta_venv_status` file.
        """
        # makes mypy happy
        assert self.ctx.venv is not None
        (pathlib.Path(self.ctx.venv.env_path) / const.INMANTA_VENV_STATUS_FILENAME).touch()


class ExecutorClient(FinalizingIPCClient[ExecutorContext], LogReceiver):
    def __init__(self, name: str):
        super().__init__(name)

        # Keeps track of when this client was active last
        self.last_used_at: datetime.datetime = datetime.datetime.now().astimezone()

    def get_idle_time(self) -> datetime.timedelta:
        return datetime.datetime.now().astimezone() - self.last_used_at

    @typing.overload
    def call(
        self, method: IPCMethod[ExecutorContext, ReturnType], has_reply: typing.Literal[True] = True
    ) -> Future[ReturnType]: ...

    @typing.overload
    def call(self, method: IPCMethod[ExecutorContext, ReturnType], has_reply: typing.Literal[False]) -> None: ...

    @typing.overload
    def call(self, method: IPCMethod[ExecutorContext, ReturnType], has_reply: bool = True) -> Future[ReturnType] | None: ...

    def call(self, method: IPCMethod[ExecutorContext, ReturnType], has_reply: bool = True) -> Future[ReturnType] | None:
        """Call a method with given arguments"""
        self.last_used_at = datetime.datetime.now().astimezone()
        response = super().call(method, has_reply)
        assert response is None or isinstance(response, Future)
        return response

    def has_outstanding_calls(self) -> bool:
        """Is this client still waiting for replies"""
        return len(self.requests) > 0

    def process_reply(self, frame: IPCReplyFrame) -> None:
        super().process_reply(frame)
        self.last_used_at = datetime.datetime.now().astimezone()


class StopCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):
    """Stop the executor process"""

    async def call(self, context: ExecutorContext) -> None:
        await context.stop()


class StopCommandFor(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):
    """Stop one specific executor"""

    def __init__(self, name: str) -> None:
        self.name = name

    async def call(self, context: ExecutorContext) -> None:
        await context.stop_for(self.name)


class InitCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, typing.Sequence[inmanta.loader.FailedModuleSource]]):
    """
    Initialize the executor process:
    1. setup the client, using the session id of the agent
    2. activate the venv created for this executor
    3. load additional source files

    :return: module source we could not load
    """

    def __init__(
        self,
        venv_path: str,
        storage_folder: str,
        session_gid: uuid.UUID,
        sources: list[inmanta.loader.ModuleSource],
        venv_touch_interval: float = 60.0,
    ):
        """
        :param venv_touch_interval: The time interval after which the virtual environment must be touched. Only used for
            testing. The default value is set to 60.0. It should not be used except for testing purposes. It can be
            overridden to speed up the tests
        """
        self.venv_path = venv_path
        self.storage_folder = storage_folder
        self.gid = session_gid
        self.sources = sources
        self._venv_touch_interval = venv_touch_interval

    async def call(self, context: ExecutorContext) -> typing.Sequence[inmanta.loader.FailedModuleSource]:
        assert context.server.timer_venv_scheduler_interval is None, "InitCommand should be only called once!"

        loop = asyncio.get_running_loop()
        parent_logger = logging.getLogger("agent.executor")
        logger = parent_logger.getChild(context.name)

        context.server.ainit(self._venv_touch_interval)

        # setup client
        context.client = inmanta.protocol.SessionClient("agent", self.gid)

        # activate venv
        context.venv = inmanta.env.VirtualEnv(self.venv_path)
        context.venv.use_virtual_env()

        # Download and load code
        loader = inmanta.loader.CodeLoader(self.storage_folder)

        sync_client = inmanta.protocol.SyncClient(client=context.client, ioloop=loop)
        sources = [s.with_client(sync_client) for s in self.sources]

        failed: list[inmanta.loader.FailedModuleSource] = []
        in_place: list[inmanta.loader.ModuleSource] = []
        # First put all files on disk
        for module_source in sources:
            try:
                await loop.run_in_executor(context.threadpool, functools.partial(loader.install_source, module_source))
                in_place.append(module_source)
            except Exception as e:
                logger.info("Failed to load sources: %s", module_source, exc_info=True)
                failed.append(
                    inmanta.loader.FailedModuleSource(
                        module_source=module_source,
                        exception=e,
                    )
                )

        # then try to import them
        for module_source in in_place:
            try:
                await loop.run_in_executor(
                    context.threadpool,
                    functools.partial(loader._load_module, module_source.name, module_source.hash_value, require_reload=False),
                )
            except Exception as e:
                logger.info("Failed to load sources: %s", module_source, exc_info=True)
                failed.append(
                    inmanta.loader.FailedModuleSource(
                        module_source=module_source,
                        exception=e,
                    )
                )

        return failed


class InitCommandFor(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):
    """Initialize one executor"""

    def __init__(self, name: str, uri: str) -> None:
        self.name = name
        self.uri = uri

    async def call(self, context: ExecutorContext) -> None:
        await context.init_for(self.name, self.uri)


class OpenVersionCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):
    """Open a cache version in an executor"""

    def __init__(self, agent_name: str, version: int) -> None:
        self.version = version
        self.agent_name = agent_name

    async def call(self, context: ExecutorContext) -> None:
        await context.get(self.agent_name).open_version(self.version)


class CloseVersionCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):
    """Close a cache version in an executor"""

    def __init__(self, agent_name: str, version: int) -> None:
        self.version = version
        self.agent_name = agent_name

    async def call(self, context: ExecutorContext) -> None:
        await context.get(self.agent_name).close_version(self.version)


class DryRunCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):
    """Run a dryrun in an executor"""

    def __init__(
        self,
        agent_name: str,
        resources: typing.Sequence["inmanta.agent.executor.ResourceDetails"],
        dry_run_id: uuid.UUID,
    ) -> None:
        self.agent_name = agent_name
        self.resources = resources
        self.dry_run_id = dry_run_id

    async def call(self, context: ExecutorContext) -> None:
        await context.get(self.agent_name).dry_run(self.resources, self.dry_run_id)


class ExecuteCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):
    """Run a deploy in an executor"""

    def __init__(
        self,
        agent_name: str,
        gid: uuid.UUID,
        resource_details: "inmanta.agent.executor.ResourceDetails",
        reason: str,
    ) -> None:
        self.agent_name = agent_name
        self.gid = gid
        self.resource_details = resource_details
        self.reason = reason

    async def call(self, context: ExecutorContext) -> None:
        await context.get(self.agent_name).execute(self.gid, self.resource_details, self.reason)


class FactsCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, inmanta.types.Apireturn]):
    """Get facts from in an executor"""

    def __init__(self, agent_name: str, resource: "inmanta.agent.executor.ResourceDetails") -> None:
        self.agent_name = agent_name
        self.resource = resource

    async def call(self, context: ExecutorContext) -> inmanta.types.Apireturn:
        return await context.get(self.agent_name).get_facts(self.resource)


def set_executor_status(name: str, status: str) -> None:
    """Update the process name to reflect the identity and status of the executor"""
    # Lives outside the ExecutorServer class, so we can set status early in the boot process
    setproctitle(f"inmanta: executor {name} - {status}")


def mp_worker_entrypoint(
    socket: socket.socket,
    name: str,
    environment: uuid.UUID,
    log_level: int,
    cli_log: bool,
    config: typing.Mapping[str, typing.Mapping[str, typing.Any]],
) -> None:
    """Entry point for child processes"""

    set_executor_status(name, "connecting")
    # Set up logging stage 1
    # Basic config, starts on std.out
    config_builder = inmanta.logging.LoggingConfigBuilder()
    logger_config: inmanta.logging.FullLoggingConfig = config_builder.get_bootstrap_logging_config(python_log_level=log_level)
    logger_config.apply_config()
    logging.captureWarnings(True)

    # Set up our own logger
    logger = logging.getLogger(f"agent.executor.{name}")

    # Load config
    inmanta.config.Config.load_config_from_dict(config)

    # Make sure logfire is configured correctly
    tracing.configure_logfire("agent.executor")

    async def serve() -> None:
        loop = asyncio.get_running_loop()
        # Start serving
        # also performs setup of log shipper
        # this is part of stage 2 logging setup
        transport, protocol = await loop.connect_accepted_socket(
            functools.partial(ExecutorServer, name, environment, logger, not cli_log), socket
        )
        inmanta.signals.setup_signal_handlers(protocol.stop)
        await protocol.stopped.wait()

    # Async init
    asyncio.run(serve())
    logger.info(f"Stopped with PID: {os.getpid()}")
    exit(0)


class MPProcess(PoolManager[executor.ExecutorId, executor.ExecutorId, "MPExecutor"], PoolMember[executor.ExecutorBlueprint]):
    """

    Physical process proxy, hands out child executors

    Termination scenarios:
    - connection loss:
       - all outstand calls fail, future calls fail as well
       - signal parent to drop this instance and all its children from the cache
       - clean up using _force_stop
    - no more children
       - send stop to remote end
       - wait for connection loss
    - termination request from parent
       - send stop to children
    """

    def __init__(
        self,
        name: str,
        process: multiprocessing.Process,
        connection: ExecutorClient,
        executor_blueprint: executor.ExecutorBlueprint,
        venv: executor.ExecutorVirtualEnvironment,
    ):
        PoolMember.__init__(self, executor_blueprint)
        PoolManager.__init__(self)

        self.name = name

        self.process = process
        self.connection = connection
        self.connection.finalizers.append(self.connection_lost)

        self.termination_lock = threading.Lock()

        # Pure for debugging purpose
        self.executor_blueprint = executor_blueprint  # TODO: duplicates my_id
        self.executor_virtual_env = venv

        # Set by init and parent class that const
        self.failed_resource_results: typing.Sequence[inmanta.loader.FailedModuleSource] = list()

    def my_name(self) -> str:
        return f"Executor Process {self.name} for PID {self.process.pid}"  # TODO: align with PS listing name

    def render_id(self, member_id: "ExecutorId") -> str:
        return f"Executor for {member_id.agent_name}"

    def get_lock_name_for(self, member_id: executor.ExecutorId) -> str:
        return member_id.identity()

    def _id_to_internal(self, ext_id: executor.ExecutorBlueprint) -> executor.ExecutorBlueprint:
        return ext_id

    async def connection_lost(self) -> None:
        # Setting is_stopping causes us not to send out stop commands
        self.is_stopping = True
        # eagerly terminate children
        # Setting is_stopping on the children shortcuts their normal termination
        # This may loop back here via the child_closed callback when the last child is removed
        # Cycle will be broken on self.close()
        for child in list(self.pool.values()):
            await child.set_shutdown()
        # wait for close
        await self.join_process()

    async def join_process(self, grace_time: float = inmanta.const.EXECUTOR_GRACE_HARD) -> None:
        """
        Stop by process close

        This method will never raise an exeption, but log it instead.
        """
        self.is_stopping = True
        if not self.shut_down:
            await asyncio.get_running_loop().run_in_executor(None, functools.partial(self._join_process, grace_time))
            # todo: manage threadpool
        await self.set_shutdown()

    def _join_process(self, grace_time: float) -> None:
        """
        This method will never raise an exeption, but log it instead, as it is used as a finalizer

        Should be called from the async variant above
        """
        if self.shut_down:
            return
        with self.termination_lock:
            # This code doesn't work when two threads go through it
            # Multiprocessing it too brittle for that
            if self.shut_down:
                return
            try:

                if self.process.exitcode is None:
                    # Running
                    self.process.join(grace_time)

                if self.process.exitcode is None:
                    LOGGER.warning(
                        "%s didn't stop after timeout of %d seconds. Killing it.",
                        self.my_name(),
                        grace_time,
                    )
                    # still running! Be a bit more firm
                    self.process.kill()
                    self.process.join()
                self.process.close()
            except ValueError as e:
                if "process object is closed" in str(e):
                    # process already closed
                    # raises a value error, so we also check the message
                    pass
                else:
                    LOGGER.warning(
                        "%s and pid %s failed to shutdown.",
                        self.my_name(),
                        self.process.pid,
                        exc_info=True,
                    )
            except Exception:
                LOGGER.warning(
                    "%s and pid %s failed to shutdown.",
                    self.my_name(),
                    self.process.pid,
                    exc_info=True,
                )

    async def request_shutdown(self) -> None:
        if not self.shutting_down:
            self.shutting_down = True
            await PoolMember.request_shutdown(self)
            self.connection.call(StopCommand(), False)

        # At the moment, we don't eagery terminate the children here yet, we wait for connection to drop

    async def notify_member_shutdown(self, pool_member: "MPExecutor") -> bool:
        result = await super().notify_member_shutdown(pool_member)
        if len(self.pool) == 0:
            await self.request_shutdown()
        return result

    async def join(self, timeout: float = inmanta.const.EXECUTOR_GRACE_HARD) -> None:
        if self.shut_down:
            return
        await self.join_process()

    async def create_member(self, executor_id: executor.ExecutorId) -> "MPExecutor":
        member = MPExecutor(self, executor_id)
        await member.start()
        return member


class MPExecutor(executor.Executor, resourcepool.PoolMember[executor.ExecutorId]):
    """A Single Child Executor

    termination:
    - stop requested by parent:
      - send stop to remote end
      - signal parent we are stopped
    - stop by timer
      - send stop to remote end
      - signal parent we are stopped

    """

    def __init__(
        self,
        process: MPProcess,
        executor_id: executor.ExecutorId,
    ):
        super().__init__(executor_id)

        self.name = executor_id.agent_name
        self.process = process

        # connection stats
        self.in_flight = 0

        # close_task
        self.stop_task: Awaitable[None]

        # Set by init and parent class that const
        self.failed_resource_results: typing.Sequence[inmanta.loader.FailedModuleSource] = process.failed_resource_results
        self.failed_resources: executor.FailedResources = {}

    async def call(self, method: IPCMethod[ExecutorContext, ReturnType]) -> ReturnType:
        try:
            self.in_flight += 1
            out = await self.process.connection.call(method)
            self.last_used_at = datetime.datetime.now().astimezone()
            return out
        finally:
            self.in_flight -= 1

    async def start(self):
        await self.call(InitCommandFor(self.name, self.id.agent_uri))

    async def request_shutdown(self) -> None:
        """Stop by shutdown"""
        if self.shutting_down:
            return
        await super().request_shutdown()

        async def inner_close() -> None:
            try:
                self.process.connection.call(StopCommandFor(self.name))
            except inmanta.protocol.ipc_light.ConnectionLost:
                # Already gone
                pass
            await self.set_shutdown()

        self.stop_task = asyncio.create_task(inner_close())

    def can_be_cleaned_up(self) -> bool:
        return self.in_flight == 0

    async def close_version(self, version: int) -> None:
        await self.call(CloseVersionCommand(self.id.agent_name, version))

    async def open_version(self, version: int) -> None:
        await self.call(OpenVersionCommand(self.id.agent_name, version))

    async def dry_run(
        self,
        resources: typing.Sequence["inmanta.agent.executor.ResourceDetails"],
        dry_run_id: uuid.UUID,
    ) -> None:
        await self.call(DryRunCommand(self.id.agent_name, resources, dry_run_id))

    async def execute(
        self,
        gid: uuid.UUID,
        resource_details: "inmanta.agent.executor.ResourceDetails",
        reason: str,
    ) -> None:
        await self.call(ExecuteCommand(self.id.agent_name, gid, resource_details, reason))

    async def get_facts(self, resource: "inmanta.agent.executor.ResourceDetails") -> inmanta.types.Apireturn:
        return await self.call(FactsCommand(self.id.agent_name, resource))

    async def join(self) -> None:
        assert self.shutting_down
        await self.stop_task


class MPPool(resourcepool.PoolManager[executor.ExecutorBlueprint, executor.ExecutorBlueprint, MPProcess]):

    def __init__(
        self,
        thread_pool: concurrent.futures.thread.ThreadPoolExecutor,
        session_gid: uuid.UUID,
        environment: uuid.UUID,
        log_folder: str,
        storage_folder: str,
        log_level: int = logging.INFO,
        cli_log: bool = False,
    ) -> None:
        """
        :param thread_pool:  threadpool to perform work on
        :param session_gid: agent session id, used to connect to the server, the agent should keep this alive
        :param environment: the inmanta environment we are deploying for
        :param log_folder: folder to place log files for the executors
        :param storage_folder: folder to place code files
        :param log_level: log level for the executors
        :param cli_log: do we also want to echo the log to std_err

        """
        super().__init__()
        self.init_once()

        # Can be overriden in tests
        self.venv_checkup_interval: float = 60.0

        self.thread_pool = thread_pool

        self.environment = environment
        self.session_gid = session_gid

        # on disk
        self.log_folder = log_folder
        self.storage_folder = storage_folder
        os.makedirs(self.log_folder, exist_ok=True)
        os.makedirs(self.storage_folder, exist_ok=True)
        venv_dir = pathlib.Path(self.storage_folder) / "venv"
        venv_dir.mkdir(exist_ok=True)

        # Env manager
        self.environment_manager = inmanta.agent.executor.VirtualEnvironmentManager(str(venv_dir.absolute()), self.thread_pool)

        # logging
        self.log_level = log_level
        self.cli_log = cli_log

    def my_name(self) -> str:
        return "Process pool"

    def render_id(self, member: executor.ExecutorBlueprint) -> str:
        return "Process for code hash: " + member.blueprint_hash()

    @classmethod
    def init_once(cls) -> None:
        try:
            multiprocessing.set_start_method("forkserver")
            # Load common modules
            # Including this one
            multiprocessing.set_forkserver_preload(["inmanta.config", __name__, "inmanta.agent._set_fork_server_process_name"])
        except RuntimeError:
            # already set
            pass

    async def start(self) -> None:
        await super().start()
        # We need to do this here, otherwise, the scheduler would crash because no event loop would be running
        await self.environment_manager.start()

    async def stop(self) -> None:
        await self.request_shutdown()

    async def request_shutdown(self) -> None:
        await super().request_shutdown()
        await asyncio.gather(*(self.request_member_shutdown(child) for child in self.pool.values()))
        await self.environment_manager.request_shutdown()

    async def join(self) -> None:
        await super().join()
        await self.environment_manager.join()
        await asyncio.gather(*(child.join() for child in self.pool.values()))

    def _id_to_internal(self, ext_id: executor.ExecutorBlueprint) -> executor.ExecutorBlueprint:
        return ext_id

    async def create_member(self, blueprint: executor.ExecutorBlueprint) -> MPProcess:
        # TODO: logging
        # LOGGER.info("Creating executor for agent %s with id %s", executor_id.agent_name, executor_id.identity())
        venv = await self.environment_manager.get_environment(blueprint.to_env_blueprint())
        executor = await self.make_child_and_connect(blueprint, venv)
        # LOGGER.debug(
        #     "Child forked (pid: %s) for executor for agent %s with id %s",
        #     executor.process.pid,
        #     executor_id.agent_name,
        #     executor_id.identity(),
        # )
        storage_for_blueprint = os.path.join(self.storage_folder, "code", blueprint.blueprint_hash())
        os.makedirs(storage_for_blueprint, exist_ok=True)
        failed_types = await executor.connection.call(
            InitCommand(
                venv.env_path,
                storage_for_blueprint,
                self.session_gid,
                [x.for_transport() for x in blueprint.sources],
                self.venv_checkup_interval,
            )
        )
        # LOGGER.debug(
        #     "Child initialized (pid: %s) for executor for agent %s with id %s",
        #     executor.process.pid,
        #     executor_id.agent_name,
        #     executor_id.identity(),
        # )
        executor.failed_resource_results = failed_types
        return executor

    async def make_child_and_connect(
        self, executor_id: executor.ExecutorBlueprint, venv: executor.ExecutorVirtualEnvironment
    ) -> MPProcess:
        """Async code to make a child process and share a socket with it"""
        loop = asyncio.get_running_loop()
        name = executor_id.blueprint_hash()  # TODO

        # Start child
        process, parent_conn = await loop.run_in_executor(
            self.thread_pool, functools.partial(self._make_child, name, self.environment, self.log_level, self.cli_log)
        )
        # Hook up the connection
        transport, protocol = await loop.connect_accepted_socket(
            functools.partial(ExecutorClient, f"executor.{name}"), parent_conn
        )

        child_handle = MPProcess(name, process, protocol, executor_id, venv)
        return child_handle

    def _make_child(
        self, name: str, environment: uuid.UUID, log_level: int, cli_log: bool
    ) -> tuple[multiprocessing.Process, socket.socket]:
        """Sync code to make a child process and share a socket with it"""
        parent_conn, child_conn = socket.socketpair()
        # Fork an ExecutorServer
        p = multiprocessing.Process(
            target=mp_worker_entrypoint,
            args=(child_conn, name, environment, log_level, cli_log, inmanta.config.Config.config_as_dict()),
            name=f"agent.executor.{name}",
        )
        p.start()
        child_conn.close()

        return p, parent_conn

    def get_lock_name_for(self, member_id: executor.ExecutorBlueprint) -> str:
        return member_id.blueprint_hash()


# `executor.PoolManager` needs to be before `executor.ExecutorManager` as it defines the start and stop methods (MRO order)
class MPManager(
    resourcepool.TimeBasedPoolManager[executor.ExecutorId, executor.ExecutorId, MPExecutor],
    executor.ExecutorManager[MPExecutor],
):
    """
    This is the executor that provides the new behavior (ISO8+),
    where the agent forks executors in specific venvs to prevent code reloading.

    This class has a two layer cache:
      blueprint -> process
      executor_id -> executor

    Executors are co-hosted on processes if they share a blueprint
    """

    def __init__(
        self,
        thread_pool: concurrent.futures.thread.ThreadPoolExecutor,
        session_gid: uuid.UUID,
        environment: uuid.UUID,
        log_folder: str,
        storage_folder: str,
        log_level: int = logging.INFO,
        cli_log: bool = False,
    ) -> None:
        """
        :param thread_pool:  threadpool to perform work on
        :param session_gid: agent session id, used to connect to the server, the agent should keep this alive
        :param environment: the inmanta environment we are deploying for
        :param log_folder: folder to place log files for the executors
        :param storage_folder: folder to place code files
        :param log_level: log level for the executors
        :param cli_log: do we also want to echo the log to std_err

        """
        super().__init__(
            retention_time=inmanta.agent.config.agent_executor_retention_time.get(),
        )

        self.process_pool = MPPool(thread_pool, session_gid, environment, log_folder, storage_folder, log_level, cli_log)

        self.environment = environment

        self.agent_map: dict[str, set[MPExecutor]] = collections.defaultdict(set)
        # cleanup
        self.max_executors_per_agent = inmanta.agent.config.agent_executor_cap.get()

    def get_lock_name_for(self, member_id: executor.ExecutorId) -> str:
        return member_id.identity()

    def _id_to_internal(self, ext_id: executor.ExecutorBlueprint) -> executor.ExecutorBlueprint:
        return ext_id

    def render_id(self, member: executor.ExecutorId) -> str:
        return f"Executor for {member.agent_name}"

    def my_name(self) -> str:
        return "Executor Manager"

    async def get_executor(
        self,
        agent_name: str,
        agent_uri: str,
        code: typing.Collection[executor.ResourceInstallSpec],
    ) -> MPExecutor:
        """
        Retrieves an Executor for a given agent with the relevant handler code loaded in its venv.
        If an Executor does not exist for the given configuration, a new one is created.

        :param agent_name: The name of the agent for which an Executor is being retrieved or created.
        :param agent_uri: The name of the host on which the agent is running.
        :param code: Collection of ResourceInstallSpec defining the configuration for the Executor i.e.
            which resource types it can act on and all necessary information to install the relevant
            handler code in its venv.
        :param venv_checkup_interval: The time interval after which the virtual environment must be touched. Only used for
            testing. The default value is set to 60.0. It should not be used except for testing purposes. It can be
            It can be overridden to speed up the tests
        :return: An Executor instance
        """
        blueprint = executor.ExecutorBlueprint.from_specs(code)
        executor_id = executor.ExecutorId(agent_name, agent_uri, blueprint)

        my_executor = await self.get(executor_id)

        if my_executor.failed_resource_results and not my_executor.failed_resources:
            # If some code loading failed, resolve here
            # reverse index
            type_for_spec: dict[inmanta.loader.ModuleSource, list[ResourceType]] = collections.defaultdict(list)
            for spec in code:
                for source in spec.blueprint.sources:
                    type_for_spec[source].append(spec.resource_type)
            # resolve
            for failed_resource_result in my_executor.failed_resource_results:
                for rtype in type_for_spec.get(failed_resource_result.module_source, []):
                    if rtype not in my_executor.failed_resources:
                        my_executor.failed_resources[rtype] = failed_resource_result.exception

        # FIXME: recovery. If loading failed, we currently never rebuild https://github.com/inmanta/inmanta-core/issues/7695
        return my_executor

    async def create_member(self, executor_id: executor.ExecutorId) -> MPExecutor:
        process = await self.process_pool.get(executor_id.blueprint)
        # TODO: we have a race here: the process can become empty between these two calls
        result = await process.get(executor_id)
        self.agent_map.get(executor_id.agent_name).add(result)
        return result

    async def notify_member_shutdown(self, pool_member: MPExecutor) -> bool:
        self.agent_map.get(pool_member.get_id().agent_name).discard(pool_member)
        return await super().notify_member_shutdown(pool_member)

    async def pre_create_capacity_check(self, member_id: executor.ExecutorId) -> None:
        executors = [executor for executor in self.agent_map[member_id.agent_name] if executor.running]

        n_executors_for_agent = len(executors)
        if n_executors_for_agent >= self.max_executors_per_agent:
            # Close oldest executor:
            oldest_executor = min(executors, key=lambda e: e.last_used)
            LOGGER.debug(
                f"Reached executor cap for agent {member_id.agent_name}. Stopping oldest executor "
                f"{member_id.identity()} to make room for a new one."
            )

            await self.request_member_shutdown(oldest_executor)

    async def start(self) -> None:
        await super().start()
        # We need to do this here, otherwise, the scheduler would crash because no event loop would be running
        await self.process_pool.start()

    async def stop(self) -> None:
        await self.request_shutdown()

    async def request_shutdown(self) -> None:
        await self.process_pool.request_shutdown()
        await super().request_shutdown()

    async def join(self) -> None:
        await super().join()
        await self.process_pool.join()

    async def stop_for_agent(self, agent_name: str) -> list[MPExecutor]:
        children = list(self.agent_map[agent_name])
        await asyncio.gather(*(self.request_member_shutdown(child) for child in children))
        return children
