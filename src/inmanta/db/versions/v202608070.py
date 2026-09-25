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
      - Add setup_cfg_hash and pyproject_toml_hash, which reference the packaging files of an editable installed module
        in the file table, so that the agent can reconstruct it as an installable python package. Both are null for a
        package installed module, and pyproject_toml_hash is null for a module that has no pyproject.toml.
      - Clear the install mode of the editable installed modules registered before this migration: they have no
        packaging files, so they fall back to the install on disk. Such a module is then only installed on the agents
        that load it, until a full compile registers it again with its packaging files.
      - Make requirements non-nullable again: the modules stored without requirements get an empty list.
    """
    schema = """
    -- Persist the packaging files an editable installed module is reconstructed from

    ALTER TABLE public.inmanta_module
        ADD COLUMN setup_cfg_hash varchar,
        ADD COLUMN pyproject_toml_hash varchar,
        ADD CONSTRAINT inmanta_module_setup_cfg_hash_fkey
            FOREIGN KEY (setup_cfg_hash) REFERENCES public.file(content_hash) ON DELETE RESTRICT,
        ADD CONSTRAINT inmanta_module_pyproject_toml_hash_fkey
            FOREIGN KEY (pyproject_toml_hash) REFERENCES public.file(content_hash) ON DELETE RESTRICT;

    -- Clear the install mode of an editable module that has no packaging files, so that it falls back to the install
    -- on disk path
    UPDATE public.inmanta_module
    SET editable_install = NULL
    WHERE editable_install AND setup_cfg_hash IS NULL;

    -- A module stored without requirements has none to install
    UPDATE public.inmanta_module
    SET requirements = ARRAY[]::character varying[]
    WHERE requirements IS NULL;

    ALTER TABLE public.inmanta_module ALTER COLUMN requirements SET NOT NULL;
    """
    await connection.execute(schema)
