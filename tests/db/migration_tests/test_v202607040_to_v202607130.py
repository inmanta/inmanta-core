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
import uuid
from collections import abc

import asyncpg
import pytest

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_token_revoked_at_column(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    # Seed the pre-migration token table with a revoked and an unrevoked token.
    revoked_jti = uuid.uuid4()
    active_jti = uuid.uuid4()
    await postgresql_client.execute(
        "INSERT INTO public.token (jti, issued_at, revoked) VALUES ($1, now(), true), ($2, now(), false)",
        revoked_jti,
        active_jti,
    )

    await migrate_db_from()

    # The revoked token is backfilled with a revocation time; the active one stays NULL.
    assert await postgresql_client.fetchval("SELECT revoked_at FROM token WHERE jti=$1", revoked_jti) is not None
    assert await postgresql_client.fetchval("SELECT revoked_at FROM token WHERE jti=$1", active_jti) is None
