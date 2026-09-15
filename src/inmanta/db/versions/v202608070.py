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
    Two changes to how the code of an inmanta module is registered.

    1. Persist the packaging files of an editable installed module, so that it can be recreated as an installable python
       package on the agent side. The content itself is stored in the 'file' table; the two new columns reference it by
       content hash. Unlike the install mode below, they stay nullable permanently. A null value is expected in three
       cases:
         - a package installed module: pip fetches setup.cfg/pyproject.toml when it installs the module, so there is no
           need to persist them.
         - an editable module that happens to lack one of these files.
         - a model version that was exported by an iso<10 orchestrator: the "old-style" code install compatibility layer
           does not populate these columns, and recomputing them would require a full recompile.

    2. Replace inmanta_module.editable_install by an install_mode column, which names the ways the code of a module can
       reach the venv of an executor. The boolean could not express 'on_disk', which a V1 module needs: it is not
       distributed as a python package, so it can only be installed on disk. The existing values map onto the new ones
       as follows:
         - false -> 'package'. That value had a single meaning, so it carries over as is.
         - true  -> 'on_disk', not 'editable'. The boolean lumped a V1 module together with an editable installed V2
           module: both had their code transported, and nothing in the database tells the two apart. 'on_disk' is what
           reproduces the behaviour of the orchestrator that wrote such a row: the module is installed on every agent of
           the model version, loaded only on the agents registered for it, and its python requirements are transported
           alongside its source, which is exactly the column that row already populates. 'editable' would be wrong on
           both counts: no packaging files were persisted back then, so the agent can not recreate the module as an
           installable python package, and an editable module's requirements are read from its setup.cfg rather than
           from the column, so they would be dropped. A module only becomes 'editable' once a version is exported again.
         - null  -> 'unknown'. A model version that was exported by an iso<10 orchestrator did not record how a module
           was installed in the compiler venv. Its code reaches the executor the same way as an 'on_disk' module, the
           only mechanism that works without that knowledge, but it is not stored as 'on_disk': that value means the
           module is installed on every agent of the model version, while a module of unknown install mode keeps the
           narrower iso<10 behaviour of only being installed on the agents that load it.
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

    -- Replace the editable_install boolean by the install mode it stood for

    ALTER TABLE public.inmanta_module
        ADD COLUMN install_mode varchar;

    UPDATE public.inmanta_module
    SET install_mode = CASE
        WHEN editable_install IS NULL THEN 'unknown'
        WHEN editable_install THEN 'on_disk'
        ELSE 'package'
    END;

    ALTER TABLE public.inmanta_module
        ALTER COLUMN install_mode SET NOT NULL,
        DROP COLUMN editable_install;
    """
    await connection.execute(schema)
