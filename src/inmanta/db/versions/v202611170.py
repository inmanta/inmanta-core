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
    Store the result of each resource of a dry run in its own row of the new dryrun_resource table, instead of in the
    resources column of the dryrun table. The todo column is dropped: it is derived from the number of stored results.
    """
    schema = """
        CREATE TABLE public.dryrun_resource (
            dryrun_id uuid NOT NULL,
            resource_id varchar NOT NULL,
            changes jsonb NOT NULL DEFAULT '{}'::jsonb,
            diff_status varchar,
            CONSTRAINT dryrun_resource_pkey PRIMARY KEY (dryrun_id, resource_id),
            CONSTRAINT dryrun_resource_dryrun_id_fkey FOREIGN KEY (dryrun_id)
                REFERENCES public.dryrun (id) ON DELETE CASCADE
        );

        INSERT INTO public.dryrun_resource (dryrun_id, resource_id, changes, diff_status)
        SELECT
            d.id,
            regexp_replace(r.value->>'id', ',v=[0-9]+$', ''),
            COALESCE(r.value->'changes', '{}'::jsonb),
            r.value->>'diff_status'
        FROM public.dryrun AS d
        CROSS JOIN LATERAL jsonb_each(d.resources) AS r
        ON CONFLICT (dryrun_id, resource_id) DO NOTHING;

        ALTER TABLE public.dryrun DROP COLUMN resources, DROP COLUMN todo;
    """
    await connection.execute(schema)
