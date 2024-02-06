import asyncio
import functools
import multiprocessing
import socket
import sys
import typing
from multiprocessing import Process
from typing import Awaitable

import inmanta.const
import inmanta.signals
from inmanta.protocol.ipc_light import IPCClient, IPCServer


class ExecutorServer(IPCServer):
    """The IPC server running on the executor"""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.stopping = False
        self.stopped = asyncio.Event()

    async def stop(self):
        """Perform shutdown"""
        self._sync_stop()

    def _sync_stop(self):
        """Actual shutdown, not async"""
        if not self.stopping:
            print("C STOP")
            self.logger.info("Stopping")
            self.transport.close()
            self.stopping = True

    def connection_lost(self, exc: Exception | None) -> None:
        """We lost connection to the controler, bail out"""
        self.logger.info("Connection lost", exc_info=exc)
        self._sync_stop()
        self.stopped.set()

    def get_method(self, name: str) -> typing.Callable[[...], typing.Coroutine[typing.Any, typing.Any, object]]:
        if name == "stop":
            print("Got stop")
            return self.stop

        async def echo(*args):
            return list(args)

        return echo


def mp_worker_entrypoint(socket, name):
    """Entry point for child processes"""

    async def serve():
        print("A Start")
        loop = asyncio.get_running_loop()
        # Start serving
        transport, protocol = await loop.connect_accepted_socket(functools.partial(ExecutorServer, name), socket)
        #    inmanta.signals.setup_signal_handlers(protocol.stop)
        await protocol.stopped.wait()
        print("A done")

    asyncio.run(serve())

    print("Done")
    exit(0)


class FinalizingIPCClient(IPCClient):
    """IPC client that can signal shutdown"""

    def __init__(self, name: str):
        super().__init__(name)
        self.finalizers: list[typing.Callable[[], Awaitable[None]]] = []

    def connection_lost(self, exc: Exception | None) -> None:
        super().connection_lost(exc)
        for fin in self.finalizers:
            asyncio.get_running_loop().create_task(fin())


class MPExecutor:
    """A Single Child Executor"""

    def __init__(self, process: multiprocessing.Process, connection: FinalizingIPCClient):
        self.process = process
        self.connection = connection
        self.connection.finalizers.append(self.force_stop)

    async def stop(self) -> None:
        """Stop by shutdown"""
        self.connection.call("stop", [], False)

    async def force_stop(self, grace_time: float = inmanta.const.SHUTDOWN_GRACE_HARD) -> None:
        """Stop by process close"""
        await asyncio.get_running_loop().run_in_executor(None, functools.partial(self.force_stop, grace_time))

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
    def __init__(self):
        self.children: list[MPExecutor] = []

    def _init_once(self) -> None:
        multiprocessing.set_start_method("forkserver")
        multiprocessing.set_forkserver_preload(["inmanta", "inmanta.config"])

    async def make_child_and_connect(self, name: str) -> MPExecutor:
        """Async code to make a child process as share a socker with it"""
        loop = asyncio.get_running_loop()
        # Start child
        # TODO: do we need a specific thread pool?
        process, parent_conn = await loop.run_in_executor(None, functools.partial(self._make_child, name))
        # Hook up the connection
        transport, protocol = await loop.connect_accepted_socket(
            functools.partial(FinalizingIPCClient, f"executor.{name}"), parent_conn
        )

        child_handle = MPExecutor(process, protocol)
        self.children.append(child_handle)
        return child_handle

    def _make_child(self, name: str) -> tuple[Process, socket.socket]:
        """Sync code to make a child process and share a socket with it"""
        parent_conn, child_conn = socket.socketpair()
        p = Process(target=mp_worker_entrypoint, args=(child_conn, name))
        p.start()
        child_conn.close()
        return p, parent_conn

    async def stop(self) -> None:
        await asyncio.gather(*(child.stop() for child in self.children))

    async def force_stop(self, grace_time: float) -> None:
        await asyncio.gather(*(child.force_stop(grace_time) for child in self.children))

    async def join(self, timeout: float) -> None:
        await asyncio.gather(*(child.join(timeout) for child in self.children))
