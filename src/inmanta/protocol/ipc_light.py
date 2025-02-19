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
import functools
import logging
import pickle
import struct
import traceback
import typing
import uuid
from asyncio import Future, Protocol, transports
from dataclasses import dataclass
from pickle import PicklingError
from typing import Optional


class IPCException(Exception):
    pass


class ConnectionLost(IPCException):
    pass


ServerContext = typing.TypeVar("ServerContext")
""" An object to give IPC calls access to the server """

ReturnType = typing.TypeVar("ReturnType")


class IPCFrame(abc.ABC):
    """Interface marker for IPC frames"""

    pass


class IPCMethod(IPCFrame, typing.Generic[ServerContext, ReturnType]):
    """Base class for methods intended for IPC"""

    @abc.abstractmethod
    async def call(self, context: ServerContext) -> ReturnType:
        pass


@dataclass
class IPCRequestFrame(IPCFrame, typing.Generic[ServerContext, ReturnType]):
    id: Optional[uuid.UUID]
    method: IPCMethod[ServerContext, ReturnType]


@dataclass
class IPCReplyFrame(IPCFrame):
    id: uuid.UUID
    returnvalue: object
    is_exception: bool


@dataclass
class IPCLogRecord(IPCFrame):
    """
    Derived from logging.LogRecord, but simplified

    :param name: the logger name, as on logging.LogRecord
    :param levelno: the log level, in numeric form, as on logging.LogRecord
    :param msg: the message, as produced by record.getMessage() i.e. this record has all arguments already formatted in
    """

    name: str
    levelno: int
    msg: str


class IPCFrameProtocol(Protocol):
    """
    Simple protocol which sends

    frame_length: 4 bytes, unsigned integer
    frame: frame_length, pickled data

    It is intended as an async replacement of the facilities offered by multiprocessing and of similar design.

    This protocol is only suited for local interprocess communications, when both ends are trusted.
    This protocol is based on pickle for speed, so it is as insecure as pickle.
    """

    def __init__(self, name: str) -> None:
        # Expected size of frame
        # -1 if no frame in flight
        self.frame_size = -1

        # Buffer with all data we have received and not dispatched
        # We could sqeeze out some more performance by using memoryview instead of an array
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
            # Failed to unpickle, drop frame
            self.logger.exception("Unexpected exception while handling frame %s", self.name)

    def send_frame(self, frame: IPCFrame) -> None:
        """
        Helper method to construct and send frames
        """
        if self.transport.is_closing():
            raise ConnectionLost()
        try:
            buffer = pickle.dumps(frame)
        except PicklingError:
            raise
        except Exception as e:
            # Pickle tends to raise other exceptions as well...
            raise PicklingError() from e
        size = struct.pack("!L", len(buffer))
        self.transport.write(size + buffer)

    def frame_received(self, frame: IPCFrame) -> None:
        """
        Method for frame handling subclasses

        Always call super, to use multiple inheritance to compose handlers
        """
        raise Exception(f"Frame not handled {frame}")


class IPCServer(IPCFrameProtocol, abc.ABC, typing.Generic[ServerContext]):
    """Base server that dispatched methods"""

    @abc.abstractmethod
    def get_context(self) -> ServerContext:
        pass

    # TODO: timeouts?
    def frame_received(self, frame: IPCFrame) -> None:
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
        except ConnectionLost:
            self.logger.debug("Connection lost", exc_info=True)
        except Exception as e:
            self.logger.debug("Exception on rpc call", exc_info=True)
            if frame.id is not None:
                try:
                    self.send_frame(IPCReplyFrame(frame.id, e, is_exception=True))
                except PicklingError:
                    # Can't pickle it

                    self.send_frame(IPCReplyFrame(frame.id, traceback.format_exception(e), is_exception=True))


class IPCClient(IPCFrameProtocol, typing.Generic[ServerContext]):
    """Base client that dispatched method calls"""

    def __init__(self, name: str):
        super().__init__(name)
        # TODO timeouts

        # All outstanding calls
        self.requests: dict[uuid.UUID, Future[object]] = {}

    @typing.overload
    def call(
        self, method: IPCMethod[ServerContext, ReturnType], has_reply: typing.Literal[True] = True
    ) -> Future[ReturnType]: ...

    @typing.overload
    def call(self, method: IPCMethod[ServerContext, ReturnType], has_reply: typing.Literal[False]) -> None: ...

    @typing.overload
    def call(self, method: IPCMethod[ServerContext, ReturnType], has_reply: bool = True) -> Future[ReturnType] | None: ...

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

    def frame_received(self, frame: IPCFrame) -> None:
        """Handle replies"""
        if isinstance(frame, IPCReplyFrame):
            self.process_reply(frame)
        else:
            super().frame_received(frame)

    def process_reply(self, frame: IPCReplyFrame) -> None:
        if frame.is_exception:
            if isinstance(frame.returnvalue, Exception):
                self.requests[frame.id].set_exception(frame.returnvalue)
            else:
                self.requests[frame.id].set_exception(Exception(frame.returnvalue))
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
        # Collection to avoid task getting garbage collected
        self.finalizer_anti_gc: set[asyncio.Task[None]] = set()

    def connection_lost(self, exc: Exception | None) -> None:
        super().connection_lost(exc)
        for fin in self.finalizers:
            task = asyncio.get_running_loop().create_task(fin())
            self.finalizer_anti_gc.add(task)
            task.add_done_callback(self.finalizer_anti_gc.discard)


class LogReceiver(IPCFrameProtocol):
    """
    IPC feature to receive log message

    It re-injects the log message into the logging framework in the exact same place as it was on the sender side.

    This makes the LogShipper/LogReceiver pair a (mostly) transparent bridge.
    Log records are simplified when transported.

    When installing the LogShipper and LogReceiver in the same process, this will create an infinite loop
    """

    def frame_received(self, frame: IPCFrame) -> None:
        if isinstance(frame, IPCLogRecord):
            # calling log here is safe because if there are no arguments, formatter is never called
            logging.getLogger(frame.name).log(frame.levelno, frame.msg)
        else:
            super().frame_received(frame)


class LogShipper(logging.Handler):
    """
    Log sender associated with the log receiver

    This sender is threadsafe
    """

    def __init__(self, protocol: IPCFrameProtocol, eventloop: asyncio.AbstractEventLoop) -> None:
        self.protocol = protocol
        self.eventloop = eventloop
        self.logger_name = "inmanta.ipc.logs"
        self.logger = logging.getLogger(self.logger_name)
        super().__init__()

    def _send_frame(self, record: IPCLogRecord) -> None:
        try:
            self.protocol.send_frame(record)
        except ConnectionLost:
            # Stop exception here
            # Log in own logger to prevent loops
            self.logger.debug("Could not send log line, connection lost %s", record.msg, exc_info=True)
            return
        except Exception:
            # Stop exception here
            # Log in own logger to prevent loops
            self.logger.info("Could not send log line %s", record.msg, exc_info=True)
            return

    def emit(self, record: logging.LogRecord) -> None:
        if record.name == self.logger_name:
            # avoid loops
            # When we fail to send, we produce a log line on this logger
            return
        self.eventloop.call_soon_threadsafe(
            functools.partial(
                self._send_frame,
                IPCLogRecord(
                    record.name,
                    record.levelno,
                    self.format(record),
                ),
            )
        )
