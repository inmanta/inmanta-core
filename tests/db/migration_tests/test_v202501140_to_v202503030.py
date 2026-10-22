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
import re
import uuid
from collections import abc

import asyncpg
import pytest

from inmanta import const, loader
from inmanta.agent.code_manager import CodeManager
from inmanta.data.model import InmantaModule as InmantaModuleDTO
from inmanta.data.model import ModuleFileMetadata, ModuleSourceMetadata
from inmanta.data.sqlalchemy import InmantaModule

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_reregister_unchanged_module_after_upgrade(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    An iso<10 orchestrator registered the modules whose code it transported without an install mode. After the upgrade,
    an export that registers one of them again, with unchanged files, has to create a registration of its own, with its
    install mode. Registering a module version that already exists is a no-op, so if it ended up at the version of the
    iso<10 registration, its model versions would be deployed with the iso<10 compatibility path.
    """
    await migrate_db_from()

    environment = uuid.UUID("bbfe114d-a91b-4cfe-be61-018c112aeafe")
    (old_registration,) = await postgresql_client.fetch(
        "SELECT version, requirements FROM public.inmanta_module WHERE environment=$1 AND name='std'", environment
    )
    files: list[ModuleFileMetadata] = [
        ModuleSourceMetadata(path=record["path"], hash_value=record["file_content_hash"])
        for record in await postgresql_client.fetch(
            """
            SELECT path, file_content_hash
            FROM public.module_files
            WHERE environment=$1 AND inmanta_module_name='std' AND inmanta_module_version=$2
            """,
            environment,
            old_registration["version"],
        )
    ]
    assert files

    # The exporter transports the setup.cfg of the module alongside its python files
    setup_cfg = b"[metadata]\nname = inmanta-module-std\n"
    setup_cfg_hash = hashlib.new("sha1", setup_cfg).hexdigest()
    await postgresql_client.execute(
        "INSERT INTO public.file(content_hash, content) VALUES($1, $2) ON CONFLICT DO NOTHING", setup_cfg_hash, setup_cfg
    )
    files.append(ModuleFileMetadata(path=const.SETUP_CFG_FILE, hash_value=setup_cfg_hash))

    # Register the very same python files and requirements again, at the version the exporter registers them at
    requirements: list[str] = list(old_registration["requirements"])
    new_version = f"{loader.SOURCE_INSTALL_VERSION_PREFIX}{loader.CodeManager.get_module_version(set(requirements), files)}"
    await InmantaModule.register_modules(
        environment,
        {
            "std": InmantaModuleDTO(
                name="std",
                version=new_version,
                files_in_module=files,
                requirements=requirements,
                load_module_on_agents=[],
                editable_install=True,
            )
        },
        postgresql_client,
    )

    registrations = {
        record["version"]: record["editable_install"]
        for record in await postgresql_client.fetch(
            "SELECT version, editable_install FROM public.inmanta_module WHERE environment=$1 AND name='std'", environment
        )
    }
    assert registrations == {old_registration["version"]: None, new_version: True}


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_tables_for_agent_code_transport_rework(migrate_db_from: abc.Callable[[], abc.Awaitable[None]]) -> None:

    await migrate_db_from()

    environments = ["bbfe114d-a91b-4cfe-be61-018c112aeafe", "7d3ec9ea-9759-4beb-8629-c7df42ed8d4e"]
    for env in environments:

        codemanager = CodeManager()
        install_spec_1 = await codemanager.get_code(
            environment=env,
            model_version=1,
            agent_name="internal",
        )
        assert len(install_spec_1) == 1
        assert ["inmanta_plugins.std", "inmanta_plugins.std.resources", "inmanta_plugins.std.types"] == [
            module.metadata.name for module in install_spec_1[0].blueprint.sources
        ]
        install_spec_2 = await codemanager.get_code(
            environment=env,
            model_version=1,
            agent_name="localhost",
        )
        assert len(install_spec_2) == 1
        assert ["inmanta_plugins.fs", "inmanta_plugins.fs.json_file", "inmanta_plugins.fs.resources"] == [
            module.metadata.name for module in install_spec_2[0].blueprint.sources
        ]
        assert "inmanta-module-std" in install_spec_2[0].blueprint.requirements
