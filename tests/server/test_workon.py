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
import asyncio
import click.testing
import pytest
import subprocess
import uuid
from collections import abc

import utils
from inmanta import config, data, protocol, workon
from server.conftest import EnvironmentFactory


@pytest.fixture
def cli_runner() -> abc.Iterator[click.testing.CliRunner]:
    yield click.testing.CliRunner(mix_stderr=False)


async def create_environment(client: protocol.Client, project: uuid.UUID, name: str) -> uuid.UUID:
    result: protocol.Result = await client.create_environment(project_id=project, name=name)
    assert result.code == 200
    return uuid.UUID(result.result["environment"]["id"])


@pytest.fixture
def cli_runner() -> abc.Iterator[click.testing.CliRunner]:
    yield click.testing.CliRunner(mix_stderr=False)


@pytest.fixture
async def simple_environments(client: protocol.Client) -> abc.Iterator[abc.Sequence[uuid.UUID]]:
    """
    Creates some simple environments that aren't set up for compilation.
    """
    async def create_project() -> uuid.UUID:
        result: protocol.Result = await client.create_project("env-test")
        assert result.code == 200
        return uuid.UUID(result.result["project"]["id"])

    async def create_environment(project: uuid.UUID, name: str) -> uuid.UUID:
        result: protocol.Result = await client.create_environment(project_id=project, name=name)
        assert result.code == 200
        return uuid.UUID(result.result["environment"]["id"])

    project = await create_project()
    yield [await create_environment(project, f"env-{i}") for i in range(5)]


@pytest.fixture
async def compiled_environments(client: protocol.Client, environment_factory: EnvironmentFactory) -> abc.Iterator[abc.Sequence[data.Environment]]:
    """
    Initialize some environments with an empty main.cf and trigger a single compile.
    """
    environments: abc.Sequence[data.Environment] = [
        await environment_factory.create_environment(name=f"env-{i}") for i in range(5)
    ]

    for env in environments:
        result: Result = await client.notify_change(env.id)
        assert result.code == 200

    async def all_compiles_done() -> bool:
        return all(
            result.code == 204 for result in await asyncio.gather(*(client.is_compiling(env.id) for env in environments))
        )

    await utils.retry_limited(all_compiles_done, 20)

    yield environments


@pytest.mark.parametrize_any("short_option", [True, False])
def test_workon_list(server, simple_environments: abc.Sequence[uuid.UUID], cli_runner: click.testing.CliRunner, short_option: bool):
    """
    Verify output of `inmanta-workon --list`.
    """
    result: click.testing.Result = cli_runner.invoke(cli=workon.workon, args=["-l" if short_option else "--list"])
    assert result.exit_code == 0, result.output
    assert len(simple_environments) <= 10, "Not strictly an issue but the assertion below assumes 1 digit"
    assert result.output.strip() == "\n".join(
        f"env-{i}                {env}" for i, env in enumerate(simple_environments)
    )


def test_workon_list_no_api(
    server,
    # fallback environment discovery is file system based and works only for environments that have had at least one compile
    compiled_environments: abc.Sequence[data.Environment],
    cli_runner: click.testing.CliRunner,
    sync_client: protocol.SyncClient,
    unused_tcp_port: int,
):
    """
    Verify output of `inmanta-workon --list` when API call to fetch environment names fails.
    """
    # set port incorrectly so the API call will fail
    config.Config.set("cmdline_rest_transport", "port", str(unused_tcp_port))

    result: click.testing.Result = cli_runner.invoke(cli=workon.workon, args=["--list"])
    assert result.exit_code == 0, result.output
    assert result.stderr.strip() == (
        "Failed to fetch environments details from the server, falling back to basic nameless environment discovery."
        " Reason: [Errno 111] Connection refused"
    )
    assert result.output.strip() == "\n".join(sorted(str(env.id) for env in compiled_environments))


# TODO: test list on non-server machine

# TODO: more tests
