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
import asyncio.subprocess
import copy
import getpass
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import uuid
from collections import abc
from dataclasses import dataclass
from typing import Optional, Sequence, Union

import py.path
import pytest
import yaml

import inmanta.data.model
import inmanta.env
import inmanta.main
import utils
from inmanta import config, data, protocol
from inmanta.module import Project
from inmanta.server.protocol import Server
from server.conftest import EnvironmentFactory

if os.name != "posix":
    pytest.skip("Skipping UNIX-only tests", allow_module_level=True)


WORKON_REGISTER: str = os.path.join(os.path.dirname(__file__), "..", "..", "misc", "inmanta-workon-register.sh")


@dataclass
class CliResult:
    exit_code: int
    stdout: str
    stderr: str


Bash = abc.Callable[[str], abc.Awaitable[CliResult]]


@pytest.fixture
def workon_environments_dir(server: Server) -> abc.Iterator[py.path.local]:
    state_dir: Optional[str] = config.Config.get("config", "state-dir")
    assert state_dir is not None
    yield py.path.local(state_dir).join("server", "environments")


@pytest.fixture
def workon_workdir(server: Server, tmpdir: py.path.local) -> abc.Iterator[py.path.local]:
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
            """.strip(
                "\n"
            )
        )
    )
    yield workdir


@pytest.fixture
def workon_broken_cli(workon_workdir: py.path.local, unused_tcp_port_factory: abc.Callable[[], int]) -> abc.Iterator[None]:
    """
    Overrides the server bind port in the config used by inmanta-workon to an unused port to make any inmanta-cli calls fail.
    """
    workon_workdir.join(".inmanta.cfg").write_text(
        workon_workdir.join(".inmanta.cfg")
        .read_text(encoding="utf-8")
        .replace(
            str(config.Config.get("server", "bind-port")),
            str(unused_tcp_port_factory()),
        ),
        encoding="utf-8",
    )
    yield


@pytest.fixture
def workon_bash(workon_workdir: py.path.local) -> abc.Iterator[Bash]:
    """
    Yields a function that runs a bash script in an environment where the inmanta-workon shell functions have been registered.
    Any inspection of the workon state should be done from within this bash script since the state change is contained to the
    sub shell. There is no easy way to lift this generically to the Python level.
    """

    async def bash(script: str, *, override_path: bool = True) -> CliResult:
        # use asyncio's subprocess for non-blocking IO so the server can handle requests
        process: asyncio.subprocess.Process = await asyncio.create_subprocess_exec(
            "bash",
            "-c",
            f"source '{WORKON_REGISTER}';\n{script}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(workon_workdir),
            env={
                **os.environ,
                **(
                    # inmanta-workon expects inmanta-cli to be present in PATH but this might not be the case for the test
                    # environment (e.g. if the venv is not activated and the tests are executed with a fully qualified Python
                    # path)
                    {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]}
                    if override_path
                    else {}
                ),
            },
        )
        stdout, stderr = await process.communicate()
        assert process.returncode is not None
        return CliResult(exit_code=process.returncode, stdout=stdout.decode(), stderr=stderr.decode())

    yield bash


async def create_environment(client: protocol.Client, project: uuid.UUID, name: str) -> uuid.UUID:
    result: protocol.Result = await client.create_environment(project_id=project, name=name)
    assert result.code == 200
    return uuid.UUID(result.result["environment"]["id"])  # type: ignore


@pytest.fixture
async def simple_environments(client: protocol.Client) -> abc.AsyncIterator[abc.Sequence[data.model.Environment]]:
    """
    Creates some simple environments that aren't set up for compilation.
    """

    async def create_project() -> uuid.UUID:
        result: protocol.Result = await client.create_project("test")
        assert result.code == 200
        return uuid.UUID(result.result["project"]["id"])  # type: ignore

    async def create_environment(project: uuid.UUID, name: str) -> data.model.Environment:
        result: protocol.Result = await client.environment_create(project_id=project, name=name)
        assert result.code == 200
        return data.model.Environment(**result.result["data"])  # type: ignore

    project = await create_project()
    yield [await create_environment(project, f"env-{i}") for i in range(5)]


@pytest.fixture
async def compiled_environments(client: protocol.Client) -> abc.AsyncIterator[abc.Sequence[data.model.Environment]]:
    """
    Initialize some environments with an empty main.cf and trigger a single compile.
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        nb_environments: int = 3
        environments: abc.Sequence[data.model.Environment] = [
            (
                await EnvironmentFactory(os.path.join(tmpdirname, f"env-{i}"), project_name=f"project-{i}").create_environment(
                    name=f"env-{i}"
                )
            ).to_dto()
            for i in range(nb_environments)
        ]

        for env in environments:
            result: protocol.Result = await client.notify_change(env.id)
            assert result.code == 200

        async def all_compiles_done() -> bool:
            return all(
                result.code == 204 for result in await asyncio.gather(*(client.is_compiling(env.id) for env in environments))
            )

        await utils.retry_limited(all_compiles_done, 15)

        yield environments


