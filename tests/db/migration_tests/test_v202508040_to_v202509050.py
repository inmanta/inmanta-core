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
from collections import abc, defaultdict

import asyncpg
import pytest

from inmanta import data

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_resource_set_table_and_drop_model(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:

    await migrate_db_from()
    # Check if resource_set table is populated correctly
    res_sets_raw = await data.ResourceSet.get_list()
    assert len(res_sets_raw) != 0
    res_sets = {(r.environment, r.id) for r in res_sets_raw}
    assert len(res_sets_raw) == len(res_sets)
    resources = await data.Resource.get_list()
    resource_set_info = {(r.environment, r.resource_set) for r in resources}
    assert res_sets == resource_set_info
    resource_set_names = {r.name for r in res_sets_raw}
    assert None in resource_set_names
    assert "set-a" in resource_set_names

    records = await postgresql_client.fetch(
        """
        SELECT rs.name, rscm.*
        FROM public.resource_set_configuration_model AS rscm
        JOIN public.resource_set AS rs
            ON rs.environment=rscm.environment AND rs.id=rscm.resource_set
        ORDER BY rs.name
        """
    )
    assert len(records) == 14
    env_1 = await data.Environment.get_one(name="dev-1")
    assert env_1

    env_3 = await data.Environment.get_one(name="dev-3")
    assert env_3

    expected_result = {
        (env_1.id, 1): [None],
        (env_1.id, 2): [None],
        (env_1.id, 3): [None],
        (env_1.id, 4): [None],
        (env_1.id, 5): [None],
        (env_1.id, 6): [None],
        (env_1.id, 7): ["set-a", "set-b", None],
        (env_1.id, 8): ["set-a", None],
        (env_3.id, 1): [None],
        (env_3.id, 2): [None],
        (env_3.id, 3): [None],
    }
    actual_result = defaultdict(list)
    for record in records:
        key = (record["environment"], record["model"])
        value = record["name"]
        actual_result[key].append(value)

    assert expected_result == dict(actual_result)
