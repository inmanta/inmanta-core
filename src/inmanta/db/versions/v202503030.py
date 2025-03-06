"""
Copyright 2025 Inmanta

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
    * Create the module_requirements table, that keeps track of the python package requirements
      per inmanta module (name, version).
    * Create the files_in_module table, that keeps track of which files belong to which inmanta
      module.
    * Create the modules_for_agent table, that keeps track of which inmanta modules are required
      by which agent.
    """
    schema = """
        CREATE TABLE public.module_requirements (
            module_name varchar,
            module_version varchar,
            environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
            requirements character varying[] DEFAULT ARRAY[]::character varying[],
            PRIMARY KEY(module_name, module_version, environment)
        );

        -- Create the files_in_module table.
        CREATE TABLE public.files_in_module (
            module_name varchar,
            module_version varchar,
            environment uuid NOT NULL,
            file_content_hash varchar NOT NULL REFERENCES file(content_hash) ON DELETE CASCADE,
            file_path varchar NOT NULL,
            FOREIGN KEY (module_name, module_version, environment)
            REFERENCES public.module_requirements(module_name, module_version, environment) ON DELETE CASCADE
        );

        CREATE INDEX files_in_module_module_name_module_version_environment_index
        ON public.files_in_module (module_name, module_version, environment);

        -- Create the modules_for_agent table.
        CREATE TABLE public.modules_for_agent (
            cm_version integer,
            agent_name varchar,
            module_name varchar,
            module_version varchar,
            environment uuid NOT NULL,
            FOREIGN KEY (cm_version, environment)
            REFERENCES public.configurationmodel(version, environment) ON DELETE CASCADE,
            FOREIGN KEY (agent_name, environment)
            REFERENCES public.agent(name, environment) ON DELETE CASCADE,
            FOREIGN KEY (module_name, module_version, environment)
            REFERENCES public.module_requirements(module_name, module_version, environment) ON DELETE CASCADE
        );

        CREATE INDEX modules_for_agent_agent_name_cm_version_environment_index
        ON public.modules_for_agent (agent_name, cm_version, environment);

    """
    await connection.execute(schema)
