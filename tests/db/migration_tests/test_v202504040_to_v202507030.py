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
import uuid
from collections import abc

import asyncpg
import pytest

from inmanta import data

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_foreign_key_notification_to_compile(
    postgresql_client: asyncpg.Connection,
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:
    result = await data.Notification.get_list(connection=postgresql_client)
    assert len(result) == 2
    assert all(r.compile_id is None for r in result)

    # Run migration script
    await migrate_db_from()

    # * One notification was removed because the associated compile not longer exists.
    # * The other notification was updated to reference the compile_id using a foreign key.
    compile_id = uuid.UUID("2f14f837-d103-45e9-932e-e75c07368e2f")
    result = await data.Notification.get_list(connection=postgresql_client)
    assert len(result) == 1
    assert result[0].uri == f"/api/v2/compilereport/{compile_id}"
    assert result[0].compile_id == compile_id
