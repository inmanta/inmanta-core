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

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from asyncpg import Connection

from inmanta.data.model import ModuleSourceMetadata
from inmanta.loader import CodeManager

LOGGER = logging.getLogger("databaseservice")


async def update(connection: Connection) -> None:
    """
    * Create the inmanta_module table, that keeps track of the python package requirements
      per inmanta module (name, version).
    * Create the module_files table, that keeps track of which files belong to which inmanta
      module.
    * Create the agent_modules table, that keeps track of which inmanta modules are required
      by which agent.
    * Transfer all known source data from the Code table into these newly created tables.
    * Delete the Code table.
    """
    schema = """
        CREATE TABLE public.inmanta_module (
            name varchar NOT NULL,
            version varchar NOT NULL,
            environment uuid NOT NULL REFERENCES environment(id) ON DELETE CASCADE,
            requirements varchar[] DEFAULT ARRAY[]::varchar[] NOT NULL,
            PRIMARY KEY(environment, name, version)
        );

        CREATE TABLE public.module_files (
            inmanta_module_name varchar NOT NULL,
            inmanta_module_version varchar NOT NULL,
            environment uuid NOT NULL,
            file_content_hash varchar NOT NULL REFERENCES file(content_hash) ON DELETE CASCADE,
            python_module_name varchar NOT NULL,
            is_byte_code boolean NOT NULL,
            PRIMARY KEY(environment, inmanta_module_name, inmanta_module_version, python_module_name),
            FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version)
                REFERENCES public.inmanta_module(environment, name, version) ON DELETE CASCADE
        );


        CREATE TABLE public.agent_modules (
            cm_version integer NOT NULL,
            agent_name varchar NOT NULL,
            inmanta_module_name varchar NOT NULL,
            inmanta_module_version varchar NOT NULL,
            environment uuid NOT NULL,
            PRIMARY KEY(environment, cm_version, agent_name, inmanta_module_name),
            FOREIGN KEY (environment, cm_version)
                REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE,
            FOREIGN KEY (environment, agent_name)
                REFERENCES public.agent(environment, name) ON DELETE CASCADE,
            FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version)
                REFERENCES public.inmanta_module(environment, name, version) ON DELETE CASCADE
        );

        -- Foreign key indexes:
        CREATE INDEX agent_modules_environment_agent_name_index
        ON public.agent_modules (environment, agent_name);
        CREATE INDEX agent_modules_environment_module_name_module_version_index
        ON public.agent_modules (environment, inmanta_module_name, inmanta_module_version);

    """

    await connection.execute(schema)

    @dataclass
    class InmantaModuleData:
        sources: set[ModuleSourceMetadata] = field(default_factory=lambda: set())
        requirements: set[str] = field(default_factory=lambda: set())

    @dataclass
    class DataPerModule:
        # Maps inmanta module names to their sources
        inmanta_modules: defaultdict[str, InmantaModuleData] = field(default_factory=lambda: defaultdict(InmantaModuleData))

    @dataclass
    class ModulesPerVersion:
        # Maps model versions to their inmanta modules
        model_versions: defaultdict[int, DataPerModule] = field(default_factory=lambda: defaultdict(DataPerModule))

    @dataclass
    class VersionsPerEnv:
        # Maps environments to model versions
        environments: defaultdict[str, ModulesPerVersion] = field(default_factory=lambda: defaultdict(ModulesPerVersion))

    async def fetch_code_data() -> tuple[VersionsPerEnv, dict[int, dict[str, set[str]]]]:
        """
        Read from the Code table and populate the two following data containers:

            1) code_data: a nested map of environment -> model version -> inmanta module name -> data.

            2) resource_type_to_module: a nested map of model version -> resource type -> set of inmanta modules.
        """

        code_data: VersionsPerEnv = VersionsPerEnv()
        resource_type_to_module: dict[int, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

        fetch_source_refs_query = """
            SELECT DISTINCT
                environment,
                version,
                source_refs,
                resource
            FROM public.code as cod
            where exists (
                select 1
                from configurationmodel AS con
                where cod.environment=con.environment
                AND cod.version=con.version
            );
        """
        result = await connection.fetch(fetch_source_refs_query)
        for res in result:
            env: str = str(res["environment"])
            model_version = res["version"]
            source_refs = res["source_refs"]
            resource_type: str = str(res["resource"])

            assert isinstance(model_version, int)

            for file_hash, file_data in source_refs.items():  # type: ignore
                file_path, python_module_name, requirements = file_data
                inmanta_module_name = python_module_name.split(".")[1]
                assert isinstance(inmanta_module_name, str)
                source_info_meta_data = ModuleSourceMetadata(
                    name=python_module_name,
                    is_byte_code=file_path.endswith(".pyc"),
                    hash_value=file_hash,
                )

                code_data.environments[env].model_versions[model_version].inmanta_modules[inmanta_module_name].sources.add(
                    source_info_meta_data
                )
                code_data.environments[env].model_versions[model_version].inmanta_modules[
                    inmanta_module_name
                ].requirements.update(requirements)
                resource_type_to_module[model_version][resource_type].add(inmanta_module_name)
        return code_data, resource_type_to_module

    def build_module_data(
        code_data: VersionsPerEnv,
    ) -> tuple[
        list[tuple[str, str, str, list[str]]],
        list[tuple[str, str, str, str, str, bool]],
        dict[int, dict[str, str]],
    ]:
        """
        Use the data from the `code_data` container to populate the following data containers:

        1) module_data: The data that will be used to populate the new inmanta_module table.
        2) files_in_module_data: The data that will be used to populate the new module_files table.
        3) model_to_module_version_map
        """
        module_data: list[tuple[str, str, str, list[str]]] = []
        files_in_module_data: list[tuple[str, str, str, str, str, bool]] = []
        model_to_module_version_map: dict[int, dict[str, str]] = defaultdict(dict)

        def compute_files_in_module(
            sources_metadata: set[ModuleSourceMetadata],
            module_name: str,
            environment: str,
            module_version: str,
        ) -> list[tuple[str, str, str, str, str, bool]]:
            """
            Helper function to populate the `files_in_module_data` data container using
            the other arguments.
            """
            files_in_module_data: list[tuple[str, str, str, str, str, bool]] = []
            for metadata in sources_metadata:
                files_in_module_data.append(
                    (module_name, module_version, environment, metadata.hash_value, metadata.name, metadata.is_byte_code)
                )
            return files_in_module_data

        for environment, modules_per_version in code_data.environments.items():
            for cm_version, version_data in modules_per_version.model_versions.items():
                for module_name, module_source_data in version_data.inmanta_modules.items():
                    module_version = CodeManager.get_module_version(
                        module_source_data.requirements, list(module_source_data.sources)
                    )
                    files_in_module_data.extend(
                        compute_files_in_module(module_source_data.sources, module_name, environment, module_version)
                    )
                    module_data.append((module_name, module_version, environment, list(module_source_data.requirements)))
                    model_to_module_version_map[cm_version][module_name] = module_version

        return module_data, files_in_module_data, model_to_module_version_map

    async def build_modules_in_agent_data(
        resource_type_to_module: dict[int, dict[str, set[str]]],
        model_to_module_version_map: dict[int, dict[str, str]],
    ) -> list[tuple[int, str, str, str, str]]:
        """
        Use the data from the `resource_type_to_module` and `model_to_module_version_map` containers to populate
        the following data container:

        modules_for_agent_data: The data that will be used to populate the new agent_modules table.
        """
        modules_for_agent_data: list[tuple[int, str, str, str, str]] = []
        fetch_agent_for_resource_query = """
        SELECT DISTINCT
            environment,
            model,
            agent,
            resource_type
        FROM public.resource
            """
        result = await connection.fetch(fetch_agent_for_resource_query)
        for res in result:
            model_version = res["model"]
            environment = str(res["environment"])
            agent_name = str(res["agent"])
            resource_type = str(res["resource_type"])

            assert isinstance(model_version, int)
            for module_name in resource_type_to_module[model_version][resource_type]:
                module_version = model_to_module_version_map[model_version][module_name]
                modules_for_agent_data.append((model_version, environment, agent_name, module_name, module_version))

        return modules_for_agent_data

    # Data containers to help compute the data to insert into the newly created tables

    code_data: VersionsPerEnv
    resource_type_to_module: dict[int, dict[str, set[str]]]

    code_data, resource_type_to_module = await fetch_code_data()

    inmanta_module_data, files_in_module_data, model_to_module_version_map = build_module_data(code_data)

    modules_for_agent_data = await build_modules_in_agent_data(resource_type_to_module, model_to_module_version_map)

    insert_module = """
    INSERT INTO public.inmanta_module (
        name,
        version,
        environment,
        requirements
        )
    VALUES ($1,$2,$3,$4)
    ON CONFLICT DO NOTHING
    """
    await connection.executemany(insert_module, inmanta_module_data)

    insert_files_in_module = """
    INSERT INTO public.module_files (
        inmanta_module_name,
        inmanta_module_version,
        environment,
        file_content_hash,
        python_module_name,
        is_byte_code
    )
    VALUES ($1,$2,$3,$4,$5,$6)
    ON CONFLICT DO NOTHING
    """
    await connection.executemany(insert_files_in_module, files_in_module_data)

    insert_modules_for_agent = """
    INSERT INTO public.agent_modules (
        cm_version,
        environment,
        agent_name,
        inmanta_module_name,
        inmanta_module_version
    )
    VALUES ($1,$2,$3,$4,$5)
    ON CONFLICT DO NOTHING
    """
    await connection.executemany(insert_modules_for_agent, modules_for_agent_data)

    drop_code_table = """
    DROP TABLE public.code
    """
    await connection.execute(drop_code_table)
