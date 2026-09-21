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
    Persist the packaging files of an editable installed module, so that it can be recreated as an installable python
    package on the agent side. The content itself is stored in the 'file' table; the two new columns reference it by
    content hash. They are nullable permanently. A null value is expected in three cases:
      - a package installed module: pip fetches setup.cfg/pyproject.toml when it installs the module, so there is no
        need to persist them.
      - an editable module that happens to lack one of these files.
      - a model version that was exported by an iso<10 orchestrator: the "old-style" code install compatibility layer
        does not populate these columns, and recomputing them would require a full recompile.
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
    """
    await connection.execute(schema)
