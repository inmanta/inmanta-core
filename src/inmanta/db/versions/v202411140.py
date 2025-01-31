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
    * Create the scheduler table, that keeps track of the last model version processed by the scheduler,
      i.e. for which the scheduler state was written to the resource_persistent_state table.
    * Add columns to the resource_persistent_state table required to be able to recover the scheduler
      state on a restart of the server.
    """
    # final changes are made on top of these in v202501140.py
    schema = """
        -- Create and populate the scheduler table.
        CREATE TABLE public.scheduler (
            environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
            last_processed_model_version integer,
            PRIMARY KEY(environment)
        );

        INSERT INTO public.scheduler (SELECT id, NULL FROM public.environment);

        -- Add additional columns to the resource_persistent_state table that are required by the scheduler.
        ALTER TABLE public.resource_persistent_state
            ADD COLUMN current_intent_attribute_hash varchar,
            ADD COLUMN is_undefined boolean,
            ADD COLUMN is_orphan boolean,
            ADD COLUMN deployment_result varchar,
            ADD COLUMN blocked_status varchar;

        -- Populate the new columns in the resource_persistent_state table for resources part of the
        -- latest released model version.
        WITH latest_released_version_per_environment AS (
            SELECT environment, MAX(version) AS version
            FROM public.configurationmodel
            WHERE released IS TRUE
            GROUP BY environment
        )
        UPDATE public.resource_persistent_state AS rps
        SET
            current_intent_attribute_hash=r.attribute_hash,
            is_orphan=FALSE,
            is_undefined=(r.status = 'undefined'::resourcestate),
            deployment_result=(
                CASE
                    WHEN r.status = 'skipped'::resourcestate
                        THEN 'SKIPPED'
                    WHEN rps.last_non_deploying_status = 'deployed'::non_deploying_resource_state
                        THEN 'DEPLOYED'
                    WHEN rps.last_non_deploying_status = 'available'::non_deploying_resource_state
                        THEN 'NEW'
                        ELSE 'FAILED'
                END
            ),
            blocked_status=(
                CASE
                    WHEN r.status = 'undefined'::resourcestate OR r.status = 'skipped_for_undefined'::resourcestate
                    THEN 'YES'
                    ELSE 'NO'
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

        -- If the current_intent_attribute_hash column is still NULL, it's either an orphan
        -- or the resource belongs to a version newer than the latest released version.
        WITH latest_released_version_per_environment AS (
            SELECT environment, MAX(version) AS version
            FROM public.configurationmodel
            WHERE released IS TRUE
            GROUP BY environment
        )
        UPDATE public.resource_persistent_state AS rps
        SET
            is_orphan=(
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
            ),
            -- We might fill in incorrect values for the is_undefined, deployment_result and the blocked_status.
            -- Tracking this accurately would require an expensive database query. These defaults are a compromise
            -- between performance an accuracy.
            is_undefined=FALSE,
            deployment_result='NEW',
            blocked_status='NO'
        WHERE rps.current_intent_attribute_hash IS NULL;

        ALTER TABLE public.resource_persistent_state
            ALTER COLUMN is_undefined SET NOT NULL,
            ALTER COLUMN is_orphan SET NOT NULL,
            ALTER COLUMN deployment_result SET NOT NULL,
            ALTER COLUMN blocked_status SET NOT NULL;
    """
    await connection.execute(schema)
