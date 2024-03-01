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
import functools
import logging
import multiprocessing
import os
import socket
import typing

import inmanta.config
import inmanta.const
import inmanta.protocol.ipc_light
import inmanta.signals
from inmanta.logging import InmantaLoggerConfig
from inmanta.protocol.ipc_light import FinalizingIPCClient, IPCServer

LOGGER = logging.getLogger(__name__)
"""
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


class ExecutorContext:
    """The context object used by the executor to expose state to the incoming calls"""

    def __init__(self, server: "ExecutorServer") -> None:
        self.server = server

    async def stop(self) -> None:
        """Request the executor to stop"""
        await self.server.stop()


class ExecutorServer(IPCServer[ExecutorContext]):
    """The IPC server running on the executor"""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.stopping = False
        self.stopped = asyncio.Event()

    def get_context(self) -> ExecutorContext:
        return ExecutorContext(self)

    async def stop(self) -> None:
        """Perform shutdown"""
        self._sync_stop()

    def _sync_stop(self) -> None:
        """Actual shutdown, not async"""
        if not self.stopping:
            self.logger.info("Stopping")
            assert self.transport is not None  # Mypy
            self.transport.close()
            self.stopping = True

    def connection_lost(self, exc: Exception | None) -> None:
        """We lost connection to the controler, bail out"""
        self.logger.info("Connection lost", exc_info=exc)
        self._sync_stop()
        self.stopped.set()


class StopCommand(inmanta.protocol.ipc_light.IPCMethod[ExecutorContext, None]):

    async def call(self, context: ExecutorContext) -> None:
        await context.stop()


def mp_worker_entrypoint(
    socket: socket.socket,
    name: str,
    logfile: str,
    inmanta_log_level: str,
    cli_log: bool,
    config: typing.Mapping[str, typing.Mapping[str, typing.Any]],
) -> None:
    """Entry point for child processes"""
    log_config = InmantaLoggerConfig.get_instance()
    log_config.configure_file_logger(logfile, inmanta_log_level)
    if cli_log:
        log_config.add_cli_logger(inmanta_log_level)
    logging.captureWarnings(True)
    logger = logging.getLogger(f"agent.executor.{name}")
    logger.info(f"Started with PID: {os.getpid()}")

    inmanta.config.Config.load_config_from_dict(config)

    async def serve() -> None:
        loop = asyncio.get_running_loop()
        # Start serving
        transport, protocol = await loop.connect_accepted_socket(functools.partial(ExecutorServer, name), socket)
        #    inmanta.signals.setup_signal_handlers(protocol.stop)
        await protocol.stopped.wait()

    asyncio.run(serve())
    logger.info(f"Stopped with PID: {os.getpid()}")
    exit(0)


class MPExecutor:
    """A Single Child Executor"""

    def __init__(self, process: multiprocessing.Process, connection: FinalizingIPCClient[ExecutorContext]):
        self.process = process
        self.connection = connection
        self.connection.finalizers.append(self.force_stop)

    async def stop(self) -> None:
        """Stop by shutdown"""
        self.connection.call(StopCommand(), False)

    async def force_stop(self, grace_time: float = inmanta.const.SHUTDOWN_GRACE_HARD) -> None:
        """Stop by process close"""
        await asyncio.get_running_loop().run_in_executor(None, functools.partial(self._force_stop, grace_time))

    def _force_stop(self, grace_time: float) -> None:
        try:
            self.process.terminate()
            self.process.join(grace_time)
            self.process.kill()
            self.process.join()
        except ValueError:
            # Process already gone:
            pass
        self.process.close()

    async def join(self, timeout: float) -> None:
        await asyncio.get_running_loop().run_in_executor(None, functools.partial(self.process.join, timeout))
        self.process.close()


class MPManager:
    def __init__(self, log_folder: str, inmanta_log_level: str = "DEBUG", cli_log: bool = False) -> None:
        """

        :param log_folder: folder to place log files for the executors
        :param inmanta_log_level: log level for the executors
        :param cli_log: do we also want to echo the log to std_err
        """
        self.children: list[MPExecutor] = []
        self.log_folder = log_folder
        os.makedirs(self.log_folder, exist_ok=True)
        self.inmanta_log_level = inmanta_log_level
        self.cli_log = cli_log

    @classmethod
    def init_once(cls) -> None:
        try:
            multiprocessing.set_start_method("forkserver")
            multiprocessing.set_forkserver_preload(["inmanta", "inmanta.config"])
        except RuntimeError:
            # already set
            pass

    async def make_child_and_connect(self, name: str) -> MPExecutor:
        """Async code to make a child process as share a socker with it"""
        loop = asyncio.get_running_loop()

        # Start child
        # TODO: do we need a specific thread pool?
        logfile = os.path.join(self.log_folder, f"{name}.log")
        process, parent_conn = await loop.run_in_executor(
            None, functools.partial(self._make_child, name, logfile, self.inmanta_log_level, self.cli_log)
        )
        # Hook up the connection
        transport, protocol = await loop.connect_accepted_socket(
            functools.partial(FinalizingIPCClient, f"executor.{name}"), parent_conn
        )

        child_handle = MPExecutor(process, protocol)
        self.children.append(child_handle)
        return child_handle

    def _make_child(
        self, name: str, log_file: str, log_level: int, cli_log: bool
    ) -> tuple[multiprocessing.Process, socket.socket]:
        """Sync code to make a child process and share a socket with it"""
        parent_conn, child_conn = socket.socketpair()
        p = multiprocessing.Process(
            target=mp_worker_entrypoint,
            args=(child_conn, name, log_file, log_level, cli_log, inmanta.config.Config.config_as_dict()),
            name=f"agent.executor.{name}",
        )
        p.start()
        child_conn.close()
        return p, parent_conn

    async def stop(self) -> None:
        await asyncio.gather(*(child.stop() for child in self.children))

    async def force_stop(self, grace_time: float) -> None:
        await asyncio.gather(*(child.force_stop(grace_time) for child in self.children))

    async def join(self, timeout: float) -> None:
        await asyncio.gather(*(child.join(timeout) for child in self.children))
