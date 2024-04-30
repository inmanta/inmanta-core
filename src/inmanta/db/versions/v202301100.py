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
    # grouped_by has as default value '__None__' as it is part of the PRIMARY KEY and can therefore not be NULL.
    schema = """
    ALTER TABLE public.environmentmetricsgauge ADD COLUMN grouped_by VARCHAR DEFAULT '__None__';
    ALTER TABLE public.environmentmetricsgauge DROP Constraint environmentmetricsgauge_pkey;
    ALTER TABLE public.environmentmetricsgauge ADD PRIMARY KEY (environment, metric_name,grouped_by, timestamp);

    ALTER TABLE public.environmentmetricstimer ADD COLUMN grouped_by VARCHAR DEFAULT '__None__';
    ALTER TABLE public.environmentmetricstimer DROP Constraint environmentmetricstimer_pkey;
    ALTER TABLE public.environmentmetricstimer ADD PRIMARY KEY (environment, metric_name,grouped_by, timestamp);
    """

    await connection.execute(schema)
