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
    Add the require table.
    """
    schema = """
        CREATE TABLE public.require (
            environment uuid NOT NULL,
            resource_set_dependent uuid NOT NULL,
            resource_id_dependent varchar NOT NULL,
            resource_id_dependency varchar NOT NULL,
            CONSTRAINT require_pkey PRIMARY KEY (
                environment, resource_set_dependent, resource_id_dependent, resource_id_dependency
            ),
            CONSTRAINT require_resource_fkey FOREIGN KEY (environment, resource_set_dependent, resource_id_dependent)
                REFERENCES public.resource (environment, resource_set, resource_id) ON DELETE CASCADE
        );

        CREATE INDEX require_environment_resource_id_dependency_index
            ON public.require (environment, resource_id_dependency);

        INSERT INTO public.require (environment, resource_set_dependent, resource_id_dependent, resource_id_dependency)
        SELECT DISTINCT r.environment, r.resource_set, r.resource_id, req.resource_id_dependency
        FROM public.resource AS r
        CROSS JOIN LATERAL jsonb_array_elements_text(
            COALESCE(r.attributes->'requires', '[]'::jsonb)
        ) AS req(resource_id_dependency);
    """
    await connection.execute(schema)
