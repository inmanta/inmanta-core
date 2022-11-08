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
import itertools
import os
import py
import pytest
import subprocess
import textwrap
import uuid
from abc import ABC, abstractmethod
from collections import abc
from dataclasses import dataclass
from typing import Optional

import utils
import inmanta.data.model
import inmanta.main
from inmanta import config, data, protocol
from server.conftest import EnvironmentFactory


# TODO: mypy
# TODO: skip tests if not UNIX


WORKON_REGISTER: str = os.path.join(os.path.dirname(__file__), "..", "..", "misc", "inmanta-workon-register.sh")


@dataclass
class CliResult:
    exit_code: int
    stdout: str
    stderr: str


Bash = abc.Callable[str, abc.Awaitable[CliResult]]


@pytest.fixture
def workon_workdir(server, tmpdir: py.path.local) -> abc.Iterator[py.path.local]:
    """
    Yields a working directory prepared for calling inmanta-workon.
    """
    port = config.Config.get("server", "bind-port")
    state_dir = config.Config.get("config", "state-dir")
    workdir: py.path.local = tmpdir.mkdir("workon_bash_workdir")
    workdir.join(".inmanta.cfg").write(
        textwrap.dedent(
            f"""
            [config]
            state-dir = {state_dir}

            [server]
            bind-port = {port}
            """.strip("\n")
        )
    )
    yield workdir


@pytest.fixture
def workon_broken_cli(workon_workdir: py.path.local, unused_tcp_port_factory: abc.Callable[[], int]) -> abc.Iterator[None]:
    """
    Overrides the server bind port in the config used by inmanta-workon to an unused port to make any inmanta-cli calls fail.
    """
    workon_workdir.join(".inmanta.cfg").write(
        workon_workdir.join(".inmanta.cfg").read().replace(
            str(config.Config.get("server", "bind-port")),
            str(unused_tcp_port_factory()),
        )
    )
    yield


