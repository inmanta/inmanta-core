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
    Add the revoked_at column to the token table: the moment a token was revoked, used for auditing and
    to bound how long revoked tokens are kept. Already-revoked tokens are backfilled with the migration
    time so the retention-based cleanup applies to them as well.
    """
    schema = """
        ALTER TABLE public.token ADD COLUMN revoked_at timestamp with time zone;
        UPDATE public.token SET revoked_at = now() WHERE revoked;
    """
    await connection.execute(schema)
