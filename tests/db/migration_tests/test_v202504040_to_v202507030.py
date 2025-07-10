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
    compile_id = uuid.UUID("06c734f1-2819-40d9-a1b3-e5d882c4b8b1")
    result = await data.Notification.get_list(connection=postgresql_client)
    assert len(result) == 1
    assert result[0].uri == f"/api/v2/compilereport/{compile_id}"
    assert result[0].compile_id is None

    # Run migration script
    await migrate_db_from()

    result = await data.Notification.get_list(connection=postgresql_client)
    assert len(result) == 1
    assert result[0].uri == f"/api/v2/compilereport/{compile_id}"
    assert result[0].compile_id == compile_id
