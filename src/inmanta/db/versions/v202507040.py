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
        environment uuid NOT NULL,
        model integer NOT NULL,
        name character varying NOT NULL,
        revision integer NOT NULL,
        PRIMARY KEY (environment, name, model, revision),
        FOREIGN KEY (environment, model)
            REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE
    );

    INSERT INTO public.resource_set (environment, model, name, revision)
    SELECT DISTINCT
        r.environment,
        r.model,
        COALESCE(r.resource_set, '') AS name,
        r.model AS revision
    FROM public.resource AS r;


    ALTER TABLE public.resource
        ADD COLUMN resource_set_revision integer;

    UPDATE public.resource
        SET resource_set_revision=model;

    ALTER TABLE public.resource
        ALTER COLUMN resource_set_revision SET NOT NULL;

    """
    await connection.execute(schema)
