"""
    Copyright 2021 Inmanta

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
from datetime import datetime
from typing import AsyncIterator, Dict, List

from asyncpg import Connection, Record

from inmanta import const

DISABLED = False


async def update(connection: Connection) -> None:
    # update all timestamp types
    await connection.execute(
        "CREATE INDEX resourceaction_environment_action_status_index ON resourceaction(environment,action, status);"
    )
