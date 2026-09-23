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

# An environment of the dump. Its model version 1 uses the std and fs modules, both installed as a package, and agent
# "localhost" loads both.
ENVIRONMENT = uuid.UUID("a21d254f-de45-425a-ad10-e09057ef1079")
AGENT = "localhost"


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_packaging_files_columns(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    Verify that this migration adds the columns that hold the packaging files of an editable installed module, that they
    are nullable, and that the model versions that are already stored keep resolving their code.
    """
    # The dump only holds package install modules, whose source is not transported. Add the two install modes that do
    # transport it: one registered as an editable install, without the packaging files this migration introduces, and
    # one of unknown install mode. Both are wired into model version 1 and loaded on the agent.
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
    await postgresql_client.executemany(
        """
        INSERT INTO public.module_files(
            inmanta_module_name, inmanta_module_version, environment, file_content_hash, python_module_name, is_byte_code
        ) VALUES ($1, $2, $3, 'c0ffee', $4, false)
        """,
        [
            ("editable_mod", "src-aaaa", ENVIRONMENT, "inmanta_plugins.editable_mod"),
            ("unknown_mod", "bbbb", ENVIRONMENT, "inmanta_plugins.unknown_mod"),
        ],
    )
    await postgresql_client.executemany(
        """
        INSERT INTO public.configurationmodel_modules(environment, cm_version, inmanta_module_name, inmanta_module_version)
        VALUES ($3, 1, $1, $2)
        """,
        [("editable_mod", "src-aaaa", ENVIRONMENT), ("unknown_mod", "bbbb", ENVIRONMENT)],
    )
    await postgresql_client.executemany(
        "INSERT INTO public.agent_modules(cm_version, agent_name, inmanta_module_name, environment) VALUES (1, $1, $2, $3)",
        [(AGENT, "editable_mod", ENVIRONMENT), (AGENT, "unknown_mod", ENVIRONMENT)],
    )

    await migrate_db_from()

    # The columns that hold the packaging files of an editable installed module exist and are nullable: nothing that was
    # already stored has them, and a package installed module never will.
    modules_with_packaging_files = await postgresql_client.fetchval(
        "SELECT count(*) FROM public.inmanta_module WHERE setup_cfg_hash IS NOT NULL OR pyproject_toml_hash IS NOT NULL"
    )
    assert modules_with_packaging_files == 0

    # Without packaging files an editable module can not be reconstructed as an installable python package, so no module
    # is left in that install mode.
    assert await postgresql_client.fetchval("SELECT count(*) FROM public.inmanta_module WHERE editable_install") == 0

    # The code of a model version that was already stored still resolves. The module that was registered as an editable
    # install now shares the unknown install mode, and with it the install on disk path.
    install_specs = await CodeManager().get_code(environment=ENVIRONMENT, model_version=1, agent_name=AGENT)
    assert {spec.module_name: spec.editable_install for spec in install_specs} == {
        "std": False,
        "fs": False,
        "editable_mod": None,
        "unknown_mod": None,
    }

    # Both modules whose source is transported install it on disk, together with their python requirements: neither
    # reaches the agent as a python package, so nothing else records them.
    for module_name, requirement in (("editable_mod", "lorem"), ("unknown_mod", "ipsum")):
        (spec,) = [spec for spec in install_specs if spec.module_name == module_name]
        assert spec.blueprint.editable_modules == []
        assert spec.blueprint.legacy_on_disk_code_install is not None
        assert [source.metadata.name for source in spec.blueprint.legacy_on_disk_code_install.module_sources] == [
            f"inmanta_plugins.{module_name}"
        ]
        assert spec.blueprint.requirements == [requirement]
        assert spec.blueprint.inmanta_modules_to_load == [module_name]

    # The package install modules are unaffected: nothing of theirs is transported.
    assert all(
        spec.blueprint.editable_modules == [] and spec.blueprint.legacy_on_disk_code_install is None
        for spec in install_specs
        if spec.module_name in ("std", "fs")
    )
