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

from inmanta.data import Environment


async def update(connection: Connection) -> None:
    """
    Ensure that the purge_on_delete setting is removed from each environment.
    """
    # Add index on resource table
    await connection.execute(f"UPDATE {Environment.table_name()} SET settings=settings - $1", "purge_on_delete")
