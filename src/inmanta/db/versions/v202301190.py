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
        # Set the columns, which are part of the primary key, in the right order to get optimal query performance.
        """
        ALTER TABLE public.environmentmetricsgauge DROP Constraint environmentmetricsgauge_pkey;
        ALTER TABLE public.environmentmetricsgauge ADD PRIMARY KEY (environment, timestamp, metric_name, category);

        ALTER TABLE public.environmentmetricstimer DROP Constraint environmentmetricstimer_pkey;
        ALTER TABLE public.environmentmetricstimer ADD PRIMARY KEY (environment, timestamp, metric_name, category);
        """
    )
