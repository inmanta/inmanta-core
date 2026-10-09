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

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]

# One of the environments of the dump, that has module code registered for several model versions
ENVIRONMENT = uuid.UUID("76dee420-e755-4b8e-92cb-ad3a9fc651d9")


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_register_modules_per_model_version(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    The new configurationmodel_modules table is populated with the module versions that the agent_modules rows of
    each model version registered, and agent_modules keeps those rows without the version of the module.
    """
    registrations_before = await postgresql_client.fetch("""
        SELECT environment, cm_version, agent_name, inmanta_module_name, inmanta_module_version
        FROM public.agent_modules
        """)
    assert registrations_before

    await migrate_db_from()

    modules_per_version = await postgresql_client.fetch(
        "SELECT environment, cm_version, inmanta_module_name, inmanta_module_version FROM public.configurationmodel_modules"
    )
    assert {tuple(record) for record in modules_per_version} == {
        (record["environment"], record["cm_version"], record["inmanta_module_name"], record["inmanta_module_version"])
        for record in registrations_before
    }

    # The version of a module is no longer registered per agent: the registrations themselves are kept as they were.
    registrations = await postgresql_client.fetch(
        "SELECT environment, cm_version, agent_name, inmanta_module_name FROM public.agent_modules"
    )
    assert {tuple(record) for record in registrations} == {
        (record["environment"], record["cm_version"], record["agent_name"], record["inmanta_module_name"])
        for record in registrations_before
    }

    # These model versions were exported by an iso<10 orchestrator: their install mode is unknown
    assert (
        await postgresql_client.fetchval("SELECT count(*) FROM public.inmanta_module WHERE editable_install IS NOT NULL") == 0
    )


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_register_modules_per_model_version_inconsistent_versions(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    A single version is expected per module and per model version, but nothing enforced that before this migration.
    A model version that registered two versions of one module keeps a single one of them, instead of failing the
    migration on the primary key of the new table.
    """
    highest_version = "f" * 40
    await postgresql_client.execute(
        "INSERT INTO public.inmanta_module(name, version, environment, requirements) VALUES('fs', $1, $2, '{}')",
        highest_version,
        ENVIRONMENT,
    )
    # Model version 1 of this environment already registered another version of the "fs" module, for another agent
    await postgresql_client.execute(
        """
        INSERT INTO public.agent_modules(cm_version, agent_name, inmanta_module_name, inmanta_module_version, environment)
        VALUES(1, 'internal', 'fs', $1, $2)
        """,
        highest_version,
        ENVIRONMENT,
    )

    await migrate_db_from()

    modules_for_version = await postgresql_client.fetch(
        """
        SELECT inmanta_module_version
        FROM public.configurationmodel_modules
        WHERE environment=$1 AND cm_version=1 AND inmanta_module_name='fs'
        """,
        ENVIRONMENT,
    )
    assert [record["inmanta_module_version"] for record in modules_for_version] == [highest_version]

    # Both agents stay registered to load the module, at the version that was kept
    assert sorted(
        record["agent_name"]
        for record in await postgresql_client.fetch(
            "SELECT agent_name FROM public.agent_modules WHERE environment=$1 AND cm_version=1 AND inmanta_module_name='fs'",
            ENVIRONMENT,
        )
    ) == ["internal", "localhost"]
