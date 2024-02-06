import abc
import asyncio
import logging
import pickle
import struct
import uuid
from asyncio import Future, Protocol, transports
from dataclasses import dataclass
from pickle import Pickler, Unpickler
from typing import Any, Callable, Coroutine, Optional


class IPCException(Exception):
    pass


class ConnectionLost(IPCException):
    pass


@dataclass
class IPCRequestFrame:
    id: uuid.UUID
    method: str
    arguments: list[object]


@dataclass
class IPCReplyFrame:
    id: uuid.UUID
    returnvalue: object
    is_exception: bool


class IPCFrameProtocol(Protocol):
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

    def send_frame(self, frame: IPCRequestFrame | IPCReplyFrame) -> None:
        """
        Helper method to construct and send frames
        """
        if self.transport.is_closing():
            raise ConnectionLost()
        buffer = pickle.dumps(frame)
        size = struct.pack("!L", len(buffer))
        self.transport.write(size + buffer)

    def frame_received(self, frame: IPCRequestFrame | IPCReplyFrame) -> None:
        """
        Method for frame handling subclasses

        Always call super, to use multiple inheritance to compose handlers
        """
        raise Exception(f"Frame not handled {frame}")


class IPCServer(IPCFrameProtocol, abc.ABC):
    """Base server that dispatched methods"""

    # TODO: timeouts?
    def frame_received(self, frame: IPCRequestFrame | IPCReplyFrame):
        if isinstance(frame, IPCRequestFrame):
            asyncio.get_running_loop().create_task(self.dispatch(frame))
        else:
            super().frame_received(frame)

    @abc.abstractmethod
    def get_method(self, name: str) -> Callable[[...], Coroutine[Any, Any, object]]:
        """
        Main dispatch method, that returns the methods to dispatch to
        """
        pass

    async def dispatch(self, frame: IPCRequestFrame) -> None:
        """
        Dispatch handler that sends back return values
        """
        try:
            method = self.get_method(frame.method)
            return_value = await method(*frame.arguments)
            if frame.id is not None:
                self.send_frame(IPCReplyFrame(frame.id, return_value, is_exception=False))
        except Exception as e:
            self.logger.debug("Exception on rpc call", exc_info=True)
            self.send_frame(IPCReplyFrame(frame.id, e, is_exception=True))


class IPCClient(IPCFrameProtocol):
    """Base client that dispatched method calls"""

    def __init__(self, name: str):
        super().__init__(name)
        # TODO timeouts
        self.requests: dict[uuid.UUID, Future[object]] = {}
        # All outstanding calls

    def call(self, method: str, arguments: list[object], has_reply: bool = True) -> Future[object]:
        """Call a method with given arguments"""
        request = IPCRequestFrame(
            id=uuid.uuid4() if has_reply else None,
            method=method,
            arguments=arguments,
        )
        self.send_frame(request)

        if not has_reply:
            return None

        done = asyncio.get_event_loop().create_future()
        self.requests[request.id] = done
        return done

    def frame_received(self, frame: IPCRequestFrame | IPCReplyFrame):
        """Handle replies"""
        if isinstance(frame, IPCReplyFrame):
            self.process_reply(frame)
        else:
            super().frame_received(frame)

    def process_reply(self, frame: IPCReplyFrame):
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
