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
import os
from collections import defaultdict
from pathlib import Path

from asyncpg import Connection

from inmanta import const, loader


async def update(connection: Connection) -> None:
    """
    * Create the module table, that keeps track of the python package requirements
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
            requirements varchar[] DEFAULT ARRAY[]::varchar[] NOT NULL,
            PRIMARY KEY(environment, name, version)
        );

        CREATE TABLE public.files_in_module (
            module_name varchar NOT NULL,
            module_version varchar NOT NULL,
            environment uuid NOT NULL,
            file_content_hash varchar NOT NULL REFERENCES file(content_hash) ON DELETE CASCADE,
            file_path varchar NOT NULL,
            PRIMARY KEY(environment, module_name, module_version, file_path),
            FOREIGN KEY (environment, module_name, module_version)
                REFERENCES public.module(environment, name, version) ON DELETE CASCADE
        );

        CREATE INDEX files_in_module_file_content_hash_index
        ON public.files_in_module (file_content_hash);

        CREATE TABLE public.modules_for_agent (
            cm_version integer NOT NULL,
            agent_name varchar NOT NULL,
            module_name varchar NOT NULL,
            module_version varchar NOT NULL,
            environment uuid NOT NULL,
            PRIMARY KEY(environment, cm_version, agent_name, module_name, module_version),
            FOREIGN KEY (environment, cm_version)
                REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE,
            FOREIGN KEY (environment, agent_name)
                REFERENCES public.agent(environment, name) ON DELETE CASCADE,
            FOREIGN KEY (environment, module_name, module_version)
                REFERENCES public.module(environment, name, version) ON DELETE CASCADE
        );

        CREATE INDEX modules_for_agent_environment_agent_name_index
        ON public.modules_for_agent (environment, agent_name);
        CREATE INDEX modules_for_agent_environment_module_name_module_version_index
        ON public.modules_for_agent (environment, module_name, module_version);

    """

    await connection.execute(schema)

    code_data: dict[str, dict[int, dict[str, set[tuple[str, str, str, set[str]]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(set))
    )
    model_to_module_version_map: dict[int, dict[str, str]] = defaultdict(dict)

    resource_type_to_module: dict[int, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    async def fetch_code_data(
        code_data: dict[str, dict[int, dict[str, set[tuple[str, str, str, set[str]]]]]],
        resource_type_to_module: dict[int, dict[str, set[str]]],
    ) -> None:
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
                code_data[env][model_version][inmanta_module_name].add(
                    tuple((file_hash, file_path, python_module_name, frozenset(requirements)))
                )

                resource_type_to_module[model_version][resource_type].add(inmanta_module_name)

    def build_module_data(
        code_data: dict[str, dict[int, dict[str, set[tuple[str, str, str, set[str]]]]]],
        module_data: list[tuple[str, str, str, list[str]]],
        files_in_module_data: list[tuple[str, str, str, str, str]],
        model_to_module_version_map: dict[int, dict[str, str]],
    ) -> None:

        def compute_version_requirements(
            source_info: set[tuple[str, str, str, set[str]]],
        ) -> tuple[str, list[str]]:
            """
            Helper method
            """
            reqs = set()
            module_version_hash = hashlib.new("sha1")

            for file_hash, _, _, requirements in sorted(source_info, key=lambda x: x[0]):
                # sort by hash to compute inmanta module version
                module_version_hash.update(file_hash.encode())
                reqs.update(requirements)

            module_version = module_version_hash.hexdigest()
            return module_version, list(reqs)

        def compute_files_in_module(
            source_info: set[tuple[str, str, str, set[str]]],
            module_name: str,
            environment: str,
            module_version: str,
            files_in_module_data: list[tuple[str, str, str, str, str]],
        ) -> None:
            """
            Helper method
            """
            for file_hash, file_path, _, _ in source_info:
                parts = Path(file_path).parts
                if f"{module_name}/plugins" in file_path:
                    # V1 module
                    rel_py_file = os.path.relpath(file_path, start="plugins")
                    relative_path = os.path.join(module_name, loader.PLUGIN_DIR, rel_py_file)
                else:
                    relative_path = str(Path(*parts[parts.index(const.PLUGINS_PACKAGE) :]))
                files_in_module_data.append((module_name, module_version, environment, file_hash, relative_path))

        for env, env_data in code_data.items():
            for cm_version, version_data in env_data.items():
                for module_name, module_source_data in version_data.items():
                    module_version, requirements = compute_version_requirements(module_source_data)
                    compute_files_in_module(module_source_data, module_name, env, module_version, files_in_module_data)
                    module_data.append((module_name, module_version, env, requirements))
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

    module_data: list[tuple[str, str, str, list[str]]] = []
    files_in_module_data: list[tuple[str, str, str, str, str]] = []
    modules_for_agent_data: list[tuple[int, str, str, str, str]] = []
    await fetch_code_data(code_data, resource_type_to_module)
    build_module_data(code_data, module_data, files_in_module_data, model_to_module_version_map)
    await build_modules_in_agent_data(resource_type_to_module, model_to_module_version_map, modules_for_agent_data)
    insert_module = """
    INSERT INTO public.module (
        name,
        version,
        environment,
        requirements
        )
    VALUES ($1,$2,$3,$4)
    ON CONFLICT DO NOTHING
    """
    await connection.executemany(insert_module, module_data)

    insert_files_in_module = """
    INSERT INTO public.files_in_module (
        module_name,
        module_version,
        environment,
        file_content_hash,
        file_path
    )
    VALUES ($1,$2,$3,$4,$5)
    ON CONFLICT DO NOTHING
    """
    await connection.executemany(insert_files_in_module, files_in_module_data)

    insert_modules_for_agent = """
    INSERT INTO public.modules_for_agent (
        cm_version,
        environment,
        agent_name,
        module_name,
        module_version
    )
    VALUES ($1,$2,$3,$4,$5)
    ON CONFLICT DO NOTHING
    """
    await connection.executemany(insert_modules_for_agent, modules_for_agent_data)

    drop_code_table = """
    DROP TABLE public.code
    """
    await connection.execute(drop_code_table)
