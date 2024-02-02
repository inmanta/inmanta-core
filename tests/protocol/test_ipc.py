import asyncio
import struct
from socket import socket

import pytest

from inmanta.protocol.ipc_light import IPCClient, IPCServer


def test_package_reassembly():
    class IPCSpy(IPCClient):
        def __init__(self):
            self.blocks = []
            super().__init__()

        def _block_received(self, block: bytes):
            self.blocks.append(block)

    base_block = "aaa".encode()
    base_block_and_length = struct.pack("!L", len(base_block)) + base_block
    twice = base_block_and_length * 2

    ipc = IPCSpy()
    ipc.data_received(base_block_and_length)
    assert ipc.blocks == [base_block]

    ipc = IPCSpy()
    ipc.data_received(base_block_and_length * 2)
    assert ipc.blocks == [base_block, base_block]

    # Cut into the length field
    ipc = IPCSpy()
    cutpoint = len(base_block_and_length) + 1
    ipc.data_received(twice[0:cutpoint])
    assert ipc.blocks == [base_block]
    ipc.data_received(twice[cutpoint:])
    assert ipc.blocks == [base_block, base_block]

    # Cut into the payload
    ipc = IPCSpy()
    cutpoint = int(len(base_block_and_length) * 1.5)
    ipc.data_received(twice[0:cutpoint])
    assert ipc.blocks == [base_block]
    ipc.data_received(twice[cutpoint:])
    assert ipc.blocks == [base_block, base_block]

async def test_normal_flow(request):
    loop = asyncio.get_running_loop()
    parent_conn, child_conn = socket.socketpair()

    class TestIPC(IPCServer):

        def get_method(self, name: str):
            if name=="fastraise":
                raise Exception("Fastraise")

            if name == "raise":
                def func():
                    raise Exception("raise")
                return func



    server_transport, server_protocol = await loop.connect_accepted_socket(TestIPC, parent_conn)
    request.addfinalizer(server_transport.close)
    client_transport, client_protocol = await loop.connect_accepted_socket(IPCClient, parent_conn)
    request.addfinalizer(client_transport.close)

    with pytest.raises(Exception, match="raise"):
        await client_protocol.call("raise")



async def main():
    server = asyncio.create_task(serve())
    await asyncio.sleep(1)

    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_connection(IPCClient, "127.0.0.1", 1456)

    print(await asyncio.gather(*[protocol.call("test", ["a.a.a", "a" * 10]) for i in range(5)]))

    await server

