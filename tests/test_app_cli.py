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

import pytest
import os
import sys
import shutil

from inmanta.app import cmd_parser
from inmanta.config import Config
from inmanta.const import VersionState
from asyncio import subprocess
import asyncio


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


@pytest.mark.parametrize("push_method", [([]),
                                         (["-d"]),
                                         (["-d", "--full"])])
@pytest.mark.asyncio
async def test_export(tmpdir, server, client, push_method):
    server_port = Config.get("client_rest_transport", "port")
    server_host = Config.get("client_rest_transport", "host", "localhost")

    result = await client.create_project("test")
    assert result.code == 200
    proj_id = result.result['project']['id']
    result = await client.create_environment(proj_id, "test", None, None)
    assert result.code == 200
    env_id = result.result['environment']['id']

    workspace = tmpdir.mkdir("tmp")
    path_main_file = workspace.join("main.cf")
    path_project_yml_file = workspace.join("project.yml")
    libs_dir = workspace.join("libs")

    content_project_yml_file = """
name: testproject
modulepath: %s
downloadpath: %s
repo: https://github.com/inmanta/
""" % (libs_dir, libs_dir)
    path_project_yml_file.write(content_project_yml_file)

    content_main_file = """
import ip
import redhat
import redhat::epel
vm1=ip::Host(name="non-existing-machine", os=redhat::centos7, ip="127.0.0.1")
"""
    path_main_file.write(content_main_file)

    os.chdir(workspace)

    args = [sys.executable, "-m", "inmanta.app", "export", "-e", str(env_id), "--server_port", str(server_port),
            "--server_address", str(server_host)]
    args += push_method

    process = await subprocess.create_subprocess_exec(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.communicate()
        raise e

    # Make sure exitcode is zero
    assert process.returncode == 0

    result = await client.list_versions(env_id)
    assert result.code == 200
    assert len(result.result['versions']) == 1

    details_exported_version = result.result['versions'][0]
    if push_method:
        assert details_exported_version['result'] == VersionState.deploying.name
    else:
        assert details_exported_version['result'] == VersionState.pending.name

    shutil.rmtree(workspace)
