"""
Copyright 2018 Inmanta

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
import os
import re
import shutil
import sys
import textwrap
from asyncio import subprocess

import py
import pytest

from inmanta import env
from inmanta.app import cmd_parser
from inmanta.command import ShowUsageException
from inmanta.compiler.config import feature_compiler_cache
from inmanta.config import Config
from inmanta.const import INMANTA_REMOVED_SET_ID
from inmanta.data import (
    AUTO_DEPLOY,
    ENVIRONMENT_METRICS_RETENTION,
    NOTIFICATION_RETENTION,
    RESOURCE_ACTION_LOGS_RETENTION,
    model,
)
from utils import v1_module_from_template


def app(args):
    parser = cmd_parser()

    options, other = parser.parse_known_args(args=args)
    options.other = other

    # Load the configuration
    Config.load_config(options.config_file)

    # start the command
    if not hasattr(options, "func"):
        # show help
        parser.print_usage()
        return

    options.func(options)


async def install_project(python_env: env.PythonEnvironment, project_dir: py.path.local) -> None:
    """
    Install a project and its modules via the `inmanta project install` command.
    """
    args = [
        python_env.python_path,
        "-m",
        "inmanta.app",
        "-Xvvv",  # for assert failure messages
        "project",
        "install",
    ]
    process = await subprocess.create_subprocess_exec(
        *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(project_dir)
    )
    try:
        (stdout, stderr) = await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError as e:
        process.kill()
        (stdout, stderr) = await process.communicate()
        print(stdout.decode())
        print(stderr.decode())
        raise e

    assert process.returncode == 0, f"{stdout}\n\n{stderr}"


def test_help(inmanta_config, capsys):
    with pytest.raises(SystemExit):
        app(["-h"])
    out, _ = capsys.readouterr()

    assert out.startswith("usage:")
    # check main options
    assert "--config" in out
    # check subcommands list
    assert "export" in out


def test_help2(inmanta_config, capsys):
    with pytest.raises(SystemExit):
        app(["help"])
    out, _ = capsys.readouterr()

    assert out.startswith("usage:")
    # check main options
    assert "--config" in out
    # check subcommands list
    assert "export" in out


def test_help_sub(inmanta_config, capsys):
    with pytest.raises(SystemExit):
        app(["help", "module"])
    out, _ = capsys.readouterr()

    assert out.startswith("usage:")
    # check main options
    assert "--config" not in out
    # check subcommands list
    assert "export" not in out
    # check subcommands help
    assert "freeze" in out


def test_feature_flags(inmanta_config, capsys):
    with pytest.raises(SystemExit):
        app(["help", "compile"])
    out, _ = capsys.readouterr()

    assert out.startswith("usage:")
    assert "--no-cache" in out

    parser = cmd_parser()

    # Check that option defaults to true
    assert feature_compiler_cache.get()

    options, other = parser.parse_known_args(args=["compile", "--no-cache"])

    # Check that option was set to false with --no-cache
    assert not options.feature_compiler_cache


def test_module_help(inmanta_config, capsys):
    with pytest.raises(ShowUsageException) as info:
        app(["module"])

    assert info.value.args[0].startswith("A subcommand is required.")


@pytest.mark.parametrize_any("push_method", [([]), (["-d"]), (["-d", "--full"])])
@pytest.mark.parametrize_any("set_server", [True, False])
@pytest.mark.parametrize_any("set_port", [True, False])
async def test_export(
    tmpvenv_active_inherit: env.VirtualEnv,
    tmpdir,
    server,
    client,
    push_method,
    set_server,
    set_port,
    null_agent,
    environment,
    clienthelper,
):
    server_port = Config.get("client_rest_transport", "port")
    server_host = Config.get("client_rest_transport", "host", "localhost")

    env_id = environment
    result = await client.environment_settings_set(tid=environment, id=AUTO_DEPLOY, value=True)
    assert result.code == 200

    # Put settings in-place to test the export of the environment settings in the project.yml file
    result = await client.environment_settings_set(tid=environment, id=RESOURCE_ACTION_LOGS_RETENTION, value=5)
    assert result.code == 200
    result = await client.environment_setting_get(tid=environment, id=ENVIRONMENT_METRICS_RETENTION)
    assert result.code == 200
    assert result.result["data"]["settings"][ENVIRONMENT_METRICS_RETENTION] == 336
    result = await client.environment_setting_get(tid=environment, id=NOTIFICATION_RETENTION)
    assert result.code == 200
    assert result.result["data"]["settings"][NOTIFICATION_RETENTION] == 365

    workspace = tmpdir.mkdir("tmp")
    path_main_file = workspace.join("main.cf")
    path_project_yml_file = workspace.join("project.yml")
    path_config_file = workspace.join(".inmanta")
    libs_dir = workspace.join("libs")

    path_project_yml_file.write(
        f"""
