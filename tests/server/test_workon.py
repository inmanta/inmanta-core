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
import click.testing
import pytest
import subprocess
import uuid
from collections import abc

from inmanta import protocol, workon


async def create_environment(client: protocol.Client, project: uuid.UUID, name: str) -> uuid.UUID:
    result: protocol.Result = await client.create_environment(project_id=project, name=name)
    assert result.code == 200
    return uuid.UUID(result.result["environment"]["id"])


@pytest.fixture
def cli_runner() -> abc.Iterator[click.testing.CliRunner]:
    yield click.testing.CliRunner()


@pytest.fixture
async def project(client: protocol.Client) -> abc.Iterator[uuid.UUID]:
    result: protocol.Result = await client.create_project("env-test")
    assert result.code == 200
    yield uuid.UUID(result.result["project"]["id"])


@pytest.fixture
async def environments(client: protocol.Client, project: uuid.UUID) -> abc.Iterator[abc.Sequence[uuid.UUID]]:
    yield [await create_environment(client, project, f"env-{i}") for i in range(10)]


# TODO: name
def test_workon(server, environments: abc.Sequence[uuid.UUID], cli_runner: click.testing.CliRunner):
    result: click.testing.Result = cli_runner.invoke(cli=workon.workon, args=["--list"])
    print(result.output)
    assert result.exit_code == 0
    assert False



# TODO: more tests
