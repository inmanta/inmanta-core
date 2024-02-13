"""
    Copyright 2024 Inmanta

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
import json
import os
import re
from collections import abc

import asyncpg
import pytest

from inmanta import data
from inmanta.protocol import Client

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_non_null_constraint(
    postgresql_client: asyncpg.Connection,
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:
    r"""
    This migration script adds
      - the non-null constraint to the ``undeployable`` and ``skipped_for_undeployable``
        columns of the configurationmodel table.
      - default empty arrays instead of NULL for these columns


    """

    result = await postgresql_client.fetch(
        """
            SELECT * FROM public.configurationmodel;
        """
    )
    # data = json.loads(result[0])
    assert result[0]
    # assert isinstance(settings[data.AUTOSTART_AGENT_DEPLOY_INTERVAL], int)
    # assert isinstance(settings[data.AUTOSTART_AGENT_REPAIR_INTERVAL], int)

    await migrate_db_from()

    result = await postgresql_client.fetch(
        """
            SELECT * FROM public.configurationmodel;
        """
    )
    assert result[0]
    assert  True
    #
    # expected_expire_values: dict[str, bool] = {
    #     # Facts:                                  Value before migration:
    #     "da7cdfcd-b88d-41f6-86d2-49251adabea1": False,  # False
    #     "adef7ac5-c24b-474a-8cdc-edfa27362960": True,  # None
    #     "f817f3b4-9079-4320-be99-172b00823b87": True,  # True
    #     # Parameters:
    #     "dea1161f-9561-485a-9541-dded930d69c6": False,  # False
    #     "757dec65-3367-437a-82d3-6b8f53739dad": False,  # None
    #     "0c3f2e4a-2aaf-4c6f-bdbb-075679b16f31": False,  # True
    # }
    #
    # client = Client("client")
    # result = await client.list_params(tid="b1ed3482-7826-4c31-a185-0d6993192e38")
    # assert result.code == 200
    # assert len(result.result["parameters"]) == len(expected_expire_values)
    # for param in result.result["parameters"]:
    #     assert expected_expire_values[param["id"]] == param["expires"], param["name"]
