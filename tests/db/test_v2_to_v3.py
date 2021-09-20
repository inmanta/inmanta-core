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

import pytest
from asyncpg import Connection

from db.common import PGRestore
from inmanta import data, protocol
from inmanta.resources import Id
from inmanta.server.bootloader import InmantaBootloader


@pytest.fixture
async def migrate_v2_to_v3(hard_clean_db, hard_clean_db_post, postgresql_client: Connection, async_finalizer, server_config):
    # Get old tables
    with open(os.path.join(os.path.dirname(__file__), "dumps/v2.sql"), "r") as fh:
        await PGRestore(fh.readlines(), postgresql_client).run()

    ibl = InmantaBootloader()

    await ibl.start()
    yield
    await ibl.stop()


@pytest.mark.asyncio
@pytest.mark.slowtest
async def test_environment_update(migrate_v2_to_v3, async_finalizer, server_config):
    client = protocol.Client("client")

    result = await client.list_environments()

    names = sorted([env["name"] for env in result.result["environments"]])
    name_to_id = {env["name"]: env["id"] for env in result.result["environments"]}
    assert names == ["dev-1", "dev-2"]

    env1 = await data.Environment.get_by_id(name_to_id["dev-1"])

    assert env1.last_version == 1569583847

    result = await client.create_environment(project_id=env1.project, name="dev-3")
    assert result.code == 200

    env3 = await data.Environment.get_by_id(result.result["environment"]["id"])
    assert env3.last_version == 0

    e1_next = await env1.get_next_version()
    assert e1_next == 1569583848

    e1_next = await env1.get_next_version()
    assert e1_next == 1569583849

    e3_next = await env3.get_next_version()
    assert e3_next == 1

    e3_next = await env3.get_next_version()
    assert e3_next == 2


@pytest.mark.asyncio
async def test_addition_resource_type_column(migrate_v2_to_v3, postgresql_client: Connection):
    results = await postgresql_client.fetch("SELECT resource_version_id, resource_type FROM public.Resource")
    for r in results:
        assert r["resource_type"] is not None
        parsed_id = Id.parse_id(r["resource_version_id"])
        assert r["resource_type"] == parsed_id.entity_type