@pytest.fixture
def workon_bash(workon_workdir: py.path.local) -> abc.Iterator[Bash]:
    """
    Yields a function that runs a bash script in an environment where the inmanta-workon shell functions have been registered.
    Any inspection of the workon state should be done from within this bash script since the state change is contained to the
    sub shell. There is no easy way to lift this generically to the Python level.
    """
    async def bash(script: str) -> CliResult:
        # use asyncio's subprocess for non-blocking IO so the server can handle requests
        process: asyncio.Process = await asyncio.create_subprocess_exec(
            "bash", "-c", f"source '{WORKON_REGISTER}';\n{script}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(workon_workdir),
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
        (await environment_factory.create_environment(name=f"env-{i}")).to_dto() for i in range(5)
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


def test_workon_source_check() -> None:
    """
    Verify that the inmanta-workon register script checks that it is sourced rather than executed and notifies the user in when
    it isn't.
    """
    process: subprocess.CompletedProcess = subprocess.run(
        ["bash", WORKON_REGISTER], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    assert process.returncode == 1
    assert process.stdout == ""
    assert process.stderr.strip() == (
        f"ERROR: This script is meant to be sourced rather than executed directly: `source '{WORKON_REGISTER}'`"
    )


# TODO: these are a lot of classes for a single test case. Can this be cleaned up?
@dataclass
class FileRef:
    """
    Reference to a file in an `ExecutablesEnvironment`.

    :param name: The name of the referred file
    :param path_index: The index of the directory in path_executables the referred file lives in. None if it is not on the
        PATH.
    """
    name: str
    path_index: Optional[int]


@dataclass
class Executable:
    name: str
    symlink: Optional[FileRef] = None


@dataclass
class ExecutablesEnvironment:
    """
    Represents an environment of executables, some of which live in PATH, others that do not.

    :param path_executables: Sequence of directories on the PATH, represented by their index. Each directory contains a
        collection of executables.
    :param nonpath_executables: Collection of executables not on the PATH.
    """
    path_executables: abc.Sequence[abc.Collection[Executable]]
    nonpath_executables: abc.Collection[Executable]

    def set_up(self, monkeypatch, working_dir: py.path.local) -> None:
        path_dir: py.path.local = working_dir.mkdir("path")
        nonpath_dir: py.path.local = working_dir.mkdir("nonpath")

        def create_executable(subdir: py.path.local, executable: Executable) -> None:
            file_path: py.path.local = subdir.join(executable.name)
            if executable.symlink is None:
                file_path.write("")
                file_path.chmod(700)
            else:
                target_path: py.path.local = (
                    path_dir.join(str(executable.symlink.path_index), executable.symlink.name)
                    if executable.symlink.path_index is not None
                    else nonpath_dir.join(executable.symlink.name)
                )
                file_path.mksymlinkto(target_path)

        for i, executables in enumerate(self.path_executables):
            subdir: py.path.local = path_dir.mkdir(str(i))
            for executable in executables:
                create_executable(subdir, executable)

        for executable in self.nonpath_executables:
            create_executable(nonpath_dir, executable)

        # TODO: no colons allowed in names
        monkeypatch.setenv("PATH", ":".join(str(i) for i in range(len(self.path_executables))))


# TODO: bash not in PATH with this approach
@pytest.mark.parametrize(
    "executables, expected_cli, expected_python",
    [
        (
            # TODO: this is very verbose -> tiny DSL probably better
            ExecutablesEnvironment(
                path_executables=list(itertools.repeat([Executable(name="python3"), Executable(name="inmanta-cli")], 2)),
                nonpath_executables=[],
            ),
            FileRef(name="inmanta-cli", path_index=0),
            FileRef(name="python3", path_index=0),
        ),
    ],
)
async def test_workon_python_check(
    monkeypatch,
    tmpdir: py.path.local,
    workon_bash: Bash,
    executables: ExecutablesEnvironment,
    expected_cli: FileRef,
    expected_python: FileRef,
) -> None:
    # TODO: update docstring + mention executables should only be python3 + inmanta-cli
    """
    Verify that the inmanta-workon script discovers the appropriate Python executable.

    Sets PATH environment variable to 0:1:...:n where n is the lenght of the executables parameter.

    :param executables: A sequence of executables that exist at various depths on the PATH. Symlinks to other
        e.g. `[["inmanta-cli", "python3"], ["inmanta-cli", "python3"]]`
    """
    print(executables)
    # create bin directories and set PATH
    executables.set_up(monkeypatch, tmpdir)

    # don't call inmanta-workon, just source the registration script and fetch some env vars
    result: CliResult = await workon_bash(f"echo $INMANTA_WORKON_CLI && echo $INMANTA_WORKON_PYTHON")
    breakpoint()


@pytest.mark.parametrize_any("short_option", [True, False])
async def test_workon_list(
    server, workon_bash: Bash, simple_environments: abc.Sequence[data.model.Environment], short_option: bool
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


async def test_workon_list_no_environments(server, workon_bash: Bash) -> None:
    """
    Verify output of `inmanta-workon --list` when no environments are present in the database.
    """
    result: CliResult = await workon_bash("inmanta-workon --list")
    assert result.exit_code == 0, (result.stderr, result.stdout)
    assert result.stderr.strip() == ""
    assert result.stdout.strip() == "No environment defined."


@pytest.mark.slowtest
async def test_workon_list_no_api(
    server,
    workon_broken_cli,
    workon_bash: Bash,
    # fallback environment discovery is file system based and works only for environments that have had at least one compile
    compiled_environments: abc.Sequence[data.model.Environment],
) -> None:
    """
    Verify output of `inmanta-workon --list` when API call to fetch environment names fails.
    """
    result: CliResult = await workon_bash("inmanta-workon --list")
    assert result.exit_code == 0, (result.stderr, result.stdout)
    assert result.stderr.strip() == (
        "WARNING: Failed to connect through inmanta-cli, falling back to file-based environment discovery."
    )
    assert result.stdout.strip() == "\n".join(sorted(str(env.id) for env in compiled_environments))


@pytest.mark.parametrize_any("server_dir_exists", [True, False])
async def test_workon_list_no_api_no_environments(
    server,
    workon_workdir: py.path.local,
    workon_broken_cli,
    workon_bash: Bash,
    tmpdir: py.path.local,
    server_dir_exists: bool,
) -> None:
    """
    Verify output of `inmanta-workon --list` when no environments were found at all in the server state dir.
    """
    if not server_dir_exists:
        # set state dir to directory that does not exist
        workon_workdir.join(".inmanta.cfg").write(
            workon_workdir.join(".inmanta.cfg").read().replace(
                str(config.Config.get("config", "state-dir")),
                str(tmpdir.join("doesnotexist")),
            )
        )

    result: CliResult = await workon_bash("inmanta-workon --list")
    if server_dir_exists:
        assert result.exit_code == 0, (result.stderr, result.stdout)
        assert result.stderr.strip() == (
            "WARNING: Failed to connect through inmanta-cli, falling back to file-based environment discovery."
        )
        assert result.stdout == ""
    else:
        assert result.exit_code == 0
        assert result.stderr.strip() == (
            "WARNING: Failed to connect through inmanta-cli, falling back to file-based environment discovery."
            "\n"
            f"WARNING: no environments directory found at '{tmpdir}/doesnotexist/server/environments'. This is expected if no"
            " environments have been compiled yet. Otherwise, make sure you use this function on the server host."
        )
        assert result.stdout == ""


# TODO: similar tests for actual workon

# TODO: more tests
