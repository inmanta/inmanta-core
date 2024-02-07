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
import socket
import struct

import pytest

from inmanta.protocol.ipc_light import IPCClient, IPCServer


def test_package_reassembly():
    class IPCSpy(IPCClient):
        def __init__(self):
            self.blocks = []
            super().__init__("SPY")

        def _block_received(self, block: bytes):
            self.blocks.append(block)

    base_block = "aaa".encode()
    base_block_and_length = struct.pack("!L", len(base_block)) + base_block
    twice = base_block_and_length * 2

    # Send one block
    ipc = IPCSpy()
    ipc.data_received(base_block_and_length)
    assert ipc.blocks == [base_block]

    # Send two blocks at once
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
        def __init__(self):
            super().__init__("SERVER")

        def get_method(self, name: str):
            if name == "fastraise":
                raise Exception("Fastraise")

            if name == "raise":

                async def func(*args):
                    raise Exception("raise")

                return func

            async def echo(*args):
                return list(args)

            return echo

    server_transport, server_protocol = await loop.connect_accepted_socket(TestIPC, parent_conn)
    request.addfinalizer(server_transport.close)
    client_transport, client_protocol = await loop.connect_accepted_socket(lambda: IPCClient("Client"), child_conn)
    request.addfinalizer(client_transport.close)

    with pytest.raises(Exception, match="raise"):
        await client_protocol.call("raise", [])

    with pytest.raises(Exception, match="Fastraise"):
        await client_protocol.call("fastraise", [])

    args = [1, 2, 3, 4]
    result = await client_protocol.call("echo", args)
    assert args == result