name: testproject
modulepath: {libs_dir}
downloadpath: {libs_dir}
repo: https://github.com/inmanta/
environment_settings:
    {ENVIRONMENT_METRICS_RETENTION}: 100
    {NOTIFICATION_RETENTION}: 200
"""
    )

    # Use non-default agent to make sure the resource can be checked in the 'deploying' state.
    # Using the internal default agent might trigger a race condition where the 'success' state
    # is reached because the resource actually gets deployed.

    path_main_file.write(
        """
import std::testing
std::testing::NullResource(name="test", agentname="non_existing_agent")
"""
    )

    path_config_file.write(
        f"""
[compiler_rest_transport]
{'host=' + server_host if not set_server else ''}
{'port=' + str(server_port) if not set_port else ''}

[cmdline_rest_transport]
{'host=' + server_host if not set_server else ''}
{'port=' + str(server_port) if not set_port else ''}
"""
    )

    await install_project(tmpvenv_active_inherit, workspace)

    os.chdir(workspace)

    args = [
        sys.executable,
        "-m",
        "inmanta.app",
        "export",
        "-e",
        str(env_id),
    ]
    if set_port:
        args.extend(["--server_port", str(server_port)])
    if set_server:
        args.extend(["--server_address", str(server_host)])
    args += push_method

    process = await subprocess.create_subprocess_exec(*args, stdout=sys.stdout, stderr=sys.stderr)
    try:
        await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.communicate()
        raise e

    # Make sure exitcode is zero
    assert process.returncode == 0, f"Process ended with bad return code, got {process.returncode} (expected 0)"

    result = await client.list_versions(env_id)
    assert result.code == 200
    assert len(result.result["versions"]) == 1

    # wait for release by auto release
    await clienthelper.wait_for_released(None)

    # Verify that the environment settings were updated correctly
    result = await client.environment_setting_get(tid=environment, id=RESOURCE_ACTION_LOGS_RETENTION)
    assert result.code == 200
    # This setting is not present in the project.yml file, so it should be changed.
    assert result.result["data"]["settings"][RESOURCE_ACTION_LOGS_RETENTION] == 5
    result = await client.environment_setting_get(tid=environment, id=ENVIRONMENT_METRICS_RETENTION)
    assert result.code == 200
    assert result.result["data"]["settings"][ENVIRONMENT_METRICS_RETENTION] == 100
    result = await client.environment_setting_get(tid=environment, id=NOTIFICATION_RETENTION)
    assert result.code == 200
    assert result.result["data"]["settings"][NOTIFICATION_RETENTION] == 200
    result = await client.environment_settings_list(tid=environment)
    for setting_name, s in result.result["data"]["settings_v2"].items():
        if setting_name in {ENVIRONMENT_METRICS_RETENTION, NOTIFICATION_RETENTION}:
            assert s["protected"]
            assert model.ProtectedBy(s["protected_by"]) == model.ProtectedBy.project_yml
        else:
            assert not s["protected"]
            assert s["protected_by"] is None

    shutil.rmtree(workspace)


async def test_export_with_specific_export_plugin(tmpvenv_active_inherit: env.VirtualEnv, tmpdir, client):
    server_port = Config.get("client_rest_transport", "port")
    server_host = Config.get("client_rest_transport", "host", "localhost")
    result = await client.create_project("test")
    assert result.code == 200
    proj_id = result.result["project"]["id"]
    result = await client.create_environment(proj_id, "test", None, None)
    assert result.code == 200
    env_id = result.result["environment"]["id"]
    workspace = tmpdir.mkdir("tmp")
    libs_dir = workspace.join("libs")

    # project.yml
    path_project_yml_file = workspace.join("project.yml")
    path_project_yml_file.write(
        f"""
name: testproject
modulepath: {libs_dir}
downloadpath: {libs_dir}
repo: https://github.com/inmanta/
"""
    )

    # main.cf
    path_main_file = workspace.join("main.cf")
    path_main_file.write("import test")

    # test module
    module_dir = libs_dir.join("test")
    os.makedirs(module_dir)

    # Module.yml
    module_yml_file = module_dir.join("module.yml")
    module_yml_file.write(
        """
