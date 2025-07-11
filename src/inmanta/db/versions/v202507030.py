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
    * Add foreign key from the notification to the compile table.
    * Remove notifications that have a reference to a compile that was removed.
    """
    schema = """
    -- Add compile_id column to notification table.
    ALTER TABLE public.notification
        ADD COLUMN compile_id UUID;

    -- Populate compile_id column.
    UPDATE public.notification
    SET compile_id=regexp_replace(uri, '^/api/v2/compilereport/', '')::uuid
    WHERE uri ~ '^/api/v2/compilereport/';

    -- Delete notifications that reference a compile that no longer exists in
    -- the database.
    DELETE FROM public.notification AS n
    WHERE n.compile_id IS NOT NULL AND NOT EXISTS(
        SELECT *
        FROM public.compile AS c
        WHERE c.id=n.compile_id
    );

    -- Add back the foreign key constraint now that the update + delete are done
    ALTER TABLE public.notification ADD CONSTRAINT notification_compile_id_fkey
        FOREIGN KEY (compile_id) REFERENCES public.compile(id) ON DELETE CASCADE;

    """
    await connection.execute(schema)
