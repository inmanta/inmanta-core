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
    dc7b5b59-33f4-417b-9afc-3c91b24b4008	fact1	value1	630a163d-d010-4f70-b158-3434f7477aa9	std::File[localhost,path=/tmp/test1]	fact	\N	\N	f       # NOQA E501
    379e582a-007e-46eb-ac76-479c23da3d14	fact2	value2	630a163d-d010-4f70-b158-3434f7477aa9	std::File[localhost,path=/tmp/test2]	fact	\N	\N	\N      # NOQA E501
    7428c4f7-d03d-47f9-8cf0-bce6688b61b3	parameter1	value1	630a163d-d010-4f70-b158-3434f7477aa9		fact	\N	\N	f
    bb53a43c-c74f-43a9-999d-dc04c54324a1	parameter2	value2	630a163d-d010-4f70-b158-3434f7477aa9		fact	\N	\N	\N
    \.

    This test checks that a sensible default value is set for parameters/facts with a null value for the 'expires' column
    i.e. parameters never expire and facts always expire by default
    """

    await migrate_db_from()

    expected_expire_values: dict[str, bool] = {
        # Facts:                                  Value before migration:
        "dc7b5b59-33f4-417b-9afc-3c91b24b4008": False,  # False
        "379e582a-007e-46eb-ac76-479c23da3d14": True,  # None
        # Parameters:
        "7428c4f7-d03d-47f9-8cf0-bce6688b61b3": False,  # False
        "bb53a43c-c74f-43a9-999d-dc04c54324a1": False,  # None
    }

    client = Client("client")
    result = await client.list_params(tid="630a163d-d010-4f70-b158-3434f7477aa9")
    assert result.code == 200
    for param in result.result["parameters"]:
        try:
            assert expected_expire_values[param["id"]] == param["expires"], param["name"]
        except KeyError:
            pass
