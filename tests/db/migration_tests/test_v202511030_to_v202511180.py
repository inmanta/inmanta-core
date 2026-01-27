"""
Copyright 2025 Inmanta

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
import re
from collections import abc

import asyncpg
import pytest

from inmanta import data

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_make_discovery_resource_id_column_mandatory(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    # Make sure we have a discovered resource where the discovery_resource_id column is not set.
    await postgresql_client.execute(f"""
        UPDATE {data.DiscoveredResource.table_name()}
        SET discovery_resource_id=NULL
        WHERE discovered_resource_id='discovery::Discovered[myagent,name=discovered]'
        """)
    assert 2 == (await postgresql_client.fetchval(f"SELECT count(*) FROM {data.DiscoveredResource.table_name()}"))

    await migrate_db_from()

    assert 2 == (await postgresql_client.fetchval(f"SELECT count(*) FROM {data.DiscoveredResource.table_name()}"))
    # Verify that the discovered resource, with the discovery_resource_id column unset, is removed.
    assert "core::UnknownDiscoveryResource[internal,key=unknown]" == await postgresql_client.fetchval(f"""
        SELECT discovery_resource_id
        FROM {data.DiscoveredResource.table_name()}
        WHERE discovered_resource_id='discovery::Discovered[myagent,name=discovered]'
        """)
    assert "discovery::Discovery[discovery,name=discoverer]" == await postgresql_client.fetchval(f"""
        SELECT discovery_resource_id
        FROM {data.DiscoveredResource.table_name()}
        WHERE discovered_resource_id='discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]'
        """)
