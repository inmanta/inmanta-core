"""
    Copyright 2022 Inmanta

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

import uuid
from collections import abc

import asyncpg
import pytest

from inmanta import data


@pytest.fixture
async def db_environment(postgresql_client: asyncpg.connection.Connection) -> abc.AsyncIterator[data.Environment]:
    """
    Creates a new environment in the database without starting the inmanta server.
    """
    project: data.Project = data.Project(
        id=uuid.uuid4(),
        name="myproject",
    )
    environment: data.Environment = data.Environment(
        id=uuid.uuid4(),
        name="myenvironment",
        project=project.id,
    )
    await project.insert(connection=postgresql_client)
    await environment.insert(connection=postgresql_client)
    yield environment
