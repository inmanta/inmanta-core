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
    Update foreign key constraints:
      - disallow deleting a module from the database if an agent is still registered to use it
      - disallow deleting a file from the database if a module is still registered to use it
    """
    schema = """
    ALTER TABLE public.agent_modules
        DROP CONSTRAINT agent_modules_environment_inmanta_module_name_inmanta_modu_fkey;

    ALTER TABLE public.agent_modules
        ADD CONSTRAINT agent_modules_environment_inmanta_module_name_inmanta_modu_fkey
        FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version)
        REFERENCES public.inmanta_module(environment, name, version)
        ON DELETE RESTRICT;

    ALTER TABLE public.module_files
        DROP CONSTRAINT module_files_file_content_hash_fkey;

    ALTER TABLE public.module_files
        ADD CONSTRAINT module_files_file_content_hash_fkey
        FOREIGN KEY (file_content_hash)
        REFERENCES public.file(content_hash)
        ON DELETE RESTRICT;
    """
    await connection.execute(schema)
