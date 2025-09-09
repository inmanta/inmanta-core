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
    -- add and populate resource_set table --

    -- Table does not really contain any data. We could have in-lined the name in the resource_set_configuration_model table
    -- but that would decrease the relational integrity because null values are not allowed to reference another table.
    --
    -- The performance of the two approaches was tested by setting up a database with 5000 model versions, with 5000 distinct
    -- resource sets each, with names the same across all model versions. This represents the (assumed) worst case scenario
    -- when it comes to performance.
    -- Performance was then tested for the query that copies resource sets (no resources) from one version to the next.
    -- The in-line approach performed slightly better at 60ms vs 70ms. Both scaled roughly linearly with the
    -- size of the test (the 5000 mentioned above). When resources were added to the test, the copy query only accounts for 30%
    -- of the insert time when few and small resource sets are updated. As resource sets in the partial export scale, the
    -- resource insert (not impacted by this decision) dominates to the point where the copy becomes negligible.
    -- Other queries that select a resource set by name and model version are still affected, with the minimal performance hit
    -- described above.
    CREATE TABLE public.resource_set (
        environment uuid NOT NULL,
        id uuid NOT NULL,
        name character varying,
        PRIMARY KEY (environment, id),
        FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE
    );

    -- create a temp table to store the relation between the resource set id and the model --
    -- this is helpful to correctly fill the resource_set, resource and the resource_set_configuration_model tables --

    CREATE TEMP TABLE temp_unique_sets_with_id
    ON COMMIT DROP AS

    -- Non-Null resource sets
    SELECT DISTINCT ON (
            r.environment,
            r.resource_set,
            r.model
        )
        r.environment,
        r.resource_set,
        r.model,
        gen_random_uuid() AS id
    FROM public.resource r;


    INSERT INTO public.resource_set (environment, id, name)
    SELECT
        us.environment,
        us.id,
        us.resource_set
    FROM temp_unique_sets_with_id AS us;


    -- add and populate resource_set_id on the resource table --

    ALTER TABLE public.resource
        ADD COLUMN resource_set_id uuid;

    UPDATE public.resource r
    SET resource_set_id=us.id
    FROM temp_unique_sets_with_id us
    WHERE
        r.environment=us.environment AND
        r.resource_set IS NOT DISTINCT FROM us.resource_set AND
        r.model=us.model;

    ALTER TABLE public.resource
    ADD CONSTRAINT resource_resource_set_id_environment_fkey
        FOREIGN KEY (resource_set_id, environment) REFERENCES public.resource_set(id, environment) ON DELETE CASCADE,
    ALTER COLUMN resource_set_id SET NOT NULL,
    DROP COLUMN model CASCADE,
    ADD CONSTRAINT resource_pkey PRIMARY KEY (environment, resource_set_id, resource_id);


    -- for selecting resource set WHERE name=... AND version=...
    -- Tested for 5000 model versions, with 5000 different but like-named sets each:
    -- (environment, name) index performs at 50%. No index at 20%.
    CREATE INDEX resource_set_environment_name_id_index ON public.resource_set (environment, name, id);


    CREATE INDEX resource_environment_resource_set_id_index ON public.resource (environment, resource_set_id);


    -- relational table between resource set and configuration model

    CREATE TABLE public.resource_set_configuration_model (
      environment uuid NOT NULL,
      model integer NOT NULL,
      resource_set_id uuid NOT NULL,
      PRIMARY KEY (environment, model, resource_set_id),
      FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE,
      FOREIGN KEY (environment, resource_set_id) REFERENCES public.resource_set(environment, id)
    );

    CREATE INDEX resource_set_configuration_model_environment_resource_set_id_index
        ON public.resource_set_configuration_model (environment, resource_set_id);

    INSERT INTO public.resource_set_configuration_model (
        environment,
        model,
        resource_set_id
    )
    SELECT
        environment,
        model,
        id
    FROM temp_unique_sets_with_id;
    """
    await connection.execute(schema)
