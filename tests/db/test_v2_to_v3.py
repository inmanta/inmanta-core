import os

import pytest
from asyncpg import Connection

from db.common import PGRestore
from inmanta import protocol
from inmanta.server.bootloader import InmantaBootloader

MODE_READ_COMMAND = 0
MODE_READ_INPUT = 1


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
    #tests go here
