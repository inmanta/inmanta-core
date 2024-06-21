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
import re
import socket
import struct
import sys
import threading
from socket import socketpair

import pytest

import inmanta.config
import inmanta.protocol.ipc_light
import inmanta.util
import utils
from inmanta.protocol.ipc_light import IPCClient, IPCServer


def test_package_reassembly():
    class IPCSpy(IPCClient[None]):
        def __init__(self) -> None:
            self.blocks = []
            super().__init__("SPY")

        def _block_received(self, block: bytes) -> None:
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


class Error(inmanta.protocol.ipc_light.IPCMethod[None, None]):
    async def call(self, ctx: None) -> None:
        raise Exception("raise")


class Echo(inmanta.protocol.ipc_light.IPCMethod[list[int], None]):
    def __init__(self, args: list[int]) -> None:
        self.args = args

    async def call(self, ctx) -> list[int]:
        return self.args


class UnPicleableError(inmanta.protocol.ipc_light.IPCMethod[None, None]):
    async def call(self, ctx: None) -> None:
        a, b = socketpair()
        a.close()
        b.close()
        raise Exception(a)


async def test_normal_flow(request):
    loop = asyncio.get_running_loop()
    parent_conn, child_conn = socket.socketpair()

    class TestIPC(IPCServer[None]):
        def __init__(self):
            super().__init__("SERVER")

        def get_context(self) -> None:
            return None

    server_transport, server_protocol = await loop.connect_accepted_socket(TestIPC, parent_conn)
    request.addfinalizer(server_transport.close)
    client_transport, client_protocol = await loop.connect_accepted_socket(lambda: IPCClient("Client"), child_conn)
    request.addfinalizer(client_transport.close)

    with pytest.raises(Exception, match="raise"):
        await client_protocol.call(Error())

    with pytest.raises(Exception, match=re.escape("<socket.socket [closed]")):
        await client_protocol.call(UnPicleableError())

    args = [1, 2, 3, 4]
    result = await client_protocol.call(Echo(args))
    assert args == result


async def test_log_transport(caplog, request):
    """
    Test for the IPC feature of shipping logs

    Ensure we can send a log line over the IPC protocol

    This doesn't actually connect the LogShipper to the logging framework, as this would create an infinite loop
    (the log is re-injected in the same place it was first received)
    """

    loop = asyncio.get_running_loop()
    parent_conn, child_conn = socket.socketpair()

    server_transport, server_protocol = await loop.connect_accepted_socket(
        lambda: inmanta.protocol.ipc_light.LogReceiver("logs"), parent_conn
    )
    request.addfinalizer(server_transport.close)
    client_transport, client_protocol = await loop.connect_accepted_socket(lambda: IPCClient("Client"), child_conn)
    request.addfinalizer(client_transport.close)
    log_shipper = inmanta.protocol.ipc_light.LogShipper(client_protocol, loop)

    with caplog.at_level(logging.INFO):
        # Test exception capture and transport
        try:
            raise Exception("test the exception capture!")
        except Exception:
            log_shipper.handle(
                logging.LogRecord("deep.in.exception", logging.INFO, "yyy", 5, "Test Exc %s", ("a",), exc_info=sys.exc_info())
            )

        # test normal log
        log_shipper.handle(logging.LogRecord("deep.in.test", logging.INFO, "xxx", 5, "Test %s", ("a",), exc_info=False))

        # wait for normal log
        def has_log(msg: str) -> bool:
            try:
                utils.log_contains(caplog, "deep.in.test", logging.INFO, f"Test {msg}")
                return True
            except AssertionError:
                return False

        await inmanta.util.retry_limited(functools.partial(has_log, "a"), 1)

        logline = utils.LogSequence(caplog).get("deep.in.exception", logging.INFO, "Test Exc a")
        assert logline.msg.startswith("Test Exc a\nTraceback (most recent call last):\n")

        # mess with threads, shows that we get at least no assertion errors
        # Also test against % injection in the format string
        thread = threading.Thread(
            target=lambda: log_shipper.handle(
                logging.LogRecord("deep.in.test", logging.INFO, "xxx", 5, "Test %s", ("%d",), exc_info=False)
            )
        )

        thread.start()
        await inmanta.util.retry_limited(functools.partial(has_log, "%d"), 1)

        # Test we are not creating a log-loop when shut down
        # This is a bit tricky to test, as we don't know how long to wait for a repeat log line to not appear

        # This logger name should be ignored, as this is the loop protection
        log_shipper.handle(
            logging.LogRecord(log_shipper.logger_name, logging.INFO, "xxx", 5, "Test %s", ("X",), exc_info=False)
        )

        client_transport.close()

        log_shipper.handle(logging.LogRecord("deep.in.test", logging.INFO, "xxx", 5, "Test %s", ("c",), exc_info=False))

        def has_diverted_log() -> bool:
            try:
                utils.log_contains(caplog, log_shipper.logger_name, logging.INFO, "Could not send log line")
                return True
            except AssertionError:
                return False

        await inmanta.util.retry_limited(functools.partial(has_diverted_log), 1)
        # Make sure we drain the buffer
        await asyncio.sleep(0.1)
        utils.log_doesnt_contain(caplog, log_shipper.logger_name, logging.INFO, "Test X")
        # Log line is not repeated
        # Not other log line after it
        utils.LogSequence(caplog).contains(log_shipper.logger_name, logging.INFO, "Could not send log line").assert_not(
            loggerpart="", level=-1, msg="", min_level=logging.DEBUG
        )
