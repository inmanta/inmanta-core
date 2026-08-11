"""
Copyright 2026 Inmanta

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
async def test_replace_is_orphan_with_orphaned_after(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    # Get orphan status before migration
    rps_before = {}
    results = await postgresql_client.fetch(f"""
        SELECT *
        FROM {data.ResourcePersistentState.table_name()}
        """)
    for rps in results:
        rps_before[rps["resource_id"]] = rps["is_orphan"]
    await migrate_db_from()

    # Get a list of the latest version processed by the scheduler in each env
    schedulers = await data.Scheduler.get_list()
    latest_version_per_env = {}
    for scheduler in schedulers:
        latest_version_per_env[scheduler.environment] = scheduler.last_processed_model_version

    all_rps = await data.ResourcePersistentState.get_list()
    for rps in all_rps:
        if rps.orphaned_after is not None:
            assert rps_before[rps.resource_id]
            assert 0 < rps.orphaned_after < latest_version_per_env[rps.environment]
        else:
            assert not rps_before[rps.resource_id]
