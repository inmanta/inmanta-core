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

from asyncpg import Connection


async def update(connection: Connection) -> None:
    """
    Rename some rps columns and values
    """
    schema = """
        ALTER TABLE public.resource_persistent_state RENAME COLUMN blocked_status TO blocked;
        ALTER TABLE public.resource_persistent_state RENAME COLUMN deployment_result TO last_deploy_result;

        UPDATE public.resource_persistent_state
        SET blocked=(
                CASE blocked
                    WHEN 'YES' THEN 'BLOCKED'
                    ELSE 'NOT_BLOCKED'
                END
            )
        ;
    """
    await connection.execute(schema)