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
import pathlib
import socket
import threading
import typing
import uuid
from asyncio import Future, transports

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
from inmanta.agent import executor
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
        if self.executor:
            # threadpool finalizer is not used, we expect threadpools to be terminated with the process
            self.executor.join([])
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
        # This interval and this task will be initialized when the InitCommand is received, see usage of `venv_cleanup_task`.
        # We set this to `None` as this field will be used to ensure that the InitCommand is only called once
        self.timer_venv_scheduler_interval: typing.Optional[float] = None
        # We keep a reference to the periodic cleanup task to prevent it
        # from disappearing mid-execution https://docs.python.org/3.11/library/asyncio-task.html#creating-tasks
        self.venv_cleanup_task: typing.Optional[asyncio.Task[None]] = None
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

    async def start_timer_venv_checkup(self) -> None:
        if self.timer_venv_scheduler_interval is None:
            return

        while not self.stopping:
            await self.touch_inmanta_venv_status()
            if not self.stopping:
                await asyncio.sleep(self.timer_venv_scheduler_interval)

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
    async def call(self, context: ExecutorContext) -> None:
        await context.stop()


class InitCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, typing.Sequence[inmanta.loader.FailedModuleSource]]):
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
        self.environment = environment
        self.uri = uri
        self._venv_touch_interval = venv_touch_interval

    async def call(self, context: ExecutorContext) -> typing.Sequence[inmanta.loader.FailedModuleSource]:
        assert context.server.timer_venv_scheduler_interval is None, "InitCommand should be only called once!"

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

        context.server.timer_venv_scheduler_interval = self._venv_touch_interval
        context.server.venv_cleanup_task = asyncio.create_task(context.server.start_timer_venv_checkup())

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

    # Make sure logfire is configured correctly
    tracing.configure_logfire("agent.executor")

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


class MPExecutor(executor.Executor, executor.PoolMember):
    """A Single Child Executor"""

    def __init__(
        self,
        owner: "MPManager",
        process: multiprocessing.Process,
        connection: ExecutorClient,
        executor_id: executor.ExecutorId,
        venv: executor.ExecutorVirtualEnvironment,
    ):
        self.process = process
        self.connection = connection
        self.connection.finalizers.append(self.force_stop)
        self.closing = False
        self.closed = False
        self.owner = owner
        self.termination_lock = threading.Lock()
        # Pure for debugging purpose
        self.executor_id = executor_id
        self.executor_virtual_env = venv

        # Set by init and parent class that const
        self.failed_resource_results: typing.Sequence[inmanta.loader.FailedModuleSource] = list()
        self.failed_resources: executor.FailedResources = {}

    async def stop(self) -> None:
        """Stop by shutdown"""
        self.closing = True
        try:
            self.connection.call(StopCommand(), False)
        except inmanta.protocol.ipc_light.ConnectionLost:
            # Already gone
            pass

    async def clean(self) -> None:
        """Stop by shutdown and catch any error that may occur"""
        try:
            await self.stop()
        except Exception:
            LOGGER.exception(
                "Unexpected error during executor %s cleanup:",
                self.executor_id.identity(),
            )

    def can_be_cleaned_up(self, retention_time: int) -> bool:
        if self.connection.has_outstanding_calls():
            return False

        return self.connection.get_idle_time() > datetime.timedelta(seconds=retention_time)

    def get_id(self) -> str:
        return self.executor_id.identity()

    def last_used(self) -> datetime.datetime:
        return self.connection.last_used_at

    async def force_stop(self, grace_time: float = inmanta.const.EXECUTOR_GRACE_HARD) -> None:
        """
        Stop by process close

        This method will never raise an exeption, but log it instead.
        """
        self.closing = True
        await asyncio.get_running_loop().run_in_executor(
            self.owner.thread_pool, functools.partial(self._force_stop, grace_time)
        )

    def _force_stop(self, grace_time: float) -> None:
        """This method will never raise an exeption, but log it instead, as it is used as a finalizer"""
        if self.closed:
            return
        with self.termination_lock:
            # This code doesn't work when two threads go through it
            # Multiprocessing it too brittle for that
            if self.closed:
                return
            try:

                if self.process.exitcode is None:
                    # Running
                    self.process.join(grace_time)

                if self.process.exitcode is None:
                    LOGGER.warning(
                        "Executor for agent %s with id %s didn't stop after timeout of %d seconds. Killing it.",
                        self.executor_id.agent_name,
                        self.executor_id.identity(),
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
                        "Executor for agent %s with id %s and pid %s failed to shutdown.",
                        self.executor_id.agent_name,
                        self.executor_id.identity(),
                        self.process.pid,
                        exc_info=True,
                    )
            except Exception:
                LOGGER.warning(
                    "Executor for agent %s with id %s and pid %s failed to shutdown.",
                    self.executor_id.agent_name,
                    self.executor_id.identity(),
                    self.process.pid,
                    exc_info=True,
                )
            # Discard this executor, even if we could not close it
            self._set_closed()

    def _set_closed(self) -> None:
        # this code can be raced from the join call and the disconnect handler
        # relying on the GIL to keep us safe
        if not self.closed:
            self.closing = True
            self.closed = True
            self.owner._child_closed(self)

    async def join(self, timeout: float = inmanta.const.EXECUTOR_GRACE_HARD) -> None:
        if self.closed:
            return
        assert self.closing
        await asyncio.get_running_loop().run_in_executor(self.owner.thread_pool, functools.partial(self._force_stop, timeout))

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


