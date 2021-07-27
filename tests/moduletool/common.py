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
import tempfile
from subprocess import CalledProcessError
from typing import Optional

import yaml

from inmanta.config import Config
from inmanta.module import InstallMode
from inmanta.moduletool import ModuleTool


def makeproject(reporoot, name, deps=[], imports=None, install_mode: Optional[InstallMode] = None):
    return makemodule(reporoot, name, deps, project=True, imports=imports, install_mode=install_mode)


def makemodule(reporoot, name, deps=[], project=False, imports=None, install_mode: Optional[InstallMode] = None):
    path = os.path.join(reporoot, name)
    os.makedirs(path)
    mainfile = "module.yml"

    if project:
        mainfile = "project.yml"

    if imports is None:
        imports = [x[0] for x in deps]

    with open(os.path.join(path, mainfile), "w", encoding="utf-8") as projectfile:
        projectfile.write("name: " + name)
        projectfile.write("\nlicense: Apache 2.0")
        projectfile.write("\nversion: '0.0.1'")

        if project:
            projectfile.write(
                """
modulepath: libs
downloadpath: libs
repo: %s"""
                % reporoot
            )

        if install_mode is not None:
            projectfile.write("\ninstall_mode: %s" % install_mode.value)
        if len(deps) != 0:
            projectfile.write("\nrequires:")
            for req in deps:
                if req[1] is not None:
                    projectfile.write("\n    - {} {}".format(req[0], req[1]))

        projectfile.write("\n")

    model = os.path.join(path, "model")
    os.makedirs(model)

    if not project:
        with open(os.path.join(model, "_init.cf"), "w", encoding="utf-8") as projectfile:
            for i in imports:
                projectfile.write("import %s\n" % i)
    else:
        with open(os.path.join(path, "main.cf"), "w", encoding="utf-8") as projectfile:
            for i in imports:
                projectfile.write("import %s\n" % i)

    subprocess.check_output(["git", "init"], cwd=path, stderr=subprocess.STDOUT)
    subprocess.check_output(["git", "config", "user.email", '"test@test.example"'], cwd=path, stderr=subprocess.STDOUT)
    subprocess.check_output(["git", "config", "user.name", "Tester test"], cwd=path, stderr=subprocess.STDOUT)

    return path


def add_file(modpath, file, content, msg, version=None, dev=False, tag=True):
    with open(os.path.join(modpath, file), "w", encoding="utf-8") as projectfile:
        projectfile.write(content)

    if version is None:
        return commitmodule(modpath, msg)
    else:
        old_cwd = os.getcwd()
        os.chdir(modpath)
        subprocess.check_output(["git", "add", "*"], cwd=modpath, stderr=subprocess.STDOUT)
        ModuleTool().commit(msg, version=version, dev=dev, commit_all=True, tag=tag)
        os.chdir(old_cwd)


def add_file_and_compiler_constraint(modpath, file, content, msg, version, compiler_version):
    cfgfile = os.path.join(modpath, "module.yml")
    with open(cfgfile, "r", encoding="utf-8") as fd:
        cfg = yaml.safe_load(fd)

    cfg["compiler_version"] = compiler_version

    with open(cfgfile, "w", encoding="utf-8") as fd:
        yaml.dump(cfg, fd)
    add_file(modpath, file, content, msg, version)


def commitmodule(modpath, mesg):
    subprocess.check_output(["git", "add", "*"], cwd=modpath, stderr=subprocess.STDOUT)
    subprocess.check_output(["git", "commit", "-a", "-m", mesg], cwd=modpath, stderr=subprocess.STDOUT)
    rev = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=modpath, stderr=subprocess.STDOUT).decode("utf-8").strip()
    return rev


def startbranch(modpath, branch):
    subprocess.check_output(["git", "checkout", "-b", branch], cwd=modpath, stderr=subprocess.STDOUT)


def add_tag(modpath, tag):
    subprocess.check_output(["git", "tag", tag], cwd=modpath, stderr=subprocess.STDOUT)


def make_module_simple(reporoot, name, depends=[], version="3.2", project=False):
    mod = makemodule(reporoot, name, depends, project=project)
    commitmodule(mod, "first commit")
    if not project:
        add_file(mod, "signal", "present", "second commit", version=version)
    return mod


def make_module_simple_deps(reporoot, name, depends=[], project=False, version="3.2"):
    prefix = "project" if project else "mod"
    return make_module_simple(reporoot, prefix + name, [("mod" + x, None) for x in depends], project=project, version=version)


def install_project(modules_dir, name, config=True):
    subroot = tempfile.mkdtemp()
    coroot = os.path.join(subroot, name)
    subprocess.check_output(["git", "clone", os.path.join(modules_dir, "repos", name)], cwd=subroot, stderr=subprocess.STDOUT)
    os.chdir(coroot)
    if config:
        Config.load_config()
    return coroot


def clone_repo(source_dir, repo_name, destination_dir):
    subprocess.check_output(
        ["git", "clone", os.path.join(source_dir, repo_name)], cwd=destination_dir, stderr=subprocess.STDOUT
    )
    subprocess.check_output(
        ["git", "config", "user.email", '"test@test.example"'],
        cwd=os.path.join(destination_dir, repo_name),
        stderr=subprocess.STDOUT,
    )
    subprocess.check_output(
        ["git", "config", "user.name", "Tester test"], cwd=os.path.join(destination_dir, repo_name), stderr=subprocess.STDOUT
    )


class BadModProvider(object):
    def __init__(self, parent, badname):
        self.parent = parent
        self.badname = badname

    def __getattr__(self, method_name):
        def delegator(*args, **kw):
            if args[0] == self.badname:
                raise CalledProcessError(128, "XX")
            return getattr(self.parent, method_name)(*args, **kw)

        return delegator
