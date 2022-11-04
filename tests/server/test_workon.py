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
import os
import py
import pytest
import subprocess
import textwrap
import uuid
from collections import abc
from dataclasses import dataclass

import utils
import inmanta.data.model
import inmanta.main
from inmanta import config, data, protocol
from server.conftest import EnvironmentFactory


# TODO: mypy


WORKON_REGISTER: str = os.path.join(os.path.dirname(__file__), "..", "..", "misc", "inmanta-workon-register.sh")


@dataclass
class CliResult:
    exit_code: int
    stdout: str
    stderr: str


Bash = abc.Callable[str, abc.Awaitable[CliResult]]


@pytest.fixture
def workon_bash(server, tmpdir: py.path.local) -> abc.Iterator[Bash]:
    """
    Yields a function that runs a bash script in an environment where the inmanta-workon shell functions have been registered.
    """
    port = config.Config.get("server", "bind-port")
    workdir: py.path.local = tmpdir.join("workon_bash_workdir")
    workdir.join(".inmanta.cfg").write(
        textwrap.dedent(
            f"""
            [server]
            bind-port = {port}
            """.strip("\n")
        )
    )

    async def bash(script: str) -> CliResult:
        # use asyncio's subprocess for non-blocking IO so the server can handle requests
        process: asyncio.Process = await asyncio.create_subprocess_exec(
            "bash", "-c", f"source '{WORKON_REGISTER}';\n{script}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(workdir),
        )
        stdout, stderr = await process.communicate()
        return CliResult(exit_code=process.returncode, stdout=stdout.decode(), stderr=stderr.decode())

    yield bash


async def create_environment(client: protocol.Client, project: uuid.UUID, name: str) -> uuid.UUID:
    result: protocol.Result = await client.create_environment(project_id=project, name=name)
    assert result.code == 200
    return uuid.UUID(result.result["environment"]["id"])


@pytest.fixture
async def simple_environments(client: protocol.Client) -> abc.Iterator[abc.Sequence[data.model.Environment]]:
    """
    Creates some simple environments that aren't set up for compilation.
    """
    async def create_project() -> uuid.UUID:
        result: protocol.Result = await client.create_project("env-test")
        assert result.code == 200
        return uuid.UUID(result.result["project"]["id"])

    async def create_environment(project: uuid.UUID, name: str) -> data.model.Environment:
        result: protocol.Result = await client.environment_create(project_id=project, name=name)
        assert result.code == 200
        return data.model.Environment(**result.result["data"])

    project = await create_project()
    yield [await create_environment(project, f"env-{i}") for i in range(5)]


@pytest.fixture
async def compiled_environments(
    client: protocol.Client, environment_factory: EnvironmentFactory
) -> abc.Iterator[abc.Sequence[data.model.Environment]]:
    """
    Initialize some environments with an empty main.cf and trigger a single compile.
    """
    environments: abc.Sequence[data.model.Environment] = [
        (await environment_factory.create_environment(name=f"env-{i}") for i in range(5)).to_dto()
    ]

    for env in environments:
        result: Result = await client.notify_change(env.id)
        assert result.code == 200

    async def all_compiles_done() -> bool:
        return all(
            result.code == 204 for result in await asyncio.gather(*(client.is_compiling(env.id) for env in environments))
        )

    await utils.retry_limited(all_compiles_done, 10)

    yield environments


@pytest.mark.parametrize_any("short_option", [True, False])
async def test_workon_list(
    server, simple_environments: abc.Sequence[data.model.Environment], workon_bash: Bash, short_option: bool
) -> None:
    """
    Verify output of `inmanta-workon --list`.
    """
    result: CliResult = await workon_bash(f"inmanta-workon {'-l' if short_option else '--list'}")
    assert result.exit_code == 0, (result.stderr, result.stdout)
    assert result.stderr.strip() == ""
    assert result.stdout.strip() == inmanta.main.get_table(
        ["Project name", "Project ID", "Environment", "Environment ID"],
        [["env-test", env.project_id, env.name, env.id] for env in simple_environments]
    ).strip()


# TODO
def test_workon_list_no_environments(server) -> None:
    """
    Verify output of `inmanta-workon --list` when no environments are present in the database.
    """
    result: click.testing.Result = cli_runner.invoke(cli=workon.workon, args=["--list"])
    assert result.exit_code == 0, (result.stderr, result.output)
    assert result.output.strip() == ""
    assert result.stderr.strip() == ""


# TODO
@pytest.mark.slowtest
def test_workon_list_no_api(
    server,
    # fallback environment discovery is file system based and works only for environments that have had at least one compile
    compiled_environments: abc.Sequence[data.model.Environment],
    unused_tcp_port: int,
) -> None:
    """
    Verify output of `inmanta-workon --list` when API call to fetch environment names fails.
    """
    # set port incorrectly so the API call will fail
    config.Config.set("cmdline_rest_transport", "port", str(unused_tcp_port))

    result: click.testing.Result = cli_runner.invoke(cli=workon.workon, args=["--list"])
    assert result.exit_code == 0, (result.stderr, result.output)
    assert result.stderr.strip() == (
        "Failed to fetch environments details from the server, falling back to basic nameless environment discovery."
        " Reason: [Errno 111] Connection refused"
    )
    assert result.output.strip() == "\n".join(sorted(str(env.id) for env in compiled_environments))


# TODO
@pytest.mark.parametrize_any("server_dir_exists", [True, False])
def test_workon_list_no_api_no_environments(
    server, tmpdir: py.path.local, unused_tcp_port: int, server_dir_exists: bool
) -> None:
    """
    Verify output of `inmanta-workon --list` when no environments were found at all in the server state dir.
    """
    # set port incorrectly so the API call will fail
    config.Config.set("cmdline_rest_transport", "port", str(unused_tcp_port))
    if not server_dir_exists:
        # set state dir to directory that does not exist
        config.Config.set("config", "state-dir", str(tmpdir.join("doesnotexist")))

    result: click.testing.Result = cli_runner.invoke(cli=workon.workon, args=["--list"])
    if server_dir_exists:
        assert result.exit_code == 0, (result.stderr, result.output)
        assert result.stderr.strip() == (
            "Failed to fetch environments details from the server, falling back to basic nameless environment discovery."
            " Reason: [Errno 111] Connection refused"
        )
        assert result.output == ""
    else:
        assert result.exit_code == 1
        assert result.stderr.strip() == (
            "Error: Failed to fetch environment details from the server or to find the server state directory. Please check"
            " you're running this command from the inmanta server host and `cmdline_rest_transport.port` and"
            " `config.state-dir` settings are set correctly."
        )
        assert result.output == ""


# TODO: similar tests for actual workon

# TODO: more tests