# `executor.PoolManager` needs to be before `executor.ExecutorManager` as it defines the start and stop methods (MRO order)
class MPManager(executor.PoolManager, executor.ExecutorManager[MPExecutor]):
    """
    This is the executor that provides the new behavior (ISO8+),
    where the agent forks executors in specific venvs to prevent code reloading.
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
            thread_pool=thread_pool,
        )
        self.init_once()
        self.environment = environment
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

        self.max_executors_per_agent = inmanta.agent.config.agent_executor_cap.get()
        venv_dir = pathlib.Path(self.storage_folder) / "venv"
        venv_dir.mkdir(exist_ok=True)
        self.environment_manager = inmanta.agent.executor.VirtualEnvironmentManager(str(venv_dir.absolute()), self.thread_pool)

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
            multiprocessing.set_forkserver_preload(["inmanta.config", __name__, "inmanta.agent._set_fork_server_process_name"])
        except RuntimeError:
            # already set
            pass

    async def get_executor(
        self,
        agent_name: str,
        agent_uri: str,
        code: typing.Collection[executor.ResourceInstallSpec],
        venv_checkup_interval: float = 60.0,
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
                    await it.join(inmanta.const.EXECUTOR_GRACE_HARD)
            n_executors_for_agent = len(self.agent_map[executor_id.agent_name])
            if n_executors_for_agent >= self.max_executors_per_agent:
                # Close oldest executor:
                executor_ids = self.agent_map[executor_id.agent_name]
                oldest_executor = min([self.executor_map[id] for id in executor_ids], key=lambda e: e.connection.last_used_at)
                LOGGER.debug(
                    f"Reached executor cap for agent {executor_id.agent_name}. Stopping oldest executor "
                    f"{oldest_executor.executor_id.identity()} to make room for a new one."
                )

                await oldest_executor.stop()

            my_executor = await self.create_executor(executor_id, venv_checkup_interval)
            self.__add_executor(executor_id, my_executor)
            if my_executor.failed_resource_results:
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

    async def create_executor(self, executor_id: executor.ExecutorId, venv_checkup_interval: float = 60.0) -> MPExecutor:
        """
        :param venv_checkup_interval: The time interval after which the virtual environment must be touched. Only used for
            testing. The default value is set to 60.0. It should not be used except for testing purposes. It can be
            overridden to speed up the tests
        """
        LOGGER.info("Creating executor for agent %s with id %s", executor_id.agent_name, executor_id.identity())
        env_blueprint = executor_id.blueprint.to_env_blueprint()
        venv = await self.environment_manager.get_environment(env_blueprint)
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
                venv_checkup_interval,
            )
        )
        LOGGER.debug(
            "Child initialized (pid: %s) for executor for agent %s with id %s",
            executor.process.pid,
            executor_id.agent_name,
            executor_id.identity(),
        )
        executor.failed_resource_results = failed_types
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

    async def start(self) -> None:
        await super().start()
        # We need to do this here, otherwise, the scheduler would crash because no event loop would be running
        await self.environment_manager.start()

    async def stop(self) -> None:
        await super().stop()
        await asyncio.gather(*(child.stop() for child in self.children))
        await self.environment_manager.stop()

    async def join(self, thread_pool_finalizer: list[concurrent.futures.ThreadPoolExecutor], timeout: float) -> None:
        await super().join(thread_pool_finalizer, timeout)
        await self.environment_manager.join(thread_pool_finalizer, timeout)

        thread_pool_finalizer.append(self.thread_pool)
        await asyncio.gather(*(child.join(timeout) for child in self.children))

    async def stop_for_agent(self, agent_name: str) -> list[MPExecutor]:
        children_ids = self.agent_map[agent_name]
        children = [self.executor_map[child_id] for child_id in children_ids]
        await asyncio.gather(*(child.stop() for child in children))
        return children

    async def get_pool_members(self) -> typing.Sequence[MPExecutor]:
        return list(self.executor_map.values())