name: test
license: test
version: 1.0.0
    """
    )

    # .inmanta
    dot_inmanta_cfg_file = workspace.join(".inmanta")
    dot_inmanta_cfg_file.write(
        """
[config]
export=other_exporter
    """
    )

    # plugin/__init__.py
    plugins_dir = module_dir.join("plugins")
    os.makedirs(plugins_dir)
    init_file = plugins_dir.join("__init__.py")
    init_file.write(
        """
from inmanta.export import export, Exporter

@export("test_exporter")
def test_exporter(exporter: Exporter) -> None:
    print("test_exporter ran")

@export("other_exporter")
def other_exporter(exporter: Exporter) -> None:
    print("other_exporter ran")
    """
    )

    # model/_init.cf
    model_dir = module_dir.join("model")
    os.makedirs(model_dir)
    init_cf_file = model_dir.join("_init.cf")
    init_cf_file.write("")

    await install_project(tmpvenv_active_inherit, workspace)

    os.chdir(workspace)

    args = [
        tmpvenv_active_inherit.python_path,
        "-m",
        "inmanta.app",
        "export",
        "--export-plugin",
        "test_exporter",
        "-e",
        str(env_id),
        "--server_port",
        str(server_port),
        "--server_address",
        str(server_host),
    ]

    process = await subprocess.create_subprocess_exec(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        (stdout, stderr) = await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.communicate()
        raise e

    # Make sure exitcode is zero
    assert process.returncode == 0

    assert "test_exporter ran" in stdout.decode("utf-8")
    assert "other_exporter" not in stdout.decode("utf-8")

    # ## Failure

    path_main_file.write(
        """import test

vm1=std::Host(name="non-existing-machine", os=std::linux)

vm1.name = "other"
"""
    )

    process = await subprocess.create_subprocess_exec(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        (stdout, stderr) = await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.communicate()
        raise e

    # Make sure exitcode is one
    assert process.returncode == 1

    assert "test_exporter ran" not in stdout.decode("utf-8")
    assert "other_exporter" not in stdout.decode("utf-8")

    shutil.rmtree(workspace)


@pytest.mark.parametrize_any("push_method", [([]), (["-d"]), (["-d", "--full"])])
async def test_export_without_environment(tmpdir, server, client, push_method):
    server_port = Config.get("client_rest_transport", "port")
    server_host = Config.get("client_rest_transport", "host", "localhost")

    result = await client.create_project("test")
    assert result.code == 200
    proj_id = result.result["project"]["id"]
    result = await client.create_environment(proj_id, "test", None, None)
    assert result.code == 200
    env_id = result.result["environment"]["id"]

    workspace = tmpdir.mkdir("tmp")
    path_main_file = workspace.join("main.cf")
    path_project_yml_file = workspace.join("project.yml")
    libs_dir = workspace.join("libs")

    path_project_yml_file.write(
        f"""
name: testproject
modulepath: {libs_dir}
downloadpath: {libs_dir}
repo: https://github.com/inmanta/
"""
    )

    path_main_file.write(
        """
import std::testing

