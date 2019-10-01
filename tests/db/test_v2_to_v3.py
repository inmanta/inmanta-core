import collections
import os

import pytest
from asyncpg import Connection
from typing import List

from inmanta import protocol, data
from inmanta.protocol import methods
from inmanta.server.bootloader import InmantaBootloader
from inmanta.server.protocol import SliceStartupException

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


@pytest.mark.asyncio
async def test_pg_restore(hard_clean_db, hard_clean_db_post, postgresql_client: Connection):

    inp = """
CREATE TABLE public.agent (
    environment uuid NOT NULL,
    name character varying NOT NULL,
    last_failover timestamp without time zone,
    paused boolean DEFAULT false,
    id_primary uuid
);

    
COPY public.agent (environment, name, last_failover, paused, id_primary) FROM stdin;
d357482f-11c9-421e-b3c1-36d11ac5b975	localhost	2019-09-27 13:30:46.239275	f	dd2524a7-b737-4b74-a68d-27fe9e4ec7b6
d357482f-11c9-421e-b3c1-36d11ac5b975	internal	2019-09-27 13:30:46.935564	f	5df30799-e712-46a4-9f90-537c5adb47f3
\.
    """
    await PGRestore(inp.splitlines(keepends=True), postgresql_client).run()


@pytest.mark.asyncio
async def test_environment_update(hard_clean_db, hard_clean_db_post, postgresql_client: Connection, async_finalizer, server_config):
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v2.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    await ibl.start()
    async_finalizer(ibl.stop)

    client = protocol.Client("client")

    if False:
        # trick autocomplete to have autocomplete on client
        client = methods
    result = await client.list_environments()

    names = sorted([env["name"] for env in result.result["environments"]])
    name_to_id = {env["name"]:env["id"] for env in result.result["environments"]}
    assert names == ["dev-1", "dev-2"]

    env = await data.Environment.get_by_id(name_to_id["dev-1"])
    print(env.next_version)

