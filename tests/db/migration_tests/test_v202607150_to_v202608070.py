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

import os
import re
import uuid
from collections import abc

import asyncpg
import pytest

from inmanta.agent.code_manager import CodeManager

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]

# An environment of the dump, whose model versions use the std and fs modules
ENVIRONMENT = uuid.UUID("48a137cb-bcd1-4a08-8daa-39da44bd3669")


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_packaging_files_columns(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    Verify that this migration adds the columns that hold the packaging files of an editable installed module, that they
    are nullable, and that the model versions that are already stored keep resolving their code.
    """
    # The dump only holds package install modules. Add an editable one and one of unknown install mode, so that the
    # install modes whose source is transported are covered as well. The editable one is wired into model version 1 in
    # full, but registered for no agent, so that it exercises a module that is installed without being loaded.
    await postgresql_client.execute(
        "INSERT INTO public.file(content_hash, content) VALUES ('c0ffee', '\\x23206120706c7567696e'::bytea)"
    )
    await postgresql_client.execute(
        """
        INSERT INTO public.inmanta_module(name, version, environment, requirements, editable_install)
        VALUES
            ('editable_mod', 'src-aaaa', $1, '{lorem}', true),
            ('unknown_mod', 'bbbb', $1, '{ipsum}', NULL)
        """,
        ENVIRONMENT,
    )
    await postgresql_client.execute(
        """
        INSERT INTO public.module_files(
            inmanta_module_name, inmanta_module_version, environment, file_content_hash, python_module_name, is_byte_code
        ) VALUES ('editable_mod', 'src-aaaa', $1, 'c0ffee', 'inmanta_plugins.editable_mod', false)
        """,
        ENVIRONMENT,
    )
    await postgresql_client.execute(
        """
        INSERT INTO public.configurationmodel_modules(environment, cm_version, inmanta_module_name, inmanta_module_version)
        VALUES ($1, 1, 'editable_mod', 'src-aaaa')
        """,
        ENVIRONMENT,
    )

    await migrate_db_from()

    # The columns that hold the packaging files of an editable installed module exist and are nullable: nothing that was
    # already stored has them, and a package installed module never will.
    modules_with_packaging_files = await postgresql_client.fetchval(
        "SELECT count(*) FROM public.inmanta_module WHERE setup_cfg_hash IS NOT NULL OR pyproject_toml_hash IS NOT NULL"
    )
    assert modules_with_packaging_files == 0

    # The code of a model version that was already stored still resolves, with the install mode it was registered at.
    install_specs = await CodeManager().get_code(environment=ENVIRONMENT, model_version=1, agent_name="localhost")
    assert {spec.module_name: spec.editable_install for spec in install_specs} == {
        "std": False,
        "fs": False,
        "editable_mod": True,
    }

    # The editable module keeps deploying the way it did before the migration: it is reconstructed as an installable
    # python package on every agent of the model version, without the packaging files this migration makes room for,
    # and it is not loaded on this agent, which was never registered for it.
    (editable,) = [spec for spec in install_specs if spec.module_name == "editable_mod"]
    (editable_module,) = editable.blueprint.editable_modules
    assert [source.metadata.name for source in editable_module.python_module_sources] == ["inmanta_plugins.editable_mod"]
    assert editable_module.setup_cfg is None
    assert editable_module.pyproject_toml is None
    assert editable.blueprint.inmanta_modules_to_load == []
    assert editable.blueprint.on_disk_code_install is None

    # The package install modules are unaffected: nothing of theirs is transported.
    assert all(spec.blueprint.editable_modules == [] for spec in install_specs if spec.module_name != "editable_mod")
