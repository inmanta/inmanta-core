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

import hashlib
from collections import defaultdict, namedtuple
from dataclasses import dataclass, field

from asyncpg import Connection


async def update(connection: Connection) -> None:
    """
    * Create the inmanta_module table, that keeps track of the python package requirements
      per inmanta module (name, version).
    * Create the files_in_module table, that keeps track of which files belong to which inmanta
      module.
    * Create the modules_for_agent table, that keeps track of which inmanta modules are required
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

        CREATE TABLE public.files_in_module (
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

        CREATE INDEX files_in_module_file_content_hash_index
        ON public.files_in_module (file_content_hash);

        CREATE TABLE public.modules_for_agent (
            cm_version integer NOT NULL,
            agent_name varchar NOT NULL,
            inmanta_module_name varchar NOT NULL,
            inmanta_module_version varchar NOT NULL,
            environment uuid NOT NULL,
            PRIMARY KEY(environment, cm_version, agent_name, inmanta_module_name, inmanta_module_version),
            FOREIGN KEY (environment, cm_version)
                REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE,
            FOREIGN KEY (environment, agent_name)
                REFERENCES public.agent(environment, name) ON DELETE CASCADE,
            FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version)
                REFERENCES public.inmanta_module(environment, name, version) ON DELETE CASCADE
        );

        CREATE INDEX modules_for_agent_environment_agent_name_index
        ON public.modules_for_agent (environment, agent_name);
        CREATE INDEX modules_for_agent_environment_module_name_module_version_index
        ON public.modules_for_agent (environment, inmanta_module_name, inmanta_module_version);

    """

    await connection.execute(schema)

    SourceInfo = namedtuple("SourceInfo", ["file_hash", "file_path", "python_module_name", "requirements"])

    @dataclass
    class SetOfSources:
        sources: set[SourceInfo] = field(default_factory=lambda: set())

    @dataclass
    class SourcesPerModule:
        # Maps inmanta module names to their sources
        inmanta_modules: defaultdict[str, SetOfSources] = field(default_factory=lambda: defaultdict(SetOfSources))

    @dataclass
    class ModulesPerVersion:
        # Maps model versions to their inmanta modules
        model_versions: defaultdict[int, SourcesPerModule] = field(default_factory=lambda: defaultdict(SourcesPerModule))

    @dataclass
    class VersionsPerEnv:
        # Maps environments to model versions
        environments: defaultdict[str, ModulesPerVersion] = field(default_factory=lambda: defaultdict(ModulesPerVersion))

    async def fetch_code_data(
        code_data: VersionsPerEnv,
        resource_type_to_module: dict[int, dict[str, set[str]]],
    ) -> None:
        """
        Read from the Code table and populate the two data containers passed as argument
        """
        fetch_source_refs_query = """
    SELECT DISTINCT environment, version, source_refs, resource from public.code
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
                source_info = SourceInfo(file_hash, file_path, python_module_name, frozenset(requirements))

                code_data.environments[env].model_versions[model_version].inmanta_modules[inmanta_module_name].sources.add(
                    source_info
                )
                resource_type_to_module[model_version][resource_type].add(inmanta_module_name)

    def build_module_data(
        code_data: VersionsPerEnv,
        module_data: list[tuple[str, str, str, list[str]]],
        files_in_module_data: list[tuple[str, str, str, str, str, bool]],
        model_to_module_version_map: dict[int, dict[str, str]],
    ) -> None:
        """
        Use the data from the `code_data` container to populate the `module_data`, `files_in_module_data` and
        `model_to_module_version_map` data containers.
        """

        def compute_version_requirements(
            source_info: set[SourceInfo],
        ) -> tuple[str, list[str]]:
            """
            Compute the version for a set of sources. This version is obtained
            by hashing the individual file hashes together and the python
            requirements for these sources.

            Return a tuple of the computed hash and the merged collection of all requirements.
            """
            reqs = set()
            module_version_hash = hashlib.new("sha1")

            for file_hash, _, _, requirements in sorted(source_info, key=lambda x: x[0]):
                # sort by hash to compute inmanta module version
                module_version_hash.update(file_hash.encode())
                reqs.update(requirements)

            for requirement in sorted(reqs):
                module_version_hash.update(str(requirement).encode())

            module_version = module_version_hash.hexdigest()
            return module_version, list(reqs)

        def compute_files_in_module(
            source_info: set[SourceInfo],
            module_name: str,
            environment: str,
            module_version: str,
            files_in_module_data: list[tuple[str, str, str, str, str, bool]],
        ) -> None:
            """
            Helper function to populate the `files_in_module_data` data container using
            the other arguments.
            """
            for file_hash, file_path, python_module_name, _ in source_info:
                is_byte_code: bool
                match file_path:
                    case _ if file_path.endswith(".py"):
                        is_byte_code = False
                    case _ if file_path.endswith(".pyc"):
                        is_byte_code = True
                    case _:
                        raise Exception("Invalid file extension for plugin file %s. Expecting `.py` or `.pyc`." % file_path)

                files_in_module_data.append(
                    (module_name, module_version, environment, file_hash, python_module_name, is_byte_code)
                )

        for environment, modules_per_version in code_data.environments.items():
            for cm_version, version_data in modules_per_version.model_versions.items():
                for module_name, module_source_data in version_data.inmanta_modules.items():
                    module_version, requirements = compute_version_requirements(module_source_data.sources)
                    compute_files_in_module(
                        module_source_data.sources, module_name, environment, module_version, files_in_module_data
                    )
                    module_data.append((module_name, module_version, environment, requirements))
                    model_to_module_version_map[cm_version][module_name] = module_version

    async def build_modules_in_agent_data(
        resource_type_to_module: dict[int, dict[str, set[str]]],
        model_to_module_version_map: dict[int, dict[str, str]],
        modules_for_agent_data: list[tuple[int, str, str, str, str]],
    ) -> None:
        fetch_agent_for_resource_query = """
        SELECT DISTINCT environment, model, agent, resource_type from public.resource
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

    # Data containers to help compute the data to insert into the newly created tables

    # Maps environment -> model version -> inmanta module name -> set of sources
    code_data: VersionsPerEnv = VersionsPerEnv()
    # Maps model versions -> resource type -> set of inmanta modules
    resource_type_to_module: dict[int, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    # Maps model versions -> inmanta module name -> inmanta module version
    model_to_module_version_map: dict[int, dict[str, str]] = defaultdict(dict)

    await fetch_code_data(code_data, resource_type_to_module)

    # Data containers used to populate the corresponding tables.
    inmanta_module_data: list[tuple[str, str, str, list[str]]] = []
    files_in_module_data: list[tuple[str, str, str, str, str, bool]] = []
    modules_for_agent_data: list[tuple[int, str, str, str, str]] = []

    build_module_data(code_data, inmanta_module_data, files_in_module_data, model_to_module_version_map)
    await build_modules_in_agent_data(resource_type_to_module, model_to_module_version_map, modules_for_agent_data)

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
    INSERT INTO public.files_in_module (
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
    INSERT INTO public.modules_for_agent (
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
