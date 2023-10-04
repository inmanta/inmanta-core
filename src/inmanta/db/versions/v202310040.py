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
    """
    Add the indexes required to perform a manual cascading delete of a configurationmodel.
    """
    schema = """
    CREATE INDEX compile_environment_version_index ON public.compile (environment, version);
    CREATE INDEX resourceaction_resource_environment_resource_version_index
        ON public.resourceaction_resource (environment, resource_version);
    """
    await connection.execute(schema)
