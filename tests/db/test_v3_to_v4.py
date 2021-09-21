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

import os
import uuid
from collections import defaultdict

import pytest
from asyncpg import Connection

from db.common import PGRestore
from inmanta.resources import Id
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
@pytest.mark.slowtest
async def migrate_v3_to_v4(hard_clean_db, hard_clean_db_post, postgresql_client: Connection, async_finalizer, server_config):
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v3.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    for table_name in ["form", "formrecord", "resourceversionid"]:
        assert await does_table_exist(postgresql_client, table_name)

    result = await postgresql_client.fetch("SELECT action_id, resource_version_id FROM public.resourceversionid")
    resource_version_id_dict = defaultdict(list)
    for r in result:
        resource_version_id_dict[r["action_id"]].append(r["resource_version_id"])

    ibl = InmantaBootloader()

    # When the bootloader is started, it also executes the migration to v4
    await ibl.start()
    yield resource_version_id_dict
    await ibl.stop()


@pytest.mark.asyncio
async def test_db_migration(migrate_v3_to_v4, postgresql_client: Connection):
    for table_name in ["form", "formrecord", "resourceversionid"]:
        assert not await does_table_exist(postgresql_client, table_name)

    result = await postgresql_client.fetch(
        """SELECT environment, version, action_id, resource_version_ids
           FROM public.resourceaction
        """
    )
    for r in result:
        assert r["environment"] == uuid.UUID("6c66ca44-da58-4924-ad17-151abc2f3726")
        rvids_old_table = migrate_v3_to_v4[r["action_id"]]
        rvids_new_table = r["resource_version_ids"]
        assert sorted(rvids_old_table) == sorted(rvids_new_table)
        assert r["version"] == int(Id.parse_id(rvids_old_table[0]).version)
    # Verify that the number of action_ids match
    assert len(result) == len(migrate_v3_to_v4)


async def does_table_exist(postgresql_client: Connection, table_name: str) -> bool:
    result = await postgresql_client.fetch(
        f"""
            SELECT EXISTS
            (SELECT 1
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename = '{table_name}');"""
    )
    return result[0]["exists"]
