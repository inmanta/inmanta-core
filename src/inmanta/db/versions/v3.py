"""
    Copyright 2019 Inmanta

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
    ALTER TABLE public.environment
        ADD COLUMN last_version integer DEFAULT 0;

    UPDATE public.environment AS e SET last_version =
        (SELECT COALESCE(
            (SELECT MAX(version) FROM public.configurationmodel AS c WHERE c.environment=e.id),
            0
        ));
    """
    async with connection.transaction():
        await connection.execute(schema)
