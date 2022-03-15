"""
    Copyright 2022 Inmanta

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

DISABLED = False


async def update(connection: Connection) -> None:
    schema = """
    CREATE TYPE notificationseverity AS ENUM('message', 'info', 'success', 'warning', 'error');

    -- Table: public.notification
    CREATE TABLE IF NOT EXISTS public.notification (
        id uuid NOT NULL,
        environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
        created TIMESTAMP WITH TIME ZONE NOT NULL,
        title varchar NOT NULL,
        message varchar NOT NULL,
        severity notificationseverity DEFAULT 'message',
        uri varchar NOT NULL,
        read boolean NOT NULL DEFAULT FALSE,
        cleared boolean NOT NULL DEFAULT FALSE,
        PRIMARY KEY(environment, id)
    );
    CREATE INDEX IF NOT EXISTS notification_env_created_id_index ON notification (environment, created DESC, id);
    """
    async with connection.transaction():
        await connection.execute(schema)
