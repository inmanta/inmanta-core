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
from subprocess import CalledProcessError
from typing import Optional

import yaml

import ruamel.yaml
from inmanta.config import Config
from inmanta.module import InstallMode, Project
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
repo: %s
"""
                % reporoot
            )

        if install_mode is not None:
            projectfile.write("\ninstall_mode: %s" % install_mode.value)
        if len(deps) != 0:
            projectfile.write("\nrequires:")
            for req in deps:
                if req[1] is not None:
                    projectfile.write(f"\n    - {req[0]} {req[1]}")

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


def add_requires(
    modpath: str, deps: list[tuple[str, str]], commit_msg: str, version: str, dev: bool = False, tag: bool = True
) -> None:
    """
    Add the version requirements of dependencies in a module's YAML file and adds the import to the .cf file.
    Performs a git commit and tags the commit with the specified version.

    :param modpath: The path to the module.
    :param deps: A list of tuples, each containing a dependency name and its corresponding version specification.
    :param commit_msg: The commit message to use
    :param version: The version to tag the commit with
    :param dev: A flag indicating whether this is a development version. Default is False.
    :param tag: A flag indicating whether to tag the commit. Default is True.
    """
    mainfile = "module.yml"
    file_path = os.path.join(modpath, mainfile)
    yaml = ruamel.yaml.YAML()

    with open(file_path) as file:
        data = yaml.load(file)

    # Ensure 'requires' field exists and is a list
    if "requires" not in data:
        data["requires"] = []

    # Prepare a dictionary to hold the latest version requirement for each module
    requires_dict = {item.strip().split()[0]: item for item in data["requires"]}

    # Update the dictionary with the new version requirements
    for module, version_spec in deps:
        requires_dict[module] = f"{module} {version_spec}"

    # Convert the dictionary back to a list
    data["requires"] = list(requires_dict.values())

    # Write the updated data back to the file
    with open(file_path, "w") as file:
        yaml.dump(data, file)

    model = os.path.join(modpath, "model")

    init_file_path = os.path.join(model, "_init.cf")
    with open(init_file_path, encoding="utf-8") as projectfile:
        existing_content = projectfile.read()

    import_statements = "\n".join(f"import {module}" for module, _ in deps)
    updated_content = f"{import_statements}\n{existing_content}"

    with open(init_file_path, "w", encoding="utf-8") as projectfile:
        projectfile.write(updated_content)

    old_cwd = os.getcwd()
    os.chdir(modpath)
    subprocess.check_output(["git", "add", "*"], cwd=modpath, stderr=subprocess.STDOUT)
    ModuleTool().commit(commit_msg, version=version, dev=dev, commit_all=True, tag=tag)
    os.chdir(old_cwd)


def add_file_and_compiler_constraint(modpath, file, content, msg, version, compiler_version):
    cfgfile = os.path.join(modpath, "module.yml")
    with open(cfgfile, encoding="utf-8") as fd:
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


def install_project(modules_dir: str, name: str, working_dir: str, config=True, config_content: Optional[str] = None):
    """
    Copy the project with `name` in `modules_dir` to the given `working_dir` and install it without verifying it.
    This method changes the current working directory to the root of the project copied into the working_dir,
    as such that the ModuleTool() can be used to act on it.

    :param modules_dir: Should match the value of the git_modules_dir fixture.
    :param name: The name of the project present in the repos subdirectory of the modules_dir directory.
    :param working_dir: The directory where the project will be copied.
    :param config: Whether to reload the configuration store.
    :param config_content: If provided, override the project.yml file with this content.
    """
    coroot = os.path.join(working_dir, name)
    subprocess.check_output(
        ["git", "clone", os.path.join(modules_dir, "repos", name)], cwd=working_dir, stderr=subprocess.STDOUT
    )
    os.chdir(coroot)
    if config_content:
        with open("project.yml", "w", encoding="utf-8") as fh:
            fh.write(config_content)
    if config:
        Config.load_config()
    Project.get().load_module_recursive(install=True)
    return coroot


def clone_repo(source_dir: str, repo_name: str, destination_dir: str, tag: Optional[str] = None) -> str:
    """
    :param tag: Clone commit with the given tag.
    """
    additional_clone_args = ["-b", tag] if tag is not None else []
    subprocess.check_output(
        ["git", "clone", *additional_clone_args, os.path.join(source_dir, repo_name)],
        cwd=destination_dir,
        stderr=subprocess.STDOUT,
    )
    subprocess.check_output(
        ["git", "config", "user.email", '"test@test.example"'],
        cwd=os.path.join(destination_dir, repo_name),
        stderr=subprocess.STDOUT,
    )
    subprocess.check_output(
        ["git", "config", "user.name", "Tester test"], cwd=os.path.join(destination_dir, repo_name), stderr=subprocess.STDOUT
    )
    return os.path.join(destination_dir, repo_name)


class BadModProvider:
    def __init__(self, parent, badname):
        self.parent = parent
        self.badname = badname

    def __getattr__(self, method_name):
        def delegator(*args, **kw):
            if args[0] == self.badname:
                raise CalledProcessError(128, "XX")
            return getattr(self.parent, method_name)(*args, **kw)

        return delegator
