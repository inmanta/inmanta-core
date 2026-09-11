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
    Two changes to how the code an agent has to install is registered.

    1. Replace inmanta_module.editable_install by an install_mode column, which names the three ways the code of a module
       can reach the venv of an executor: 'editable', 'package' and 'on_disk'. The boolean could not express the third
       one, which a V1 module needs: it is not distributed as a python package, so it can only be installed on disk.
       The existing values map onto the new ones without loss:
         - true  -> 'editable'
         - false -> 'package'
         - null  -> 'on_disk'. A model version that was exported by an iso<10 orchestrator did not record how a module
           was installed in the compiler venv, and installing on disk is the only mechanism that works without that
           knowledge. It is also what the compatibility layer already did for those versions. Whether such a version is
           loaded the old way is decided by agent_modules.load_module_on_agent being null, which is untouched here.

    2. Add the configurationmodel_modules table, which registers the modules of a model version once per version instead
       of once per agent. A module that is not installed as a package is installed on every agent of the version, so
       agent_modules used to hold a row per (agent, module) pair for it. It now only holds the registrations that really
       are per agent, i.e. which agent loads which module. The new table is backfilled from agent_modules so that the
       model versions that are already stored keep resolving their code. Their now redundant agent_modules rows are left
       alone: an extra row only says that the module is registered for that agent, which it is.
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

    CREATE TABLE public.configurationmodel_modules(
        environment uuid NOT NULL,
        cm_version integer NOT NULL,
        inmanta_module_name varchar NOT NULL,
        inmanta_module_version varchar NOT NULL,
        CONSTRAINT configurationmodel_modules_pkey
            PRIMARY KEY (environment, cm_version, inmanta_module_name),
        CONSTRAINT configurationmodel_modules_environment_cm_version_fkey
            FOREIGN KEY (environment, cm_version)
            REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE,
        CONSTRAINT configurationmodel_modules_environment_inmanta_module_na_fkey
            FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version)
            REFERENCES public.inmanta_module(environment, name, version) ON DELETE RESTRICT
    );

    INSERT INTO public.configurationmodel_modules(
        environment, cm_version, inmanta_module_name, inmanta_module_version
    )
    SELECT DISTINCT environment, cm_version, inmanta_module_name, inmanta_module_version
    FROM public.agent_modules;
    """
    await connection.execute(schema)
