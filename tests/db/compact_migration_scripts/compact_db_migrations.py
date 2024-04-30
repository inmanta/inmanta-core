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


    Tool to compact db migration scripts
"""

import os

from common import compact_and_dump
from inmanta.data.schema import CORE_SCHEMA_NAME


async def test_compact_and_dump(postgres_db, database_name):
    """
    Compact, apply database migrations using DBSchema, and dump the database schema with modifications.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    compact_dir = os.path.join(script_dir, "versions_to_compact")
    original_dir = os.path.abspath(os.path.join(script_dir, "../../../src/inmanta/db/versions"))
    outfile = f"{os.path.dirname(__file__)}/compacted_dump.sql"

    await compact_and_dump(compact_dir, original_dir, outfile, CORE_SCHEMA_NAME, database_name, postgres_db)
