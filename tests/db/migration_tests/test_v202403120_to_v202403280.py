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

    # Verify that each resource in the resource table has exactly one corresponding entry in the persistent state table,
    # with which it shares all id-derived values.
    # Exactly one because:
    #   - join condition includes primary key on both tables => right side of join is at most 1
    #   - given that right side of join is at most 1, the total number of joined rows equals the number of resources with
    #       exactly one match
    records = await postgresql_client.fetch(
        """
        WITH resources_with_matching_rps AS (
            SELECT COUNT(*)
            FROM public.resource AS r
            JOIN public.resource_persistent_state AS rps
            ON
                r.environment = rps.environment
                AND r.resource_id = rps.resource_id
                AND r.resource_type = rps.resource_type
                AND r.agent = rps.agent
                AND r.resource_id_value = rps.resource_id_value
        )
        SELECT
            resources_with_matching_rps.count AS nb_matching,
            all_resources.count AS nb_total
        FROM resources_with_matching_rps
        CROSS JOIN (SELECT COUNT(*) FROM public.resource) AS all_resources
        """
    )

    assert len(records) == 1
    assert records[0]["nb_matching"] == records[0]["nb_total"]
