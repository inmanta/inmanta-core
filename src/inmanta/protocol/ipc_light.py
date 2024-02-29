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

import abc
import asyncio
import logging
import pickle
import struct
import typing
import uuid
from asyncio import Future, Protocol, transports
from dataclasses import dataclass
from typing import Optional


class IPCException(Exception):
    pass


class ConnectionLost(IPCException):
    pass


ServerContext = typing.TypeVar("ServerContext")
""" An object to give IPC calls access to the server """

ReturnType = typing.TypeVar("ReturnType")


class IPCMethod(abc.ABC, typing.Generic[ServerContext, ReturnType]):
    """Base class for methods intended for IPC"""

    @abc.abstractmethod
    async def call(self, context: ServerContext) -> ReturnType:
        pass


@dataclass
class IPCRequestFrame(typing.Generic[ServerContext, ReturnType]):
    id: Optional[uuid.UUID]
    method: IPCMethod[ServerContext, ReturnType]


@dataclass
class IPCReplyFrame:
    id: uuid.UUID
    returnvalue: object
    is_exception: bool


class IPCFrameProtocol(Protocol, typing.Generic[ServerContext]):
    """
    Simple protocol which sends

    frame_length: 4 bytes, unsigned integer
    frame: frame_length, pickled data
    """

    # TODo: investigate memory view
    def __init__(self, name: str) -> None:
        # Expected size of frame
        # -1 if no frame in flight
        self.frame_size = -1

        # Buffer with all data we have received and not dispatched
        self.frame_buffer: Optional[bytes] = None

        # Our transport
        self.transport: Optional[transports.Transport] = None

        self.name = name
        self.logger = logging.getLogger(f"ipc.{name}")

    def connection_made(self, transport: transports.Transport) -> None:
        # Capture the transport
        self.transport = transport

    def data_received(self, data: bytes) -> None:
        # Get a block of data
        # Append to frame buffer
        if self.frame_buffer is not None:
            self.frame_buffer += data
        else:
            self.frame_buffer = data
        while True:
            # Eat up frames
            if self.frame_size == -1:
                if len(self.frame_buffer) < 4:
                    # incomplete length field, wait for data
                    break

                # new frame length received
                length = struct.unpack_from("!L", self.frame_buffer)[0]
                self.frame_size = length
            if len(self.frame_buffer) >= self.frame_size + 4:
                # Fill frame in buffer, dispatch
                self._block_received(self.frame_buffer[4 : self.frame_size + 4])
                # Truncate buffer
                self.frame_buffer = self.frame_buffer[self.frame_size + 4 :]
                # Reset frame size
                self.frame_size = -1
            else:
                # Not full frame anymore, wait for data
                break

    def _block_received(self, block: bytes) -> None:
        """Interception point for tests of block handling"""
        try:
            frame = pickle.loads(block)
        except Exception:
            # Failed to unpickle, drop connection
            self.logger.exception("Dropping IPC connection %s because of deserialization failure", self.name)
            self.transport.close()
            return
        try:
            self.frame_received(frame)
        except Exception:
            # Failed to unpickle, drop connection
            self.logger.exception("Unexpected exception while handling frame", self.name)

    def send_frame(self, frame: IPCRequestFrame[ServerContext, ReturnType] | IPCReplyFrame) -> None:
        """
        Helper method to construct and send frames
        """
        if self.transport.is_closing():
            raise ConnectionLost()
        buffer = pickle.dumps(frame)
        size = struct.pack("!L", len(buffer))
        self.transport.write(size + buffer)

    def frame_received(self, frame: IPCRequestFrame[ServerContext, ReturnType] | IPCReplyFrame) -> None:
        """
        Method for frame handling subclasses

        Always call super, to use multiple inheritance to compose handlers
        """
        raise Exception(f"Frame not handled {frame}")


class IPCServer(IPCFrameProtocol[ServerContext], abc.ABC, typing.Generic[ServerContext]):
    """Base server that dispatched methods"""

    @abc.abstractmethod
    def get_context(self) -> ServerContext:
        pass

    # TODO: timeouts?
    def frame_received(self, frame: IPCRequestFrame[ServerContext, ReturnType] | IPCReplyFrame) -> None:
        if isinstance(frame, IPCRequestFrame):
            asyncio.get_running_loop().create_task(self.dispatch(frame))
        else:
            super().frame_received(frame)

    async def dispatch(self, frame: IPCRequestFrame[ServerContext, ReturnType]) -> None:
        """
        Dispatch handler that sends back return values
        """
        try:
            return_value = await frame.method.call(self.get_context())
            if frame.id is not None:
                self.send_frame(IPCReplyFrame(frame.id, return_value, is_exception=False))
        except Exception as e:
            self.logger.debug("Exception on rpc call", exc_info=True)
            if frame.id is not None:
                self.send_frame(IPCReplyFrame(frame.id, e, is_exception=True))


class IPCClient(IPCFrameProtocol[ServerContext]):
    """Base client that dispatched method calls"""

    def __init__(self, name: str):
        super().__init__(name)
        # TODO timeouts
        self.requests: dict[uuid.UUID, Future[object]] = {}
        # All outstanding calls

    @typing.overload
    def call(
        self, method: IPCMethod[ServerContext, ReturnType], has_reply: typing.Literal[True] = True
    ) -> Future[ReturnType]: ...

    @typing.overload
    def call(self, method: IPCMethod[ServerContext, ReturnType], has_reply: typing.Literal[False]) -> None: ...

    def call(self, method: IPCMethod[ServerContext, ReturnType], has_reply: bool = True) -> Future[ReturnType] | None:
        """Call a method with given arguments"""
        request = IPCRequestFrame(
            id=uuid.uuid4() if has_reply else None,
            method=method,
        )
        self.send_frame(request)

        if not has_reply:
            return None

        done = asyncio.get_event_loop().create_future()
        self.requests[request.id] = done  # Mypy can't do it
        return done

    def frame_received(self, frame: IPCRequestFrame[ServerContext, ReturnType] | IPCReplyFrame) -> None:
        """Handle replies"""
        if isinstance(frame, IPCReplyFrame):
            self.process_reply(frame)
        else:
            super().frame_received(frame)

    def process_reply(self, frame: IPCReplyFrame) -> None:
        if frame.is_exception:
            self.requests[frame.id].set_exception(frame.returnvalue)
        else:
            self.requests[frame.id].set_result(frame.returnvalue)
        del self.requests[frame.id]

    def connection_lost(self, exc: Exception | None) -> None:
        excn = ConnectionLost()
        excn.__cause__ = exc
        for outstanding_request in self.requests.values():
            outstanding_request.set_exception(excn)
        self.requests.clear()
        super().connection_lost(exc)


class FinalizingIPCClient(IPCClient[ServerContext]):
    """IPC client that can signal shutdown"""

    def __init__(self, name: str):
        super().__init__(name)
        self.finalizers: list[typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, None]]] = []

    def connection_lost(self, exc: Exception | None) -> None:
        super().connection_lost(exc)
        for fin in self.finalizers:
            asyncio.get_running_loop().create_task(fin())
