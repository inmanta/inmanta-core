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

        -- Populate resource_status field for non-orphan resources
        WITH latest_released_version_per_environment AS (
            SELECT environment, MAX(version) AS version
            FROM public.configurationmodel
            WHERE released IS TRUE
            GROUP BY environment
        )
        UPDATE public.resource_persistent_state AS rps
        SET resource_status=(
            CASE
                -- The resource_persistent_state.last_non_deploying_status column is only populated for
                -- actual deployment operations to prevent locking issues. This case-statement calculates
                -- the correct state from the combination of the resource table and the resource_persistent_state table.
                WHEN r.status = 'undefined'::resourcestate
                    -- The undefined states are not tracked in the resource_persistent_state table.
                    THEN 'UNDEFINED'::new_resource_status
                WHEN rps.last_deployed_attribute_hash != r.attribute_hash
                    -- The hash changed since the last deploy -> new desired state
                    THEN 'HAS_UPDATE'::new_resource_status
                    -- No override required, use last known state from actual deployment
                    ELSE (
                        CASE
                            WHEN rps.last_non_deploying_status = 'deployed'::non_deploying_resource_state
                                THEN 'UP_TO_DATE'::new_resource_status
                                ELSE 'HAS_UPDATE'::new_resource_status
                        END
                    )
            END
        )
        FROM resource AS r
        WHERE r.environment=rps.environment
            AND r.model=(
                SELECT lrv.version
                FROM latest_released_version_per_environment AS lrv
                WHERE lrv.environment=rps.environment
            )
            AND r.resource_id=rps.resource_id;

        -- If the resource_status column is still NULL, it's either an orphan or the resource belongs to a version newer
        -- then the latest released version.
        WITH latest_released_version_per_environment AS (
            SELECT environment, MAX(version) AS version
            FROM public.configurationmodel
            WHERE released IS TRUE
            GROUP BY environment
        )
        UPDATE public.resource_persistent_state AS rps
        SET resource_status=(
            CASE
                WHEN (
                    NOT EXISTS(
                        SELECT *
                        FROM resource AS r
                        WHERE r.environment=rps.environment
                            AND r.model>=(
                                SELECT latest.version
                                FROM latest_released_version_per_environment AS latest
                                WHERE latest.environment=rps.environment
                            )
                            AND r.resource_id=rps.resource_id
                    )
                )
                THEN 'ORPHAN'::new_resource_status
                ELSE 'HAS_UPDATE'::new_resource_status
            END
        )
        WHERE rps.resource_status IS NULL;

        ALTER TABLE public.resource_persistent_state ALTER COLUMN resource_status SET NOT NULL;
    """
    await connection.execute(schema)
