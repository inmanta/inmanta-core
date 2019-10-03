"""
    Copyright 2019 Inmanta

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


    Tool to populate the database and dump it for database update testing
"""
import collections
from typing import List

from asyncpg import Connection

MODE_READ_COMMAND = 0
MODE_READ_INPUT = 1


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
