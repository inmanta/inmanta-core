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
from collections import abc

import pytest

file_name_regex = re.compile("test_v([0-9]{9})_to_v[0-9]{9}")
part = file_name_regex.match(__name__)[1]


@pytest.mark.db_restore_dump(os.path.join(os.path.dirname(__file__), f"dumps/v{part}.sql"))
async def test_drop_is_suitable_for_partial_compiles_column(
    migrate_db_from: abc.Callable[[], abc.Awaitable[None]],
    get_columns_in_db_table: abc.Callable[[str], abc.Awaitable[list[str]]],
) -> None:
    """
    The is_suitable_for_partial_compiles column is dropped from the configurationmodel table.
    """
    assert "is_suitable_for_partial_compiles" in await get_columns_in_db_table("configurationmodel")

    await migrate_db_from()

    assert "is_suitable_for_partial_compiles" not in await get_columns_in_db_table("configurationmodel")
