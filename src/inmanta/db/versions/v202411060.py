"""
    Copyright 2024 Inmanta

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
    Add `resource_status` field to the resource_persistent_state table and populate it.
    """
    schema = """
        CREATE TYPE public.new_resource_status AS ENUM ('UP_TO_DATE', 'HAS_UPDATE', 'UNDEFINED', 'ORPHAN');
        ALTER TABLE public.resource_persistent_state ADD COLUMN resource_status new_resource_status;
        WITH latest_released_version_per_environment AS (
            -- Create table with latest released version for each environment
            SELECT environment, MAX(version) AS version
            FROM public.configurationmodel
            WHERE released IS TRUE
            GROUP BY environment
        )
        UPDATE public.resource_persistent_state AS rps
        SET resource_status=(
            CASE WHEN (
                     NOT EXISTS(
                         SELECT *
                         FROM public.resource AS c
                         WHERE c.environment=rps.environment
                               AND c.model=(
                                   SELECT latest.version
                                   FROM latest_released_version_per_environment AS latest
                                   WHERE latest.environment=rps.environment
                               )
                               AND c.resource_id=rps.resource_id
                     )
                 )
                     THEN 'ORPHAN'::new_resource_status
                 WHEN EXISTS (
                        SELECT *
                        FROM public.resource AS c2
                        WHERE c2.environment=rps.environment
                              AND c2.model=(
                                  SELECT latest.version
                                  FROM latest_released_version_per_environment AS latest
                                  WHERE latest.environment=rps.environment
                              )
                              AND c2.resource_id=rps.resource_id
                              AND c2.status = 'undefined'::resourcestate
                     )
                     THEN 'UNDEFINED'::new_resource_status
                 WHEN rps.last_non_deploying_status = 'deployed'
                     THEN 'UP_TO_DATE'::new_resource_status
                     ELSE 'HAS_UPDATE'::new_resource_status
            END
        );
        ALTER TABLE public.resource_persistent_state ALTER COLUMN resource_status SET NOT NULL;
    """
    await connection.execute(schema)
