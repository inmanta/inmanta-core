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

import os
import re
from collections import abc

import asyncpg
import pytest

from inmanta.protocol import Client

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_add_non_null_constraint(
    postgresql_client: asyncpg.Connection,
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
) -> None:
    r"""
    This migration script adds the non-null constraint to the ``expires`` column of the parameter table.

    The v202401160.sql dump is initialized with 3 parameters and 3 facts:

    COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
    da7cdfcd-b88d-41f6-86d2-49251adabea1	fact1	value1	b1ed3482-7826-4c31-a185-0d6993192e38	std::File[localhost,path=/tmp/test1]	fact	\N	\N	f  # NOQA E501
    adef7ac5-c24b-474a-8cdc-edfa27362960	fact2	value2	b1ed3482-7826-4c31-a185-0d6993192e38	std::File[localhost,path=/tmp/test2]	fact	\N	\N	\N  # NOQA E501
    f817f3b4-9079-4320-be99-172b00823b87	fact3	value3	b1ed3482-7826-4c31-a185-0d6993192e38	std::File[localhost,path=/tmp/test3]	fact	\N	\N	t  # NOQA E501
    dea1161f-9561-485a-9541-dded930d69c6	parameter1	value1	b1ed3482-7826-4c31-a185-0d6993192e38		fact	\N	\N	f
    757dec65-3367-437a-82d3-6b8f53739dad	parameter2	value2	b1ed3482-7826-4c31-a185-0d6993192e38		fact	\N	\N	\N
    0c3f2e4a-2aaf-4c6f-bdbb-075679b16f31	parameter3	value3	b1ed3482-7826-4c31-a185-0d6993192e38		fact	\N	\N	t
    \.

    This test checks that a sensible default value is set for parameters/facts with a null value for the 'expires' column
    i.e. parameters never expire and facts always expire by default
    And that parameters never expire
    """

    await migrate_db_from()

    expected_expire_values: dict[str, bool] = {
        # Facts:                                  Value before migration:
        "da7cdfcd-b88d-41f6-86d2-49251adabea1": False,  # False
        "adef7ac5-c24b-474a-8cdc-edfa27362960": True,  # None
        "f817f3b4-9079-4320-be99-172b00823b87": True,  # True
        # Parameters:
        "dea1161f-9561-485a-9541-dded930d69c6": False,  # False
        "757dec65-3367-437a-82d3-6b8f53739dad": False,  # None
        "0c3f2e4a-2aaf-4c6f-bdbb-075679b16f31": False,  # True
    }

    client = Client("client")
    result = await client.list_params(tid="b1ed3482-7826-4c31-a185-0d6993192e38")
    assert result.code == 200
    assert len(result.result["parameters"]) == len(expected_expire_values)
    for param in result.result["parameters"]:
        assert expected_expire_values[param["id"]] == param["expires"], param["name"]
