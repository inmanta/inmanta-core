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
    Update the schema of the environment.settings column.
    """
    schema = """
    -- Migrate settings in environment table to new schema
    UPDATE public.environment AS e
    SET settings=(
        jsonb_build_object(
            'settings',
            (
                SELECT jsonb_object_agg(
                    t.key,
                    jsonb_build_object(
                        'value',
                        t.value,
                        'protected',
                        FALSE,
                        'protected_by',
                        NULL
                    )
                )
                FROM jsonb_each(e.settings) AS t(key, value)
            )
        )
    )
    """
    await connection.execute(schema)
