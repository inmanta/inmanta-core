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
import socket
import typing
import uuid
from asyncio import transports
from datetime import timedelta

import inmanta.agent.cache
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
import inmanta.util
from inmanta import util
from inmanta.agent import executor
from inmanta.data.model import ResourceType
from inmanta.protocol.ipc_light import FinalizingIPCClient, IPCServer, LogReceiver, LogShipper
from inmanta.util import IntervalSchedule
from setproctitle import setproctitle

LOGGER = logging.getLogger(__name__)


class ExecutorContext:
    """The context object used by the executor to expose state to the incoming calls"""

    client: typing.Optional[inmanta.protocol.SessionClient]
    venv: typing.Optional[inmanta.env.VirtualEnv]
    name: str
    executor: typing.Optional["inmanta.agent.in_process_executor.InProcessExecutor"]

    def __init__(self, server: "ExecutorServer") -> None:
        self.server = server
        self.threadpool = concurrent.futures.thread.ThreadPoolExecutor()
        self.name = server.name

    async def stop(self) -> None:
        """Request the executor to stop"""
        if self.executor:
            self.executor.stop()
        await self.server.stop()
        if self.executor:
            # threadpool finalizer is not used, we expect threadpools to be terminated with the process
            self.executor.join([])


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

    def __init__(self, name: str, logger: logging.Logger, take_over_logging: bool = True) -> None:
        """
        :param take_over_logging: when we are connected and are able to stream logs, do we remove all other log handlers?
        """
        super().__init__(name)
        self.stopping = False
        self.stopped = asyncio.Event()
        self.ctx = ExecutorContext(self)
        self.log_transport: typing.Optional[LogShipper] = None
        self.take_over_logging = take_over_logging
        self.logger = logger

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
            self.log_transport = None

    def get_context(self) -> ExecutorContext:
        return self.ctx

    async def stop(self) -> None:
        """Perform shutdown"""
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
        self._sync_stop()
        self.stopped.set()


class ExecutorClient(FinalizingIPCClient[ExecutorContext], LogReceiver):
    pass


class StopCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):
    async def call(self, context: ExecutorContext) -> None:
        await context.stop()


class InitCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, typing.Sequence[inmanta.loader.ModuleSource]]):
    """
    Initialize the executor:
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
        environment: uuid.UUID,
        uri: str,
    ):
        self.venv_path = venv_path
        self.storage_folder = storage_folder
        self.gid = session_gid
        self.sources = sources
        self.environment = environment
        self.uri = uri

    async def call(self, context: ExecutorContext) -> typing.Sequence[inmanta.loader.ModuleSource]:
        loop = asyncio.get_running_loop()
        parent_logger = logging.getLogger("agent.executor")
        logger = parent_logger.getChild(context.name)

        # setup client
        context.client = inmanta.protocol.SessionClient("agent", self.gid)

        # Setup agent instance
        context.executor = inmanta.agent.in_process_executor.InProcessExecutor(
            agent_name=context.name,
            agent_uri=self.uri,
            environment=self.environment,
            client=context.client,
            eventloop=loop,
            parent_logger=parent_logger,
        )

        # activate venv
        context.venv = inmanta.env.VirtualEnv(self.venv_path)
        context.venv.use_virtual_env()

        # Download and load code
        loader = inmanta.loader.CodeLoader(self.storage_folder)

        sync_client = inmanta.protocol.SyncClient(client=context.client, ioloop=loop)
        sources = [s.with_client(sync_client) for s in self.sources]

        failed: list[inmanta.loader.ModuleSource] = []
        in_place: list[inmanta.loader.ModuleSource] = []
        # First put all files on disk
        for module_source in sources:
            try:
                await loop.run_in_executor(context.threadpool, functools.partial(loader.install_source, module_source))
                in_place.append(module_source)
            except Exception:
                logger.info("Failed to load sources: %s", module_source, exc_info=True)
                failed.append(module_source)

        # then try to import them
        for module_source in in_place:
            try:
                await loop.run_in_executor(
                    context.threadpool, functools.partial(loader._load_module, module_source.name, module_source.hash_value)
                )
            except Exception:
                logger.info("Failed to load sources: %s", module_source, exc_info=True)
                failed.append(module_source)

        return failed


class OpenVersionCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):

    def __init__(self, version: int) -> None:
        self.version = version

    async def call(self, context: ExecutorContext) -> None:
        assert context.executor is not None
        await context.executor.open_version(self.version)


class CloseVersionCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):

    def __init__(self, version: int) -> None:
        self.version = version

    async def call(self, context: ExecutorContext) -> None:
        assert context.executor is not None
        await context.executor.close_version(self.version)


class DryRunCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):

    def __init__(
        self,
        resources: typing.Sequence["inmanta.agent.executor.ResourceDetails"],
        dry_run_id: uuid.UUID,
    ) -> None:
        self.resources = resources
        self.dry_run_id = dry_run_id

    async def call(self, context: ExecutorContext) -> None:
        assert context.executor is not None
        await context.executor.dry_run(self.resources, self.dry_run_id)


class ExecuteCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):

    def __init__(
        self,
        gid: uuid.UUID,
        resource_details: "inmanta.agent.executor.ResourceDetails",
        reason: str,
    ) -> None:
        self.gid = gid
        self.resource_details = resource_details
        self.reason = reason

    async def call(self, context: ExecutorContext) -> None:
        assert context.executor is not None
        await context.executor.execute(self.gid, self.resource_details, self.reason)


class FactsCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, inmanta.types.Apireturn]):

    def __init__(self, resource: "inmanta.agent.executor.ResourceDetails") -> None:
        self.resource = resource

    async def call(self, context: ExecutorContext) -> inmanta.types.Apireturn:
        assert context.executor is not None
        return await context.executor.get_facts(self.resource)


def set_executor_status(name: str, status: str) -> None:
    """Update the process name to reflect the identity and status of the executor"""
    # Lives outside the ExecutorServer class, so we can set status early in the boot process
    setproctitle(f"inmanta: executor {name} - {status}")


def mp_worker_entrypoint(
    socket: socket.socket,
    name: str,
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

    async def serve() -> None:
        loop = asyncio.get_running_loop()
        # Start serving
        # also performs setup of log shipper
        # this is part of stage 2 logging setup
        transport, protocol = await loop.connect_accepted_socket(
            functools.partial(ExecutorServer, name, logger, not cli_log), socket
        )
        inmanta.signals.setup_signal_handlers(protocol.stop)
        await protocol.stopped.wait()

    # Async init
    asyncio.run(serve())
    logger.info(f"Stopped with PID: {os.getpid()}")
    exit(0)


class MPExecutor(executor.Executor):
    """A Single Child Executor"""

    def __init__(
        self,
        owner: "MPManager",
        process: multiprocessing.Process,
        connection: FinalizingIPCClient[ExecutorContext],
        executor_id: executor.ExecutorId,
        venv: executor.ExecutorVirtualEnvironment,
    ):
        self.process = process
        self.connection = connection
        self.connection.finalizers.append(self.force_stop)
        self.closing = False
        self.closed = False
        self.owner = owner
        # Pure for debugging purpose
        self.executor_id = executor_id
        self.executor_virtual_env = venv

        # Set by init and parent class that const
        self.failed_resource_sources: typing.Sequence[inmanta.loader.ModuleSource] = list()
        self.failed_resource_types: set[ResourceType] = set()

    async def stop(self) -> None:
        """Stop by shutdown"""
        self.closing = True
        try:
            self.connection.call(StopCommand(), False)
        except inmanta.protocol.ipc_light.ConnectionLost:
            # Already gone
            pass

    async def force_stop(self, grace_time: float = inmanta.const.SHUTDOWN_GRACE_HARD) -> None:
        """Stop by process close"""
        self.closing = True
        await asyncio.get_running_loop().run_in_executor(
            self.owner.thread_pool, functools.partial(self._force_stop, grace_time)
        )

    def _force_stop(self, grace_time: float) -> None:
        if self.closed:
            return
        try:
            self.process.terminate()
            self.process.join(grace_time)
            self.process.kill()
            self.process.join()
        except ValueError:
            # Process already gone:
            pass
        self._set_closed()

    def _set_closed(self) -> None:
        # this code can be raced from the join call and the disconnect handler
        # relying on the GIL to keep us safe
        if not self.closed:
            self.closing = True
            self.closed = True
            self.process.close()
            self.owner._child_closed(self)

    async def join(self, timeout: float) -> None:
        if self.closed:
            return
        try:
            await asyncio.get_running_loop().run_in_executor(
                self.owner.thread_pool, functools.partial(self.process.join, timeout)
            )
            if self.process.exitcode is None:
                LOGGER.warning(
                    "Executor for agent %s with id %s didn't stop after timeout of %d seconds. Killing it.",
                    self.executor_id.agent_name,
                    self.executor_id.identity(),
                    timeout,
                )
                self.process.kill()
                await asyncio.get_running_loop().run_in_executor(
                    self.owner.thread_pool, functools.partial(self.process.join, timeout)
                )
            self._set_closed()
        except ValueError as e:
            if "process object is closed" in str(e):
                # process already closed
                # raises a value error, so we also check the message
                pass
            else:
                raise

    async def close_version(self, version: int) -> None:
        await self.connection.call(CloseVersionCommand(version))

    async def open_version(self, version: int) -> None:
        await self.connection.call(OpenVersionCommand(version))

    async def dry_run(
        self,
        resources: typing.Sequence["inmanta.agent.executor.ResourceDetails"],
        dry_run_id: uuid.UUID,
    ) -> None:
        await self.connection.call(DryRunCommand(resources, dry_run_id))

    async def execute(
        self,
        gid: uuid.UUID,
        resource_details: "inmanta.agent.executor.ResourceDetails",
        reason: str,
    ) -> None:
        await self.connection.call(ExecuteCommand(gid, resource_details, reason))

    async def get_facts(self, resource: "inmanta.agent.executor.ResourceDetails") -> inmanta.types.Apireturn:
        return await self.connection.call(FactsCommand(resource))


class MPManager(executor.ExecutorManager[MPExecutor]):
    """
    This is the executor that provides the new behavior (ISO8+),
    where the agent forks executors in specific venvs to prevent code reloading.
    """

    def __init__(
        self,
        thread_pool: concurrent.futures.thread.ThreadPoolExecutor,
        environment_manager: executor.VirtualEnvironmentManager,
        session_gid: uuid.UUID,
        environment: uuid.UUID,
        log_folder: str,
        storage_folder: str,
        log_level: int = logging.INFO,
        cli_log: bool = False,
    ) -> None:
        """
        :param thread_pool:  threadpool to perform work on
        :param environment_manager: The VirtualEnvironmentManager responsible for managing the virtual environments
        :param session_gid: agent session id, used to connect to the server, the agent should keep this alive
        :param environment: the inmanta environment we are deploying for
        :param log_folder: folder to place log files for the executors
        :param storage_folder: folder to place code files
        :param log_level: log level for the executors
        :param cli_log: do we also want to echo the log to std_err

        """
        self.init_once()
        self.environment = environment
        self.thread_pool = thread_pool
        self.environment_manager = environment_manager
        self.children: list[MPExecutor] = []
        self.log_folder = log_folder
        self.storage_folder = storage_folder
        os.makedirs(self.log_folder, exist_ok=True)
        os.makedirs(self.storage_folder, exist_ok=True)
        self.log_level = log_level
        self.cli_log = cli_log
        self.session_gid = session_gid

        # These maps are cleaned by the close callbacks
        # This means it can contain closing entries
        self.executor_map: dict[executor.ExecutorId, MPExecutor] = {}
        self.agent_map: dict[str, set[executor.ExecutorId]] = collections.defaultdict(set)

        self._locks: inmanta.util.NamedLock = inmanta.util.NamedLock()

        self.executor_retention_time = inmanta.agent.config.executor_retention.get()
        self.max_executors_per_agent = inmanta.agent.config.executor_cap_per_agent.get()

        self._sched = util.Scheduler("MP manager")

        self._sched.add_action(self.cleanup_inactive_executors, IntervalSchedule(2))

    def __add_executor(self, theid: executor.ExecutorId, the_executor: MPExecutor) -> None:
        self.executor_map[theid] = the_executor
        self.agent_map[theid.agent_name].add(theid)

    def __remove_executor(self, the_executor: MPExecutor) -> None:
        theid = the_executor.executor_id
        registered_for_id = self.executor_map.get(theid)
        if registered_for_id is None:
            # Not found
            return
        if registered_for_id != the_executor:
            # We have a stale instance that refused to close before
            # it was replaced and has now gone down
            return
        self.executor_map.pop(theid)
        self.agent_map[theid.agent_name].discard(theid)

    @classmethod
    def init_once(cls) -> None:
        try:
            multiprocessing.set_start_method("forkserver")
            # Load common modules
            # Including this one
            multiprocessing.set_forkserver_preload(["inmanta.config", __name__])
        except RuntimeError:
            # already set
            pass

    async def get_executor(
        self, agent_name: str, agent_uri: str, code: typing.Collection[executor.ResourceInstallSpec]
    ) -> MPExecutor:
        """
        Retrieves an Executor for a given agent with the relevant handler code loaded in its venv.
        If an Executor does not exist for the given configuration, a new one is created.

        :param agent_name: The name of the agent for which an Executor is being retrieved or created.
        :param agent_uri: The name of the host on which the agent is running.
        :param code: Collection of ResourceInstallSpec defining the configuration for the Executor i.e.
            which resource types it can act on and all necessary information to install the relevant
            handler code in its venv.
        :return: An Executor instance
        """
        blueprint = executor.ExecutorBlueprint.from_specs(code)
        executor_id = executor.ExecutorId(agent_name, agent_uri, blueprint)
        if executor_id in self.executor_map:
            it = self.executor_map[executor_id]
            if not it.closing:
                LOGGER.debug("Found existing executor for agent %s with id %s", agent_name, executor_id.identity())
                return it
        # Acquire a lock based on the executor's identity (agent name, agent uri and blueprint hash)
        async with self._locks.get(executor_id.identity()):
            if executor_id in self.executor_map:
                it = self.executor_map[executor_id]
                if not it.closing:
                    LOGGER.debug("Found existing executor for agent %s with id %s", agent_name, executor_id.identity())
                    return it
                else:
                    LOGGER.debug(
                        "Found stale executor for agent %s with id %s, waiting for close", agent_name, executor_id.identity()
                    )
                    await it.join(2.0)
            n_executors_for_agent = len(self.agent_map[executor_id.agent_name])
            if n_executors_for_agent >= self.max_executors_per_agent:
                # Close oldest executor:
                executor_ids = self.agent_map[executor_id.agent_name]
                oldest_executor = min([self.executor_map[id] for id in executor_ids], key=lambda e: e.connection.last_used_at)

                await oldest_executor.stop()

            my_executor = await self.create_executor(executor_id)
            self.__add_executor(executor_id, my_executor)
            if my_executor.failed_resource_sources:
                # If some code loading failed, resolve here
                # reverse index
                type_for_spec: dict[inmanta.loader.ModuleSource, list[ResourceType]] = collections.defaultdict(list)
                for spec in code:
                    for source in spec.blueprint.sources:
                        type_for_spec[source].append(spec.resource_type)
                # resolve
                for source in my_executor.failed_resource_sources:
                    for rtype in type_for_spec.get(source, []):
                        my_executor.failed_resource_types.add(rtype)

            # TODO: recovery. If loading failed, we currently never rebuild
            # https://github.com/inmanta/inmanta-core/issues/7281
            return my_executor

    async def create_executor(self, executor_id: executor.ExecutorId) -> MPExecutor:
        LOGGER.info("Creating executor for agent %s with id %s", executor_id.agent_name, executor_id.identity())
        env_blueprint = executor_id.blueprint.to_env_blueprint()
        venv = await self.environment_manager.get_environment(env_blueprint, self.thread_pool)
        executor = await self.make_child_and_connect(executor_id, venv)
        LOGGER.debug(
            "Child forked (pid: %s) for executor for agent %s with id %s",
            executor.process.pid,
            executor_id.agent_name,
            executor_id.identity(),
        )
        storage_for_blueprint = os.path.join(self.storage_folder, "code", executor_id.blueprint.blueprint_hash())
        os.makedirs(storage_for_blueprint, exist_ok=True)
        failed_types = await executor.connection.call(
            InitCommand(
                venv.env_path,
                storage_for_blueprint,
                self.session_gid,
                [x.for_transport() for x in executor_id.blueprint.sources],
                self.environment,
                executor_id.agent_uri,
            )
        )
        LOGGER.debug(
            "Child initialized (pid: %s) for executor for agent %s with id %s",
            executor.process.pid,
            executor_id.agent_name,
            executor_id.identity(),
        )
        executor.failed_resource_sources = failed_types
        return executor

    async def make_child_and_connect(
        self, executor_id: executor.ExecutorId, venv: executor.ExecutorVirtualEnvironment
    ) -> MPExecutor:
        """Async code to make a child process and share a socket with it"""
        loop = asyncio.get_running_loop()
        name = executor_id.agent_name

        # Start child
        process, parent_conn = await loop.run_in_executor(
            self.thread_pool, functools.partial(self._make_child, name, self.log_level, self.cli_log)
        )
        # Hook up the connection
        transport, protocol = await loop.connect_accepted_socket(
            functools.partial(ExecutorClient, f"executor.{name}"), parent_conn
        )

        child_handle = MPExecutor(self, process, protocol, executor_id, venv)
        self.children.append(child_handle)
        return child_handle

    def _child_closed(self, child_handle: MPExecutor) -> None:
        """Internal, for child to remove itself once stopped"""
        try:
            self.children.remove(child_handle)
            self.__remove_executor(child_handle)
        except ValueError:
            # already gone
            pass

    def _make_child(self, name: str, log_level: int, cli_log: bool) -> tuple[multiprocessing.Process, socket.socket]:
        """Sync code to make a child process and share a socket with it"""
        parent_conn, child_conn = socket.socketpair()
        # Fork an ExecutorServer
        p = multiprocessing.Process(
            target=mp_worker_entrypoint,
            args=(child_conn, name, log_level, cli_log, inmanta.config.Config.config_as_dict()),
            name=f"agent.executor.{name}",
        )
        p.start()
        child_conn.close()

        return p, parent_conn

    async def stop(self) -> None:
        await asyncio.gather(*(child.stop() for child in self.children))

    async def force_stop(self, grace_time: float) -> None:
        await asyncio.gather(*(child.force_stop(grace_time) for child in self.children))

    async def join(self, thread_pool_finalizer: list[concurrent.futures.ThreadPoolExecutor], timeout: float) -> None:
        thread_pool_finalizer.append(self.thread_pool)
        await asyncio.gather(*(child.join(timeout) for child in self.children))

    async def stop_for_agent(self, agent_name: str) -> list[MPExecutor]:
        children_ids = self.agent_map[agent_name]
        children = [self.executor_map[child_id] for child_id in children_ids]
        await asyncio.gather(*(child.stop() for child in children))
        return children

    async def cleanup_inactive_executors(self) -> None:
        now = datetime.datetime.now().astimezone()

        for _executor in self.executor_map.values():
            if now - _executor.connection.last_used_at > timedelta(seconds=self.executor_retention_time):
                await _executor.stop()
