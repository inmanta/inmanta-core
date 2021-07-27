"""
    Copyright 2017 Inmanta

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
import sys

import pytest

from inmanta.command import CLIException
from inmanta.moduletool import ModuleTool
from moduletool.common import install_project
from test_app_cli import app


def test_freeze_basic(modules_dir, modules_repo):
    install_project(modules_dir, "projectA")
    modtool = ModuleTool()
    cmod = modtool.get_module("modC")
    assert cmod.get_freeze("modC", recursive=False, mode="==") == {"std": "== 3.2", "modE": "== 3.2", "modF": "== 3.2"}
    assert cmod.get_freeze("modC", recursive=True, mode="==") == {
        "std": "== 3.2",
        "modE": "== 3.2",
        "modF": "== 3.2",
        "modH": "== 3.2",
        "modJ": "== 3.2",
    }

    assert cmod.get_freeze("modC::a", recursive=False, mode="==") == {"std": "== 3.2", "modI": "== 3.2"}


def test_project_freeze_basic(modules_dir, modules_repo):
    install_project(modules_dir, "projectA")
    modtool = ModuleTool()
    proj = modtool.get_project()
    assert proj.get_freeze(recursive=False, mode="==") == {
        "std": "== 3.2",
        "modB": "== 3.2",
        "modC": "== 3.2",
        "modD": "== 3.2",
    }
    assert proj.get_freeze(recursive=True, mode="==") == {
        "std": "== 3.2",
        "modB": "== 3.2",
        "modC": "== 3.2",
        "modD": "== 3.2",
        "modE": "== 3.2",
        "modF": "== 3.2",
        "modG": "== 3.2",
        "modH": "== 3.2",
        "modJ": "== 3.2",
    }


def test_project_freeze_bad(modules_dir, modules_repo, capsys, caplog):
    coroot = install_project(modules_dir, "baddep", config=False)

    with pytest.raises(CLIException) as e:
        app(["project", "freeze"])

    assert e.value.exitcode == 1
    assert str(e.value) == "Could not load project"

    out, err = capsys.readouterr()

    assert len(err) == 0, err
    assert len(out) == 0, out
    assert "requirement mod2<2016 on module mod2 not fullfilled, now at version 2016.1" in caplog.text

    assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0


def test_project_freeze(modules_dir, modules_repo, capsys):
    coroot = install_project(modules_dir, "projectA")

    app(["project", "freeze", "-o", "-"])

    out, err = capsys.readouterr()

    assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
    assert len(err) == 0, err
    assert (
        out
        == """name: projectA
license: Apache 2.0
version: 0.0.1
modulepath: libs
downloadpath: libs
repo: %s
requires:
- modB ~= 3.2
- modC ~= 3.2
- modD ~= 3.2
- std ~= 3.2
"""
        % modules_repo
    )


def test_project_freeze_disk(modules_dir, modules_repo, capsys):
    coroot = install_project(modules_dir, "projectA")

    app(["project", "freeze"])

    out, err = capsys.readouterr()

    assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
    assert len(err) == 0, err

    with open(os.path.join(coroot, "project.yml"), "r", encoding="utf-8") as fh:
        assert (
            fh.read()
            == """name: projectA
license: Apache 2.0
version: 0.0.1
modulepath: libs
downloadpath: libs
repo: %s
requires:
- modB ~= 3.2
- modC ~= 3.2
- modD ~= 3.2
- std ~= 3.2
"""
            % modules_repo
        )


def test_project_freeze_odd_opperator(modules_dir, modules_repo):
    coroot = install_project(modules_dir, "projectA")

    # Start a new subprocess, because inmanta-cli executes sys.exit() when an invalid argument is used.
    process = subprocess.Popen(
        [sys.executable, "-m", "inmanta.app", "project", "freeze", "-o", "-", "--operator", "xxx"],
        encoding="utf-8",
        cwd=coroot,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = process.communicate()

    assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0

    assert process.returncode != 0
    assert "argument --operator: invalid choice: 'xxx'" in err


def test_project_options_in_config(modules_dir, modules_repo, capsys):
    coroot = install_project(modules_dir, "projectA")
    with open("project.yml", "w", encoding="utf-8") as fh:
        fh.write(
            """name: projectA
license: Apache 2.0
version: 0.0.1
modulepath: libs
downloadpath: libs
repo: %s
freeze_recursive: true
freeze_operator: ==
"""
            % modules_repo
        )

    def verify():
        out, err = capsys.readouterr()

        assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
        assert len(err) == 0, err
        assert len(out) == 0, out

        with open("project.yml", "r", encoding="utf-8") as fh:
            assert fh.read() == (
                """name: projectA
license: Apache 2.0
version: 0.0.1
modulepath: libs
downloadpath: libs
repo: %s
freeze_recursive: true
freeze_operator: ==
requires:
- modB == 3.2
- modC == 3.2
- modD == 3.2
- modE == 3.2
- modF == 3.2
- modG == 3.2
- modH == 3.2
- modJ == 3.2
- std == 3.2
"""
                % modules_repo
            )

    app(["project", "freeze"])
    verify()
    app(["project", "freeze"])
    verify()


def test_module_freeze(modules_dir, modules_repo, capsys):
    coroot = install_project(modules_dir, "projectA")

    def verify():
        out, err = capsys.readouterr()

        assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
        assert len(err) == 0, err
        assert out == (
            """name: modC
license: Apache 2.0
version: '3.2'
requires:
- modE ~= 3.2
- modF ~= 3.2
- modI ~= 3.2
- std ~= 3.2
"""
        )

    app(["module", "-m", "modC", "freeze", "-o", "-"])
    verify()


def test_module_freeze_self_disk(modules_dir, modules_repo, capsys):
    coroot = install_project(modules_dir, "projectA")

    def verify():
        out, err = capsys.readouterr()

        assert len(err) == 0, err
        assert len(out) == 0, out

        modpath = os.path.join(coroot, "libs/modC/module.yml")
        assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
        assert os.path.getsize(modpath) != 0

        with open(modpath, "r", encoding="utf-8") as fh:
            outf = fh.read()
            assert outf == (
                """name: modC
license: Apache 2.0
version: '3.2'
requires:
- modE ~= 3.2
- modF ~= 3.2
- modI ~= 3.2
- std ~= 3.2
"""
            )

    modp = os.path.join(coroot, "libs/modC")
    app(["module", "install"])
    os.chdir(modp)
    app(["module", "freeze"])
    verify()
