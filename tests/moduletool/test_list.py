"""
    Copyright 2023 Inmanta

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
import os
import subprocess

from inmanta.module import Project
from inmanta.moduletool import ModuleTool
from moduletool.common import install_project


def test_module_list_bugfixes(modules_dir: str, modules_repo: str, tmpdir, capsys):
    """
    This test case verifies whether the following bugs in the `inmanta modules list` command, were fixed correctly:

    * Verify that the `inmanta modules list` command correctly reports whether the installed version matches
      the relevant version constraints.
    * Verify that the version numbers, reported by the `inmanta modules list` command, are correctly formatted.
    """
    coroot = install_project(modules_dir, "project_with_underscored_dep_name", tmpdir)

    os.chdir(coroot)
    ModuleTool().execute("install", [])

    def assert_modules_list_output(output: str, installed_version: str, expected_version: str, match: bool) -> None:
        lines_about_mod_a = [line for line in output.split("\n") if "mod_a" in line]
        assert len(lines_about_mod_a) == 1
        splitted_line = lines_about_mod_a[0].split("|")
        assert splitted_line[2].strip() == installed_version
        assert splitted_line[3].strip() == expected_version
        assert splitted_line[4].strip() == "1" if match else "0"

    ModuleTool().execute("list", [])
    # Version 3.2 of mod_a was checked out by the `inmanta module install` command, so the versions match
    assert_modules_list_output(output=capsys.readouterr().out, installed_version="3.2", expected_version="3.2", match=True)

    # Install a version that is incompatible
    subprocess.check_call(["git", "checkout", "4.0.0"], cwd=os.path.join(coroot, "libs", "mod_a"))
    # Reset modules cache
    Project._project = None
    ModuleTool().execute("list", [])
    assert_modules_list_output(output=capsys.readouterr().out, installed_version="4.0.0", expected_version="3.2", match=False)
