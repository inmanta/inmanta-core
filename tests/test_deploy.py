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
import collections
import os
import subprocess
import sys

import pytest
from tornado import process

from inmanta import deploy


def test_deploy(snippetcompiler, tmpdir, postgres_db):
    file_name = tmpdir.join("test_file")
    # TODO: when agentconfig deploys no longer require an agent restart, define a new agent. Currently this makes the
    # test to slow.
    snippetcompiler.setup_for_snippet(
        """
    host = std::Host(name="internal", os=std::linux)
    file = std::Symlink(host=host, source="/dev/null", target="%s")
    """
        % file_name
    )

    os.chdir(snippetcompiler.project_dir)
    Options = collections.namedtuple("Options", ["dryrun", "dashboard"])
    options = Options(dryrun=False, dashboard=False)

    assert not file_name.exists()

    run = deploy.Deploy(options, postgresport=postgres_db.port)
    try:
        if not run.setup():
            raise Exception("Failed to setup server")
        run.run()
    finally:
        run.stop()

    assert file_name.exists()


@pytest.mark.slowtest
def test_deploy_with_non_default_config(snippetcompiler, tmpdir) -> None:
    """
    Ensure that configuration options set in one of the inmanta configuration
    files cannot make the `inmanta deploy` fail.
    """
    file_name = tmpdir.join("test_file")
    snippetcompiler.setup_for_snippet(
        """
    host = std::Host(name="internal", os=std::linux)
    file = std::Symlink(host=host, source="/dev/null", target="%s")
    """
        % file_name
    )

    path_dot_inmanta_file = os.path.join(snippetcompiler.project_dir, ".inmanta")
    with open(path_dot_inmanta_file, "w") as fh:
        fh.write(
            """
[database]
name=non-default-username
host=non-default-value
port=9999
username=non-default-value
password=non-default-value

[server]
bind-port=7777
bind-address=192.168.100.100
        """
        )

    assert not file_name.exists()
    subprocess.check_call([sys.executable, "-m", "inmanta.app", "deploy"], cwd=snippetcompiler.project_dir)
    assert file_name.exists()


async def test_fork(server):
    """
    This test should not fail. Some Subprocess'es can make the ioloop hang, this tests fails when that happens.
    """
    i = 0
    while i < 5:
        i += 1
        sub_process = process.Subprocess(["true"])
        await sub_process.wait_for_exit(raise_error=False)


@pytest.mark.timeout(30)
def test_embedded_inmanta_server(tmpdir, postgres_db):
    """Test starting an embedded server"""
    project_dir = tmpdir.mkdir("project")
    os.chdir(project_dir)
    main_cf_file = project_dir.join("main.cf")
    project_yml_file = project_dir.join("project.yml")
    with open(project_yml_file, "w", encoding="utf-8") as f:
        f.write("name: test\n")
        f.write("modulepath: " + str(project_dir.join("libs")) + "\n")
        f.write("downloadpath: " + str(project_dir.join("libs")) + "\n")
        f.write("repo: https://github.com/inmanta/\n")
        f.write("description: Test\n")
    with open(main_cf_file, "w", encoding="utf-8") as f:
        f.write("")

    Options = collections.namedtuple("Options", ["dryrun", "dashboard"])
    options = Options(dryrun=False, dashboard=False)
    depl = deploy.Deploy(options, postgresport=postgres_db.port)
    assert depl.setup()
    depl.stop()
