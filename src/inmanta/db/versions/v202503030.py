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
        CREATE TABLE public.module (
            name varchar NOT NULL,
            version varchar NOT NULL,
            environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
            requirements character varying[] DEFAULT ARRAY[]::character varying[] NOT NULL,
            PRIMARY KEY(environment, name, version)
        );

        -- Create the files_in_module table.
        CREATE TABLE public.files_in_module (
            module_name varchar,
            module_version varchar,
            environment uuid NOT NULL,
            file_content_hash varchar NOT NULL REFERENCES file(content_hash) ON DELETE CASCADE,
            file_path varchar NOT NULL,
            PRIMARY KEY(environment, module_name, module_version, file_path),
            FOREIGN KEY (environment, module_name, module_version)
                REFERENCES public.module(environment, name, version) ON DELETE CASCADE
        );

        CREATE INDEX files_in_module_environment_module_name_module_version_index
        ON public.files_in_module (environment, module_name, module_version);

        -- Create the modules_for_agent table.
        CREATE TABLE public.modules_for_agent (
            cm_version integer,
            agent_name varchar,
            module_name varchar,
            module_version varchar,
            environment uuid NOT NULL,
            PRIMARY KEY(environment, cm_version, agent_name, module_name, module_version),
            FOREIGN KEY (environment, cm_version)
                REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE,
            FOREIGN KEY (environment, agent_name)
                REFERENCES public.agent(environment, name) ON DELETE CASCADE,
            FOREIGN KEY (environment, module_name, module_version)
                REFERENCES public.module(environment, name, version) ON DELETE CASCADE
        );

        CREATE INDEX modules_for_agent_environment_cm_version_index
        ON public.modules_for_agent (environment, cm_version);
        CREATE INDEX modules_for_agent_environment_agent_name_index
        ON public.modules_for_agent (environment, agent_name);
        CREATE INDEX modules_for_agent_environment_module_name_module_version_index
        ON public.modules_for_agent (environment, module_name, module_version);

    """
    await connection.execute(schema)
