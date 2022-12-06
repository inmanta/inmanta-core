"""
    Copyright 2022 Inmanta

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
    schema = """
    CREATE TABLE IF NOT EXISTS public.environmentmetricscounter(
        metric_name VARCHAR NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        count INT NOT NULL,
        PRIMARY KEY (metric_name, timestamp)
    );
    CREATE INDEX IF NOT EXISTS environment_metrics_counter_index ON environmentmetricscounter(metric_name);

    CREATE TABLE IF NOT EXISTS public.environmentmetricsnoncounter (
        metric_name VARCHAR NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        count INT NOT NULL,
        value INT NOT NULL,
        PRIMARY KEY (metric_name, timestamp)
    );
    CREATE INDEX IF NOT EXISTS environment_metrics_counter_index ON environmentmetricsnoncounter(metric_name);
    """

    await connection.execute(schema)
