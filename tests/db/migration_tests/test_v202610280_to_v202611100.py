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

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_require_table(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    The require table is populated with the requires stored in the attributes of the resources.
    """
    requires_in_attributes = {tuple(record) for record in await postgresql_client.fetch("""
            SELECT r.environment, r.resource_set, r.resource_id, req.resource_id_dependency
            FROM public.resource AS r
            CROSS JOIN LATERAL jsonb_array_elements_text(r.attributes->'requires') AS req(resource_id_dependency)
            """)}
    assert requires_in_attributes

    await migrate_db_from()

    requires_in_table = {tuple(record) for record in await postgresql_client.fetch("""
            SELECT environment, resource_set_dependent, resource_id_dependent, resource_id_dependency
            FROM public.require
            """)}
    assert requires_in_table == requires_in_attributes
