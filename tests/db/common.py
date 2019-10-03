import collections
from typing import List

from asyncpg import Connection

from db.test_v2_to_v3 import MODE_READ_COMMAND, MODE_READ_INPUT


class AsyncSingleton(collections.abc.AsyncIterable):
    """ AsyncPG wants an async iterable """

    def __init__(self, item):
        self.item = item

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.item is None:
            raise StopAsyncIteration
        item = self.item
        self.item = None
        return item


class PGRestore:
    # asyncpg execute method can not read in COPY IN

    def __init__(self, script: List[str], postgresql_client: Connection) -> None:
        self.commandbuffer = ""
        self.extbuffer = ""
        self.mode = MODE_READ_COMMAND
        self.script = script
        self.client = postgresql_client

    async def run(self):
        for line in self.script:
            if self.mode == MODE_READ_COMMAND:
                if line.startswith("COPY"):
                    await self.execute_buffer()
                    self.extbuffer = line
                    self.mode = MODE_READ_INPUT
                else:
                    self.buffer(line)
            else:
                if line == "\\.\n":
                    await self.execute_input()
                    self.mode = MODE_READ_COMMAND
                else:
                    self.buffer(line)
        assert self.mode == MODE_READ_COMMAND
        await self.execute_buffer()

    def buffer(self, cmd):
        if cmd.startswith("--"):
            return
        if not cmd.strip():
            return
        self.commandbuffer += cmd

    async def execute_buffer(self):
        if not self.commandbuffer.strip():
            return
        await self.client.execute(self.commandbuffer)
        self.commandbuffer = ""

    async def execute_input(self):
        await self.client._copy_in(self.extbuffer, AsyncSingleton(self.commandbuffer.encode()), 10)
        self.commandbuffer = ""
