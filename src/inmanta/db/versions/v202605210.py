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
    Add a partial index on resource_persistent_state(environment) WHERE is_deploying.

    The scheduler issues a sweep UPDATE on (re)start that resets is_deploying for all
    rows in an environment. Without this index the sweep seq-scans the env and locks
    every visited row, which under load queues per-row UPDATEs from the executor
    behind it. With the partial index the sweep targets only the currently-deploying
    rows.
    """
    schema = """
    CREATE INDEX resource_persistent_state_environment_is_deploying_index
        ON public.resource_persistent_state (environment) WHERE is_deploying;
    """
    await connection.execute(schema)
