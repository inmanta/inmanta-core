import struct

from inmanta.protocol.ipc_light import IPCClient


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
