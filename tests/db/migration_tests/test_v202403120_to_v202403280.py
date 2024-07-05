"""
    Copyright 2024 Inmanta

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
from collections.abc import Awaitable, Callable

import asyncpg
import pytest

import inmanta.resources

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_replace_index(
    postgresql_client: asyncpg.Connection,
    migrate_db_from: Callable[[], Awaitable[None]],
) -> None:
    # Assert invariant of the migration: (resource_type, agent, resource_id_value) is uniquely derived from the table identity
    records = await postgresql_client.fetch(
        """
        SELECT COUNT(DISTINCT resource_id)
        FROM public.resource
        GROUP BY (environment, resource_type, agent, resource_id_value)
        """
    )
    # there should be no duplicates
    assert all(record["count"] == 1 for record in records)

    # execute migration
    await migrate_db_from()

    # Verify that each distinct resource in the resource table has exactly one corresponding entry in the persistent state
    # table, with which it shares all id-derived values.
    rps_records = await postgresql_client.fetch("SELECT * FROM public.resource_persistent_state")
    resource_count_records = await postgresql_client.fetch("SELECT COUNT(DISTINCT resource_id) FROM public.resource")

    def verify_rps(rid: str, resource_type: str, agent: str, resource_id_value: str) -> None:
        parsed: inmanta.resources.Id = inmanta.resources.Id.parse_id(rid)
        assert (parsed.entity_type, parsed.agent_name, parsed.attribute_value) == (resource_type, agent, resource_id_value)

    assert len(resource_count_records) == 1
    assert len(rps_records) == resource_count_records[0]["count"]
    for record in rps_records:
        verify_rps(record["resource_id"], record["resource_type"], record["agent"], record["resource_id_value"])
