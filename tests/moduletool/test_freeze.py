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
import shutil
import subprocess
import sys

import pytest

from inmanta.ast import CompilerException
from inmanta.command import CLIException
from inmanta.moduletool import ModuleTool
from moduletool.common import install_project
from test_app_cli import app


@pytest.mark.slowtest
def test_freeze_basic(git_modules_dir: str, modules_repo: str, tmpdir):
    install_project(git_modules_dir, "projectA", tmpdir)
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


@pytest.mark.slowtest
def test_project_freeze_basic(git_modules_dir: str, modules_repo: str, tmpdir):
    install_project(git_modules_dir, "projectA", tmpdir)
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


@pytest.mark.slowtest
def test_project_freeze_bad(git_modules_dir: str, modules_repo: str, tmpdir):
    coroot = install_project(git_modules_dir, "baddep", tmpdir, config=False)

    with pytest.raises(CompilerException) as e:
        app(["project", "freeze"])

    assert "requirement mod2<2016 on module mod2 not fulfilled, now at version 2016.1" in str(e.value)

    assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0


@pytest.mark.slowtest
def test_project_freeze(git_modules_dir: str, modules_repo: str, capsys, tmpdir):
    coroot = install_project(git_modules_dir, "projectA", tmpdir)

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


@pytest.mark.slowtest
def test_project_freeze_disk(git_modules_dir: str, modules_repo: str, capsys, tmpdir):
    coroot = install_project(git_modules_dir, "projectA", tmpdir)

    app(["project", "freeze"])

    out, err = capsys.readouterr()

    assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
    assert len(err) == 0, err

    with open(os.path.join(coroot, "project.yml"), encoding="utf-8") as fh:
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


@pytest.mark.slowtest
def test_project_freeze_odd_opperator(git_modules_dir: str, modules_repo: str, tmpdir):
    coroot = install_project(git_modules_dir, "projectA", tmpdir)

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


@pytest.mark.slowtest
def test_project_options_in_config(git_modules_dir: str, modules_repo: str, capsys, tmpdir):
    coroot = install_project(
        git_modules_dir,
        "projectA",
        tmpdir,
        config_content=f"""
name: projectA
license: Apache 2.0
version: 0.0.1
modulepath: libs
downloadpath: libs
repo: {modules_repo}
freeze_recursive: true
freeze_operator: ==
        """.strip(),
    )

    def verify():
        out, err = capsys.readouterr()

        assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
        assert len(err) == 0, err
        assert len(out) == 0, out

        with open("project.yml", encoding="utf-8") as fh:
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


@pytest.mark.slowtest
def test_module_freeze(git_modules_dir: str, modules_repo: str, capsys, tmpdir):
    coroot = install_project(git_modules_dir, "projectA", tmpdir)

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


@pytest.mark.slowtest
def test_module_freeze_self_disk(git_modules_dir: str, modules_repo: str, capsys, tmpdir):
    coroot = install_project(git_modules_dir, "projectA", tmpdir)

    def verify():
        out, err = capsys.readouterr()

        assert len(err) == 0, err
        assert len(out) == 0, out

        modpath = os.path.join(coroot, "libs/modC/module.yml")
        assert os.path.getsize(os.path.join(coroot, "project.yml")) != 0
        assert os.path.getsize(modpath) != 0

        with open(modpath, encoding="utf-8") as fh:
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
    app(["project", "install"])
    os.chdir(modp)
    app(["module", "freeze"])
    verify()


@pytest.mark.parametrize("use_min_m_option", [True, False])
def test_module_freeze_on_v2_module(tmpdir, monkeypatch, use_min_m_option: bool) -> None:
    """
    Verify that an appropriate error message is returned when the `inmanta module freeze` command is executed on a V2 module.
    """
    v2_mod_path_original = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "modules_v2", "minimalv2module")
    v2_mod_path = os.path.join(tmpdir, "minimalv2module")
    shutil.copytree(v2_mod_path_original, v2_mod_path)

    if use_min_m_option:
        cmd = ["module", "-m", v2_mod_path, "freeze"]
    else:
        cmd = ["module", "freeze"]
        monkeypatch.chdir(v2_mod_path)

    with pytest.raises(CLIException) as exc_info:
        app(cmd)

    assert "The `inmanta module freeze` command is not supported on V2 modules. Use the `pip freeze` command instead." in str(
        exc_info.value
    )
    assert exc_info.value.exitcode == 1
