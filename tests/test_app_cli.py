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
import shutil
import sys
from asyncio import subprocess

import pytest

from inmanta.app import cmd_parser, compiler_features
from inmanta.command import ShowUsageException
from inmanta.compiler.config import feature_compiler_cache
from inmanta.config import Config
from inmanta.const import VersionState


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
    assert "update" in out


def test_feature_flags(inmanta_config, capsys):
    with pytest.raises(SystemExit):
        app(["help", "compile"])
    out, _ = capsys.readouterr()

    assert out.startswith("usage:")
    assert "--experimental-cache" in out

    parser = cmd_parser()

    assert not feature_compiler_cache.get()

    options, other = parser.parse_known_args(args=["compile", "--experimental-cache"])
    compiler_features.read_options_to_config(options)

    assert feature_compiler_cache.get()


def test_module_help(inmanta_config, capsys):
    with pytest.raises(ShowUsageException) as info:
        app(["module"])

    assert info.value.args[0].startswith("A subcommand is required.")


@pytest.mark.asyncio
@pytest.mark.parametrize("add_types", [True, False])
async def test_export_to_json(tmpdir, add_types):
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
vm1=std::Host(name="non-existing-machine", os=std::linux)
std::ConfigFile(host=vm1, path="/test", content="")
"""
    )

    os.chdir(workspace)

    args = [sys.executable, "-m", "inmanta.app", "export", "-j", "dump.json"]
    if add_types:
        args.append("--model-export")

    process = await subprocess.create_subprocess_exec(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.communicate()
        raise e

    # Make sure exitcode is zero
    assert process.returncode == 0

    assert os.path.exists("dump.json")
    assert add_types == os.path.exists("dump.json.types")


@pytest.mark.parametrize("push_method", [([]), (["-d"]), (["-d", "--full"])])
@pytest.mark.parametrize("set_server", [True, False])
@pytest.mark.parametrize("set_port", [True, False])
@pytest.mark.asyncio
async def test_export(tmpdir, server, client, push_method, set_server, set_port):
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
    path_config_file = workspace.join(".inmanta")
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
vm1=std::Host(name="non-existing-machine", os=std::linux)
std::ConfigFile(host=vm1, path="/test", content="")
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

    details_exported_version = result.result["versions"][0]

    assert details_exported_version["result"] == VersionState.deploying.name

    shutil.rmtree(workspace)


@pytest.mark.asyncio
async def test_export_with_specific_export_plugin(tmpdir, client):
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

    os.chdir(workspace)

    args = [
        sys.executable,
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


@pytest.mark.parametrize("push_method", [([]), (["-d"]), (["-d", "--full"])])
@pytest.mark.asyncio
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
vm1=std::Host(name="non-existing-machine", os=std::linux)
std::ConfigFile(host=vm1, path="/test", content="")
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
