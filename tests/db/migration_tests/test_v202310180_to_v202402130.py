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
from collections import abc

import asyncpg
import pytest

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_non_null_constraint(
    postgresql_client: asyncpg.Connection,
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:
    r"""
    This migration script adds
      - the non-null constraint to the ``undeployable`` and ``skipped_for_undeployable``
        columns of the configurationmodel table.
      - default empty arrays instead of NULL for these columns
    """

    query = """
        SELECT undeployable, skipped_for_undeployable FROM public.configurationmodel
        WHERE environment ='35707199-1500-4ff4-a853-51413de9e736'
        AND version=5;
    """
    result = await postgresql_client.fetch(query)

    assert result[0]["undeployable"] is None
    assert result[0]["skipped_for_undeployable"] is None

    await migrate_db_from()

    result = await postgresql_client.fetch(query)

    assert isinstance(result[0]["undeployable"], list)
    assert len(result[0]["undeployable"]) == 0
    assert isinstance(result[0]["skipped_for_undeployable"], list)
    assert len(result[0]["skipped_for_undeployable"]) == 0
