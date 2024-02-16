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
    await connection.execute(
        """
CREATE TABLE IF NOT EXISTS public.resource_persistent_state (
    environment uuid NOT NULL REFERENCES public.environment(id) ON DELETE CASCADE,
    resource_id character varying NOT NULL,
    last_deploy timestamp with time zone,
    last_success timestamp with time zone,
    last_produced_events timestamp with time zone,
    last_deployed_attribute_hash character varying,
    last_deployed_version integer,
    last_non_deploying_status public.non_deploying_resource_state
        DEFAULT 'available'::public.non_deploying_resource_state NOT NULL,
    PRIMARY KEY(environment, resource_id)
);

INSERT INTO public.resource_persistent_state (environment, resource_id, last_deploy, last_success, last_non_deploying_status, last_produced_events)
 SELECT environment, resource_id, last_deploy, last_success, last_non_deploying_status, last_produced_events
 FROM public.resource
 WHERE (environment, model) IN (
    SELECT environment, max(version) FROM public.configurationmodel WHERE released=true GROUP BY environment
 );

ALTER TABLE public.resource DROP COLUMN last_success;
ALTER TABLE public.resource DROP COLUMN last_non_deploying_status;
ALTER TABLE public.resource DROP COLUMN last_produced_events;
ALTER TABLE public.resource DROP COLUMN last_deploy;

"""
    )
