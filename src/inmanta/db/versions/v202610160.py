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
    Changes to the inmanta_module table:
      - Clear the install mode of the editable installed modules that were registered without a setup.cfg: the agent can
        not rebuild them as installable python packages, so they fall back to the install on disk, together with the
        requirements that were registered for them. Such a module is then only installed on the agents that load it,
        until a new export registers it again with its setup.cfg.
      - Make requirements non-nullable: the modules stored without requirements get an empty list.
    """
    schema = """
    UPDATE public.inmanta_module AS m
    SET editable_install = NULL
    WHERE m.editable_install AND NOT EXISTS (
        SELECT 1
        FROM public.module_files AS f
        WHERE f.environment = m.environment
            AND f.inmanta_module_name = m.name
            AND f.inmanta_module_version = m.version
            AND f.path = 'setup.cfg'
    );

    UPDATE public.inmanta_module
    SET requirements = ARRAY[]::character varying[]
    WHERE requirements IS NULL;

    ALTER TABLE public.inmanta_module ALTER COLUMN requirements SET NOT NULL;
    """
    await connection.execute(schema)
