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
    Create resource_diff table and add the non_compliant_diff field to the rps table.
    Populate resource_diff table with the diffs from non_compliant resources found on the resourceaction table
    """
    schema = """
    CREATE TABLE public.resource_diff(
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        environment uuid NOT NULL,
        resource_id character varying NOT NULL,
        diff jsonb NOT NULL,
        created timestamp with time zone NOT NULL,
        FOREIGN KEY (environment, resource_id)
            REFERENCES public.resource_persistent_state(environment, resource_id) ON DELETE CASCADE
    );

    -- used for purging old_diffs --
    CREATE INDEX resource_diff_environment_created ON public.resource_diff (environment, created);

    -- used to join with rps table --
    CREATE INDEX resource_diff_environment_resource_id ON public.resource_diff (environment, resource_id);

    ALTER TABLE public.resource_persistent_state
        ADD COLUMN non_compliant_diff uuid,
        ADD CONSTRAINT resource_persistent_state_non_compliant_diff_fkey
        FOREIGN KEY (non_compliant_diff) REFERENCES public.resource_diff(id) ON DELETE RESTRICT;
    """

    await connection.execute(schema)

    result = await connection.fetchval("""
        SELECT 1
        FROM public.resource_persistent_state AS rps
        WHERE rps.last_non_deploying_status::text='non_compliant'
        LIMIT 1;
    """)
    if result:
        await connection.execute("""
    -- populate resource_diff table --
            WITH non_compliant_resources AS (
                SELECT rps.environment, rps.resource_id
                FROM public.resource_persistent_state AS rps
                WHERE rps.last_non_deploying_status::text='non_compliant'
            ),
            changes_for_non_compliant_resources AS (
                SELECT DISTINCT ON (ra.environment, rar.resource_id)
                    ra.environment as environment,
                    ra.changes as changes,
                    ra.finished as last_executed_at,
                    rar.resource_id as resource_id
                FROM public.resourceaction as ra
                INNER JOIN public.resourceaction_resource as rar
                    ON ra.environment = rar.environment
                    AND ra.action_id = rar.resource_action_id
                INNER JOIN non_compliant_resources AS ncr
                    ON ra.environment=ncr.environment
                    AND rar.resource_id=ncr.resource_id
                WHERE ra.changes IS NOT NULL
                  AND ra.changes != '{}'
                  AND ra.action::text='deploy'
                  AND ra.status::text='non_compliant'
                ORDER BY
                    ra.environment,
                    rar.resource_id,
                    ra.finished DESC
            ),
            new_diff AS (
                INSERT INTO resource_diff (environment, resource_id, created, diff)
                SELECT environment, resource_id, last_executed_at as created, changes as diff
                FROM changes_for_non_compliant_resources
                RETURNING id, environment, resource_id
            )
            UPDATE public.resource_persistent_state AS rps
            SET non_compliant_diff=nd.id
            FROM new_diff AS nd
            WHERE rps.environment=nd.environment
              AND rps.resource_id=nd.resource_id;
    """)
