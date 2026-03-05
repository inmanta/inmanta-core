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
async def test_replace_heartbeat_sessions_with_websocket(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    # Verify pre-migration state
    old_tables = {
        r["tablename"] for r in await postgresql_client.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    }
    assert "agentprocess" in old_tables
    assert "agentinstance" in old_tables
    assert "schedulersession" not in old_tables

    # Verify agent table has id_primary column
    agent_cols = {
        r["column_name"]
        for r in await postgresql_client.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'agent'")
    }
    assert "id_primary" in agent_cols

    await migrate_db_from()

    # Verify post-migration state
    new_tables = {
        r["tablename"] for r in await postgresql_client.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    }
    assert "schedulersession" in new_tables
    assert "agentprocess" not in new_tables
    assert "agentinstance" not in new_tables

    # Verify agent.id_primary column is removed
    agent_cols_after = {
        r["column_name"]
        for r in await postgresql_client.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'agent'")
    }
    assert "id_primary" not in agent_cols_after

    # Verify last_seen column is removed from schedulersession
    session_cols = {
        r["column_name"]
        for r in await postgresql_client.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'schedulersession'"
        )
    }
    assert "last_seen" not in session_cols

    # Verify renamed indexes exist
    indexes = {
        r["indexname"]
        for r in await postgresql_client.fetch("SELECT indexname FROM pg_indexes WHERE tablename = 'schedulersession'")
    }
    assert "schedulersession_env_expired_index" in indexes
    assert "schedulersession_env_hostname_expired_index" in indexes
    assert "schedulersession_expired_index" in indexes
    assert "schedulersession_sid_expired_index" in indexes
