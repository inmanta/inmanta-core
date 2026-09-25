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
    content hash. They are nullable permanently. A null value is expected in two cases:
      - a package installed module: pip fetches setup.cfg/pyproject.toml when it installs the module, so there is no
        need to persist them.
      - an editable module without a pyproject.toml. That file is optional; setup.cfg is not, since it is what makes a
        module a V2 module.

    A module that is already registered as an editable install has neither packaging file, so it can not be
    reconstructed. Its install mode is cleared so that it falls back to the install on disk path: that path carries the
    same python files and needs no packaging files, so such a model version keeps deploying, on the agents it
    registered the module for. The module is then only installed on the agents that load it, rather than on every agent
    of the model version, so the handler of another module can no longer import it on an agent that doesn't. A full
    compile registers the module again with its packaging files, for the model versions it exports from then on.

    The requirements column is made non-nullable again. It only carries requirements for the modules of a model version
    that was exported by an iso<10 orchestrator: the modules that were stored without requirements get an empty list.
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
