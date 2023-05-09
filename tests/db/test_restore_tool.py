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
"""
import pytest
from asyncpg import Connection

from db.common import PGRestore


@pytest.mark.asyncio
async def test_pg_restore(hard_clean_db, hard_clean_db_post, postgresql_client: Connection):

    inp = r"""
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
