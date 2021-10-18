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

import pytest

from inmanta import module
from inmanta.ast import CompilerException, ModuleNotFoundException
from inmanta.config import Config
from inmanta.moduletool import ModuleTool
from moduletool.common import BadModProvider, install_project


def test_bad_checkout(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "badproject")
    subprocess.check_output(
        ["git", "clone", os.path.join(modules_dir, "repos", "badproject")], cwd=modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    with pytest.raises(ModuleNotFoundException):
        ModuleTool().execute("install", [])


def test_bad_setup(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "badprojectx")
    subprocess.check_output(
        ["git", "clone", os.path.join(modules_dir, "repos", "badproject"), coroot], cwd=modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    mod1 = os.path.join(coroot, "libs", "mod1")
    os.makedirs(mod1)
    subprocess.check_output(
        ["git", "clone", os.path.join(modules_dir, "repos", "mod2"), mod1], cwd=modules_dir, stderr=subprocess.STDOUT
    )

    with pytest.raises(ModuleNotFoundException):
        ModuleTool().execute("verify", [])


def test_complex_checkout(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "testproject")
    subprocess.check_output(
        ["git", "clone", os.path.join(modules_dir, "repos", "testproject")], cwd=modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    ModuleTool().execute("install", [])
    expected = ["mod1", "mod2", "mod3", "mod6", "mod7"]
    for i in expected:
        dirname = os.path.join(coroot, "libs", i)
        assert os.path.exists(os.path.join(dirname, "signal"))
        assert not os.path.exists(os.path.join(dirname, "badsignal"))

    assert not os.path.exists(os.path.join(coroot, "libs", "mod5"))

    # test all tools, perhaps isolate to other test case
    ModuleTool().execute("list", [])
    ModuleTool().execute("update", [])
    ModuleTool().execute("status", [])
    ModuleTool().execute("push", [])


def test_for_git_failures(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "testproject2")
    subprocess.check_output(
        ["git", "clone", os.path.join(modules_dir, "repos", "testproject"), "testproject2"],
        cwd=modules_dir,
        stderr=subprocess.STDOUT,
    )
    os.chdir(coroot)
    Config.load_config()

    ModuleTool().execute("install", [])

    gp = module.gitprovider
    module.gitprovider = BadModProvider(gp, os.path.join(coroot, "libs", "mod6"))
    try:
        # test all tools, perhaps isolate to other test case
        ModuleTool().execute("install", [])
        ModuleTool().execute("list", [])
        ModuleTool().execute("update", [])
        ModuleTool().execute("status", [])
        ModuleTool().execute("push", [])
    finally:
        module.gitprovider = gp


def test_install_for_git_failures(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "testproject3")
    subprocess.check_output(
        ["git", "clone", os.path.join(modules_dir, "repos", "testproject"), "testproject3"],
        cwd=modules_dir,
        stderr=subprocess.STDOUT,
    )
    os.chdir(coroot)
    Config.load_config()

    gp = module.gitprovider
    module.gitprovider = BadModProvider(gp, os.path.join(coroot, "libs", "mod6"))
    try:
        with pytest.raises(ModuleNotFoundException):
            ModuleTool().execute("install", [])
    finally:
        module.gitprovider = gp


def test_for_repo_without_versions(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "noverproject")
    subprocess.check_output(
        ["git", "clone", os.path.join(modules_dir, "repos", "noverproject")], cwd=modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    ModuleTool().execute("install", [])


def test_bad_dep_checkout(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "baddep")
    subprocess.check_output(
        ["git", "clone", os.path.join(modules_dir, "repos", "baddep")], cwd=modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    with pytest.raises(CompilerException):
        ModuleTool().execute("install", [])


def test_master_checkout(modules_dir, modules_repo):
    coroot = install_project(modules_dir, "masterproject")

    ModuleTool().execute("install", [])

    dirname = os.path.join(coroot, "libs", "mod8")
    assert os.path.exists(os.path.join(dirname, "devsignal"))
    assert os.path.exists(os.path.join(dirname, "mastersignal"))


def test_dev_checkout(modules_dir, modules_repo):
    coroot = os.path.join(modules_dir, "devproject")
    subprocess.check_output(
        ["git", "clone", os.path.join(modules_dir, "repos", "devproject")], cwd=modules_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    Config.load_config()

    ModuleTool().execute("install", [])

    dirname = os.path.join(coroot, "libs", "mod8")
    assert os.path.exists(os.path.join(dirname, "devsignal"))
    assert not os.path.exists(os.path.join(dirname, "mastersignal"))