def test_workon_source_check() -> None:
    """
    Verify that the inmanta-workon register script checks that it is sourced rather than executed and notifies the user in when
    it isn't.
    """
    process: subprocess.CompletedProcess[str] = subprocess.run(
        ["bash", WORKON_REGISTER], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    assert process.returncode == 1
    assert process.stdout == ""
    assert (
        process.stderr.strip()
        == f"ERROR: This script is meant to be sourced rather than executed directly: `source '{WORKON_REGISTER}'`"
    )


async def test_workon_python_check(
    monkeypatch: pytest.MonkeyPatch,
    tmpdir: py.path.local,
    workon_bash: Bash,
) -> None:
    """
    Verify that the inmanta-workon script discovers the appropriate Python executable. This test only covers the most complex
    scenario (which is also the most relevant one): the default server installation:

    PATH=/bin/:...
    /bin/inmanta-cli -> /opt/inmanta/bin/inmanta-cli
    /bin/python3
    /opt/inmanta/bin/inmanta-cli
    /opt/inmanta/bin/python3
    """
    bin_dir: py.path.local = tmpdir.mkdir("bin")  # represents /bin/
    opt_dir: py.path.local = tmpdir.mkdir("opt")  # represents /opt/inmanta/bin/

    system_python: py.path.local = bin_dir.join("python3")
    system_inmanta: py.path.local = bin_dir.join("inmanta-cli")
    opt_inmanta: py.path.local = opt_dir.join("inmanta-cli")
    opt_python: py.path.local = opt_dir.join("python3")

    # create executables and set up PATH
    for actual_executable in [system_python, opt_inmanta, opt_python]:
        actual_executable.write("")
        actual_executable.chmod(0o700)
    system_inmanta.mksymlinkto(opt_inmanta)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")

    # don't call inmanta-workon, just source the registration script and fetch some env vars
    result: CliResult = await workon_bash("echo $INMANTA_WORKON_CLI && echo $INMANTA_WORKON_PYTHON", override_path=False)
    assert result.exit_code == 0
    assert result.stderr.strip() == ""
    assert result.stdout.splitlines() == [str(opt_inmanta), str(opt_python)]


@pytest.mark.parametrize_any("option", [None, "-h", "--help"])
async def test_workon_help(workon_bash: Bash, option: Optional[str]) -> None:
    """
    Verify output of `inmanta-workon --help`.
    """
    result: CliResult = await workon_bash(f"inmanta-workon {option if option is not None else ''}")
    assert result.exit_code == 0, (result.stderr, result.stdout)
    assert result.stderr == ""
    assert result.stdout == textwrap.dedent(
        """
        Usage: inmanta-workon [-l | --list] [ENVIRONMENT]
        Activate the Python virtual environment for an inmanta environment.

        -l, --list      list the inmanta environments on this server

        The ENVIRONMENT argument may be the name or the id of an inmanta environment.
        """.strip(
            "\n"
        ),
    )


@pytest.mark.parametrize_any("short_option", [True, False])
async def test_workon_list(
    server: Server, workon_bash: Bash, simple_environments: abc.Sequence[data.model.Environment], short_option: bool
) -> None:
    """
    Verify output of `inmanta-workon --list`.
    """
    result: CliResult = await workon_bash(f"inmanta-workon {'-l' if short_option else '--list'}")
    assert result.exit_code == 0, (result.stderr, result.stdout)
    assert result.stderr == ""
    assert (
        result.stdout.strip()
        == inmanta.main.get_table(
            ["Project name", "Project ID", "Environment", "Environment ID"],
            [["test", str(env.project_id), env.name, str(env.id)] for env in simple_environments],
        ).strip()
    )


async def test_workon_list_no_environments(server: Server, workon_bash: Bash) -> None:
    """
    Verify output of `inmanta-workon --list` when no environments are present in the database.
    """
    result: CliResult = await workon_bash("inmanta-workon --list")
    assert result.exit_code == 0, (result.stderr, result.stdout)
    assert result.stderr == ""
    assert result.stdout.strip() == "No environments defined."


@pytest.mark.slowtest
async def test_workon_list_no_api(
    server: Server,
    workon_broken_cli: None,
    workon_bash: Bash,
    # fallback environment discovery is file system based and works only for environments that have had at least one compile
    compiled_environments: abc.Sequence[data.model.Environment],
) -> None:
    """
    Verify output of `inmanta-workon --list` when API call to fetch environment names fails.
    """
    result: CliResult = await workon_bash("inmanta-workon --list")
    assert result.exit_code == 0, (result.stderr, result.stdout)
    assert (
        result.stderr.strip()
        == "WARNING: Failed to connect through inmanta-cli, falling back to file-based environment discovery."
    )
    assert result.stdout.strip() == "\n".join(sorted(str(env.id) for env in compiled_environments))


@pytest.mark.parametrize_any("server_dir_exists", [True, False])
async def test_workon_list_no_api_no_environments(
    server: Server,
    workon_workdir: py.path.local,
    workon_broken_cli: None,
    workon_bash: Bash,
    tmpdir: py.path.local,
    server_dir_exists: bool,
) -> None:
    """
    Verify output of `inmanta-workon --list` when no environments were found at all in the server state dir.
    """
    if not server_dir_exists:
        # set state dir to directory that does not exist
        workon_workdir.join(".inmanta.cfg").write_text(
            workon_workdir.join(".inmanta.cfg")
            .read_text(encoding="utf-8")
            .replace(
                str(config.Config.get("config", "state-dir")),
                str(tmpdir.join("doesnotexist")),
            ),
            encoding="utf-8",
        )

    result: CliResult = await workon_bash("inmanta-workon --list")
    if server_dir_exists:
        assert result.exit_code == 0, (result.stderr, result.stdout)
        assert (
            result.stderr.strip()
            == "WARNING: Failed to connect through inmanta-cli, falling back to file-based environment discovery."
        )
        assert result.stdout == ""
    else:
        assert result.exit_code == 0
        assert (
            result.stderr.strip()
            == "WARNING: Failed to connect through inmanta-cli, falling back to file-based environment discovery."
            "\n"
            f"WARNING: no environments directory found at '{tmpdir}/doesnotexist/server/environments'. This is expected if no"
            " environments have been compiled yet. Otherwise, make sure you use this function on the server host."
        )
        assert result.stdout == ""


async def test_workon_list_invalid_config(
    server: Server,
    workon_workdir: py.path.local,
    workon_broken_cli: None,
    workon_bash: Bash,
) -> None:
    """
    Verify error behavior of `inmanta-workon --list` when an invalid cfg file is encountered.
    """
    # write invalid config
    workon_workdir.join(".inmanta.cfg").write("this is not compatible with the cfg format")
    result: CliResult = await workon_bash("inmanta-workon --list")
    assert result.exit_code == 1, (result.stderr, result.stdout)
    assert (
        result.stderr.strip() == "ERROR: Failed to determine server bind port. Is the server config valid?"
        "\n"
        "WARNING: Failed to connect through inmanta-cli, falling back to file-based environment discovery."
        "\n"
        "ERROR: Failed to determine server state directory. Is the server config valid?"
    )
    assert result.stdout == ""


async def test_workon_invalid_config(
    server: Server,
    workon_workdir: py.path.local,
    workon_bash: Bash,
) -> None:
    """
    Verify error behavior of `inmanta-workon someenvironment` when an invalid cfg file is encountered.
    """
    # write invalid config
    workon_workdir.join(".inmanta.cfg").write("this is not compatible with the cfg format")
    result: CliResult = await workon_bash("inmanta-workon someenvironment")
    assert result.exit_code == 1, (result.stderr, result.stdout)
    assert result.stderr.strip() == "ERROR: Failed to determine server state directory. Is the server config valid?"
    assert result.stdout == ""


async def assert_workon_state(
    workon_bash: Bash,
    arg: str,
    *,
    pre_activate: Optional[str] = None,
    post_activate: Optional[str] = None,
    inmanta_user: Optional[str] = None,
    expected_dir: py.path.local,
    invert_success_assert: bool = False,
    invert_working_dir_assert: bool = False,
    invert_python_assert: bool = False,
    invert_ps1_assert: bool = False,
    expect_stderr: str = "",
) -> None:
    """
    Helper function to call inmanta-workon with an argument and assert the expected state.

    :param workon_bash: The Bash environment to use for this assertion.
    :param arg: The environment argument to pass to inmanta-workon. May be either a name or a UUID.
    :param pre_activate: Additional script to execute after running inmanta-workon. The success assertion will include a
        check on the status of the last command in this script.
    :param post_activate: Additional script to execute after running inmanta-workon. The success assertion will include a
        check on the status of the last command in this script.
    :param inmanta_user: The user that should be considered the owner of the inmanta state directory for the purpose of
        ownership checks during deactivation. The user must exist on the system running the tests. Defaults to the active
        user.
    :param expected_dir: The directory that is expected to be selected.
    :param invert_success_assert: If true, assert that inmanta-workon returns a non-zero exit code.
    :param invert_working_dir_assert: If true, assert that the working directory has not changed to the environment dir.
    :param invert_python_assert: If true, assert that `which python` does not resolve to the environment's Python.
    :param invert_ps1_assert: If true, assert that PS1 has received the environment as a prefix.
    """
    result: CliResult = await workon_bash(
        textwrap.dedent(
            f"""
            # mock PS1 to mimic terminal behavior
            test_workon_ps1_pre=myps1
            export PS1="$test_workon_ps1_pre"
            # set inmanta user to active user for deactivation logic
            INMANTA_USER='{inmanta_user if inmanta_user is not None else getpass.getuser()}'

            %s
            pre_activate_result=$?
            inmanta-workon '{arg}'
            activate_result=$?
            %s
            post_activate_result=$?

            # output three lines
            echo "$(pwd)"
            which python || echo ""  # make sure to always output a line, even if no python is found
            echo "${{PS1%%$test_workon_ps1_pre}}"

            # exit with result code
            [ "$pre_activate_result" -eq 0 ] && [ "$activate_result" -eq 0 ] && [ "$post_activate_result" -eq 0 ]
            """.strip(
                "\n"
            )
        )
        % (pre_activate if pre_activate is not None else "", post_activate if post_activate is not None else "")
    )
    assert (result.exit_code == 0) != invert_success_assert
    lines: abc.Sequence[str] = result.stdout.split("\n")  # don't use splitlines because it ignores empty lines
    assert len(lines) == 4  # trailing newline
    working_dir, python, ps1_prefix, empty = lines
    assert (working_dir == str(expected_dir)) != invert_working_dir_assert
    assert (python == str(expected_dir.join(".env", "bin", "python"))) != invert_python_assert
    assert ps1_prefix == ("" if invert_ps1_assert else f"({arg}) ")
    assert empty == ""
    assert result.stderr.strip() == expect_stderr.strip()


@pytest.mark.slowtest
async def test_workon(
    server: Server,
    workon_bash: Bash,
    workon_environments_dir: py.path.local,
    compiled_environments: abc.Sequence[data.model.Environment],
) -> None:
    """
    Verify the basics of inmanta-workon behavior when an environment id or name is specified.
    """
    # by id
    await assert_workon_state(
        workon_bash,
        str(compiled_environments[0].id),
        expected_dir=workon_environments_dir.join(str(compiled_environments[0].id)),
        expect_stderr=(
            "WARNING: Make sure you exit the current environment by running the 'deactivate' command rather than simply exiting"
            " the shell. This ensures the proper permission checks are performed.\n"
        ),
    )
    # by name
    await assert_workon_state(
        workon_bash,
        compiled_environments[1].name,
        expected_dir=workon_environments_dir.join(str(compiled_environments[1].id)),
        expect_stderr=(
            "WARNING: Make sure you exit the current environment by running the 'deactivate' command rather than simply exiting"
            " the shell. This ensures the proper permission checks are performed.\n"
        ),
    )
    # .env dir missing
    env_dir: py.path.local = workon_environments_dir.join(str(compiled_environments[2].id))
    shutil.rmtree(str(env_dir.join(".env")))
    await assert_workon_state(
        workon_bash,
        compiled_environments[2].name,
        expected_dir=env_dir,
        invert_success_assert=True,
        invert_working_dir_assert=False,
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=f"ERROR: Environment '{env_dir}' does not contain a venv. This may mean it has never started a compile.",
    )


@pytest.mark.slowtest
async def test_workon_no_env(
    server: Server,
    workon_bash: Bash,
    workon_environments_dir: py.path.local,
    simple_environments: abc.Sequence[data.model.Environment],
) -> None:
    """
    Verify the behavior of various inmanta-workon failure scenarios when the requested environment doesn't exist.
    """
    # env dir does not exist
    env: data.model.Environment = simple_environments[0]
    env_dir: py.path.local = workon_environments_dir.join(str(env.id))
    for identifier in (str(env.id), env.name):
        await assert_workon_state(
            workon_bash,
            identifier,
            expected_dir=env_dir,
            invert_success_assert=True,
            invert_working_dir_assert=True,
            invert_python_assert=True,
            invert_ps1_assert=True,
            expect_stderr=(
                f"ERROR: Directory '{env_dir}' does not exist. This may mean the environment has never started a compile."
            ),
        )
    # no environment with this name exists
    await assert_workon_state(
        workon_bash,
        "thisenvironmentdoesnotexist",
        expected_dir=env_dir,
        invert_success_assert=True,
        invert_working_dir_assert=True,
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=(
            "ERROR: Environment 'thisenvironmentdoesnotexist' could not be uniquely identified. Available environments are:\n"
            + inmanta.main.get_table(
                ["Project name", "Project ID", "Environment", "Environment ID"],
                [["test", str(env.project_id), env.name, str(env.id)] for env in simple_environments],
            )
        ),
    )
    # no environment with this id exists
    random_id: uuid.UUID = uuid.uuid4()
    await assert_workon_state(
        workon_bash,
        str(random_id),
        expected_dir=workon_environments_dir.join(str(env.id)),
        invert_success_assert=True,
        invert_working_dir_assert=True,
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=(
            f"ERROR: Environment '{random_id}' could not be uniquely identified. Available environments are:\n"
            + inmanta.main.get_table(
                ["Project name", "Project ID", "Environment", "Environment ID"],
                [["test", str(env.project_id), env.name, str(env.id)] for env in simple_environments],
            )
        ),
    )


@pytest.mark.slowtest
async def test_workon_broken_cli(
    server: Server,
    workon_bash: Bash,
    workon_environments_dir: py.path.local,
    workon_broken_cli: None,
    compiled_environments: abc.Sequence[data.model.Environment],
) -> None:
    """
    Verify the behavior of inmanta-workon when an environment id or name is specified but the inmanta-cli command does
    not work (fallback file-based workon).
    """
    # by id
    await assert_workon_state(
        workon_bash,
        str(compiled_environments[0].id),
        expected_dir=workon_environments_dir.join(str(compiled_environments[0].id)),
        expect_stderr=(
            "WARNING: Make sure you exit the current environment by running the 'deactivate' command rather than simply exiting"
            " the shell. This ensures the proper permission checks are performed.\n"
        ),
    )
    # by name
    await assert_workon_state(
        workon_bash,
        compiled_environments[1].name,
        expected_dir=workon_environments_dir.join(str(compiled_environments[1].id)),
        invert_success_assert=True,
        invert_working_dir_assert=True,
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=(
            "ERROR: Unable to connect through inmanta-cli to look up environment by name. Please supply its id instead."
        ),
    )
    # no environment with this id exists
    random_id: uuid.UUID = uuid.uuid4()
    env_dir: py.path.local = workon_environments_dir.join(str(random_id))
    await assert_workon_state(
        workon_bash,
        str(random_id),
        expected_dir=env_dir,
        invert_success_assert=True,
        invert_working_dir_assert=True,
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=(
            f"ERROR: Directory '{env_dir}' does not exist. This may mean the environment has never started a compile."
        ),
    )


@pytest.mark.slowtest
async def test_workon_non_unique_name(
    tmpdir: py.path.local,
    server: Server,
    client: protocol.Client,
    workon_bash: Bash,
    workon_environments_dir: py.path.local,
    compiled_environments: abc.Sequence[data.model.Environment],
) -> None:
    """
    Verify the behavior of the inmanta-workon command if a lookup by name is attempted with a non-unique environment name.
    """
    env: data.model.Environment = compiled_environments[0]
    second_factory: EnvironmentFactory = EnvironmentFactory(str(tmpdir.join("second_environment_factory")))
    second_factory.project = data.Project(name="second_project")
    new_env: data.model.Environment = (await second_factory.create_environment(name=env.name)).to_dto()
    await assert_workon_state(
        workon_bash,
        str(env.name),
        expected_dir=workon_environments_dir.join(str(env.id)),
        invert_success_assert=True,
        invert_working_dir_assert=True,
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=(
            "ERROR: Environment 'env-0' could not be uniquely identified. Available environments are:\n"
            + inmanta.main.get_table(
                ["Project name", "Project ID", "Environment", "Environment ID"],
                [
                    [project_name, str(env.project_id), env.name, str(env.id)]
                    for (project_name, env) in sorted(
                        (
                            ("second_project", new_env),
                            *zip((f"project-{i}" for i in range(len(compiled_environments))), compiled_environments),
                        ),
                        key=lambda t: (t[1].project_id, t[1].name, t[1].id),
                    )
                ],
            )
        ),
    )


@pytest.mark.slowtest
async def test_workon_compile(
    server: Server,
    workon_bash: Bash,
    workon_environments_dir: py.path.local,
    compiled_environments: abc.Sequence[data.model.Environment],
    # no need to run this test in a separate venv: either it works as expected and does not affect the outer venv, or this
    # fixture will catch it
    guard_testing_venv: None,
) -> None:
    """
    Verify the inmanta command works as expected after using inmanta-workon. Specifically, verify that the inmanta command
    considers this venv as the active one.
    """
    assert not inmanta.env.PythonWorkingSet.are_installed(
        ["lorem"]
    ), "This test assumes lorem is not preinstalled and therefore will not work as expected."
    await assert_workon_state(
        workon_bash,
        str(compiled_environments[0].name),
        # call inmanta before activation to guard against command caching errors (see `man hash`)
        pre_activate="inmanta --help > /dev/null 2>&1",
        # Add a requirement and install it.
        post_activate=textwrap.dedent(
            """
            declare -F inmanta > /dev/null 2>&1 || exit 1  # check that inmanta is a shell function
            (pip --disable-pip-version-check --no-python-version-warning list | grep lorem > /dev/null 2>&1) \
                && exit 1  # check that lorem is not installed yet
            echo lorem >> requirements.txt
            # verify that the inmanta command works, accepts options, and is contained within this enviroment
            inmanta project install > /dev/null 2>&1 || exit 1
            (pip --disable-pip-version-check --no-python-version-warning list | grep lorem > /dev/null 2>&1) \
                || exit 1  # check that lorem is now installed
            deactivate
            declare -F inmanta > /dev/null 2>&1
            [ "$?" -eq 1 ] # check that inmanta is no longer a shell function
            """.strip(
                "\n"
            )
        ),
        expected_dir=workon_environments_dir.join(str(compiled_environments[0].id)),
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=(
            "WARNING: Make sure you exit the current environment by running the 'deactivate' command rather than simply exiting"
            " the shell. This ensures the proper permission checks are performed.\n"
        ),
    )


@pytest.mark.slowtest
async def test_workon_deactivate(
    server: Server,
    workon_workdir: py.path.local,
    workon_bash: Bash,
    workon_environments_dir: py.path.local,
    compiled_environments: abc.Sequence[data.model.Environment],
) -> None:
    """
    Verify the deactivate behavior of inmanta-workon.
    """
    env_id: uuid.UUID = compiled_environments[0].id
    env_dir: py.path.local = workon_environments_dir.join(str(compiled_environments[0].id))
    # simple deactivate
    await assert_workon_state(
        workon_bash,
        str(env_id),
        post_activate="deactivate",
        expected_dir=env_dir,
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=(
            "WARNING: Make sure you exit the current environment by running the 'deactivate' command rather than simply exiting"
            " the shell. This ensures the proper permission checks are performed."
        ),
    )
    # ownership warning on deactivate
    await assert_workon_state(
        workon_bash,
        str(env_id),
        post_activate="deactivate",
        # declare root owner of the inmanta state directory to trigger the ownership warning (files are owned by active user)
        inmanta_user="root",
        expected_dir=env_dir,
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=(
            "WARNING: The inmanta-workon tool should be run as either root or the inmanta user to have write access (to be"
            " able to run pip install or inmanta project install).\nWARNING: Make sure you exit the current environment by"
            " running the 'deactivate' command rather than simply exiting the shell. This ensures the proper permission checks"
            " are performed.\nWARNING: Some files in the environment are not owned by the root user. To fix this, run `chown"
            f" -R root:root '{env_dir}'` as root."
        ),
    )
    # ownership warning on activation of a different environment
    env1_dir: py.path.local = workon_environments_dir.join(str(compiled_environments[1].id))
    env2_dir: py.path.local = workon_environments_dir.join(str(compiled_environments[2].id))
    await assert_workon_state(
        workon_bash,
        # activate env 0
        str(env_id),
        # then activate env 1 and env 2 without explicit deactivate
        # do it twice to verify that the deactivate function is kept / registered correctly the second time around.
        post_activate=textwrap.dedent(
            f"""
            cd '{workon_workdir}' && inmanta-workon {compiled_environments[1].id}
            cd '{workon_workdir}' && inmanta-workon {compiled_environments[2].id}
            # verify PS1 correctness, then reset it to what assert_workon_state expects
            [ "${{PS1%$test_workon_ps1_pre}}" = '({compiled_environments[2].id}) ' ] && export PS1="$test_workon_ps1_pre"
            """.strip(
                "\n"
            )
        ),
        # declare root owner of the inmanta state directory to trigger the ownership warning (files are owned by active user)
        inmanta_user="root",
        # env 2 should be activated in the end
        expected_dir=env2_dir,
        invert_ps1_assert=True,  # see mock PS1 in post_activate script
        # expect warnings for env 0 and env 1 but not for env 2 because it is still active
        expect_stderr=(
            "WARNING: The inmanta-workon tool should be run as either root or the inmanta user to have write access (to be"
            " able to run pip install or inmanta project install).\nWARNING: Make sure you exit the current environment by"
            " running the 'deactivate' command rather than simply exiting the shell. This ensures the proper permission checks"
            " are performed.\nWARNING: The inmanta-workon tool should be run as either root or the inmanta user to have write"
            " access (to be able to run pip install or inmanta project install).\nWARNING: Some files in the environment are"
            f" not owned by the root user. To fix this, run `chown -R root:root '{env_dir}'` as root.\nWARNING: Make sure you"
            " exit the current environment by running the 'deactivate' command rather than simply exiting the shell. This"
            " ensures the proper permission checks are performed.\nWARNING: The inmanta-workon tool should be run as either"
            " root or the inmanta user to have write access (to be able to run pip install or inmanta project"
            " install).\nWARNING: Some files in the environment are not owned by the root user. To fix this, run `chown -R"
            f" root:root '{env1_dir}'` as root.\nWARNING: Make sure you exit the current environment by running the"
            " 'deactivate' command rather than simply exiting the shell. This ensures the proper permission checks are"
            " performed."
        ),
    )


@pytest.mark.slowtest
async def test_workon_sets_inmanta_config_environment(
    server: Server,
    workon_workdir: py.path.local,
    workon_bash: Bash,
    workon_environments_dir: py.path.local,
    compiled_environments: abc.Sequence[data.model.Environment],
) -> None:
    """
    Verify that INMANTA_CONFIG_ENVIRONMENT is correctly reset to its previous value.
    """
    outer_env_id: uuid.UUID = uuid.uuid4()
    inner_env_id: uuid.UUID = compiled_environments[0].id
    env_dir: py.path.local = workon_environments_dir.join(str(compiled_environments[0].id))
    # simple deactivate
    await assert_workon_state(
        workon_bash,
        str(inner_env_id),
        pre_activate=textwrap.dedent(
            f"""
            # Set INMANTA_CONFIG_ENVIRONMENT to the outer env's id
            export INMANTA_CONFIG_ENVIRONMENT={outer_env_id}
            """.strip(
                "\n"
            )
        ),
        post_activate=textwrap.dedent(
            f"""
            # After activation, verify INMANTA_CONFIG_ENVIRONMENT is set to the inner env's id
            if [ ! "${{INMANTA_CONFIG_ENVIRONMENT}}" = "{inner_env_id}" ] ; then
                exit 1
            fi
            deactivate
            # After deactivation, verify INMANTA_CONFIG_ENVIRONMENT has been set back to the outer env's id
            if [ ! "${{INMANTA_CONFIG_ENVIRONMENT}}" = "{outer_env_id}" ] ; then
                exit 1
            fi
            """.strip(
                "\n"
            )
        ),
        expected_dir=env_dir,
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=(
            "WARNING: Make sure you exit the current environment by running the 'deactivate' command rather than simply exiting"
            " the shell. This ensures the proper permission checks are performed."
        ),
    )


@pytest.mark.slowtest
async def test_workon_sets_inmanta_config_environment_empty_outer(
    server: Server,
    workon_workdir: py.path.local,
    workon_bash: Bash,
    workon_environments_dir: py.path.local,
    compiled_environments: abc.Sequence[data.model.Environment],
) -> None:
    """
    Verify that INMANTA_CONFIG_ENVIRONMENT is correctly unset if non-existent prior to activation.
    """
    inner_env_id: uuid.UUID = compiled_environments[0].id
    env_dir: py.path.local = workon_environments_dir.join(str(compiled_environments[0].id))
    await assert_workon_state(
        workon_bash,
        str(inner_env_id),
        pre_activate=textwrap.dedent(
            """
            # Make sure INMANTA_CONFIG_ENVIRONMENT is not set
            unset INMANTA_CONFIG_ENVIRONMENT
            """.strip(
                "\n"
            )
        ),
        post_activate=textwrap.dedent(
            f"""
            # After activation, verify INMANTA_CONFIG_ENVIRONMENT is set to the inner env's id
            if [ ! "${{INMANTA_CONFIG_ENVIRONMENT}}" = "{inner_env_id}" ] ; then
                exit 1
            fi
            deactivate
            # After deactivation, verify INMANTA_CONFIG_ENVIRONMENT has been unset
            if [ -n "${{INMANTA_CONFIG_ENVIRONMENT:-}}" ] ; then
                exit 1
            fi
            """.strip(
                "\n"
            )
        ),
        expected_dir=env_dir,
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=(
            "WARNING: Make sure you exit the current environment by running the 'deactivate' command rather than simply exiting"
            " the shell. This ensures the proper permission checks are performed."
        ),
    )


def create_script(script_parts: Sequence[str]) -> str:
    """
    Utility function to put together bash code
    """
    out = ""
    for part in script_parts:
        out += textwrap.dedent(part)

    return out


def add_check(var_name: str, expected_value: str, extra_debug_info: Optional[str] = "") -> str:
    """
    This method is meant to be used in a post_activate or pre_activate script passed to the assert_workon_state method.
    It checks that a given variable has the expected value
    """
    if expected_value:
        return textwrap.dedent(
            f"""
                if [ ! "${{{var_name}}}" = "{expected_value}" ] ; then
                    echo $"{extra_debug_info} '{var_name}' expected '{expected_value}' got '${{{var_name}}}'"
                    exit 1
                fi
            """
        )
    # Check for unset var:
    return textwrap.dedent(
        f"""
            if [ -n "${{{var_name}}}" ] ; then
                echo $"{extra_debug_info} '{var_name}' expected empty str got '${{{var_name}}}'"
                exit 1
            fi
        """
    )


@dataclass
class TestScenario:
    pip_config: dict[str, Union[str, bool, list[str]]]
    expected_warning: str
    pre_activate_script: str
    pre_deactivate_script: str
    post_deactivate_script: str

    def post_activate_script(self):
        return create_script([self.pre_deactivate_script, "deactivate", self.post_deactivate_script])


@pytest.fixture(scope="session")
def scenarios() -> dict[str, TestScenario]:
    # Scenario 1: [ use-system-config = True]

    # BEFORE activation:
    # - Set some values for the pip env variables
    # BEFORE deactivation:
    # - Check that PIP_CONFIG_FILE is left untouched
    # - Check that PIP_EXTRA_INDEX_URL is extended with the values from the pip config
    # - Check that the other env variable take the corresponding values from the pip config
    # AFTER deactivation:
    # - Check that all pip env variables are reset to their initial values

    index_url = "http://example.com/index"
    extra_indexes = ["http://example.com/extra_index_1", "http://example.com/extra_index_2"]
    pip_config = {"use-system-config": True, "index-url": index_url, "extra-index-url": extra_indexes, "pre": False}
    scenario_1 = TestScenario(
        pip_config=pip_config,
        expected_warning="",
        pre_activate_script=create_script(
            [
                """
                # Set some pip env var with dummy values:
                export PIP_INDEX_URL="initial_dummy_value"
                export PIP_EXTRA_INDEX_URL="initial_dummy_value"
                export PIP_PRE="initial_dummy_value"
                export PIP_CONFIG_FILE="initial_dummy_value"
                """
            ]
        ),
        pre_deactivate_script=create_script(
            [
                # Check we extend extra index value
                add_check("PIP_EXTRA_INDEX_URL", f"initial_dummy_value {' '.join(extra_indexes)}"),
                # Make sure PIP_CONFIG_FILE is left untouched:
                add_check("PIP_CONFIG_FILE", "initial_dummy_value", "pre_deactivate_script"),
                add_check("PIP_INDEX_URL", index_url),
                add_check("PIP_PRE", "False"),
            ]
        ),
        post_deactivate_script=create_script(
            [
                add_check("PIP_INDEX_URL", "initial_dummy_value", "post_deactivation_check"),
                add_check("PIP_EXTRA_INDEX_URL", "initial_dummy_value", "post_deactivation_check"),
                add_check("PIP_PRE", "initial_dummy_value", "post_deactivation_check"),
                add_check("PIP_CONFIG_FILE", "initial_dummy_value", "post_deactivation_check"),
            ]
        ),
    )

    # Scenario 2 [ use-system-config = False]

    # Same as Scenario 1 except for:
    # BEFORE deactivation:
    # - Check that PIP_CONFIG_FILE is set to /dev/null
    # - Check that PIP_EXTRA_INDEX_URL is only using the values from the pip config

    scenario_2 = copy.deepcopy(scenario_1)
    scenario_2.pip_config["use-system-config"] = False
    scenario_2.pre_deactivate_script = create_script(
        [
            # Check we override extra index value
            add_check("PIP_EXTRA_INDEX_URL", f"{' '.join(extra_indexes)}"),
            # Make sure PIP_CONFIG_FILE is unset:
            add_check("PIP_CONFIG_FILE", "/dev/null", "pre_deactivate_script"),
            add_check("PIP_INDEX_URL", index_url),
            add_check("PIP_PRE", "False"),
        ]
    )

    # Scenario 3 [ use-system-config = False]

    # Same as Scenario 1 except for:

    # BEFORE activation:
    # - Leave PIP_PRE unset

    # AFTER deactivation:
    # - Check PIP_PRE is unset

    scenario_3 = copy.deepcopy(scenario_1)
    scenario_3.pre_activate_script = create_script(
        [
            """
            # Set some pip env var with dummy values:
            export PIP_INDEX_URL="initial_dummy_value"
            export PIP_EXTRA_INDEX_URL="initial_dummy_value"
            export PIP_CONFIG_FILE="initial_dummy_value"
            """
        ]
    )
    scenario_3.pip_config["use-system-config"] = False
    scenario_3.pre_deactivate_script = create_script(
        [
            # Check we override extra index value
            add_check("PIP_EXTRA_INDEX_URL", f"{' '.join(extra_indexes)}"),
            # Make sure PIP_CONFIG_FILE is unset:
            add_check("PIP_CONFIG_FILE", "/dev/null", "pre_deactivate_script"),
            add_check("PIP_INDEX_URL", index_url),
            add_check("PIP_PRE", "False"),
        ]
    )
    scenario_3.post_deactivate_script = create_script(
        [
            # add_check("PIP_INDEX_URL", "initial_dummy_value", "post_deactivation_check"),
            add_check("PIP_EXTRA_INDEX_URL", "initial_dummy_value"),
            add_check("PIP_PRE", ""),
            add_check("PIP_CONFIG_FILE", "initial_dummy_value"),
        ]
    )

    # Scenario 4 [ use-system-config = False and no index set in pip config]

    # - Make sure a warning is raised
    # - Make sure pip env variables are not changed at any time

    pip_config = {"use-system-config": False, "pre": True}
    scenario_4 = TestScenario(
        pip_config=pip_config,
        expected_warning=(
            "WARNING: Cannot use project.yml pip configuration: pip.use-system-config is False, but no index is defined "
            "in the pip.index-url section of the project.yml\n"
        ),
        pre_activate_script=create_script(
            [
                """
                # Set some pip env var with dummy values:
                export PIP_INDEX_URL="initial_dummy_value"
                export PIP_EXTRA_INDEX_URL="initial_dummy_value"
                export PIP_PRE="False"
                export PIP_CONFIG_FILE="initial_dummy_value"
                """
            ]
        ),
        pre_deactivate_script=create_script(
            [
                # Make sure config is left untouched:
                add_check("PIP_INDEX_URL", "initial_dummy_value", "pre_deactivate_script"),
                add_check("PIP_EXTRA_INDEX_URL", "initial_dummy_value", "pre_deactivate_script"),
                add_check("PIP_PRE", "False", "pre_deactivate_script"),
                add_check("PIP_CONFIG_FILE", "initial_dummy_value", "pre_deactivate_script"),
            ]
        ),
        post_deactivate_script=create_script(
            [
                add_check("PIP_INDEX_URL", "initial_dummy_value", "post_deactivation_check"),
                add_check("PIP_EXTRA_INDEX_URL", "initial_dummy_value", "post_deactivation_check"),
                add_check("PIP_PRE", "False", "post_deactivation_check"),
                add_check("PIP_CONFIG_FILE", "initial_dummy_value", "post_deactivation_check"),
            ]
        ),
    )

    return {
        "scenario_1": scenario_1,
        "scenario_2": scenario_2,
        "scenario_3": scenario_3,
        "scenario_4": scenario_4,
    }


def patch_projectyml_pip_config(env_dir: py.path.local, pip_config: dict[str, str]):
    """
    Util function to override the project's pip config.

    :param env_dir: Environment directory in which a project.yml is expected.
    :pip_config: The specific pip config to write in the project.yml
    """
    with open(os.path.join(env_dir, Project.PROJECT_FILE), "r", encoding="utf-8") as fd:
        config = yaml.safe_load(fd)

        config["pip"] = pip_config

    with open(os.path.join(env_dir, Project.PROJECT_FILE), "w", encoding="utf-8") as fd:
        fd.write(yaml.dump(config, default_flow_style=False, sort_keys=False))


@pytest.mark.slowtest
@pytest.mark.parametrize(
    "scenario_id",
    [
        "scenario_1",
        "scenario_2",
        "scenario_3",
        "scenario_4",
    ],
)
async def test_workon_sets_pip_config(
    server: Server,
    workon_workdir: py.path.local,
    workon_bash: Bash,
    workon_environments_dir: py.path.local,
    compiled_environments: abc.Sequence[data.model.Environment],
    scenario_id: str,
    scenarios: dict[str, TestScenario],
) -> None:
    """
    Check the expected behaviour for the different scenarios defined in the "scenarios" fixture.
    """
    inner_env_id: uuid.UUID = compiled_environments[0].id
    env_dir: py.path.local = workon_environments_dir.join(str(compiled_environments[0].id))

    scenario = scenarios[scenario_id]

    patch_projectyml_pip_config(env_dir, scenario.pip_config)

    await assert_workon_state(
        workon_bash,
        str(inner_env_id),
        pre_activate=scenario.pre_activate_script,
        post_activate=scenario.post_activate_script(),
        expected_dir=env_dir,
        invert_python_assert=True,
        invert_ps1_assert=True,
        expect_stderr=(
            f"{scenario.expected_warning}"
            "WARNING: Make sure you exit the current environment by running the 'deactivate' command rather than simply exiting"
            " the shell. This ensures the proper permission checks are performed."
        ),
    )
