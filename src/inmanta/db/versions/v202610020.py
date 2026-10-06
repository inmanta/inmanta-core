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
    Key the module_files table by the path of each file instead of by the name of the python module it defines.

    The name doesn't say where the file goes: inmanta_plugins.mod.sub can be inmanta_plugins/mod/sub.py or
    inmanta_plugins/mod/sub/__init__.py. The path does, and it also says whether the file holds byte code, so a path
    column replaces the python_module_name and is_byte_code columns.

    Existing rows get the path the agent has always installed them at: every python module as a package, i.e.
    <module/as/dirs>/__init__.py, or __init__.pyc for byte code.
    """
    schema = """
    ALTER TABLE public.module_files ADD COLUMN path varchar;

    UPDATE public.module_files
    SET path = replace(python_module_name, '.', '/')
        || '/__init__.py'
        || CASE WHEN is_byte_code THEN 'c' ELSE '' END;

    ALTER TABLE public.module_files
        ALTER COLUMN path SET NOT NULL,
        DROP CONSTRAINT module_files_pkey,
        DROP COLUMN python_module_name,
        DROP COLUMN is_byte_code,
        ADD CONSTRAINT module_files_pkey PRIMARY KEY (environment, inmanta_module_name, inmanta_module_version, path);
    """
    await connection.execute(schema)
