"""
Copyright 2026 Inmanta

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
    Create resource_diff table and add the non_compliant_diff field to the rps table.
    Populate resource_diff table with the diffs from non_compliant resources found on the resourceaction table
    """
    schema = """
        UPDATE public.resource_diff AS rd
        SET diff=diff->rd.id::text
        WHERE diff ? rd.resource_id::text;
    """

    await connection.execute(schema)
