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

import json
import os
import re
import uuid
from collections import abc

import asyncpg
import pytest

from inmanta import data
from inmanta.data.model import ResourceDiffStatus
from inmanta.resources import Id

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_move_dryrun_results_to_own_table(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    The results stored in the resources column of a dryrun are moved to one row per resource in dryrun_resource, and the
    todo count derived from them matches the stored one. Results that can't be attributed to a resource are dropped.
    """
    finished = await postgresql_client.fetchrow("SELECT environment, model FROM public.dryrun")
    assert finished is not None

    # A dry run that is still running, with a result without changes and a malformed result next to a regular one
    partial_id = uuid.uuid4()
    partial_resources = {
        "key1": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {"value": {"current": "a", "desired": "b"}}},
        "key2": {"id": "test::Resource[agent1,key=key2],v=1", "changes": None},
        "no_id": {"changes": {}},
        "not_an_object": [],
    }
    # A dry run without any result yet
    empty_id = uuid.uuid4()
    for dryrun_id, total, todo, resources in ((partial_id, 5, 3, partial_resources), (empty_id, 4, 4, {})):
        await postgresql_client.execute(
            """
            INSERT INTO public.dryrun (id, environment, model, date, total, todo, resources)
            VALUES ($1, $2, $3, now(), $4, $5, $6::jsonb)
            """,
            dryrun_id,
            finished["environment"],
            finished["model"],
            total,
            todo,
            json.dumps(resources),
        )

    records = await postgresql_client.fetch("SELECT id, todo, resources FROM public.dryrun")
    expected: dict[uuid.UUID, tuple[int, dict[str, tuple[object, ResourceDiffStatus | None]]]] = {}
    for record in records:
        resources = json.loads(record["resources"]) if isinstance(record["resources"], str) else record["resources"]
        results = {
            Id.parse_id(value["id"]).resource_str(): (
                value["changes"] if value["changes"] is not None else {},
                ResourceDiffStatus(value["diff_status"]) if "diff_status" in value else None,
            )
            for value in resources.values()
            if isinstance(value, dict) and "id" in value
        }
        expected[record["id"]] = (record["todo"], results)
    assert len(expected[partial_id][1]) == 2
    assert any(
        diff_status is not None for _, results in expected.values() for _, diff_status in results.values()
    ), "The dump should hold a result with a diff status"

    await migrate_db_from()

    dryruns = await data.DryRun.list_dryruns()
    assert {dryrun.id for dryrun in dryruns} == expected.keys()
    for dryrun in dryruns:
        todo, results = expected[dryrun.id]
        assert dryrun.todo == todo
        stored = await data.DryRun.get_results(dryrun.id)
        assert {result.resource_id: (result.changes, result.diff_status) for result in stored} == results

    columns = await postgresql_client.fetch(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='dryrun'"
    )
    assert not {"resources", "todo"} & {column["column_name"] for column in columns}
