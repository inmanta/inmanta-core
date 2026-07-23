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
    Persist the packaging files of editable-installed inmanta modules so that they can be recreated as
    installable python packages on the agent side. The content itself is stored in the 'file' table; these
    two columns reference it by content hash.

    These columns are nullable, and remain so permanently (unlike inmanta_module.editable_install, which
    becomes NOT NULL in iso 11). A NULL value is expected in three cases:
      - Package (non-editable) installed modules: pip fetches setup.cfg/pyproject.toml when installing the
        module, so there is no need to persist them.
      - Editable modules that happen to lack one of these files.
      - Model versions deployed before the orchestrator was upgraded to iso 10 (the iso version containing the
        agent code install improvement feature). These are handled by the "old-style" code install compatibility
        layer, which does not populate these columns (recomputing them would require a full recompile).

    Note: a nullable foreign key is only enforced for non-NULL values (MATCH SIMPLE), so NULL entries are allowed.
    """
    schema = """
    ALTER TABLE public.inmanta_module
    ADD COLUMN setup_cfg_hash varchar,
    ADD COLUMN pyproject_toml_hash varchar,
    ADD CONSTRAINT inmanta_module_setup_cfg_hash_fkey
        FOREIGN KEY (setup_cfg_hash) REFERENCES public.file(content_hash) ON DELETE RESTRICT,
    ADD CONSTRAINT inmanta_module_pyproject_toml_hash_fkey
        FOREIGN KEY (pyproject_toml_hash) REFERENCES public.file(content_hash) ON DELETE RESTRICT;
    """
    await connection.execute(schema)
