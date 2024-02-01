import asyncio
import multiprocessing
import socket
from multiprocessing import Process

from inmanta.protocol.ipc_light import IPCClient, IPCServer


def worker(socket):
    """Entry point for child processes"""

    async def serve():
        # Start serving
        loop = asyncio.get_running_loop()
        server = await loop.connect_accepted_socket(IPCServer, socket)
        stop = loop.create_future()
        await stop

    asyncio.run(serve())


def make_child() -> tuple[Process, socket.socket]:
    """Sync code to make a child process and share a socket with it"""
    parent_conn, child_conn = socket.socketpair()
    p = Process(target=worker, args=(child_conn,))
    p.start()
    return p, parent_conn


async def make_child_and_connect():
    """Async code to make a child process as share a socker with it"""
    loop = asyncio.get_running_loop()
    # Start child
    process, parent_conn = await loop.run_in_executor(None, make_child)
    # Hook up the connection
    transport, protocol = await loop.connect_accepted_socket(IPCClient, parent_conn)

    print(await asyncio.gather(*[protocol.call("test", ["a.a.a", "a" * 1000]) for i in range(5)]))


if __name__ == "__main__":
    multiprocessing.set_start_method("forkserver")
    assert not asyncio.get_event_loop().is_running()
    asyncio.run(make_child_and_connect())
