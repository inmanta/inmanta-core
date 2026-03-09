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

from asyncpg import Connection


async def update(connection: Connection) -> None:
    """
    Replace heartbeat-based agent sessions with WebSocket-based scheduler sessions.

    - Drop agent.id_primary FK and index (references removed agentinstance table)
    - Drop agent.last_failover column (no longer meaningful without heartbeat sessions)
    - Drop agentinstance table
    - Rename agentprocess to schedulersession and drop last_seen column
    - Rename indexes to match new table name
    """
    schema = """
        DROP INDEX IF EXISTS public.agent_id_primary_index;
        ALTER TABLE public.agent DROP CONSTRAINT IF EXISTS agent_id_primary_fkey;
        ALTER TABLE public.agent DROP COLUMN id_primary;
        ALTER TABLE public.agent DROP COLUMN last_failover;

        DROP TABLE public.agentinstance;

        ALTER TABLE public.agentprocess RENAME TO schedulersession;
        ALTER TABLE public.schedulersession DROP COLUMN last_seen;

        ALTER INDEX agentprocess_env_expired_index RENAME TO schedulersession_env_expired_index;
        ALTER INDEX agentprocess_env_hostname_expired_index RENAME TO schedulersession_env_hostname_expired_index;
        ALTER INDEX agentprocess_expired_index RENAME TO schedulersession_expired_index;
        ALTER INDEX agentprocess_sid_expired_index RENAME TO schedulersession_sid_expired_index;
    """
    await connection.execute(schema)