std::testing::NullResource(name="test")
"""
    )

    os.chdir(workspace)

    args = [
        sys.executable,
        "-m",
        "inmanta.app",
        "export",
    ]
    args.extend(["--server_port", str(server_port)])
    args.extend(["--server_address", str(server_host)])
    args += push_method

    process = await subprocess.create_subprocess_exec(*args, stdout=sys.stdout, stderr=sys.stderr)
    try:
        await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.communicate()
        raise e

    # Make sure exitcode is one
    assert process.returncode == 1, f"Process ended with bad return code, got {process.returncode} (expected 1)"

    result = await client.list_versions(env_id)
    assert result.code == 200
    assert len(result.result["versions"]) == 0

    shutil.rmtree(workspace)


async def test_export_invalid_argument_combination() -> None:
    """
    Ensure that the `inmanta export` command exits with an error when resource sets are marked for deletion
    (either by the --delete-resource-set option or the INMANTA_REMOVED_SET_ID env variable) without the --partial
    option being provided.
    """
    args = [sys.executable, "-m", "inmanta.app", "export", "--delete-resource-set", "test"]
    process = await subprocess.create_subprocess_exec(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        (stdout, stderr) = await asyncio.wait_for(process.communicate(), timeout=5)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.communicate()
        raise e

    missing_partial_flag = (
        "A full export was requested but resource sets were marked for deletion (via the --delete-resource-set cli option "
        "or the INMANTA_REMOVED_SET_ID env variable). Deleting a resource set can only be performed during a partial export. "
        "To trigger a partial export, use the --partial option."
    )

    assert process.returncode == 1
    assert missing_partial_flag in stderr.decode("utf-8")

    args = [sys.executable, "-m", "inmanta.app", "export"]
    env = {INMANTA_REMOVED_SET_ID: "a b c"}
    process = await subprocess.create_subprocess_exec(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    try:
        (stdout, stderr) = await asyncio.wait_for(process.communicate(), timeout=5)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.communicate()
        raise e

    assert process.returncode == 1
    assert missing_partial_flag in stderr.decode("utf-8")


@pytest.mark.parametrize("set_keep_logger_names_option", [True, False])
async def test_logger_name_in_compiler_exporter_output(
    server,
    environment: str,
    tmpvenv_active_inherit: env.VirtualEnv,
    modules_dir: str,
    tmpdir,
    monkeypatch,
    set_keep_logger_names_option: bool,
) -> None:
    """
    This test case verifies that the logger name mentioned in the log of the compile/export command is correct. Namely:

    * compiler: For log lines produced by the compiler.
    * exporter: For log lines produced by the exporter.
    * <name-of-module>: For log lines produced by a specific module and the name of the logger was set to __name__.
    """
    v1_template_path: str = os.path.join(modules_dir, "minimalv1module")
    mod_name = "mymod"
    libs_dir = os.path.join(tmpdir, "libs")
    v1_module_from_template(
        source_dir=v1_template_path,
        dest_dir=os.path.join(libs_dir, mod_name),
        new_name=mod_name,
        new_content_init_cf="",
        new_content_init_py=textwrap.dedent(
            """
                from inmanta.plugins import plugin
                import logging

                LOGGER = logging.getLogger(__name__)

                @plugin
                def test_plugin():
                    LOGGER.info("test")
            """,
        ),
    )

    path_project_yml_file = tmpdir.join("project.yml")
    path_project_yml_file.write(
        textwrap.dedent(
            f"""
                name: testproject
                modulepath: {libs_dir}
                downloadpath: {libs_dir}
                repo: https://github.com/inmanta/
            """
        )
    )

    path_main_cf = tmpdir.join("main.cf")
    path_main_cf.write(
        textwrap.dedent(
            """
                import mymod
                mymod::test_plugin()
            """
        )
    )

    await install_project(python_env=tmpvenv_active_inherit, project_dir=tmpdir)

    # Compile command
    args = [
        tmpvenv_active_inherit.python_path,
        "-m",
        "inmanta.app",
        "-vvv",
        *(["--keep-logger-names"] if set_keep_logger_names_option else []),
        "compile",
    ]
    process = await subprocess.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, cwd=tmpdir
    )
    try:
        (stdout, _) = await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.communicate()
        raise e

    stdout = stdout.decode("utf-8")
    assert process.returncode == 0, f"Process ended with bad return code, got {process.returncode} (expected 0): {stdout}"
    if set_keep_logger_names_option:
        assert "inmanta.compiler         DEBUG   Starting compile" in stdout
        assert "inmanta_plugins.mymod    INFO    test" in stdout
    else:
        assert "compiler       DEBUG   Starting compile" in stdout
        assert "mymod          INFO    test" in stdout

    # Export command
    server_port = Config.get("client_rest_transport", "port")
    server_host = Config.get("client_rest_transport", "host", "localhost")
    args = [
        tmpvenv_active_inherit.python_path,
        "-m",
        "inmanta.app",
        "-vvv",
        *(["--keep-logger-names"] if set_keep_logger_names_option else []),
        "export",
    ]
    args.extend(["--server_port", str(server_port)])
    args.extend(["--server_address", str(server_host)])
    args.extend(["-e", environment])

    process = await subprocess.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, cwd=tmpdir
    )
    try:
        (stdout, _) = await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.communicate()
        raise e

    stdout = stdout.decode("utf-8")
    assert process.returncode == 0, f"Process ended with bad return code, got {process.returncode} (expected 0): {stdout}"
    if set_keep_logger_names_option:
        assert "inmanta.compiler         DEBUG   Starting compile" in stdout
        assert "inmanta_plugins.mymod    INFO    test" in stdout
        assert re.search("inmanta.export[ ]+INFO[ ]+Committed resources with version 1", stdout)
    else:
        assert re.search("^compiler[ ]*DEBUG[ ]+Starting compile", stdout, re.MULTILINE)
        assert "mymod          INFO    test" in stdout
        assert re.search("\nexporter[ ]+INFO[ ]+Committed resources with version 1", stdout)
