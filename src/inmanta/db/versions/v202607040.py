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
    Create the token table: a registry of issued, revocable authentication tokens. A token that
    carries a jti claim is only accepted if its jti is present in this table and not revoked.
    """
    schema = """
        CREATE TABLE public.token (
            jti uuid PRIMARY KEY,
            created_by varchar,
            client_types varchar[] DEFAULT ARRAY[]::varchar[] NOT NULL,
            environment uuid REFERENCES environment(id) ON DELETE CASCADE,
            issued_at timestamp with time zone NOT NULL,
            expires_at timestamp with time zone,
            revoked boolean DEFAULT false NOT NULL,
            last_used timestamp with time zone
        );

        CREATE INDEX token_environment_index ON public.token USING btree (environment);
    """
    await connection.execute(schema)
