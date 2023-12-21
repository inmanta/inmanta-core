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
    last_non_deploying_status public.non_deploying_resource_state
        DEFAULT 'available'::public.non_deploying_resource_state NOT NULL,
    PRIMARY KEY(environment, resource_id)
);

ALTER TABLE public.resource DROP COLUMN last_success;
ALTER TABLE public.resource DROP COLUMN last_non_deploying_status;
ALTER TABLE public.resource DROP COLUMN last_produced_events;

"""
    )
    # TODO POPULATE

    #
    # @classmethod
    # async def copy_last_success(
    #     cls,
    #     environment: uuid.UUID,
    #     from_version: int,
    #     to_version: int,
    #     *,
    #     connection: Optional[Connection] = None,
    # ) -> None:
    #     query = f"""
    #     UPDATE {cls.table_name()} as new_resource
    #     SET
    #         last_success = (
    #             SELECT last_success from {cls.table_name()} as old_resource
    #             WHERE old_resource.model=$3
    #             AND old_resource.environment=$2
    #             AND old_resource.resource_id=new_resource.resource_id
    #         )
    #     WHERE new_resource.model=$1
    #     AND new_resource.environment=$2
    #     AND new_resource.last_success is null"""
    #     await cls._execute_query(query, to_version, environment, from_version, connection=connection)

    #
    # @classmethod
    # async def copy_last_produced_events(
    #     cls,
    #     environment: uuid.UUID,
    #     from_version: int,
    #     to_version: int,
    #     *,
    #     connection: Optional[Connection] = None,
    # ) -> None:
    #     """
    #     Copy the value of last_produced events for every resource in the to_version from the from_version
    #     """
    #     query = f"""
    #        UPDATE {cls.table_name()} as new_resource
    #        SET
    #            last_produced_events = (
    #                SELECT old_resource.last_produced_events
    #                FROM {cls.table_name()} as old_resource
    #                WHERE old_resource.model=$3
    #                AND old_resource.environment=$2
    #                AND old_resource.resource_id=new_resource.resource_id
    #            )
    #        WHERE new_resource.model=$1
    #        AND new_resource.environment=$2
    #        AND new_resource.last_produced_events is null"""
    #     await cls._execute_query(query, to_version, environment, from_version, connection=connection)
