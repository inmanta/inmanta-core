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
    Add executor_status column to the agent table.
    It denotes the state of the latest executor built for this agent:
        - down: the executor didn't come up successfully
        - degraded: the executor didn't successfully load all handler code
        - up: the executor came up successfully
    """
    schema = """
        CREATE TYPE public.executor_status AS ENUM (
            'up',
            'degraded',
            'down'
        );

        ALTER TABLE public.agent ADD COLUMN executor_status executor_status DEFAULT 'down'::public.executor_status;

        UPDATE public.agent
        SET executor_status = 'down'::public.executor_status;

        ALTER TABLE  public.agent ALTER COLUMN executor_status SET NOT NULL;
    """
    await connection.execute(schema)
