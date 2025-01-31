"""
Copyright 2024 Inmanta

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
    """Change index on resource table to speed up query to get deployment progress in inmanta-lsm"""
    schema = """
-- Drop the old index
DROP INDEX IF EXISTS resource_environment_model_resource_type_idx;

-- Create the new index with the additional column
CREATE INDEX resource_environment_model_resource_type_idx
ON public.resource USING btree (environment, model, resource_type, resource_id_value);
    """
    await connection.execute(schema)
