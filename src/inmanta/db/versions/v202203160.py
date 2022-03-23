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
    """
    Add the last_stable_status field in the public.resource table which
    represent the last stable state of a given resource. A stable state
    is any state different from the deploying state.
    """
    schema_updates = """
CREATE TYPE non_deploying_resource_state AS ENUM('unavailable', 'skipped', 'dry', 'deployed', 'failed', 'available',
                                                 'cancelled', 'undefined', 'skipped_for_undefined', 'processing_events');

ALTER TABLE public.resource ADD COLUMN last_non_deploying_status non_deploying_resource_state NOT NULL DEFAULT 'available';

-- Change the default value of the `last_non_deploying_status` column to the correct value.
WITH table_last_non_deploying_status AS (
    SELECT DISTINCT ON (r.environment, r.resource_version_id) r.environment, r.resource_version_id, ra.status
    FROM resource AS r INNER JOIN resourceaction AS ra
         ON r.environment=ra.environment AND ra.resource_version_ids::varchar[] @> ARRAY[r.resource_version_id]::varchar[]
    WHERE ra.status IS NOT NULL AND ra.status!='deploying'
    ORDER BY r.environment, r.resource_version_id, ra.started DESC
)
UPDATE resource AS r
SET last_non_deploying_status=s.status::text::non_deploying_resource_state
FROM table_last_non_deploying_status AS s
WHERE r.environment=s.environment AND r.resource_version_id=s.resource_version_id
    """
    async with connection.transaction():
        await connection.execute(schema_updates)
