"""
    Copyright 2023 Inmanta
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
    schema = """
    -- Add the 'last_success' column
    ALTER TABLE public.resource ADD COLUMN last_success TIMESTAMP WITH TIME ZONE;
    """
    await connection.execute(schema)

    # For each environment
    # For the latest released version
    # Set the last success
    update_query = """
    UPDATE resource as r
    SET last_success = (
        SELECT max(started)
        FROM resourceaction_resource as jt
        INNER JOIN resourceaction as ra
            ON ra.action_id = jt.resource_action_id
        WHERE
            jt.environment=r.environment
            AND ra.environment=r.environment
            AND jt.resource_id=r.resource_id
            AND ra.action='deploy'
            AND ra.status='deployed'
            AND NOT (ra.messages[1]->>'msg' = 'Setting deployed due to known good status')
    )
    WHERE ROW(model, environment) in (
        SELECT
            max(version) as version,
            environment
        FROM configurationmodel where released = True
        GROUP BY environment);
    """
    await connection.execute(update_query)
