"""
    Copyright 2023 Inmanta

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
from collections import abc
from typing import Awaitable, Callable, List

import pytest

from inmanta.data import Environment, ConfigurationModel, Resource


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), "dumps/v202306060.sql"))
async def test_migration(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:
    await migrate_db_from()
    env = await Environment.get_one(name="dev-1")
    assert env
    model = await ConfigurationModel.get_latest_version(env.id)
    assert model
    resources = await Resource.get_list(environment=env.id, model=model.version)
    assert resources

    for resource in resources:
        print(resource)
        assert resource.last_success



