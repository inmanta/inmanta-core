import asyncio
import pickle
import struct
import uuid
from asyncio import Future, Protocol, transports
from dataclasses import dataclass
from pickle import Pickler, Unpickler
from typing import Any, Callable, Coroutine


@dataclass
class IPCRequestFrame:
    id: uuid.UUID
    method: str
    arguments: list[object]


@dataclass
class IPCReplyFrame:
    id: uuid.UUID
    returnvalue: object


class IPCFrameProtocol(Protocol):
    """
    Simple protocol which sends

    frame_length: 4 bytes, unsigned integer
    frame: frame_length, pickled data
    """

    # TODo: investigate memory view
    def __init__(self) -> None:
        # Expected size of frame
        # -1 if no frame in flight
        self.frame_size = -1

        # Buffer with all data we have received and not dispatched
        self.frame_buffer: Optional[bytes] = None

        # Our transport
        self.transport = None

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
        frame = pickle.loads(block)
        self.frame_received(frame)

    def send_frame(self, frame: IPCRequestFrame | IPCReplyFrame) -> None:
        """
        Helper method to construct and send frames
        """
        buffer = pickle.dumps(frame)
        size = struct.pack("!L", len(buffer))
        self.transport.write(size + buffer)

    def frame_received(self, frame: IPCRequestFrame | IPCReplyFrame) -> None:
        """
        Method for frame handling subclasses

        Always call super, to use multiple inheritance to compose handlers
        """
        raise Exception(f"Frame not handled {frame}")


class IPCServer(IPCFrameProtocol):
    """Base server that dispatched methods"""

    # TODO: timeouts?
    def frame_received(self, frame: IPCRequestFrame | IPCReplyFrame):
        if isinstance(frame, IPCRequestFrame):
            asyncio.get_running_loop().create_task(self.dispatch(frame))
        else:
            super().frame_received(frame)

    def get_method(self, name: str) -> Callable[[...], Coroutine[Any, Any, object]]:
        """
        Main dispatch method, that returns the methods to dispatch to
        """

        async def printer(*args):
            print(name, args)
            return "V"

        return printer

    async def dispatch(self, frame: IPCRequestFrame) -> None:
        """
        Dispatch handler that sends back return values
        """
        # TODO error handling
        method = self.get_method(frame.method)
        return_value = await method(frame.arguments)
        if frame.id is not None:
            self.send_frame(IPCReplyFrame(frame.id, return_value))


class IPCClient(IPCFrameProtocol):
    """Base client that dispatched method calls"""

    def __init__(self):
        super().__init__()
        # TODO timeouts
        self.requests: dict[uuid.UUID, Future[object]] = {}
        # All outstanding calls

    def call(self, method: str, arguments: list[object]) -> Future[object]:
        """Call a method with given arguments"""
        request = IPCRequestFrame(
            id=uuid.uuid4(),
            method=method,
            arguments=arguments,
        )
        done = asyncio.get_event_loop().create_future()
        self.requests[request.id] = done
        self.send_frame(request)
        return done

    def frame_received(self, frame: IPCRequestFrame | IPCReplyFrame):
        """Handle replies"""
        if isinstance(frame, IPCReplyFrame):
            self.process_reply(frame)
        else:
            super().frame_received(frame)

    def process_reply(self, frame: IPCReplyFrame):
        # TODO: exceptions
        self.requests[frame.id].set_result(frame.returnvalue)
        del self.requests[frame.id]


#
# async def serve():
#     # Get a reference to the event loop as we plan to use
#     # low-level APIs.
#     loop = asyncio.get_running_loop()
#
#     server = await loop.create_server(IPCServer, "127.0.0.1", 1456)
#
#     async with server:
#         await server.serve_forever()
#
#
# async def main():
#     server = asyncio.create_task(serve())
#     await asyncio.sleep(1)
#
#     loop = asyncio.get_running_loop()
#     transport, protocol = await loop.create_connection(IPCClient, "127.0.0.1", 1456)
#
#     print(await asyncio.gather(*[protocol.call("test", ["a.a.a", "a" * 10]) for i in range(5)]))
#
#     await server
#
# if __name__ == '__main__':
#     asyncio.run(main())
