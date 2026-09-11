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
    Replace inmanta_module.editable_install by an install_mode column, which names the three ways the code of a module
    can reach the venv of an executor: 'editable', 'package' and 'on_disk'. The boolean could not express the third
    one, which a V1 module needs: it is not distributed as a python package, so it can only be installed on disk.
    The existing values map onto the new ones without loss:
      - true  -> 'editable'
      - false -> 'package'
      - null  -> 'on_disk'. A model version that was exported by an iso<10 orchestrator did not record how a module
        was installed in the compiler venv, and installing on disk is the only mechanism that works without that
        knowledge. It is also what the compatibility layer already did for those versions.
    """
    schema = """
    ALTER TABLE public.inmanta_module
        ADD COLUMN install_mode varchar;

    UPDATE public.inmanta_module
    SET install_mode = CASE
        WHEN editable_install IS NULL THEN 'on_disk'
        WHEN editable_install THEN 'editable'
        ELSE 'package'
    END;

    ALTER TABLE public.inmanta_module
        ALTER COLUMN install_mode SET NOT NULL,
        DROP COLUMN editable_install;
    """
    await connection.execute(schema)
