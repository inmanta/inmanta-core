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

from inmanta import const, data

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_resource_diff_table(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    This adds the resource_diff table to the database and the non_compliant_diff column to the rps table.
    """
    await migrate_db_from()
    all_rps = await data.ResourcePersistentState.get_list()

    non_compliant_rps = {
        rps for rps in all_rps if rps.last_non_deploying_status is const.NonDeployingResourceState.non_compliant
    }
    assert len(non_compliant_rps) == 2
    remaining_rps = set(all_rps) - non_compliant_rps
    assert len(remaining_rps) > 0

    for rps in remaining_rps:
        assert rps.non_compliant_diff is None
    for rps in non_compliant_rps:
        assert rps.non_compliant_diff is not None

    result = await data.ResourcePersistentState.get_compliance_report(
        env=next(iter(non_compliant_rps)).environment, resource_ids=[rps.resource_id for rps in non_compliant_rps]
    )
    assert len(result) == 2
