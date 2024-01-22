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
import json
import os
import re
from collections import abc

import asyncpg
import pytest

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_non_expiring_facts(postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]) -> None:
    # This migration script adds a column. Just verify that the script doesn't fail.

    result = await postgresql_client.fetch(
    """
        SELECT * FROM public.environment;
    """
    )
    result = await postgresql_client.fetch(
        """
            SELECT * FROM public.parameter;
        """
    )

    # settings = json.loads(result[0]["settings"])
    print(result)
    await migrate_db_from()
    result = await postgresql_client.fetch(
    """
        SELECT * FROM public.environment;
    """
    )
    result = await postgresql_client.fetch(
        """
            SELECT * FROM public.parameter;
        """
    )

    print(result)
    a = 3
