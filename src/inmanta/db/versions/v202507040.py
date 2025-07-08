"""
Copyright 2025 Inmanta

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
    Create resource_set table
    """
    schema = """
    CREATE TABLE public.resource_set (
        name character varying NOT NULL,
        environment uuid NOT NULL,
        model integer NOT NULL,
        revision integer NOT NULL,
        PRIMARY KEY (name, environment, model, revision),
        FOREIGN KEY (environment, model)
            REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE,
    );

    INSERT INTO public.resource_set (name, environment, model, revision)
    SELECT DISTINCT
        resource.resource_set AS name,
        resource.environment,
        resource.model,
        resource.model AS revision
    FROM public.resource AS r
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.resource_set rs
        WHERE rs.name=r.resource_set
          AND rs.environment=r.environment
          AND rs.model=r.model
          AND rs.revision=r.model
    );

    ALTER TABLE ONLY public.resource
        ADD COLUMN revision integer;

    UPDATE public.resource
        SET revision=model;

    ALTER TABLE ONLY public.resource
        ALTER COLUMN revision SET NOT NULL;

    """
    await connection.execute(schema)
