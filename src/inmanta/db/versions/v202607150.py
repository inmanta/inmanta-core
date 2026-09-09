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
    Rework how the inmanta modules used by a model version are registered:
      - The new configurationmodel_modules table pins, per model version, the version of each inmanta module that
        version uses. A single version is used per module and per model version, which its primary key now
        enforces. It is populated with the module versions that the agent_modules rows of each model version
        registered.
      - agent_modules keeps only the registration of which agents load which module. On which agents a module is
        installed follows from the install mode of that module, so it no longer needs a row per (agent, module):
        an editable install module is installed on every agent of the model version, a package install module only
        on the agents that load it.
      - The new editable_install column on inmanta_module holds that install mode.

    The editable_install column is nullable on purpose for now:
      - for all model versions deployed after the orchestrator was upgraded to iso 10 (The iso version
      containing the agent code install improvement feature), the code exporter will set this column and the
      code loader will read this **NON-NULL** value and use the "New-style" code install.
      - But, we still need to be able to run dry-runs for old model versions deployed before the orchestrator
      was upgraded to iso 10. Setting the value of this column would require a full compile for each
      of these versions, which is out of the question. Instead, if the code loader encounters a null value
      for this column, it will use the "Old-style" code install.

    In the next major (iso 11) this column can be made 'NOT NULL' and the code loader can use the
    "New-style" only.

    """
    schema = """
    -- Pin, per model version, the version of each inmanta module it uses

    CREATE TABLE public.configurationmodel_modules (
        environment uuid NOT NULL,
        cm_version integer NOT NULL,
        inmanta_module_name varchar NOT NULL,
        inmanta_module_version varchar NOT NULL,
        CONSTRAINT configurationmodel_modules_pkey
            PRIMARY KEY (environment, cm_version, inmanta_module_name),
        CONSTRAINT configurationmodel_modules_configurationmodel_fkey
            FOREIGN KEY (environment, cm_version)
            REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE,
        CONSTRAINT configurationmodel_modules_inmanta_module_fkey
            FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version)
            REFERENCES public.inmanta_module(environment, name, version) ON DELETE RESTRICT
    );

    -- Foreign key index:
    CREATE INDEX configurationmodel_modules_inmanta_module_index
    ON public.configurationmodel_modules (environment, inmanta_module_name, inmanta_module_version);

    -- The modules a model version uses are the ones its agent_modules rows registered. A single version is
    -- expected per module and per model version: DISTINCT ON keeps one if that expectation was ever violated,
    -- as a version registered twice would already break the code install for that model version.
    INSERT INTO public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version)
    SELECT DISTINCT ON (environment, cm_version, inmanta_module_name)
        environment, cm_version, inmanta_module_name, inmanta_module_version
    FROM public.agent_modules
    ORDER BY environment, cm_version, inmanta_module_name, inmanta_module_version DESC;

    -- agent_modules now only registers which agents load which module: the version of the module comes from
    -- configurationmodel_modules, and the index on that column is dropped along with it. The foreign key to
    -- configurationmodel becomes redundant as well, as configurationmodel_modules carries it.
    ALTER TABLE public.agent_modules
        DROP CONSTRAINT agent_modules_environment_inmanta_module_name_inmanta_modu_fkey,
        DROP CONSTRAINT agent_modules_environment_cm_version_fkey,
        DROP COLUMN inmanta_module_version;

    -- The columns of the foreign key to configurationmodel_modules are a prefix of the new primary key, so that
    -- key's index serves that foreign key as well.
    ALTER TABLE public.agent_modules DROP CONSTRAINT agent_modules_pkey;
    ALTER TABLE public.agent_modules
        ADD CONSTRAINT agent_modules_pkey
        PRIMARY KEY (environment, cm_version, inmanta_module_name, agent_name);
    ALTER TABLE public.agent_modules
        ADD CONSTRAINT agent_modules_configurationmodel_modules_fkey
        FOREIGN KEY (environment, cm_version, inmanta_module_name)
        REFERENCES public.configurationmodel_modules(environment, cm_version, inmanta_module_name)
        ON DELETE CASCADE;

    -- Add the 'editable_install' column

    ALTER TABLE public.inmanta_module
    ADD COLUMN editable_install boolean;

    -- A package installed module stores no requirements: pip resolves the requirements of the version it installs
    ALTER TABLE public.inmanta_module ALTER COLUMN requirements DROP NOT NULL;
    """
    await connection.execute(schema)
