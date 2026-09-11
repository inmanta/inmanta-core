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
from inmanta.data.model import InmantaModuleInstallMode

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]

# An environment of the dump, which holds two model versions using the std and fs modules
ENVIRONMENT = uuid.UUID("d76a1c0d-5e9c-4f9d-962c-8f270bf82041")


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_install_mode_and_per_version_modules(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    Verify that this migration
        - maps every value of the inmanta_module.editable_install boolean onto the new install_mode column.
        - registers the modules of the model versions that are already stored in the new configurationmodel_modules
          table, so that those versions keep resolving their code.
    """
    # The dump only holds package install modules. Add one module of each other install mode, so that all three mappings
    # onto the new column are covered.
    await postgresql_client.execute(
        """
        INSERT INTO public.inmanta_module(name, version, environment, requirements, editable_install)
        VALUES
            ('editable_mod', 'aaaa', $1, '{}', true),
            ('unknown_mod', 'bbbb', $1, '{lorem}', NULL);
        """,
        ENVIRONMENT,
    )

    await migrate_db_from()

    # The boolean is replaced by the install mode it stood for. A module of a model version that was exported by an
    # iso<10 orchestrator (null) is installed on disk: that is what the compatibility layer already did for it.
    install_modes = {
        record["name"]: record["install_mode"]
        for record in await postgresql_client.fetch(
            "SELECT name, install_mode FROM public.inmanta_module WHERE environment=$1", ENVIRONMENT
        )
    }
    assert install_modes == {
        "std": InmantaModuleInstallMode.PACKAGE.value,
        "fs": InmantaModuleInstallMode.PACKAGE.value,
        "editable_mod": InmantaModuleInstallMode.EDITABLE.value,
        "unknown_mod": InmantaModuleInstallMode.ON_DISK.value,
    }

    with pytest.raises(asyncpg.UndefinedColumnError):
        await postgresql_client.execute("SELECT editable_install FROM public.inmanta_module")

    # The modules of each model version are registered once per version, backfilled from the per agent registrations. The
    # two modules that were just inserted are not part of a model version, so they are not registered.
    per_version_modules = {
        (record["cm_version"], record["inmanta_module_name"], record["inmanta_module_version"])
        for record in await postgresql_client.fetch(
            "SELECT cm_version, inmanta_module_name, inmanta_module_version"
            " FROM public.configurationmodel_modules WHERE environment=$1",
            ENVIRONMENT,
        )
    }
    registered_per_agent = {
        (record["cm_version"], record["inmanta_module_name"], record["inmanta_module_version"])
        for record in await postgresql_client.fetch(
            "SELECT DISTINCT cm_version, inmanta_module_name, inmanta_module_version"
            " FROM public.agent_modules WHERE environment=$1",
            ENVIRONMENT,
        )
    }
    assert per_version_modules == registered_per_agent
    # The dump has both of its modules registered for its first model version
    assert {(1, "std", "8.7.3"), (1, "fs", "1.2.0")} <= per_version_modules
    # The two modules that were just inserted are not part of any model version
    assert not {module_name for _, module_name, _ in per_version_modules} & {"editable_mod", "unknown_mod"}

    # The code of a model version that was already stored still resolves, with the install mode the boolean stood for.
    install_specs = await CodeManager().get_code(environment=ENVIRONMENT, model_version=1, agent_name="localhost")
    assert {spec.module_name: spec.install_mode for spec in install_specs} == {
        "std": InmantaModuleInstallMode.PACKAGE,
        "fs": InmantaModuleInstallMode.PACKAGE,
    }
    assert all(spec.blueprint.on_disk_code_install is None for spec in install_specs)
