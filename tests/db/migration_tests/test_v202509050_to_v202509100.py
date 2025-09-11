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

import os
import re
from collections import abc

import asyncpg
import pytest

from inmanta import data

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_created_to_resource_persistent_state(
    postgresql_client: asyncpg.Connection, migrate_db_from: abc.Callable[[], abc.Awaitable[None]]
) -> None:
    """
    Check that the RPS column is added and that it is populated to the
    configuration model version that the resource first appears in.
    """
    await migrate_db_from()
    environments = await data.Environment.get_list()
    for env in environments:
        configuration_models = await data.ConfigurationModel.get_list(
            environment=env.id, order_by_column="version", order="ASC"
        )
        resource_to_first_cm = {}
        for cm in configuration_models:
            resources_in_version = await data.Resource.get_resources_for_version(env.id, cm.version)
            for resource in resources_in_version:
                if resource.resource_id not in resource_to_first_cm:
                    resource_to_first_cm[resource.resource_id] = cm.date

        rps_list = await data.ResourcePersistentState.get_list(environment=env.id)
        for rps in rps_list:
            assert rps.resource_id in resource_to_first_cm
            assert resource_to_first_cm[rps.resource_id] == rps.created
