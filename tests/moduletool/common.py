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
import configparser
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from subprocess import CalledProcessError
from typing import Optional, Sequence, Union

import yaml
from pkg_resources import Requirement

from inmanta import const, module
from inmanta.config import Config
from inmanta.module import InstallMode
from inmanta.moduletool import ModuleTool
from libpip2pi.commands import dir2pi
from packaging import version


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


@dataclass
class PipIndex:
    """
    Local pip index that makes use of dir2pi to publish its artifacts.
    """

    artifact_dir: str

    @property
    def url(self) -> str:
        return f"{self.artifact_dir}/simple"

    def publish(self) -> None:
        dir2pi(argv=["dir2pi", self.artifact_dir])


def module_from_template(
    source_dir: str,
    dest_dir: str,
    *,
    new_version: Optional[version.Version] = None,
    new_name: Optional[str] = None,
    new_requirements: Optional[Sequence[Union[module.InmantaModuleRequirement, Requirement]]] = None,
    install: bool = False,
    editable: bool = False,
    publish_index: Optional[PipIndex] = None,
    new_content_init_cf: Optional[str] = None,
) -> module.ModuleV2Metadata:
    """
    Creates a v2 module from a template.

    :param source_dir: The directory where the original module lives.
    :param dest_dir: The directory to use to copy the original to and to stage any changes in.
    :param new_version: The new version for the module, if any.
    :param new_name: The new name of the inmanta module, if any.
    :param new_requirements: The new requirements for the module, if any.
    :param install: Install the newly created module with the module tool. Requires virtualenv to be installed in the
        python environment unless editable is True.
    :param editable: Whether to install the module in editable mode, ignored if install is False.
    :param publish_index: Publish to the given local path index. Requires virtualenv to be installed in the python environment.
    :param new_content_init_cf: The new content of the _init.cf file.
    """
    # preinstall older version of module
    shutil.copytree(source_dir, dest_dir)
    config_file: str = os.path.join(dest_dir, module.ModuleV2.MODULE_FILE)
    config: configparser.ConfigParser = configparser.ConfigParser()
    config.read(config_file)
    if new_version is not None:
        config["metadata"]["version"] = str(new_version)
        if new_version.is_devrelease:
            config["egg_info"] = {"tag_build": f".dev{new_version.dev}"}
    if new_name is not None:
        os.rename(
            os.path.join(
                dest_dir, const.PLUGINS_PACKAGE, module.ModuleV2Source.get_inmanta_module_name(config["metadata"]["name"])
            ),
            os.path.join(dest_dir, const.PLUGINS_PACKAGE, new_name),
        )
        config["metadata"]["name"] = module.ModuleV2Source.get_python_package_name(new_name)
    if new_requirements:
        config["options"]["install_requires"] = "\n    ".join(
            str(req if isinstance(req, Requirement) else module.ModuleV2Source.get_python_package_requirement(req))
            for req in new_requirements
        )
    if new_content_init_cf is not None:
        init_cf_file = os.path.join(dest_dir, "model", "_init.cf")
        with open(init_cf_file, "w", encoding="utf-8") as fd:
            fd.write(new_content_init_cf)
    with open(config_file, "w") as fh:
        config.write(fh)
    if install:
        ModuleTool().install(editable=editable, path=dest_dir)
    if publish_index is not None:
        ModuleTool().build(path=dest_dir, output_dir=publish_index.artifact_dir)
        publish_index.publish()
    with open(config_file, "r") as fh:
        return module.ModuleV2Metadata.parse(fh)
