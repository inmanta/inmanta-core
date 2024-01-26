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

    The v202401160.sql dump is initialized with 2 parameters and 2 facts:

    COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
    aa4d8e29-3ee3-45bc-bef7-a7e8048d132b	fact1	value1	2c47658c-27f4-4cb6-acb0-74f01d32f8f6	std::File[localhost,path=/tmp/test1]	fact	\N	\N	f
    86a03d38-29e0-4c0a-bcf5-a1f6aaae4f40	fact2	value2	2c47658c-27f4-4cb6-acb0-74f01d32f8f6	std::File[localhost,path=/tmp/test2]	fact	\N	\N	\N
    5c78a8f4-8e96-4c76-9625-c3de5cc868a1	parameter1	value1	2c47658c-27f4-4cb6-acb0-74f01d32f8f6		fact	\N	\N	t
    58c20147-2e79-4b74-958d-8fd60280b914	parameter2	value2	2c47658c-27f4-4cb6-acb0-74f01d32f8f6		fact	\N	\N	\N

    This test checks that a sensible default value is set for parameters/facts with a null value for the 'expires' column
    i.e. parameters never expire and facts always expire by default
    """

    expected_expire_values: dict[str, bool]= {
        "aa4d8e29-3ee3-45bc-bef7-a7e8048d132b": False,
        "86a03d38-29e0-4c0a-bcf5-a1f6aaae4f40": True,
        "5c78a8f4-8e96-4c76-9625-c3de5cc868a1": False,
        "58c20147-2e79-4b74-958d-8fd60280b914": False
    }

    await migrate_db_from()
    client = Client("client")
    result = await client.list_params(tid="2c47658c-27f4-4cb6-acb0-74f01d32f8f6")
    assert result.code == 200
    for param in result.result["parameters"]:
        try:
            assert expected_expire_values[param['id']] == param["expires"], param["name"]
        except KeyError:
            pass
