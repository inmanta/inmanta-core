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


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_editable_modules_without_setup_cfg_install_on_disk(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    An editable installed module registered without a setup.cfg can not be rebuilt by the agent: it falls back to the
    install on disk. Every other module keeps its install mode, and a module stored without requirements gets an empty
    list.
    """
    environment: uuid.UUID = await postgresql_client.fetchval("SELECT id FROM public.environment LIMIT 1")
    await postgresql_client.execute(
        """
        INSERT INTO public.inmanta_module(name, version, environment, requirements, editable_install)
        VALUES
            ('without_setup_cfg', 'a', $1, '{"jinja2"}', true),
            ('with_setup_cfg', 'b', $1, '{}', true),
            ('package', '1.0.0', $1, NULL, false),
            ('legacy', 'c', $1, '{}', NULL)
        """,
        environment,
    )
    await postgresql_client.execute(
        "INSERT INTO public.file(content_hash, content) VALUES('h1', 'a'), ('h2', 'b') ON CONFLICT DO NOTHING"
    )
    await postgresql_client.execute(
        """
        INSERT INTO public.module_files(inmanta_module_name, inmanta_module_version, environment, file_content_hash, path)
        VALUES
            ('without_setup_cfg', 'a', $1, 'h1', 'inmanta_plugins/without_setup_cfg/__init__.py'),
            ('with_setup_cfg', 'b', $1, 'h1', 'inmanta_plugins/with_setup_cfg/__init__.py'),
            ('with_setup_cfg', 'b', $1, 'h2', 'setup.cfg')
        """,
        environment,
    )

    await migrate_db_from()

    modules = {
        record["name"]: (record["editable_install"], record["requirements"])
        for record in await postgresql_client.fetch(
            "SELECT name, editable_install, requirements FROM public.inmanta_module WHERE environment=$1", environment
        )
    }
    assert modules["without_setup_cfg"] == (None, ["jinja2"])
    assert modules["with_setup_cfg"] == (True, [])
    assert modules["package"] == (False, [])
    assert modules["legacy"] == (None, [])

    with pytest.raises(asyncpg.NotNullViolationError):
        await postgresql_client.execute(
            "UPDATE public.inmanta_module SET requirements = NULL WHERE environment=$1 AND name='package'", environment
        )
